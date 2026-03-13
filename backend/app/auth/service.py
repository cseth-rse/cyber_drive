# app/auth/service.py
import logging
import random
import string
import hashlib
import hmac
from datetime import datetime, timedelta

import bcrypt as _bcrypt
from fastapi import HTTPException, Request, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.audit.service import AuditService
from app.config import Settings
from app.email.service import EmailService
from app.models import AuditAction, User

logger = logging.getLogger(__name__)

OTP_TTL_MINUTES = 10


def _generate_otp() -> str:
    return "".join(random.choices(string.digits, k=6))


def _hash(value: str) -> str:
    return _bcrypt.hashpw(value.encode(), _bcrypt.gensalt()).decode()


def _verify(plain: str, hashed: str) -> bool:
    return _bcrypt.checkpw(plain.encode(), hashed.encode())

def _hash_token(token: str) -> str:
    """SHA-256 hex digest — safe for long strings like JWTs (bcrypt caps at 72 bytes)."""
    return hashlib.sha256(token.encode()).hexdigest()


def _verify_token(raw: str, stored_hash: str) -> bool:
    """Constant-time compare to prevent timing attacks."""
    return hmac.compare_digest(hashlib.sha256(raw.encode()).hexdigest(), stored_hash)


def _make_jwt(payload: dict, secret: str, expires_delta: timedelta) -> str:
    data = payload.copy()
    data["exp"] = datetime.utcnow() + expires_delta
    return jwt.encode(data, secret, algorithm="HS256")


class AuthService:
    def __init__(self, db: Session, settings: Settings, email_svc: EmailService):
        self.db = db
        self.settings = settings
        self.email_svc = email_svc
        self.audit = AuditService(db)

    # ── Register (send OTP) ──────────────────────────────────────────────────
    async def register(self, email: str) -> dict:
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            user = User(email=email)
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)

        otp = _generate_otp()
        user.otp = _hash(otp)
        user.otp_expiry = datetime.utcnow() + timedelta(minutes=OTP_TTL_MINUTES)
        self.db.commit()

        await self.email_svc.send_otp(email, otp)
        return {"message": "OTP sent to your email address"}

    # ── Verify OTP ───────────────────────────────────────────────────────────
    async def verify_otp(self, email: str, otp: str, request: Request | None = None) -> dict:
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

        if not user.otp or not user.otp_expiry:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "No OTP requested – please register first")

        if datetime.utcnow() > user.otp_expiry:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "OTP has expired")

        if not _verify(otp, user.otp):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid OTP")

        user.otp = None
        user.otp_expiry = None

        access_token, refresh_token = self._issue_tokens(user)
        user.refresh_token = _hash_token(refresh_token)
        self.db.commit()

        self.audit.log(user_id=user.id, action=AuditAction.LOGIN, request=request)
        return {"access_token": access_token, "refresh_token": refresh_token, "role": user.role}

    # ── Refresh — with rotation + reuse detection ────────────────────────────
    async def refresh(self, raw_refresh_token: str | None, request: Request | None = None) -> dict:
        if not raw_refresh_token:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token missing")

        # 1. Decode JWT (signature + expiry check)
        try:
            payload = jwt.decode(
                raw_refresh_token,
                self.settings.jwt_refresh_secret,
                algorithms=["HS256"],
            )
        except JWTError:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token")

        user = self.db.query(User).filter(User.id == payload.get("sub")).first()
        if not user:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session not found")

        # 2. Reuse detection: if stored hash is None, session was already revoked
        if not user.refresh_token:
            logger.warning(
                "Refresh token reuse detected for user %s — all sessions revoked", user.email
            )
            # Revoke all sessions by keeping refresh_token = None (already is)
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session revoked — please log in again")

        # 3. Hash comparison
        if not _verify_token(raw_refresh_token, user.refresh_token):
            # Token mismatch → possible token theft; revoke the session
            logger.warning("Refresh token mismatch for user %s — revoking session", user.email)
            user.refresh_token = None
            self.db.commit()
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token invalid — session revoked")

        # 4. Rotate: issue new pair, replace stored hash
        access_token, new_refresh_token = self._issue_tokens(user)
        user.refresh_token = _hash_token(new_refresh_token)
        self.db.commit()

        self.audit.log(user_id=user.id, action=AuditAction.REFRESH, request=request)
        return {"access_token": access_token, "refresh_token": new_refresh_token}

    # ── Logout ───────────────────────────────────────────────────────────────
    def logout(self, user_id: str, request: Request | None = None) -> dict:
        user = self.db.query(User).filter(User.id == user_id).first()
        if user:
            user.refresh_token = None
            self.db.commit()
            self.audit.log(user_id=user_id, action=AuditAction.LOGOUT, request=request)
        return {"message": "Logged out"}

    # ── Helpers ──────────────────────────────────────────────────────────────
    def _issue_tokens(self, user: User) -> tuple[str, str]:
        payload = {"sub": user.id, "email": user.email, "role": user.role.value}
        access = _make_jwt(payload, self.settings.jwt_secret, timedelta(minutes=self.settings.jwt_expires_minutes))
        refresh = _make_jwt(payload, self.settings.jwt_refresh_secret, timedelta(days=self.settings.jwt_refresh_expires_days))
        return access, refresh
