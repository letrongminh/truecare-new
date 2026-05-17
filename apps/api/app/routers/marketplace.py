from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, require_user
from app.db.session import get_session
from app.schemas.marketplace import (
    BookingDto,
    BookingListResponse,
    CancelBookingRequest,
    CheckInRequest,
    CreateHoldRequest,
    MerchantBaysResponse,
    MerchantNearbyDto,
    MerchantQueueResponse,
    MerchantServicesResponse,
    MerchantsNearbyResponse,
    ServiceTemplatesResponse,
)
from app.services.booking_service import BookingService
from app.services.marketplace_service import DEFAULT_RADIUS_METERS, MAX_RADIUS_METERS, MarketplaceService

router = APIRouter(tags=["marketplace"])

IMPLEMENTED_MARKETPLACE_ROUTES = {
    ("GET", "/v1/search"),
    ("GET", "/v1/service-templates"),
    ("GET", "/v1/merchants/nearby"),
    ("GET", "/v1/merchants/{id}"),
    ("GET", "/v1/merchants/{id}/services"),
    ("GET", "/v1/merchants/{id}/bays"),
    ("GET", "/v1/merchants/{id}/queue"),
    ("POST", "/v1/bookings/holds"),
    ("GET", "/v1/bookings"),
    ("GET", "/v1/bookings/{id}"),
    ("POST", "/v1/bookings/{id}/cancel"),
    ("POST", "/v1/bookings/{id}/check-in"),
    ("POST", "/v1/bookings/{id}/start-service"),
    ("POST", "/v1/bookings/{id}/complete-service"),
}


@router.get("/v1/service-templates", response_model=ServiceTemplatesResponse, operation_id="get_v1_service_templates", tags=["search"])
async def list_service_templates(session: AsyncSession = Depends(get_session)) -> ServiceTemplatesResponse:
    return ServiceTemplatesResponse(templates=await MarketplaceService(session).list_service_templates())


@router.get("/v1/search", response_model=MerchantsNearbyResponse, operation_id="get_v1_search", tags=["search"])
async def search(
    q: str | None = Query(default=None, max_length=120),
    lat: float | None = Query(default=None, ge=-90, le=90),
    lng: float | None = Query(default=None, ge=-180, le=180),
    type: str = Query(default="merchant", pattern="^(merchant|place)$"),
    current: CurrentUser = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> MerchantsNearbyResponse:
    if type == "place":
        return MerchantsNearbyResponse(merchants=[], total=0, gps_fallback=lat is None or lng is None)
    async with session.begin():
        merchants, gps_fallback = await MarketplaceService(session).nearby(current=current, lat=lat, lng=lng, query=q)
    return MerchantsNearbyResponse(merchants=merchants, total=len(merchants), gps_fallback=gps_fallback)


@router.get("/v1/merchants/nearby", response_model=MerchantsNearbyResponse, operation_id="get_v1_merchants_nearby", tags=["merchants"])
async def nearby_merchants(
    lat: float | None = Query(default=None, ge=-90, le=90),
    lng: float | None = Query(default=None, ge=-180, le=180),
    radius: int = Query(default=DEFAULT_RADIUS_METERS, ge=1, le=MAX_RADIUS_METERS),
    page: int = Query(default=0, ge=0),
    current: CurrentUser = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> MerchantsNearbyResponse:
    async with session.begin():
        merchants, gps_fallback = await MarketplaceService(session).nearby(current=current, lat=lat, lng=lng, radius_meters=radius, page=page)
    return MerchantsNearbyResponse(merchants=merchants, total=len(merchants), gps_fallback=gps_fallback)


@router.get("/v1/merchants/{id}", response_model=MerchantNearbyDto, operation_id="get_v1_merchants_by_id", tags=["merchants"])
async def merchant_detail(
    id: UUID,
    current: CurrentUser = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> MerchantNearbyDto:
    async with session.begin():
        return await MarketplaceService(session).detail(current=current, merchant_id=id)


@router.get("/v1/merchants/{id}/services", response_model=MerchantServicesResponse, operation_id="get_v1_merchants_by_id_services", tags=["merchants"])
async def merchant_services(
    id: UUID,
    current: CurrentUser = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> MerchantServicesResponse:
    async with session.begin():
        services = await MarketplaceService(session).list_merchant_services(current=current, merchant_id=id)
    return MerchantServicesResponse(services=services)


@router.get("/v1/merchants/{id}/bays", response_model=MerchantBaysResponse, operation_id="get_v1_merchants_by_id_bays", tags=["merchants"])
async def merchant_bays(
    id: UUID,
    current: CurrentUser = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> MerchantBaysResponse:
    async with session.begin():
        bays = await MarketplaceService(session).list_bays(current=current, merchant_id=id)
    return MerchantBaysResponse(bays=bays)


@router.get("/v1/merchants/{id}/queue", response_model=MerchantQueueResponse, operation_id="get_v1_merchants_by_id_queue", tags=["merchant"])
async def merchant_queue(
    id: UUID,
    current: CurrentUser = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> MerchantQueueResponse:
    async with session.begin():
        queue = await BookingService(session).merchant_queue(current=current, merchant_id=id)
    return MerchantQueueResponse(queue=queue)


@router.post("/v1/bookings/holds", response_model=BookingDto, status_code=status.HTTP_201_CREATED, operation_id="post_v1_bookings_holds", tags=["bookings"])
async def create_booking_hold(
    request: CreateHoldRequest,
    current: CurrentUser = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> BookingDto:
    async with session.begin():
        return await BookingService(session).create_hold(current=current, request=request)


@router.get("/v1/bookings", response_model=BookingListResponse, operation_id="get_v1_bookings", tags=["bookings"])
async def list_bookings(
    current: CurrentUser = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> BookingListResponse:
    async with session.begin():
        bookings = await BookingService(session).list_user_bookings(current=current)
    return BookingListResponse(bookings=bookings)


@router.get("/v1/bookings/{id}", response_model=BookingDto, operation_id="get_v1_bookings_by_id", tags=["bookings"])
async def get_booking(
    id: UUID,
    current: CurrentUser = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> BookingDto:
    async with session.begin():
        return await BookingService(session).get_user_booking(current=current, booking_id=id)


@router.post("/v1/bookings/{id}/cancel", response_model=BookingDto, operation_id="post_v1_bookings_by_id_cancel", tags=["bookings"])
async def cancel_booking(
    id: UUID,
    request: CancelBookingRequest,
    current: CurrentUser = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> BookingDto:
    async with session.begin():
        return await BookingService(session).cancel(current=current, booking_id=id, reason=request.reason)


@router.post("/v1/bookings/{id}/check-in", response_model=BookingDto, operation_id="post_v1_bookings_by_id_check_in", tags=["merchant"])
async def check_in_booking(
    id: UUID,
    request: CheckInRequest,
    current: CurrentUser = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> BookingDto:
    async with session.begin():
        return await BookingService(session).check_in(current=current, booking_id=id, code=request.code)


@router.post("/v1/bookings/{id}/start-service", response_model=BookingDto, operation_id="post_v1_bookings_by_id_start_service", tags=["merchant"])
async def start_booking_service(
    id: UUID,
    current: CurrentUser = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> BookingDto:
    async with session.begin():
        return await BookingService(session).start_service(current=current, booking_id=id)


@router.post("/v1/bookings/{id}/complete-service", response_model=BookingDto, operation_id="post_v1_bookings_by_id_complete_service", tags=["merchant"])
async def complete_booking_service(
    id: UUID,
    current: CurrentUser = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> BookingDto:
    async with session.begin():
        return await BookingService(session).complete_service(current=current, booking_id=id)
