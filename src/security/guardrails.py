from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from threading import Lock
from time import monotonic
import re
import unicodedata

from src.core.config import Settings, settings
from src.utils.logger import get_logger


logger = get_logger(__name__)


class GuardrailViolation(ValueError):
    """Se lanza cuando una consulta infringe una regla del backend."""

    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class ValidatedQuery:
    """Consulta normalizada que supero los guardrails de entrada."""

    original_query: str
    sanitized_query: str


@dataclass(frozen=True)
class GuardrailRule:
    """Regla declarativa para filtrar requests de bajo costo."""

    rule_id: str
    category: str
    pattern: str
    severity: str = "high"
    action: str = "block"


@dataclass(frozen=True)
class GuardrailDecision:
    """Resultado estructurado devuelto por la capa de guardrails."""

    allowed: bool
    sanitized_query: str
    reason_code: str | None = None
    matched_rule_id: str | None = None
    severity: str | None = None
    status_code: int = 200
    message: str | None = None


@dataclass(frozen=True)
class GuardrailEvent:
    """Instantanea amigable para logs de una evaluacion de guardrails."""

    identity: str
    query_preview: str
    decision: GuardrailDecision


class QueryInputGuardrails:
    """Validacion barata de entrada y deteccion basica de prompt injection."""

    _CONTROL_CHARS_PATTERN = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")

    def __init__(
        self,
        *,
        min_length: int,
        max_length: int,
        prompt_injection_patterns: tuple[str, ...],
    ) -> None:
        self._min_length = min_length
        self._max_length = max_length
        self._rules = tuple(
            GuardrailRule(
                rule_id=f"prompt_injection_{index + 1}",
                category="prompt_injection",
                pattern=self._normalize_text(pattern),
            )
            for index, pattern in enumerate(prompt_injection_patterns)
            if pattern.strip()
        )

    @classmethod
    def from_settings(
        cls,
        app_settings: Settings = settings,
    ) -> "QueryInputGuardrails":
        return cls(
            min_length=app_settings.QUERY_MIN_LENGTH,
            max_length=app_settings.QUERY_MAX_LENGTH,
            prompt_injection_patterns=app_settings.QUERY_PROMPT_INJECTION_PATTERNS,
        )

    def validate(self, query: str) -> ValidatedQuery:
        decision = self.evaluate(query)
        if not decision.allowed:
            raise GuardrailViolation(
                decision.message or "La consulta fue rechazada por los guardrails de seguridad.",
                status_code=decision.status_code,
            )
        return ValidatedQuery(
            original_query=query,
            sanitized_query=decision.sanitized_query,
        )

    def evaluate(self, query: str) -> GuardrailDecision:
        sanitized_query = self._sanitize(query)
        query_length = len(sanitized_query)

        if not sanitized_query:
            return GuardrailDecision(
                allowed=False,
                sanitized_query=sanitized_query,
                reason_code="empty_query",
                severity="medium",
                status_code=400,
                message="La consulta no debe estar vacia ni contener solo espacios.",
            )

        if query_length < self._min_length:
            return GuardrailDecision(
                allowed=False,
                sanitized_query=sanitized_query,
                reason_code="query_too_short",
                severity="low",
                status_code=400,
                message=f"La consulta debe contener al menos {self._min_length} caracteres.",
            )

        if query_length > self._max_length:
            return GuardrailDecision(
                allowed=False,
                sanitized_query=sanitized_query,
                reason_code="query_too_long",
                severity="low",
                status_code=400,
                message=f"La consulta no debe exceder {self._max_length} caracteres.",
            )

        matched_rule = self._match_prompt_injection(sanitized_query)
        if matched_rule is not None:
            logger.warning(
                "Patron de prompt injection detectado. rule_id=%s pattern=%s query_preview=%s",
                matched_rule.rule_id,
                matched_rule.pattern,
                sanitized_query[:120],
            )
            return GuardrailDecision(
                allowed=False,
                sanitized_query=sanitized_query,
                reason_code=matched_rule.category,
                matched_rule_id=matched_rule.rule_id,
                severity=matched_rule.severity,
                status_code=400,
                message=(
                    "La consulta fue rechazada por los guardrails de seguridad "
                    "debido a indicadores de prompt injection."
                ),
            )

        return GuardrailDecision(
            allowed=True,
            sanitized_query=sanitized_query,
        )

    @classmethod
    def _sanitize(cls, query: str) -> str:
        without_controls = cls._CONTROL_CHARS_PATTERN.sub(" ", query)
        collapsed_whitespace = re.sub(r"\s+", " ", without_controls)
        return collapsed_whitespace.strip()

    def _match_prompt_injection(self, query: str) -> GuardrailRule | None:
        normalized_query = self._normalize_text(query)
        for rule in self._rules:
            if rule.pattern in normalized_query:
                return rule
        return None

    @staticmethod
    def _normalize_text(value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value)
        ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
        return re.sub(r"\s+", " ", ascii_only).strip().lower()


