from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, require_user
from app.db.session import get_session
from app.schemas.me import (
    AccountDeletionResponse,
    ChangePasswordRequest,
    DataExportResponse,
    DataExportStatusResponse,
    MutationResponse,
    NotificationPreferencesResponse,
    NotificationPreferencesUpdateRequest,
    NotificationRegisterRequest,
    OpsPasswordResetRequest,
    OpsPasswordResetResponse,
    OpsUserCreateRequest,
    OpsUserDto,
    OpsUserListResponse,
    ProfileResponse,
    ProfileUpdateRequest,
    SessionsResponse,
    VehicleDto,
    VehicleListResponse,
    VehicleUpdateRequest,
    VehicleWriteRequest,
)
from app.services.auth_service import AuthService
from app.services.me_service import MeService

router = APIRouter(tags=["me"])

IMPLEMENTED_ME_ROUTES = {
    ("GET", "/v1/me/profile"),
    ("PATCH", "/v1/me/profile"),
    ("GET", "/v1/me/vehicles"),
    ("POST", "/v1/me/vehicles"),
    ("PATCH", "/v1/me/vehicles/{id}"),
    ("POST", "/v1/me/data-export"),
    ("GET", "/v1/me/data-export/{job_id}"),
    ("DELETE", "/v1/me/account"),
    ("POST", "/v1/me/notifications/register"),
    ("GET", "/v1/me/notifications/preferences"),
    ("PATCH", "/v1/me/notifications/preferences"),
    ("POST", "/v1/me/password"),
    ("GET", "/v1/me/sessions"),
    ("DELETE", "/v1/me/sessions/{id}"),
    ("POST", "/v1/me/cancel-delete"),
    ("GET", "/v1/ops/users"),
    ("POST", "/v1/ops/users"),
    ("POST", "/v1/ops/users/{id}/reset-password"),
}


