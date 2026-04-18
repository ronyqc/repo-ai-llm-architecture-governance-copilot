from __future__ import annotations

import base64
from dataclasses import dataclass
import json
from html.parser import HTMLParser
from typing import Any, Protocol
from urllib import error, parse, request

from src.core.config import Settings, settings
from src.utils.logger import get_logger


logger = get_logger(__name__)


class ConfluenceConfigurationError(ValueError):
    """Raised when Confluence Cloud settings are incomplete or invalid."""


class ConfluenceError(RuntimeError):
    """Raised when Confluence runtime access fails."""


@dataclass(frozen=True)
class ConfluenceSearchRequest:
    """Stable request contract for bounded Confluence runtime search."""

    query: str
    space_key: str | None = None
    top_k: int | None = None


@dataclass(frozen=True)
class ConfluencePage:
    """Normalized Confluence page returned to the orchestrator."""

    page_id: str
    title: str
    content: str
    url: str
    space_key: str | None
    score: float


class ConfluenceClient(Protocol):
    """Abstraction for Confluence runtime search and fetch."""

    def search(self, request: ConfluenceSearchRequest) -> list[ConfluencePage]:
        """Return a bounded list of normalized pages relevant to the query."""


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self._parts.append(data.strip())

    def get_text(self) -> str:
        return " ".join(self._parts)


