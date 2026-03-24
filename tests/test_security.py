import pytest

from app.core.security import create_access_token, decode_access_token
from app.core.security import hash_password, verify_password


def test_access_token_round_trip():
    token = create_access_token("42")
    payload = decode_access_token(token)

    assert payload["sub"] == "42"
    assert "exp" in payload


def test_password_hash_round_trip():
    password = "CorrectHorseBatteryStaple!"
    password_hash = hash_password(password)

    assert verify_password(password, password_hash) is True
    assert verify_password("wrong-password", password_hash) is False


def test_long_password_is_rejected_gracefully():
    long_password = "a" * 73

    with pytest.raises(ValueError, match="72 bytes"):
        hash_password(long_password)

    assert verify_password(long_password, "$2b$12$invalidhash") is False
