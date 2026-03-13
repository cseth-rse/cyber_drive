# tests/test_auth.py
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from passlib.context import CryptContext

from app.auth.service import AuthService, _hash
from app.models import Role, User

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def make_user(**kwargs) -> User:
    defaults = dict(
        id="user-uuid",
        email="test@example.com",
        role=Role.STUDENT,
        otp=None,
        otp_expiry=None,
        refresh_token=None,
    )
    defaults.update(kwargs)
    u = User.__new__(User)
    for k, v in defaults.items():
        setattr(u, k, v)
    return u


def make_svc(db=None, settings=None, email_svc=None):
    db = db or MagicMock()
    if settings is None:
        settings = MagicMock()
        settings.jwt_secret = "test-secret-16chars"
        settings.jwt_refresh_secret = "refresh-secret-16"
        settings.jwt_expires_minutes = 15
        settings.jwt_refresh_expires_days = 7
    email_svc = email_svc or AsyncMock()
    return AuthService(db, settings, email_svc)


# ── register ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_creates_user_when_not_exists():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    new_user = make_user()
    db.add = MagicMock()
    db.commit = MagicMock()
    db.refresh = MagicMock(side_effect=lambda u: None)

    email_svc = AsyncMock()
    svc = make_svc(db=db, email_svc=email_svc)

    # Patch user creation
    with patch("app.auth.service.User", return_value=new_user):
        result = await svc.register("test@example.com")

    assert result["message"] == "OTP sent to your email address"
    email_svc.send_otp.assert_awaited_once()


@pytest.mark.asyncio
async def test_register_reuses_existing_user():
    existing = make_user()
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = existing
    email_svc = AsyncMock()
    svc = make_svc(db=db, email_svc=email_svc)

    result = await svc.register("test@example.com")

    db.add.assert_not_called()
    assert "message" in result


# ── verify_otp ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_verify_otp_user_not_found():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    svc = make_svc(db=db)

    with pytest.raises(HTTPException) as exc_info:
        await svc.verify_otp("nobody@example.com", "123456")
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_verify_otp_no_otp_set():
    user = make_user(otp=None)
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = user
    svc = make_svc(db=db)

    with pytest.raises(HTTPException) as exc_info:
        await svc.verify_otp("test@example.com", "123456")
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_verify_otp_expired():
    user = make_user(otp=_hash("123456"), otp_expiry=datetime.utcnow() - timedelta(minutes=1))
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = user
    svc = make_svc(db=db)

    with pytest.raises(HTTPException) as exc_info:
        await svc.verify_otp("test@example.com", "123456")
    assert exc_info.value.status_code == 400
    assert "expired" in str(exc_info.value.detail).lower()


@pytest.mark.asyncio
async def test_verify_otp_wrong_code():
    user = make_user(otp=_hash("654321"), otp_expiry=datetime.utcnow() + timedelta(minutes=5))
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = user
    svc = make_svc(db=db)

    with pytest.raises(HTTPException) as exc_info:
        await svc.verify_otp("test@example.com", "000000")
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_verify_otp_success():
    otp = "482910"
    user = make_user(otp=_hash(otp), otp_expiry=datetime.utcnow() + timedelta(minutes=5))
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = user
    svc = make_svc(db=db)

    result = await svc.verify_otp("test@example.com", otp)

    assert "access_token" in result
    assert "role" in result