class QueryRateLimiter:
    """Rate limiter simple en memoria con ventana deslizante para /query."""

    def __init__(
        self,
        *,
        max_requests: int,
        window_seconds: int,
        clock: callable | None = None,
    ) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._clock = clock or monotonic
        self._events: dict[str, deque[float]] = {}
        self._lock = Lock()

    @classmethod
    def from_settings(
        cls,
        app_settings: Settings = settings,
    ) -> "QueryRateLimiter":
        return cls(
            max_requests=app_settings.QUERY_RATE_LIMIT_REQUESTS,
            window_seconds=app_settings.QUERY_RATE_LIMIT_WINDOW_SECONDS,
        )

    def check(self, identity: str) -> None:
        decision = self.evaluate(identity)
        if not decision.allowed:
            raise GuardrailViolation(
                decision.message
                or "Se excedio el limite de solicitudes para /query. Intenta nuevamente mas tarde.",
                status_code=decision.status_code,
            )

    def evaluate(self, identity: str) -> GuardrailDecision:
        if self._max_requests <= 0 or self._window_seconds <= 0:
            return GuardrailDecision(
                allowed=True,
                sanitized_query="",
            )

        now = float(self._clock())
        window_start = now - self._window_seconds

        with self._lock:
            bucket = self._events.setdefault(identity, deque())
            while bucket and bucket[0] <= window_start:
                bucket.popleft()

            if len(bucket) >= self._max_requests:
                logger.warning(
                    "Limite de solicitudes excedido. identity=%s max_requests=%s window_seconds=%s",
                    identity,
                    self._max_requests,
                    self._window_seconds,
                )
                return GuardrailDecision(
                    allowed=False,
                    sanitized_query="",
                    reason_code="rate_limit_exceeded",
                    severity="medium",
                    status_code=429,
                    message=(
                        "Se excedio el limite de solicitudes para /query. "
                        "Intenta nuevamente mas tarde."
                    ),
                )

            bucket.append(now)
        return GuardrailDecision(
            allowed=True,
            sanitized_query="",
        )

    def reset(self) -> None:
        with self._lock:
            self._events.clear()


class GuardrailService:
    """Compone validacion de entrada y rate limiting tras una API estable."""

    def __init__(
        self,
        *,
        input_guardrails: QueryInputGuardrails,
        rate_limiter: QueryRateLimiter,
    ) -> None:
        self._input_guardrails = input_guardrails
        self._rate_limiter = rate_limiter

    @classmethod
    def from_settings(cls, app_settings: Settings = settings) -> "GuardrailService":
        return cls(
            input_guardrails=QueryInputGuardrails.from_settings(app_settings),
            rate_limiter=QueryRateLimiter.from_settings(app_settings),
        )

    def protect_query(self, *, query: str, identity: str) -> ValidatedQuery:
        input_decision = self._input_guardrails.evaluate(query)
        self._log_event(
            GuardrailEvent(
                identity=identity,
                query_preview=input_decision.sanitized_query[:120],
                decision=input_decision,
            )
        )
        if not input_decision.allowed:
            raise GuardrailViolation(
                input_decision.message or "La consulta fue rechazada por los guardrails de seguridad.",
                status_code=input_decision.status_code,
            )

        rate_decision = self._rate_limiter.evaluate(identity)
        self._log_event(
            GuardrailEvent(
                identity=identity,
                query_preview=input_decision.sanitized_query[:120],
                decision=rate_decision,
            )
        )
        if not rate_decision.allowed:
            raise GuardrailViolation(
                rate_decision.message
                or "Se excedio el limite de solicitudes para /query. Intenta nuevamente mas tarde.",
                status_code=rate_decision.status_code,
            )

        return ValidatedQuery(
            original_query=query,
            sanitized_query=input_decision.sanitized_query,
        )

    @staticmethod
    def _log_event(event: GuardrailEvent) -> None:
        if event.decision.allowed:
            logger.debug(
                "Guardrail permitio la solicitud. identity=%s query_preview=%s",
                event.identity,
                event.query_preview,
            )
            return

        logger.warning(
            (
                "Guardrail bloqueo la solicitud. identity=%s reason_code=%s "
                "matched_rule_id=%s severity=%s query_preview=%s"
            ),
            event.identity,
            event.decision.reason_code,
            event.decision.matched_rule_id,
            event.decision.severity,
            event.query_preview,
        )
