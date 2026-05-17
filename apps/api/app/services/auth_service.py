from __future__ import annotations

import base64
import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy import Select, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import ApiError, ErrorCode
from app.db.models import Profile, RefreshToken, Tenant, TenantMembership, User

ACCESS_TOKEN_SECONDS = 15 * 60
REFRESH_TOKEN_DAYS = 30

password_hasher = PasswordHasher()
_dev_private_key: Ed25519PrivateKey | None = None


@dataclass(frozen=True)
class JwtClaims:
    user_id: UUID
    tenant_id: UUID
    roles: list[str]
    locale: str | None


def normalize_identifier(identifier: str) -> tuple[str, str]:
    value = identifier.strip()
    if "@" in value:
        return "email", value.lower()
    return "phone", value


def _b64url_decode(value: str) -> bytes:
    padded = value + "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def _load_private_key_from_jwk(path: str | None) -> Ed25519PrivateKey | None:
    if not path:
        return None
    key_path = Path(path)
    if not key_path.exists():
        return None
    data = json.loads(key_path.read_text())
    if data.get("kty") != "OKP" or data.get("crv") != "Ed25519" or "d" not in data:
        raise RuntimeError("JWT_SIGNING_PRIVATE_JWK must be an Ed25519 private JWK")
    return Ed25519PrivateKey.from_private_bytes(_b64url_decode(data["d"]))


