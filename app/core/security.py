from datetime import UTC, datetime, timedelta
from secrets import choice
from typing import Any

import bcrypt
from jose import jwt

from app.core.config import settings

_BCRYPT_MAX_PASSWORD_BYTES = 72
_TEMP_PASSWORD_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"


def _password_to_bytes(password: str) -> bytes:
    return password.encode("utf-8")


def _password_is_bcrypt_compatible(password: str) -> bool:
    return len(_password_to_bytes(password)) <= _BCRYPT_MAX_PASSWORD_BYTES


def hash_password(password: str) -> str:
    if not _password_is_bcrypt_compatible(password):
        raise ValueError("Password cannot be longer than 72 bytes.")
    return bcrypt.hashpw(_password_to_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    if not _password_is_bcrypt_compatible(password):
        return False

    try:
        return bcrypt.checkpw(_password_to_bytes(password), _password_to_bytes(password_hash))
    except ValueError:
        return False


def create_access_token(subject: str, expires_delta_minutes: int | None = None) -> str:
    expiry_minutes = expires_delta_minutes or settings.access_token_expiry_minutes
    expire = datetime.now(UTC) + timedelta(minutes=expiry_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )


def generate_temporary_password(length: int = 12) -> str:
    return "".join(choice(_TEMP_PASSWORD_ALPHABET) for _ in range(length))
