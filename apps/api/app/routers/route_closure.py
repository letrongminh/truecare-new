from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, require_user
from app.db.session import get_session
from app.schemas.marketplace import BookingDto, BookingListResponse, MerchantBaysResponse
from app.schemas.route_closure import (
    GoldenHourResponse,
    GoldenHourUpdateRequest,
    OpsCheckInRequest,
    OpsConciergeResultResponse,
    OpsConfirmPaymentRequest,
    OpsCreateBookingRequest,
    OpsDataRoomResponse,
    OpsEvidenceUploadRequest,
    OpsExportRequest,
    OpsExportResponse,
    OpsMintVoucherRequest,
    OpsMintVoucherResponse,
    SlotMaintenanceRequest,
    SlotMaintenanceResponse,
)
from app.services.route_closure_service import RouteClosureService

router = APIRouter(tags=["route-closure"])

IMPLEMENTED_ROUTE_CLOSURE_ROUTES = {
    ("GET", "/v1/me/bookings"),
    ("POST", "/v1/bookings/{id}/arrived"),
    ("GET", "/v1/merchants/{id}/calendar"),
    ("POST", "/v1/merchants/{id}/calendar/maintenance"),
    ("GET", "/v1/merchants/{id}/golden-hour"),
    ("PUT", "/v1/merchants/{id}/golden-hour"),
    ("GET", "/v1/ops/data-room/{section}"),
    ("POST", "/v1/ops/exports"),
    ("GET", "/v1/ops/exports/{job_id}"),
    ("POST", "/v1/ops/bookings"),
    ("POST", "/v1/ops/bookings/{id}/check-in"),
    ("POST", "/v1/ops/evidence/upload"),
    ("POST", "/v1/ops/payments/{id}/confirm"),
    ("POST", "/v1/ops/reward/voucher"),
}


