import uuid
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any

import bcrypt
import jwt

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError
from app.core.time import now_utc

PASSWORD_MAX_BYTES = 72  # bcrypt limit


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def _encode(payload: dict[str, Any]) -> str:
    settings = get_settings()
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_access_token(*, user_id: int, role: str) -> tuple[str, int]:
    """Returns (token, expires_in_seconds)."""
    settings = get_settings()
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    issued_at = now_utc()
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": TokenType.ACCESS.value,
        "iat": issued_at,
        "exp": issued_at + expires_delta,
        "jti": uuid.uuid4().hex,
    }
    return _encode(payload), int(expires_delta.total_seconds())


def create_refresh_token(*, user_id: int, role: str) -> tuple[str, str, datetime]:
    """Returns (token, jti, expires_at). The jti is persisted so the token can be revoked."""
    settings = get_settings()
    issued_at = now_utc()
    expires_at = issued_at + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    jti = uuid.uuid4().hex
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": TokenType.REFRESH.value,
        "iat": issued_at,
        "exp": expires_at,
        "jti": jti,
    }
    return _encode(payload), jti, expires_at


def decode_token(token: str, *, expected_type: TokenType, verify_exp: bool = True) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_exp": verify_exp, "require": ["sub", "type", "exp", "jti"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("Token has expired", code="token_expired") from exc
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError("Invalid token", code="invalid_token") from exc

    if payload.get("type") != expected_type.value:
        raise UnauthorizedError("Invalid token type", code="invalid_token")
    return payload