@router.get("/v1/me/profile", response_model=ProfileResponse, operation_id="get_v1_me_profile")
async def get_profile(current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> ProfileResponse:
    async with session.begin():
        return await MeService(session).profile(current)


@router.patch("/v1/me/profile", response_model=ProfileResponse, operation_id="patch_v1_me_profile")
async def patch_profile(body: ProfileUpdateRequest, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> ProfileResponse:
    async with session.begin():
        return await MeService(session).update_profile(current, display_name=body.display_name, locale=body.locale)


@router.get("/v1/me/vehicles", response_model=VehicleListResponse, operation_id="get_v1_me_vehicles")
async def list_vehicles(current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> VehicleListResponse:
    async with session.begin():
        vehicles = await MeService(session).list_vehicles(current)
    return VehicleListResponse(vehicles=vehicles)


@router.post("/v1/me/vehicles", response_model=VehicleDto, status_code=status.HTTP_201_CREATED, operation_id="post_v1_me_vehicles")
async def create_vehicle(body: VehicleWriteRequest, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> VehicleDto:
    async with session.begin():
        return await MeService(session).create_vehicle(current, body)


@router.patch("/v1/me/vehicles/{id}", response_model=VehicleDto, operation_id="patch_v1_me_vehicles_by_id")
async def patch_vehicle(id: UUID, body: VehicleUpdateRequest, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> VehicleDto:
    async with session.begin():
        return await MeService(session).update_vehicle(current, id, body)


@router.post("/v1/me/notifications/register", response_model=MutationResponse, operation_id="post_v1_me_notifications_register")
async def register_notification_token(body: NotificationRegisterRequest, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> MutationResponse:
    async with session.begin():
        await MeService(session).register_notification_token(current, token=body.token, platform=body.platform, device_id=body.device_id)
    return MutationResponse()


@router.get("/v1/me/notifications/preferences", response_model=NotificationPreferencesResponse, operation_id="get_v1_me_notifications_preferences")
async def get_notification_preferences(current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> NotificationPreferencesResponse:
    async with session.begin():
        return await MeService(session).notification_preferences(current)


@router.patch("/v1/me/notifications/preferences", response_model=NotificationPreferencesResponse, operation_id="patch_v1_me_notifications_preferences")
async def patch_notification_preferences(
    body: NotificationPreferencesUpdateRequest,
    current: CurrentUser = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> NotificationPreferencesResponse:
    async with session.begin():
        return await MeService(session).update_notification_preferences(
            current,
            booking_updates=body.booking_updates,
            golden_hour=body.golden_hour,
            referral_reward=body.referral_reward,
            wash_reminder=body.wash_reminder,
            quiet_hours_start=body.quiet_hours_start,
            quiet_hours_end=body.quiet_hours_end,
        )


@router.post("/v1/me/password", response_model=MutationResponse, operation_id="post_v1_me_password")
async def change_password(body: ChangePasswordRequest, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> MutationResponse:
    async with session.begin():
        await AuthService(session).change_password(user_id=current.user_id, current_password=body.current_password, new_password=body.new_password)
    return MutationResponse()


@router.get("/v1/me/sessions", response_model=SessionsResponse, operation_id="get_v1_me_sessions")
async def list_sessions(current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> SessionsResponse:
    async with session.begin():
        sessions = await MeService(session).list_sessions(current)
    return SessionsResponse(sessions=sessions)


@router.delete("/v1/me/sessions/{id}", status_code=status.HTTP_204_NO_CONTENT, operation_id="delete_v1_me_sessions_by_id")
async def delete_session(id: str, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> Response:
    async with session.begin():
        await MeService(session).revoke_session(current, id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/v1/me/data-export", response_model=DataExportResponse, status_code=status.HTTP_202_ACCEPTED, operation_id="post_v1_me_data_export")
async def request_data_export(current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> DataExportResponse:
    async with session.begin():
        job = await MeService(session).request_data_export(current)
    return DataExportResponse(job_id=job.id, status=job.status)


@router.get("/v1/me/data-export/{job_id}", response_model=DataExportStatusResponse, operation_id="get_v1_me_data_export_by_job_id")
async def get_data_export(job_id: UUID, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> DataExportStatusResponse:
    async with session.begin():
        return await MeService(session).data_export_status(current, job_id)


@router.delete("/v1/me/account", response_model=AccountDeletionResponse, status_code=status.HTTP_202_ACCEPTED, operation_id="delete_v1_me_account")
async def delete_account(current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> AccountDeletionResponse:
    async with session.begin():
        return await MeService(session).request_account_deletion(current)


@router.post("/v1/me/cancel-delete", response_model=AccountDeletionResponse, operation_id="post_v1_me_cancel_delete")
async def cancel_delete(current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> AccountDeletionResponse:
    async with session.begin():
        return await MeService(session).cancel_account_deletion(current)


@router.get("/v1/ops/users", response_model=OpsUserListResponse, operation_id="get_v1_ops_users", tags=["ops"])
async def list_ops_users(
    role: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    current: CurrentUser = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> OpsUserListResponse:
    async with session.begin():
        users = await MeService(session).list_ops_users(current, role=role, limit=limit)
    return OpsUserListResponse(users=users)


@router.post("/v1/ops/users", response_model=OpsUserDto, status_code=status.HTTP_201_CREATED, operation_id="post_v1_ops_users", tags=["ops"])
async def create_ops_user(body: OpsUserCreateRequest, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> OpsUserDto:
    async with session.begin():
        return await MeService(session).create_ops_user(current, identifier=body.identifier, password=body.password, display_name=body.display_name, role=body.role)


@router.post("/v1/ops/users/{id}/reset-password", response_model=OpsPasswordResetResponse, operation_id="post_v1_ops_users_by_id_reset_password", tags=["ops"])
async def reset_user_password(id: UUID, body: OpsPasswordResetRequest, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> OpsPasswordResetResponse:
    async with session.begin():
        await MeService(session).reset_user_password(current, user_id=id, new_password=body.new_password)
    return OpsPasswordResetResponse(user_id=id)