@router.get("/v1/me/bookings", response_model=BookingListResponse, operation_id="get_v1_me_bookings", tags=["me"])
async def list_my_bookings(current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> BookingListResponse:
    async with session.begin():
        bookings = await RouteClosureService(session).me_bookings(current=current)
    return BookingListResponse(bookings=bookings)


@router.post("/v1/bookings/{id}/arrived", response_model=BookingDto, operation_id="post_v1_bookings_by_id_arrived", tags=["bookings"])
async def booking_arrived(id: UUID, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> BookingDto:
    async with session.begin():
        return await RouteClosureService(session).booking_arrived(current=current, booking_id=id)


@router.get("/v1/merchants/{id}/calendar", response_model=MerchantBaysResponse, operation_id="get_v1_merchants_by_id_calendar", tags=["merchant"])
async def merchant_calendar(
    id: UUID,
    date_: date | None = Query(default=None, alias="date"),
    current: CurrentUser = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> MerchantBaysResponse:
    async with session.begin():
        bays = await RouteClosureService(session).merchant_calendar(current=current, merchant_id=id, for_date=date_ or datetime.now(UTC).date())
    return MerchantBaysResponse(bays=bays)


@router.post(
    "/v1/merchants/{id}/calendar/maintenance",
    response_model=SlotMaintenanceResponse,
    operation_id="post_v1_merchants_by_id_calendar_maintenance",
    tags=["merchant"],
)
async def merchant_calendar_maintenance(
    id: UUID,
    request: SlotMaintenanceRequest,
    current: CurrentUser = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> SlotMaintenanceResponse:
    async with session.begin():
        return await RouteClosureService(session).mark_maintenance(
            current=current,
            merchant_id=id,
            bay_number=request.bay_number,
            time_slot=request.time_slot,
            status=request.status,
        )


@router.get("/v1/merchants/{id}/golden-hour", response_model=GoldenHourResponse, operation_id="get_v1_merchants_by_id_golden_hour", tags=["merchant"])
async def get_golden_hour(id: UUID, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> GoldenHourResponse:
    async with session.begin():
        rules = await RouteClosureService(session).list_golden_hours(current=current, merchant_id=id)
    return GoldenHourResponse(rules=rules)


@router.put("/v1/merchants/{id}/golden-hour", response_model=GoldenHourResponse, operation_id="put_v1_merchants_by_id_golden_hour", tags=["merchant"])
async def put_golden_hour(
    id: UUID,
    request: GoldenHourUpdateRequest,
    current: CurrentUser = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> GoldenHourResponse:
    async with session.begin():
        rules = await RouteClosureService(session).replace_golden_hours(current=current, merchant_id=id, rules=request.rules)
    return GoldenHourResponse(rules=rules)


@router.get("/v1/ops/data-room/{section}", response_model=OpsDataRoomResponse, operation_id="get_v1_ops_data_room_by_section", tags=["ops"])
async def ops_data_room(section: str, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> OpsDataRoomResponse:
    async with session.begin():
        return await RouteClosureService(session).data_room(current=current, section=section)


@router.post("/v1/ops/exports", response_model=OpsExportResponse, status_code=status.HTTP_202_ACCEPTED, operation_id="post_v1_ops_exports", tags=["ops"])
async def ops_export(request: OpsExportRequest, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> OpsExportResponse:
    async with session.begin():
        return await RouteClosureService(session).create_export(current=current, section=request.section, format=request.format)


@router.get("/v1/ops/exports/{job_id}", response_model=OpsExportResponse, operation_id="get_v1_ops_exports_by_job_id", tags=["ops"])
async def ops_export_status(job_id: UUID, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> OpsExportResponse:
    async with session.begin():
        return await RouteClosureService(session).export_status(current=current, job_id=job_id)


@router.post("/v1/ops/bookings", response_model=OpsConciergeResultResponse, status_code=status.HTTP_201_CREATED, operation_id="post_v1_ops_bookings", tags=["ops"])
async def ops_create_booking(request: OpsCreateBookingRequest, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> OpsConciergeResultResponse:
    async with session.begin():
        booking, audit_id = await RouteClosureService(session).ops_create_booking(
            current=current,
            user_id=request.user_id,
            merchant_id=request.merchant_id,
            merchant_service_id=request.merchant_service_id,
            bay_number=request.bay_number,
            reason=request.reason,
        )
    return OpsConciergeResultResponse(id=booking.id, audit_log_id=audit_id)


@router.post("/v1/ops/bookings/{id}/check-in", response_model=OpsConciergeResultResponse, operation_id="post_v1_ops_bookings_by_id_check_in", tags=["ops"])
async def ops_check_in_booking(id: UUID, request: OpsCheckInRequest, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> OpsConciergeResultResponse:
    async with session.begin():
        booking, audit_id = await RouteClosureService(session).ops_check_in(current=current, booking_id=id, reason=request.reason)
    return OpsConciergeResultResponse(id=booking.id, audit_log_id=audit_id)


@router.post("/v1/ops/evidence/upload", response_model=OpsConciergeResultResponse, status_code=status.HTTP_201_CREATED, operation_id="post_v1_ops_evidence_upload", tags=["ops"])
async def ops_upload_evidence(request: OpsEvidenceUploadRequest, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> OpsConciergeResultResponse:
    async with session.begin():
        evidence_id, audit_id = await RouteClosureService(session).ops_upload_evidence(
            current=current,
            booking_id=request.booking_id,
            type=request.type,
            photo_key=request.photo_key,
            reason=request.reason,
        )
    return OpsConciergeResultResponse(id=evidence_id, audit_log_id=audit_id)


@router.post("/v1/ops/payments/{id}/confirm", response_model=OpsConciergeResultResponse, operation_id="post_v1_ops_payments_by_id_confirm", tags=["ops"])
async def ops_confirm_payment(id: UUID, request: OpsConfirmPaymentRequest, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> OpsConciergeResultResponse:
    async with session.begin():
        payment_id, audit_id = await RouteClosureService(session).ops_confirm_payment(current=current, payment_id=id, reason=request.reason)
    return OpsConciergeResultResponse(id=payment_id, audit_log_id=audit_id)


@router.post("/v1/ops/reward/voucher", response_model=OpsMintVoucherResponse, status_code=status.HTTP_201_CREATED, operation_id="post_v1_ops_reward_voucher", tags=["ops"])
async def ops_mint_reward_voucher(request: OpsMintVoucherRequest, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> OpsMintVoucherResponse:
    async with session.begin():
        return await RouteClosureService(session).ops_mint_voucher(current=current, user_id=request.user_id, voucher_type_code=request.voucher_type_code, reason=request.reason)
