from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.errors import ApiError, ErrorCode
from app.services.auth_service import AuthService, JwtClaims

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    user_id: UUID
    tenant_id: UUID
    roles: tuple[str, ...]
    locale: str | None = None


async def require_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> CurrentUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise ApiError(ErrorCode.unauthorized, detail="Bearer token required.")
    claims: JwtClaims = AuthService().verify_access_token(credentials.credentials)
    return CurrentUser(
        user_id=claims.user_id,
        tenant_id=claims.tenant_id,
        roles=tuple(claims.roles),
        locale=claims.locale,
    )


def require_role(*allowed_roles: str):
    async def dependency(current: CurrentUser = Depends(require_user)) -> CurrentUser:
        if not set(current.roles).intersection(allowed_roles):
            raise ApiError(ErrorCode.forbidden, detail="Required role is missing.")
        return current

    return dependency


async def require_tenant(current: CurrentUser = Depends(require_user)) -> UUID:
    if not current.tenant_id:
        raise ApiError(ErrorCode.tenant_context_missing)
    return current.tenant_id