class ConfluenceCloudClient:
    """Small Confluence Cloud client using bounded CQL search plus page fetch."""

    def __init__(
        self,
        *,
        base_url: str,
        email: str,
        api_token: str,
        default_space_key: str | None,
        default_top_k: int,
        opener: Any | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._email = email.strip()
        self._api_token = api_token.strip()
        self._default_space_key = (default_space_key or "").strip() or None
        self._default_top_k = default_top_k
        self._validate_configuration()
        self._opener = opener or request.build_opener()
        auth_value = f"{self._email}:{self._api_token}".encode("utf-8")
        self._auth_header = "Basic " + base64.b64encode(auth_value).decode("ascii")

    @classmethod
    def from_settings(
        cls,
        app_settings: Settings = settings,
    ) -> "ConfluenceCloudClient":
        return cls(
            base_url=app_settings.CONFLUENCE_BASE_URL,
            email=app_settings.CONFLUENCE_EMAIL,
            api_token=app_settings.CONFLUENCE_API_TOKEN,
            default_space_key=app_settings.CONFLUENCE_DEFAULT_SPACE_KEY,
            default_top_k=app_settings.CONFLUENCE_SEARCH_TOP_K,
        )

    def search(self, request: ConfluenceSearchRequest) -> list[ConfluencePage]:
        top_k = request.top_k or self._default_top_k
        if top_k <= 0:
            raise ValueError("Confluence search top_k must be greater than zero.")

        cql = self._build_cql(
            query=request.query,
            space_key=request.space_key or self._default_space_key,
        )
        logger.info(
            "Confluence search started. base_url=%s query=%s space_key=%s top_k=%s cql=%s",
            self._base_url,
            _preview_text(request.query),
            request.space_key or self._default_space_key,
            top_k,
            cql,
        )
        search_payload = self._request_json(
            f"/wiki/rest/api/search?{parse.urlencode({'cql': cql, 'limit': top_k})}"
        )
        raw_results = search_payload.get("results", [])
        logger.info(
            "Confluence search payload received. results=%s",
            len(raw_results) if isinstance(raw_results, list) else 0,
        )

        pages: list[ConfluencePage] = []
        for index, item in enumerate(raw_results[:top_k], start=1):
            content = item.get("content") or {}
            page_id = str(content.get("id") or "").strip()
            title = str(content.get("title") or "").strip()
            if not page_id or not title:
                logger.warning(
                    "Confluence search result skipped due to missing id/title. index=%s raw_content=%s",
                    index,
                    content,
                )
                continue

            body_payload = self._request_json(
                f"/wiki/rest/api/content/{page_id}"
                "?expand=body.storage,space,_links"
            )
            normalized = self._normalize_page(body_payload, fallback_title=title, rank=index)
            if normalized.content:
                pages.append(normalized)
                logger.info(
                    "Confluence page normalized. page_id=%s title=%s score=%s space_key=%s content_chars=%s",
                    normalized.page_id,
                    normalized.title,
                    normalized.score,
                    normalized.space_key,
                    len(normalized.content),
                )
            else:
                logger.warning(
                    "Confluence page normalized without content. page_id=%s title=%s",
                    normalized.page_id,
                    normalized.title,
                )

        logger.info("Confluence search completed. pages=%s", len(pages))
        return pages

    def check_health(self, timeout_seconds: float) -> None:
        if self._default_space_key:
            encoded_space = parse.quote(self._default_space_key, safe="")
            self._request_json(
                f"/wiki/rest/api/space/{encoded_space}",
                timeout_seconds=timeout_seconds,
            )
            return

        self._request_json(
            "/wiki/rest/api/space?limit=1",
            timeout_seconds=timeout_seconds,
        )

    def _build_cql(self, *, query: str, space_key: str | None) -> str:
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("Confluence query must be a non-empty string.")

        escaped_query = normalized_query.replace('"', '\\"')
        clauses = ['type = page', f'text ~ "{escaped_query}"']
        if space_key:
            clauses.append(f'space = "{space_key}"')
        return " AND ".join(clauses) + " ORDER BY lastmodified DESC"

    def _request_json(
        self,
        path: str,
        *,
        timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        logger.info("Confluence request. url=%s", url)
        req = request.Request(
            url,
            headers={
                "Accept": "application/json",
                "Authorization": self._auth_header,
            },
        )
        try:
            if timeout_seconds is None:
                response_context = self._opener.open(req)
            else:
                response_context = self._opener.open(req, timeout=timeout_seconds)
            with response_context as response:
                raw = response.read().decode("utf-8")
        except error.HTTPError as exc:
            logger.error("Confluence HTTP error. url=%s status=%s", url, exc.code)
            raise ConfluenceError(
                f"Confluence request failed with status {exc.code}."
            ) from exc
        except error.URLError as exc:
            logger.error("Confluence URL error. url=%s reason=%s", url, exc.reason)
            raise ConfluenceError("Confluence request failed.") from exc

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ConfluenceError("Confluence returned invalid JSON.") from exc
        if not isinstance(payload, dict):
            raise ConfluenceError("Confluence returned an unexpected payload.")
        return payload

    def _normalize_page(
        self,
        payload: dict[str, Any],
        *,
        fallback_title: str,
        rank: int,
    ) -> ConfluencePage:
        page_id = str(payload.get("id") or "").strip()
        title = str(payload.get("title") or fallback_title).strip()
        body = (((payload.get("body") or {}).get("storage") or {}).get("value") or "")
        content = self._html_to_text(str(body)).strip()
        content = " ".join(content.split())
        if len(content) > 4000:
            content = content[:4000].rstrip() + "..."

        links = payload.get("_links") or {}
        webui = str(links.get("webui") or "").strip()
        base = str(links.get("base") or "").strip() or self._base_url
        url = f"{base}{webui}" if webui else f"{self._base_url}/wiki/pages/viewpage.action?pageId={page_id}"
        space = payload.get("space") or {}
        space_key = str(space.get("key") or "").strip() or None

        # Confluence search API does not expose a stable relevance score here.
        score = max(0.0, 1.0 - ((rank - 1) * 0.1))

        return ConfluencePage(
            page_id=page_id,
            title=title or page_id,
            content=content,
            url=url,
            space_key=space_key,
            score=score,
        )

    @staticmethod
    def _html_to_text(html: str) -> str:
        parser = _HTMLTextExtractor()
        parser.feed(html)
        return parser.get_text()

    def _validate_configuration(self) -> None:
        missing = []
        if not self._base_url:
            missing.append("CONFLUENCE_BASE_URL")
        if not self._email:
            missing.append("CONFLUENCE_EMAIL")
        if not self._api_token:
            missing.append("CONFLUENCE_API_TOKEN")
        if self._default_top_k <= 0:
            raise ConfluenceConfigurationError(
                "CONFLUENCE_SEARCH_TOP_K must be greater than zero."
            )
        if missing:
            raise ConfluenceConfigurationError(
                "Missing Confluence configuration: " + ", ".join(sorted(missing))
            )


def _preview_text(value: str, limit: int = 120) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."
