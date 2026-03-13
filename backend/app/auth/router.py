# app/auth/router.py
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_refresh_token
from app.auth.service import AuthService
from app.config import Settings, get_settings
from app.database import get_db
from app.email.service import EmailService, get_email_service
from app.models import User
from app.schemas import MessageResponse, RefreshResponse, RegisterRequest, TokenResponse, VerifyOtpRequest

router = APIRouter(prefix="/auth", tags=["Auth"])

COOKIE_NAME = "refresh_token"
# SameSite=strict prevents CSRF on the refresh cookie.
# Set secure=True in production (behind HTTPS).
COOKIE_OPTS = dict(httponly=True, samesite="strict", secure=False)


def _auth_svc(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    email_svc: EmailService = Depends(get_email_service),
) -> AuthService:
    return AuthService(db, settings, email_svc)


@router.post("/register", response_model=MessageResponse)
async def register(body: RegisterRequest, svc: AuthService = Depends(_auth_svc)):
    return await svc.register(body.email)


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(
    body: VerifyOtpRequest,
    request: Request,
    response: Response,
    svc: AuthService = Depends(_auth_svc),
    settings: Settings = Depends(get_settings),
):
    result = await svc.verify_otp(body.email, body.otp, request)
    response.set_cookie(
        COOKIE_NAME,
        result["refresh_token"],
        max_age=settings.jwt_refresh_expires_days * 86400,
        **COOKIE_OPTS,
    )
    return {"access_token": result["access_token"], "role": result["role"]}


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    request: Request,
    response: Response,
    # CSRF extra layer: require X-Requested-With header
    x_requested_with: str | None = Header(default=None, alias="X-Requested-With"),
    raw_token: str | None = Depends(get_refresh_token),
    svc: AuthService = Depends(_auth_svc),
    settings: Settings = Depends(get_settings),
):
    """
    Refresh access token using the HttpOnly cookie.
    Requires X-Requested-With: XMLHttpRequest header (CSRF mitigation).
    """
    if x_requested_with != "XMLHttpRequest":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Missing or invalid X-Requested-With header")

    result = await svc.refresh(raw_token, request)
    response.set_cookie(
        COOKIE_NAME,
        result["refresh_token"],
        max_age=settings.jwt_refresh_expires_days * 86400,
        **COOKIE_OPTS,
    )
    return {"access_token": result["access_token"]}


@router.post("/logout", response_model=MessageResponse)
def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    svc: AuthService = Depends(_auth_svc),
):
    response.delete_cookie(COOKIE_NAME, samesite="strict")
    return svc.logout(current_user.id, request)