def signing_key() -> Ed25519PrivateKey:
    global _dev_private_key
    settings = get_settings()
    configured = _load_private_key_from_jwk(settings.jwt_signing_private_jwk)
    if configured is not None:
        return configured
    if _dev_private_key is None:
        _dev_private_key = Ed25519PrivateKey.generate()
    return _dev_private_key


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class AuthService:
    def __init__(self, session: AsyncSession | None = None):
        self.session = session

    def _db(self) -> AsyncSession:
        if self.session is None:
            raise RuntimeError("AuthService database session required")
        return self.session

    async def exists(self, identifier: str) -> bool:
        session = self._db()
        column, normalized = normalize_identifier(identifier)
        stmt: Select[tuple[User]] = select(User).where(User.deleted_at.is_(None))
        stmt = stmt.where(User.email == normalized) if column == "email" else stmt.where(User.phone == normalized)
        return (await session.scalar(stmt)) is not None

    async def signup(self, *, identifier: str, password: str, display_name: str | None, locale: str) -> tuple[User, str]:
        session = self._db()
        column, normalized = normalize_identifier(identifier)
        if await self.exists(normalized):
            raise ApiError(ErrorCode.duplicate_identity, detail="Identifier already exists.")

        tenant = await self._get_or_create_default_tenant()
        user = User(
            tenant_id=tenant.id,
            email=normalized if column == "email" else None,
            phone=normalized if column == "phone" else None,
            password_hash=password_hasher.hash(password),
            name=display_name,
            role="consumer",
            referral_code=self._referral_code(),
        )
        session.add(user)
        await session.flush()
        session.add(TenantMembership(user_id=user.id, tenant_id=tenant.id, role="consumer"))
        session.add(Profile(user_id=user.id, tenant_id=tenant.id, display_name=display_name or "", locale=locale or "vi"))
        await session.flush()
        return user, locale or "vi"

    async def login(self, *, identifier: str, password: str) -> tuple[User, str | None]:
        session = self._db()
        column, normalized = normalize_identifier(identifier)
        stmt = select(User, Profile.locale).join(Profile, Profile.user_id == User.id, isouter=True).where(User.deleted_at.is_(None))
        stmt = stmt.where(User.email == normalized) if column == "email" else stmt.where(User.phone == normalized)
        row = (await session.execute(stmt)).first()
        if row is None:
            raise ApiError(ErrorCode.invalid_credentials, detail="Invalid identifier or password.")
        user, locale = row
        try:
            password_hasher.verify(user.password_hash, password)
        except VerifyMismatchError:
            raise ApiError(ErrorCode.invalid_credentials, detail="Invalid identifier or password.") from None
        return user, locale

    async def issue_token_pair(self, user: User, *, locale: str | None, parent_hash: str | None = None, family_id: UUID | None = None) -> dict[str, str | int]:
        session = self._db()
        roles = await self.roles_for_user(user.id)
        access_token = self.mint_access_token(user_id=user.id, tenant_id=user.tenant_id, roles=roles, locale=locale)
        refresh_token = secrets.token_urlsafe(48)
        token_hash = hash_refresh_token(refresh_token)
        session.add(
            RefreshToken(
                token_hash=token_hash,
                user_id=user.id,
                family_id=family_id or uuid4(),
                parent_hash=parent_hash,
                expires_at=datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_DAYS),
            )
        )
        if parent_hash is not None:
            await session.execute(update(RefreshToken).where(RefreshToken.token_hash == parent_hash).values(superseded_by=token_hash))
        await session.flush()
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_SECONDS,
        }

    async def refresh(self, refresh_token: str) -> dict[str, str | int]:
        session = self._db()
        token_hash = hash_refresh_token(refresh_token)
        row = await session.get(RefreshToken, token_hash)
        now = datetime.now(UTC)
        if row is None or row.expires_at <= now:
            raise ApiError(ErrorCode.unauthorized, detail="Refresh token is invalid.")
        if row.revoked_at is not None or row.superseded_by is not None:
            await self._revoke_family(row.family_id, reused_hash=row.token_hash)
            raise ApiError(ErrorCode.token_reused, detail="Refresh token reuse detected.")
        user = await session.get(User, row.user_id)
        if user is None or user.deleted_at is not None:
            raise ApiError(ErrorCode.unauthorized, detail="Refresh token user is no longer active.")
        locale = await self._locale_for_user(user.id)
        return await self.issue_token_pair(user, locale=locale, parent_hash=row.token_hash, family_id=row.family_id)

    async def logout(self, refresh_token: str) -> bool:
        session = self._db()
        row = await session.get(RefreshToken, hash_refresh_token(refresh_token))
        if row is None:
            return False
        row.revoked_at = datetime.now(UTC)
        await session.flush()
        return True

    async def logout_all(self, user_id: UUID) -> bool:
        session = self._db()
        await session.execute(update(RefreshToken).where(RefreshToken.user_id == user_id).values(revoked_at=datetime.now(UTC)))
        return True

    async def roles_for_user(self, user_id: UUID) -> list[str]:
        session = self._db()
        roles = (await session.scalars(select(TenantMembership.role).where(TenantMembership.user_id == user_id))).all()
        return list(roles or ["consumer"])

    def mint_access_token(self, *, user_id: UUID, tenant_id: UUID, roles: list[str], locale: str | None) -> str:
        settings = get_settings()
        now = datetime.now(UTC)
        payload = {
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "roles": roles,
            "locale": locale,
            "iat": int(now.timestamp()),
            "nbf": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=ACCESS_TOKEN_SECONDS)).timestamp()),
            "jti": str(uuid4()),
        }
        return jwt.encode(payload, signing_key(), algorithm="EdDSA", headers={"kid": "local-dev"})

    def verify_access_token(self, token: str) -> JwtClaims:
        settings = get_settings()
        try:
            payload = jwt.decode(
                token,
                signing_key().public_key(),
                algorithms=["EdDSA"],
                audience=settings.jwt_audience,
                issuer=settings.jwt_issuer,
            )
        except jwt.ExpiredSignatureError:
            raise ApiError(ErrorCode.token_expired, detail="Access token expired.") from None
        except jwt.PyJWTError:
            raise ApiError(ErrorCode.unauthorized, detail="Access token is invalid.") from None
        return JwtClaims(
            user_id=UUID(payload["sub"]),
            tenant_id=UUID(payload["tenant_id"]),
            roles=list(payload.get("roles") or []),
            locale=payload.get("locale"),
        )

    async def _get_or_create_default_tenant(self) -> Tenant:
        session = self._db()
        tenant = await session.scalar(select(Tenant).order_by(Tenant.created_at).limit(1))
        if tenant is not None:
            return tenant
        tenant = Tenant(name=get_settings().default_tenant_name)
        session.add(tenant)
        await session.flush()
        return tenant

    async def _locale_for_user(self, user_id: UUID) -> str | None:
        return await self._db().scalar(select(Profile.locale).where(Profile.user_id == user_id))

    async def _revoke_family(self, family_id: UUID, *, reused_hash: str) -> None:
        session = self._db()
        now = datetime.now(UTC)
        await session.execute(update(RefreshToken).where(RefreshToken.family_id == family_id).values(revoked_at=now))
        await session.execute(update(RefreshToken).where(RefreshToken.token_hash == reused_hash).values(reused_at=now))

    def _referral_code(self) -> str:
        return secrets.token_urlsafe(9).replace("-", "").replace("_", "")[:10].upper()
