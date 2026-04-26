from __future__ import annotations

from dataclasses import dataclass
import unittest
from unittest.mock import Mock, patch

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jwt import ExpiredSignatureError, InvalidTokenError

from src.security import auth
from src.security.auth import AuthenticatedUser


@dataclass(frozen=True)
class _FakeSettings:
    AZURE_TENANT_ID: str = "tenant-123"
    AZURE_API_AUDIENCE: str = "api://agc"
    AZURE_JWKS_URL: str = "https://login.microsoftonline.com/tenant-123/discovery/v2.0/keys"
    REQUIRE_ADMIN_FOR_INGEST: bool = True
    INGEST_ADMIN_ROLES: tuple[str, ...] = ("admin", "arch-admin")
    INGEST_ADMIN_SCOPES: tuple[str, ...] = ("copilot.ingest",)

    @property
    def azure_jwks_url(self) -> str:
        return self.AZURE_JWKS_URL

    @property
    def azure_issuers(self) -> tuple[str, ...]:
        return (
            "https://login.microsoftonline.com/tenant-123/v2.0",
            "https://sts.windows.net/tenant-123/",
        )


class AuthHelpersTests(unittest.TestCase):
    def test_extract_roles_supports_list_and_string(self) -> None:
        self.assertEqual(auth._extract_roles({"roles": ["Admin", "Reader"]}), ["Admin", "Reader"])
        self.assertEqual(auth._extract_roles({"roles": "Admin"}), ["Admin"])
        self.assertEqual(auth._extract_roles({"roles": 123}), [])

    def test_extract_scopes_splits_space_delimited_claim(self) -> None:
        self.assertEqual(
            auth._extract_scopes({"scp": "copilot.query copilot.ingest"}),
            ["copilot.query", "copilot.ingest"],
        )
        self.assertEqual(auth._extract_scopes({"scp": ""}), [])

    def test_build_authenticated_user_requires_oid_or_sub(self) -> None:
        with self.assertRaises(HTTPException) as context:
            auth._build_authenticated_user({"roles": ["admin"]})

        self.assertEqual(context.exception.status_code, 403)

    def test_build_authenticated_user_enriches_scope_claims(self) -> None:
        user = auth._build_authenticated_user(
            {"oid": "user-123", "roles": "Admin", "scp": "copilot.query copilot.ingest"}
        )

        self.assertEqual(user.user_id, "user-123")
        self.assertEqual(user.roles, ["Admin"])
        self.assertEqual(user.claims["scp"], ["copilot.query", "copilot.ingest"])


class AuthDependenciesTests(unittest.TestCase):
    def test_require_authenticated_user_rejects_missing_credentials(self) -> None:
        with self.assertRaises(HTTPException) as context:
            auth.require_authenticated_user(None)

        self.assertEqual(context.exception.status_code, 401)
        self.assertEqual(context.exception.detail, "Authorization token is required.")

    def test_require_authenticated_user_decodes_token_and_returns_user(self) -> None:
        fake_user = AuthenticatedUser(user_id="user-1", roles=["reader"], claims={"scp": []})
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token-123")

        with patch.object(auth, "_decode_token", return_value={"oid": "user-1", "roles": ["reader"]}) as decode_token:
            with patch.object(auth, "_build_authenticated_user", return_value=fake_user) as build_user:
                result = auth.require_authenticated_user(credentials)

        self.assertIs(result, fake_user)
        decode_token.assert_called_once_with("token-123")
        build_user.assert_called_once()

    def test_require_ingest_user_allows_non_admin_when_setting_disabled(self) -> None:
        user = AuthenticatedUser(user_id="user-1", roles=["reader"], claims={"scp": []})

        with patch.object(auth, "settings", _FakeSettings(REQUIRE_ADMIN_FOR_INGEST=False)):
            result = auth.require_ingest_user(user)

        self.assertIs(result, user)

    def test_ensure_admin_access_accepts_matching_role_or_scope(self) -> None:
        with patch.object(auth, "settings", _FakeSettings()):
            by_role = auth._ensure_admin_access(
                AuthenticatedUser(user_id="role-user", roles=["Admin"], claims={"scp": []})
            )
            by_scope = auth._ensure_admin_access(
                AuthenticatedUser(
                    user_id="scope-user",
                    roles=["reader"],
                    claims={"scp": ["copilot.ingest"]},
                )
            )

        self.assertEqual(by_role.user_id, "role-user")
        self.assertEqual(by_scope.user_id, "scope-user")

    def test_ensure_admin_access_rejects_user_without_admin_role_or_scope(self) -> None:
        with patch.object(auth, "settings", _FakeSettings()):
            with self.assertRaises(HTTPException) as context:
                auth._ensure_admin_access(
                    AuthenticatedUser(
                        user_id="reader-1",
                        roles=["reader"],
                        claims={"scp": ["copilot.query"]},
                    )
                )

        self.assertEqual(context.exception.status_code, 403)


class AuthTokenValidationTests(unittest.TestCase):
    def test_get_signing_key_rejects_malformed_header(self) -> None:
        with patch.object(auth.jwt, "get_unverified_header", side_effect=InvalidTokenError("bad header")):
            with self.assertRaises(HTTPException) as context:
                auth._get_signing_key("bad-token")

        self.assertEqual(context.exception.status_code, 401)
        self.assertEqual(context.exception.detail, "Invalid bearer token.")

    def test_decode_token_rejects_invalid_issuer_before_signature_validation(self) -> None:
        fake_settings = _FakeSettings()

        with patch.object(auth, "settings", fake_settings):
            with patch.object(auth, "_get_signing_key", return_value="signing-key"):
                with patch.object(
                    auth.jwt,
                    "decode",
                    side_effect=[
                        {
                            "oid": "user-1",
                            "aud": fake_settings.AZURE_API_AUDIENCE,
                            "iss": "https://issuer.invalid/v2.0",
                            "sub": "user-1",
                        }
                    ],
                ):
                    with self.assertRaises(HTTPException) as context:
                        auth._decode_token("token-123")

        self.assertEqual(context.exception.status_code, 401)

    def test_decode_token_maps_expired_signature_to_401(self) -> None:
        fake_settings = _FakeSettings()

        with patch.object(auth, "settings", fake_settings):
            with patch.object(auth, "_get_signing_key", return_value="signing-key"):
                with patch.object(
                    auth.jwt,
                    "decode",
                    side_effect=[
                        {
                            "oid": "user-1",
                            "aud": fake_settings.AZURE_API_AUDIENCE,
                            "iss": fake_settings.azure_issuers[0],
                            "sub": "user-1",
                        },
                        ExpiredSignatureError("expired"),
                    ],
                ):
                    with self.assertRaises(HTTPException) as context:
                        auth._decode_token("token-123")

        self.assertEqual(context.exception.status_code, 401)
        self.assertEqual(context.exception.detail, "Invalid bearer token.")

    def test_get_signing_key_resolves_jwks_key(self) -> None:
        fake_signing_key = Mock()
        fake_signing_key.key = "resolved-key"
        fake_jwk_client = Mock()
        fake_jwk_client.get_signing_key_from_jwt.return_value = fake_signing_key

        with patch.object(auth, "settings", _FakeSettings()):
            with patch.object(auth.jwt, "get_unverified_header", return_value={"kid": "kid-123"}):
                with patch.object(auth, "PyJWKClient", return_value=fake_jwk_client) as jwk_client_cls:
                    result = auth._get_signing_key("token-123")

        self.assertEqual(result, "resolved-key")
        jwk_client_cls.assert_called_once_with(_FakeSettings().azure_jwks_url)


if __name__ == "__main__":
    unittest.main()
