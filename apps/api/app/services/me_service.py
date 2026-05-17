from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from argon2 import PasswordHasher
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError, ErrorCode
from app.core.security import CurrentUser
from app.db.models import (
    AccountDeletionRequest,
    AuditLog,
    DataExportJob,
    DeviceToken,
    NotificationPreference,
    Profile,
    RefreshToken,
    SupportRequest,
    Tenant,
    TenantMembership,
    User,
    Vehicle,
)
from app.db.session import set_local_context
from app.schemas.me import (
    AccountDeletionResponse,
    DataExportStatusResponse,
    NotificationPreferencesResponse,
    OpsUserDto,
    ProfileResponse,
    SessionDto,
    VehicleDto,
    VehicleUpdateRequest,
    VehicleWriteRequest,
)
from app.services.auth_service import normalize_identifier

password_hasher = PasswordHasher()


class MeService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_password_reset_request(self, *, identifier: str) -> SupportRequest:
        tenant = await self._default_tenant()
        await set_local_context(self.session, tenant_id=tenant.id)
        subject = await self._user_by_identifier(identifier)
        request = SupportRequest(
            id=uuid4(),
            tenant_id=subject.tenant_id if subject else tenant.id,
            subject_user_id=subject.id if subject else None,
            kind="password_reset",
            identifier=identifier.strip(),
            status="open",
            payload={"source": "forgot_password"},
        )
        self.session.add(request)
        await self.session.flush()
        return request

    async def profile(self, current: CurrentUser) -> ProfileResponse:
        await self._context(current)
        user = await self._current_user(current)
        profile = await self._ensure_profile(current, user)
        return ProfileResponse(
            user_id=user.id,
            tenant_id=user.tenant_id,
            display_name=profile.display_name,
            locale=profile.locale,
            email=user.email,
            phone=user.phone,
            referral_code=user.referral_code,
            no_show_count=profile.no_show_count,
            created_at=profile.created_at,
        )

    async def update_profile(self, current: CurrentUser, *, display_name: str | None, locale: str | None) -> ProfileResponse:
        await self._context(current)
        user = await self._current_user(current)
        profile = await self._ensure_profile(current, user)
        if display_name is not None:
            profile.display_name = display_name
            user.name = display_name
        if locale is not None:
            profile.locale = locale
        await self.session.flush()
        return await self.profile(current)

    async def list_vehicles(self, current: CurrentUser) -> list[VehicleDto]:
        await self._context(current)
        rows = (
            await self.session.scalars(
                select(Vehicle).where(Vehicle.tenant_id == current.tenant_id, Vehicle.user_id == current.user_id, Vehicle.deleted_at.is_(None)).order_by(Vehicle.created_at.desc())
            )
        ).all()
        return [self._vehicle_dto(row) for row in rows]

    async def create_vehicle(self, current: CurrentUser, request: VehicleWriteRequest) -> VehicleDto:
        await self._context(current)
        if request.is_default:
            await self._clear_default_vehicle(current)
        row = Vehicle(
            id=uuid4(),
            tenant_id=current.tenant_id,
            user_id=current.user_id,
            kind=request.kind,
            license_plate=request.license_plate,
            make=request.make,
            model=request.model,
            year=request.year,
            color=request.color,
            is_default=request.is_default,
        )
        self.session.add(row)
        await self.session.flush()
        return self._vehicle_dto(row)

    async def update_vehicle(self, current: CurrentUser, vehicle_id: UUID, request: VehicleUpdateRequest) -> VehicleDto:
        await self._context(current)
        row = await self.session.scalar(select(Vehicle).where(Vehicle.id == vehicle_id, Vehicle.tenant_id == current.tenant_id, Vehicle.user_id == current.user_id, Vehicle.deleted_at.is_(None)))
        if row is None:
            raise ApiError(ErrorCode.resource_not_found, detail="Vehicle was not found.")
        if request.is_default:
            await self._clear_default_vehicle(current)
        for field in ("kind", "license_plate", "make", "model", "year", "color", "is_default"):
            value = getattr(request, field)
            if value is not None:
                setattr(row, field, value)
        row.updated_at = datetime.now(UTC)
        await self.session.flush()
        return self._vehicle_dto(row)

    async def register_notification_token(self, current: CurrentUser, *, token: str, platform: str, device_id: str | None) -> None:
        await self._context(current)
        existing = await self.session.get(DeviceToken, token)
        now = datetime.now(UTC)
        if existing is None:
            self.session.add(DeviceToken(token=token, tenant_id=current.tenant_id, user_id=current.user_id, platform=platform, device_id=device_id, last_seen_at=now))
        else:
            existing.tenant_id = current.tenant_id
            existing.user_id = current.user_id
            existing.platform = platform
            existing.device_id = device_id
            existing.last_seen_at = now
        await self.session.flush()

    async def notification_preferences(self, current: CurrentUser) -> NotificationPreferencesResponse:
        pref = await self._ensure_notification_preferences(current)
        return self._notification_preferences_response(pref)

    async def update_notification_preferences(self, current: CurrentUser, **updates: object) -> NotificationPreferencesResponse:
        pref = await self._ensure_notification_preferences(current)
        for field, value in updates.items():
            if value is not None:
                setattr(pref, field, value)
        pref.updated_at = datetime.now(UTC)
        await self.session.flush()
        return self._notification_preferences_response(pref)

    async def list_sessions(self, current: CurrentUser) -> list[SessionDto]:
        await self._context(current)
        rows = (
            await self.session.scalars(
                select(RefreshToken).where(RefreshToken.user_id == current.user_id).order_by(RefreshToken.created_at.desc())
            )
        ).all()
        return [
            SessionDto(
                id=row.token_hash[:16],
                subject=row.user_id,
                current=row.revoked_at is None and row.superseded_by is None,
                created_at=row.created_at,
                expires_at=row.expires_at,
                revoked_at=row.revoked_at,
            )
            for row in rows
        ]

    async def revoke_session(self, current: CurrentUser, session_id: str) -> None:
        await self._context(current)
        result = await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == current.user_id, RefreshToken.token_hash.startswith(session_id), RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
        if result.rowcount == 0:
            raise ApiError(ErrorCode.resource_not_found, detail="Session was not found.")

    async def request_data_export(self, current: CurrentUser) -> DataExportJob:
        await self._context(current)
        row = DataExportJob(
            id=uuid4(),
            tenant_id=current.tenant_id,
            user_id=current.user_id,
            status="queued",
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def data_export_status(self, current: CurrentUser, job_id: UUID) -> DataExportStatusResponse:
        await self._context(current)
        row = await self.session.scalar(select(DataExportJob).where(DataExportJob.id == job_id, DataExportJob.tenant_id == current.tenant_id, DataExportJob.user_id == current.user_id))
        if row is None:
            raise ApiError(ErrorCode.resource_not_found, detail="Data export job was not found.")
        return DataExportStatusResponse(job_id=row.id, status=row.status, bundle_url=row.bundle_url, expires_at=row.expires_at)

    async def request_account_deletion(self, current: CurrentUser) -> AccountDeletionResponse:
        await self._context(current)
        now = datetime.now(UTC)
        row = AccountDeletionRequest(
            id=uuid4(),
            tenant_id=current.tenant_id,
            user_id=current.user_id,
            status="waiting",
            cancel_until=now + timedelta(days=20),
        )
        self.session.add(row)
        await self.session.flush()
        return AccountDeletionResponse(request_id=row.id, status=row.status, cancel_until=row.cancel_until)

    async def cancel_account_deletion(self, current: CurrentUser) -> AccountDeletionResponse:
        await self._context(current)
        row = await self.session.scalar(
            select(AccountDeletionRequest)
            .where(AccountDeletionRequest.tenant_id == current.tenant_id, AccountDeletionRequest.user_id == current.user_id, AccountDeletionRequest.status == "waiting")
            .order_by(AccountDeletionRequest.requested_at.desc())
        )
        if row is None:
            raise ApiError(ErrorCode.resource_not_found, detail="No pending account deletion request was found.")
        row.status = "cancelled"
        row.cancelled_at = datetime.now(UTC)
        await self.session.flush()
        return AccountDeletionResponse(request_id=row.id, status=row.status, cancel_until=row.cancel_until)

    async def list_ops_users(self, current: CurrentUser, *, role: str | None = None, limit: int = 100) -> list[OpsUserDto]:
        await self._require_ops(current)
        stmt = select(User).where(User.tenant_id == current.tenant_id, User.deleted_at.is_(None)).order_by(User.created_at.desc()).limit(min(max(limit, 1), 500))
        if role:
            stmt = stmt.where(User.role == role)
        rows = (await self.session.scalars(stmt)).all()
        return [self._ops_user_dto(row) for row in rows]

    async def create_ops_user(self, current: CurrentUser, *, identifier: str, password: str, display_name: str | None, role: str) -> OpsUserDto:
        await self._require_ops(current)
        column, normalized = normalize_identifier(identifier)
        existing = await self.session.scalar(select(User).where(User.tenant_id == current.tenant_id, User.deleted_at.is_(None), User.email == normalized if column == "email" else User.phone == normalized))
        if existing is not None:
            raise ApiError(ErrorCode.duplicate_identity, detail="Identifier already exists.")
        user = User(
            id=uuid4(),
            tenant_id=current.tenant_id,
            email=normalized if column == "email" else None,
            phone=normalized if column == "phone" else None,
            password_hash=password_hasher.hash(password),
            name=display_name,
            role=role,
        )
        self.session.add(user)
        await self.session.flush()
        self.session.add(TenantMembership(user_id=user.id, tenant_id=current.tenant_id, role=role))
        self.session.add(Profile(user_id=user.id, tenant_id=current.tenant_id, display_name=display_name or "", locale="vi"))
        self._audit(current=current, action="ops_user.create", target_kind="user", target_id=user.id, payload={"role": role})
        await self.session.flush()
        return self._ops_user_dto(user)

    async def reset_user_password(self, current: CurrentUser, *, user_id: UUID, new_password: str) -> None:
        await self._require_ops(current)
        user = await self.session.scalar(select(User).where(User.id == user_id, User.tenant_id == current.tenant_id, User.deleted_at.is_(None)))
        if user is None:
            raise ApiError(ErrorCode.resource_not_found, detail="User was not found.")
        user.password_hash = password_hasher.hash(new_password)
        await self.session.execute(update(RefreshToken).where(RefreshToken.user_id == user.id).values(revoked_at=datetime.now(UTC)))
        self._audit(current=current, action="user.password_reset", target_kind="user", target_id=user.id)
        await self.session.flush()

    async def _default_tenant(self) -> Tenant:
        tenant = await self.session.scalar(select(Tenant).order_by(Tenant.created_at).limit(1))
        if tenant is None:
            tenant = Tenant(id=UUID("00000000-0000-0000-0000-000000000001"), name="TrueCare Pilot")
            self.session.add(tenant)
            await self.session.flush()
        return tenant

    async def _user_by_identifier(self, identifier: str) -> User | None:
        column, normalized = normalize_identifier(identifier)
        stmt = select(User).where(User.deleted_at.is_(None))
        stmt = stmt.where(User.email == normalized) if column == "email" else stmt.where(User.phone == normalized)
        return await self.session.scalar(stmt)

    async def _context(self, current: CurrentUser) -> None:
        await set_local_context(self.session, tenant_id=current.tenant_id, user_id=current.user_id, role=",".join(current.roles))

    async def _current_user(self, current: CurrentUser) -> User:
        user = await self.session.get(User, current.user_id)
        if user is None or user.tenant_id != current.tenant_id or user.deleted_at is not None:
            raise ApiError(ErrorCode.unauthorized, detail="User is not active.")
        return user

    async def _ensure_profile(self, current: CurrentUser, user: User) -> Profile:
        profile = await self.session.get(Profile, current.user_id)
        if profile is None:
            profile = Profile(user_id=current.user_id, tenant_id=current.tenant_id, display_name=user.name or "", locale=current.locale or "vi")
            self.session.add(profile)
            await self.session.flush()
        return profile

    async def _ensure_notification_preferences(self, current: CurrentUser) -> NotificationPreference:
        await self._context(current)
        pref = await self.session.get(NotificationPreference, current.user_id)
        if pref is None:
            pref = NotificationPreference(user_id=current.user_id, tenant_id=current.tenant_id)
            self.session.add(pref)
            await self.session.flush()
        return pref

    async def _require_ops(self, current: CurrentUser) -> None:
        await self._context(current)
        if "ops" not in current.roles:
            raise ApiError(ErrorCode.forbidden, detail="Ops role is required.")

    async def _clear_default_vehicle(self, current: CurrentUser) -> None:
        await self.session.execute(update(Vehicle).where(Vehicle.tenant_id == current.tenant_id, Vehicle.user_id == current.user_id).values(is_default=False))

    def _vehicle_dto(self, row: Vehicle) -> VehicleDto:
        return VehicleDto(
            id=row.id,
            kind=row.kind,
            license_plate=row.license_plate,
            make=row.make,
            model=row.model,
            year=row.year,
            color=row.color,
            is_default=row.is_default,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _notification_preferences_response(self, pref: NotificationPreference) -> NotificationPreferencesResponse:
        return NotificationPreferencesResponse(
            booking_updates=pref.booking_updates,
            golden_hour=pref.golden_hour,
            referral_reward=pref.referral_reward,
            wash_reminder=pref.wash_reminder,
            quiet_hours_start=pref.quiet_hours_start,
            quiet_hours_end=pref.quiet_hours_end,
        )

    def _ops_user_dto(self, row: User) -> OpsUserDto:
        return OpsUserDto(
            id=row.id,
            tenant_id=row.tenant_id,
            email=row.email,
            phone=row.phone,
            name=row.name,
            role=row.role,
            created_at=row.created_at,
        )

    def _audit(self, *, current: CurrentUser, action: str, target_kind: str, target_id: UUID | None, payload: dict[str, object] | None = None) -> None:
        self.session.add(
            AuditLog(
                id=uuid4(),
                tenant_id=current.tenant_id,
                actor_user_id=current.user_id,
                action=action,
                target_kind=target_kind,
                target_id=target_id,
                payload=payload or {},
            )
        )
