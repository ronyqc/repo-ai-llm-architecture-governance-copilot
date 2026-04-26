from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.error import URLError

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import (
    ExpiredSignatureError,
    ImmatureSignatureError,
    InvalidAudienceError,
    InvalidIssuerError,
    InvalidTokenError,
    MissingRequiredClaimError,
    PyJWKClient,
)

from src.core.config import settings
from src.utils.logger import get_logger


security = HTTPBearer(auto_error=False)
logger = get_logger(__name__)


@dataclass
class AuthenticatedUser:
    user_id: str
    roles: list[str]
    claims: dict[str, Any]


def _ensure_auth_is_configured() -> None:
    required_values = {
        "AZURE_TENANT_ID": settings.AZURE_TENANT_ID,
        "AZURE_API_AUDIENCE": settings.AZURE_API_AUDIENCE,
        "AZURE_JWKS_URL": settings.azure_jwks_url,
    }
    missing = [name for name, value in required_values.items() if not value]
    if missing:
        logger.error(
            "JWT auth misconfigured. Missing settings: %s",
            ", ".join(sorted(missing)),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Authentication settings are incomplete: "
                + ", ".join(sorted(missing))
            ),
        )


def _get_signing_key(token: str) -> Any:
    try:
        header = jwt.get_unverified_header(token)
    except InvalidTokenError:
        logger.warning("JWT rejected before JWKS lookup: malformed token header.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token.",
        ) from None

    logger.info(
        "Resolving signing key from JWKS. kid=%s jwks_url=%s",
        header.get("kid"),
        settings.azure_jwks_url,
    )

    try:
        jwk_client = PyJWKClient(settings.azure_jwks_url)
        signing_key = jwk_client.get_signing_key_from_jwt(token)
        return signing_key.key
    except (InvalidTokenError, URLError, json.JSONDecodeError, Exception) as exc:
        logger.warning(
            "JWT signing key resolution failed. kid=%s error=%s",
            header.get("kid"),
            str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token.",
        ) from None


def _extract_roles(claims: dict[str, Any]) -> list[str]:
    raw_roles = claims.get("roles", [])
    if isinstance(raw_roles, list):
        return [str(role) for role in raw_roles]
    if isinstance(raw_roles, str) and raw_roles.strip():
        return [raw_roles.strip()]
    return []


def _extract_scopes(claims: dict[str, Any]) -> list[str]:
    raw_scopes = claims.get("scp", "")
    if isinstance(raw_scopes, str) and raw_scopes.strip():
        return raw_scopes.split()
    return []


def _decode_token(token: str) -> dict[str, Any]:
    _ensure_auth_is_configured()
    signing_key = _get_signing_key(token)
    unverified_claims = jwt.decode(
        token,
        options={"verify_signature": False},
        algorithms=["RS256"],
    )

    logger.info(
        (
            "Validating JWT. oid=%s sub=%s aud=%s iss=%s "
            "expected_aud=%s expected_issuers=%s"
        ),
        unverified_claims.get("oid"),
        unverified_claims.get("sub"),
        unverified_claims.get("aud"),
        unverified_claims.get("iss"),
        settings.AZURE_API_AUDIENCE,
        settings.azure_issuers,
    )

    token_issuer = unverified_claims.get("iss")
    if token_issuer not in settings.azure_issuers:
        logger.warning(
            "JWT rejected: invalid issuer. token_iss=%s expected_issuers=%s",
            token_issuer,
            settings.azure_issuers,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token.",
        )

    try:
        return jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=settings.AZURE_API_AUDIENCE,
            options={
                "require": ["exp", "iat", "iss", "aud"],
                "verify_iss": False,
            },
        )
    except InvalidAudienceError as exc:
        logger.warning(
            "JWT rejected: invalid audience. token_aud=%s expected_aud=%s error=%s",
            unverified_claims.get("aud"),
            settings.AZURE_API_AUDIENCE,
            str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token.",
        ) from None
    except InvalidIssuerError as exc:
        logger.warning(
            "JWT rejected: invalid issuer. token_iss=%s expected_issuers=%s error=%s",
            unverified_claims.get("iss"),
            settings.azure_issuers,
            str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token.",
        ) from None
    except ExpiredSignatureError:
        logger.warning("JWT rejected: token expired.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token.",
        ) from None
    except ImmatureSignatureError:
        logger.warning("JWT rejected: token not yet valid.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token.",
        ) from None
    except MissingRequiredClaimError as exc:
        logger.warning("JWT rejected: missing required claim %s.", exc.claim)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token.",
        ) from None
    except InvalidTokenError as exc:
        logger.warning("JWT rejected: generic invalid token error=%s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token.",
        ) from None


def _build_authenticated_user(claims: dict[str, Any]) -> AuthenticatedUser:
    user_id = claims.get("oid") or claims.get("sub")
    if not isinstance(user_id, str) or not user_id.strip():
        logger.warning("JWT rejected: token missing oid/sub user identifier.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token does not include a supported user identifier.",
        )

    roles = _extract_roles(claims)
    scopes = _extract_scopes(claims)

    enriched_claims = dict(claims)
    enriched_claims["scp"] = scopes

    return AuthenticatedUser(
        user_id=user_id,
        roles=roles,
        claims=enriched_claims,
    )


def require_authenticated_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> AuthenticatedUser:
    if credentials is None or not credentials.credentials:
        logger.warning("Request rejected: missing Authorization bearer token.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization token is required.",
        )

    claims = _decode_token(credentials.credentials)
    user = _build_authenticated_user(claims)
    logger.info(
        "JWT accepted. user_id=%s roles=%s scopes=%s",
        user.user_id,
        user.roles,
        user.claims.get("scp", []),
    )
    return user


def require_admin_user(
    user: AuthenticatedUser = Depends(require_authenticated_user),
) -> AuthenticatedUser:
    return _ensure_admin_access(user)


def require_ingest_user(
    user: AuthenticatedUser = Depends(require_authenticated_user),
) -> AuthenticatedUser:
    if not settings.REQUIRE_ADMIN_FOR_INGEST:
        return user

    return _ensure_admin_access(user)


def _ensure_admin_access(user: AuthenticatedUser) -> AuthenticatedUser:
    normalized_roles = {role.lower() for role in user.roles}
    normalized_admin_roles = {
        role.lower()
        for role in settings.INGEST_ADMIN_ROLES
        if role.strip()
    }
    normalized_scopes = {
        scope.lower()
        for scope in user.claims.get("scp", [])
        if isinstance(scope, str) and scope.strip()
    }
    normalized_admin_scopes = {
        scope.lower()
        for scope in settings.INGEST_ADMIN_SCOPES
        if scope.strip()
    }

    has_admin_role = bool(normalized_roles & normalized_admin_roles)
    has_admin_scope = bool(normalized_scopes & normalized_admin_scopes)
    if not has_admin_role and not has_admin_scope:
        logger.warning(
            "Request rejected: admin role or scope required. user_id=%s roles=%s scopes=%s",
            user.user_id,
            user.roles,
            user.claims.get("scp", []),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role or scope is required for this operation.",
        )

    return user
