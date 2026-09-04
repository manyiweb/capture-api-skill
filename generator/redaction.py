"""Shared rules for removing credentials from generated test artifacts."""

from __future__ import annotations

import re
from typing import Any, Optional


_LOGIN_PATH_PATTERN = re.compile(r"(?:login|loginaction|sign.?in|auth|session)", re.I)
_USERNAME_FIELDS = {"email", "username", "user_name", "account"}
_PASSWORD_SUFFIXES = ("password", "passwd", "pwd")
_SECRET_SUFFIXES = (
    "access_token",
    "refresh_token",
    "id_token",
    "auth_token",
    "session_token",
    "csrf_token",
    "api_token",
    "api_key",
    "auth_key",
    "secret_key",
    "private_key",
    "session_id",
    "authorization",
    "cookie",
    "credential",
    "credentials",
    "secret",
    "token",
)
_LOGIN_ONLY_FIELDS = {
    "key",
    "auth_key",
    "captcha",
    "captcha_token",
    "verification_code",
    "verify_code",
    "otp",
    "code",
}
_SENSITIVE_HEADERS = {
    "authorization",
    "proxy_authorization",
    "cookie",
    "x_api_key",
    "api_key",
}


def _normalize(value: str) -> str:
    separated = re.sub(r"[^a-zA-Z0-9]+", "_", str(value))
    snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", separated).lower()
    return re.sub(r"_+", "_", snake).strip("_")


def _safe_config_name(value: str, fallback: str = "sensitive_value") -> str:
    normalized = _normalize(value)
    if not normalized:
        return fallback
    if normalized[0].isdigit():
        return f"field_{normalized}"
    return normalized


def is_login_request(path: str) -> bool:
    return bool(_LOGIN_PATH_PATTERN.search(path or ""))


def sensitive_field_config_name(
    field_name: str,
    path: str,
    value: Any = None,
) -> Optional[str]:
    """Return the config key to use instead of a captured field value."""
    normalized = _normalize(field_name)
    login_request = is_login_request(path)

    if normalized.endswith(_PASSWORD_SUFFIXES):
        return "login_password" if login_request else _safe_config_name(field_name)
    if normalized.endswith(_SECRET_SUFFIXES):
        prefix = "login_request_" if login_request else ""
        return f"{prefix}{_safe_config_name(field_name)}"
    if login_request and normalized in _USERNAME_FIELDS:
        return f"login_{_safe_config_name(field_name)}"
    if login_request and normalized in _LOGIN_ONLY_FIELDS:
        return f"login_request_{_safe_config_name(field_name)}"

    # A bare `key` is ambiguous outside authentication endpoints. Treat it as
    # sensitive only when it resembles a credential rather than a short enum.
    if normalized == "key" and isinstance(value, str) and len(value) >= 20:
        return _safe_config_name(field_name)
    return None


def is_sensitive_header(header_name: str) -> bool:
    normalized = _normalize(header_name)
    return (
        normalized in _SENSITIVE_HEADERS
        or normalized.endswith(_SECRET_SUFFIXES)
        or normalized.endswith("_authorization")
        or normalized.endswith("_cookie")
    )


def sensitive_header_config_name(header_name: str) -> str:
    normalized = _normalize(header_name)
    if normalized.endswith("authorization"):
        return "auth_token"
    if normalized.endswith("cookie"):
        return "session_cookie"
    if normalized.endswith("api_key"):
        return "api_key"
    return _safe_config_name(header_name)
