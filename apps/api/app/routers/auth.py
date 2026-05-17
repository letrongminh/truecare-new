from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import enforce_login_rate_limit, enforce_refresh_rate_limit, enforce_signup_rate_limit
from app.core.security import CurrentUser, require_user
from app.db.models import Merchant
from app.db.session import get_session
from app.schemas.auth import (
    AuthExistsRequest,
    AuthExistsResponse,
    AuthMeResponse,
    LoginRequest,
    LogoutRequest,
    LogoutResponse,
    RefreshRequest,
    SignupRequest,
    TokenPair,
)
from app.schemas.me import ForgotPasswordRequest, SupportRequestResponse
from app.services.auth_service import AuthService
from app.services.me_service import MeService

router = APIRouter(prefix="/v1/auth", tags=["auth"])

IMPLEMENTED_AUTH_ROUTES = {
    ("POST", "/v1/auth/exists"),
    ("POST", "/v1/auth/signup"),
    ("POST", "/v1/auth/login"),
    ("POST", "/v1/auth/refresh"),
    ("POST", "/v1/auth/logout"),
    ("POST", "/v1/auth/logout-all"),
    ("GET", "/v1/auth/me"),
    ("POST", "/v1/auth/forgot-password"),
}


@router.post("/exists", response_model=AuthExistsResponse, operation_id="post_v1_auth_exists")
async def exists(request: AuthExistsRequest, session: AsyncSession = Depends(get_session)) -> AuthExistsResponse:
    return AuthExistsResponse(exists=await AuthService(session).exists(request.identifier))


@router.post("/signup", response_model=TokenPair, operation_id="post_v1_auth_signup")
async def signup(request: Request, body: SignupRequest, session: AsyncSession = Depends(get_session)) -> TokenPair:
    enforce_signup_rate_limit(request, body.identifier)
    async with session.begin():
        user, locale = await AuthService(session).signup(
            identifier=body.identifier,
            password=body.password,
            display_name=body.display_name,
            locale=body.locale,
            invite_code=body.invite_code,
            referral_code=body.referral_code,
            device_id=request.headers.get("x-device-id"),
        )
        token_pair = await AuthService(session).issue_token_pair(user, locale=locale)
    return TokenPair(**token_pair)


@router.post("/login", response_model=TokenPair, operation_id="post_v1_auth_login")
async def login(request: Request, body: LoginRequest, session: AsyncSession = Depends(get_session)) -> TokenPair:
    enforce_login_rate_limit(request, body.identifier)
    async with session.begin():
        user, locale = await AuthService(session).login(identifier=body.identifier, password=body.password)
        token_pair = await AuthService(session).issue_token_pair(user, locale=locale)
    return TokenPair(**token_pair)


@router.post("/refresh", response_model=TokenPair, operation_id="post_v1_auth_refresh")
async def refresh(request: Request, body: RefreshRequest, session: AsyncSession = Depends(get_session)) -> TokenPair:
    enforce_refresh_rate_limit(request, body.refresh_token)
    async with session.begin():
        token_pair = await AuthService(session).refresh(body.refresh_token)
    return TokenPair(**token_pair)


@router.post("/logout", response_model=LogoutResponse, operation_id="post_v1_auth_logout")
async def logout(request: LogoutRequest, session: AsyncSession = Depends(get_session)) -> LogoutResponse:
    async with session.begin():
        revoked = await AuthService(session).logout(request.refresh_token)
    return LogoutResponse(revoked=revoked)


@router.post("/logout-all", response_model=LogoutResponse, operation_id="post_v1_auth_logout_all")
async def logout_all(current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> LogoutResponse:
    async with session.begin():
        revoked = await AuthService(session).logout_all(current.user_id)
    return LogoutResponse(revoked=revoked)


@router.get("/me", response_model=AuthMeResponse, operation_id="get_v1_auth_me")
async def me(current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> AuthMeResponse:
    merchant = await session.scalar(
        select(Merchant)
        .where(
            Merchant.tenant_id == current.tenant_id,
            Merchant.user_id == current.user_id,
            Merchant.deleted_at.is_(None),
        )
        .order_by(Merchant.created_at.desc())
        .limit(1)
    )
    return AuthMeResponse(
        user_id=current.user_id,
        tenant_id=current.tenant_id,
        roles=list(current.roles),
        locale=current.locale,
        merchant_id=merchant.id if merchant else None,
        merchant_status=merchant.status if merchant else None,
        merchant_pipeline_status=merchant.pipeline_status if merchant else None,
    )


@router.post("/forgot-password", response_model=SupportRequestResponse, operation_id="post_v1_auth_forgot_password")
async def forgot_password(body: ForgotPasswordRequest, session: AsyncSession = Depends(get_session)) -> SupportRequestResponse:
    async with session.begin():
        request = await MeService(session).create_password_reset_request(identifier=body.identifier)
    return SupportRequestResponse(request_id=request.id, status=request.status)
