from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, require_user
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
from app.services.auth_service import AuthService

router = APIRouter(prefix="/v1/auth", tags=["auth"])

IMPLEMENTED_AUTH_ROUTES = {
    ("POST", "/v1/auth/exists"),
    ("POST", "/v1/auth/signup"),
    ("POST", "/v1/auth/login"),
    ("POST", "/v1/auth/refresh"),
    ("POST", "/v1/auth/logout"),
    ("POST", "/v1/auth/logout-all"),
    ("GET", "/v1/auth/me"),
}


@router.post("/exists", response_model=AuthExistsResponse, operation_id="post_v1_auth_exists")
async def exists(request: AuthExistsRequest, session: AsyncSession = Depends(get_session)) -> AuthExistsResponse:
    return AuthExistsResponse(exists=await AuthService(session).exists(request.identifier))


@router.post("/signup", response_model=TokenPair, operation_id="post_v1_auth_signup")
async def signup(request: SignupRequest, session: AsyncSession = Depends(get_session)) -> TokenPair:
    async with session.begin():
        user, locale = await AuthService(session).signup(
            identifier=request.identifier,
            password=request.password,
            display_name=request.display_name,
            locale=request.locale,
        )
        token_pair = await AuthService(session).issue_token_pair(user, locale=locale)
    return TokenPair(**token_pair)


@router.post("/login", response_model=TokenPair, operation_id="post_v1_auth_login")
async def login(request: LoginRequest, session: AsyncSession = Depends(get_session)) -> TokenPair:
    async with session.begin():
        user, locale = await AuthService(session).login(identifier=request.identifier, password=request.password)
        token_pair = await AuthService(session).issue_token_pair(user, locale=locale)
    return TokenPair(**token_pair)


@router.post("/refresh", response_model=TokenPair, operation_id="post_v1_auth_refresh")
async def refresh(request: RefreshRequest, session: AsyncSession = Depends(get_session)) -> TokenPair:
    async with session.begin():
        token_pair = await AuthService(session).refresh(request.refresh_token)
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
async def me(current: CurrentUser = Depends(require_user)) -> AuthMeResponse:
    return AuthMeResponse(
        user_id=current.user_id,
        tenant_id=current.tenant_id,
        roles=list(current.roles),
        locale=current.locale,
    )
