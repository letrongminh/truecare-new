from __future__ import annotations

import math
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError, ErrorCode
from app.core.security import CurrentUser
from app.db.models import Merchant, MerchantService, ServiceTemplate, SlotCapacity
from app.db.session import set_local_context
from app.schemas.marketplace import (
    MerchantBayDto,
    MerchantNearbyDto,
    MerchantServiceDto,
    ServiceTemplateDto,
)

HANOI_LAT = 21.0285
HANOI_LNG = 105.8542
DEFAULT_RADIUS_METERS = 5_000
MAX_RADIUS_METERS = 20_000


def round_to_current_slot(now: datetime | None = None) -> datetime:
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    return current.replace(minute=(current.minute // 30) * 30, second=0, microsecond=0)


def distance_meters(lat_a: float, lng_a: float, lat_b: float, lng_b: float) -> int:
    radius = 6_371_000
    phi_a = math.radians(lat_a)
    phi_b = math.radians(lat_b)
    delta_phi = math.radians(lat_b - lat_a)
    delta_lambda = math.radians(lng_b - lng_a)
    hav = math.sin(delta_phi / 2) ** 2 + math.cos(phi_a) * math.cos(phi_b) * math.sin(delta_lambda / 2) ** 2
    return int(radius * 2 * math.atan2(math.sqrt(hav), math.sqrt(1 - hav)))


class MarketplaceService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_service_templates(self) -> list[ServiceTemplateDto]:
        rows = (await self.session.scalars(select(ServiceTemplate).order_by(ServiceTemplate.name))).all()
        return [
            ServiceTemplateDto(
                id=row.id,
                name=row.name,
                floor_price=row.floor_price,
                ceiling_price=row.ceiling_price,
                duration_min=row.duration_min,
                duration_max=row.duration_max,
                evidence_required=row.evidence_required,
                sop_checklist_url=row.sop_checklist_url,
            )
            for row in rows
        ]

    async def nearby(
        self,
        *,
        current: CurrentUser,
        lat: float | None,
        lng: float | None,
        radius_meters: int = DEFAULT_RADIUS_METERS,
        page: int = 0,
        page_size: int = 20,
        query: str | None = None,
    ) -> tuple[list[MerchantNearbyDto], bool]:
        await set_local_context(self.session, tenant_id=current.tenant_id, user_id=current.user_id, role=current.roles[0] if current.roles else None)
        gps_fallback = lat is None or lng is None
        origin_lat = lat if lat is not None else HANOI_LAT
        origin_lng = lng if lng is not None else HANOI_LNG
        capped_radius = min(max(radius_meters, 1), MAX_RADIUS_METERS)

        stmt = select(Merchant).where(
            Merchant.tenant_id == current.tenant_id,
            Merchant.status == "live",
            Merchant.deleted_at.is_(None),
            Merchant.stale.is_(False),
        )
        if query:
            pattern = f"%{query.strip()}%"
            stmt = stmt.where(or_(Merchant.name.ilike(pattern), Merchant.address.ilike(pattern)))

        rows = (await self.session.scalars(stmt)).all()
        slot_start = round_to_current_slot()
        merchants: list[MerchantNearbyDto] = []
        for row in rows:
            distance = distance_meters(origin_lat, origin_lng, row.latitude, row.longitude)
            if distance > capped_radius:
                continue
            available_bays = await self._available_bays(row.id, slot_start)
            merchants.append(self._merchant_dto(row, distance, available_bays))

        merchants.sort(key=lambda item: (-item.available_bays, -item.rating_average, item.distance_meters))
        start = max(page, 0) * page_size
        return merchants[start : start + page_size], gps_fallback

    async def detail(self, *, current: CurrentUser, merchant_id: UUID) -> MerchantNearbyDto:
        await set_local_context(self.session, tenant_id=current.tenant_id, user_id=current.user_id, role=current.roles[0] if current.roles else None)
        row = await self.session.get(Merchant, merchant_id)
        if row is None or row.tenant_id != current.tenant_id or row.deleted_at is not None:
            raise ApiError(ErrorCode.merchant_not_found, detail="Merchant was not found.")
        return self._merchant_dto(row, 0, await self._available_bays(row.id, round_to_current_slot()))

    async def list_merchant_services(self, *, current: CurrentUser, merchant_id: UUID) -> list[MerchantServiceDto]:
        await self.detail(current=current, merchant_id=merchant_id)
        rows = (
            await self.session.scalars(
                select(MerchantService)
                .where(MerchantService.tenant_id == current.tenant_id, MerchantService.merchant_id == merchant_id, MerchantService.status == "active")
                .order_by(MerchantService.name)
            )
        ).all()
        return [
            MerchantServiceDto(
                id=row.id,
                merchant_id=row.merchant_id,
                template_id=row.template_id,
                name=row.name,
                price=row.price,
                duration_min=row.duration_min,
                duration_max=row.duration_max,
                status=row.status,
                is_custom=row.is_custom,
                description=row.description,
                photo_url=row.photo_url,
            )
            for row in rows
        ]

    async def list_bays(self, *, current: CurrentUser, merchant_id: UUID) -> list[MerchantBayDto]:
        await self.detail(current=current, merchant_id=merchant_id)
        rows = (
            await self.session.scalars(
                select(SlotCapacity)
                .where(
                    SlotCapacity.tenant_id == current.tenant_id,
                    SlotCapacity.merchant_id == merchant_id,
                    SlotCapacity.time_slot >= round_to_current_slot(),
                )
                .order_by(SlotCapacity.time_slot, SlotCapacity.bay_number)
                .limit(200)
            )
        ).all()
        return [
            MerchantBayDto(
                bay_number=row.bay_number,
                time_slot=row.time_slot,
                status=row.status,
            )
            for row in rows
        ]

    async def _available_bays(self, merchant_id: UUID, slot_start: datetime) -> int:
        return (
            await self.session.scalar(
                select(func.count())
                .select_from(SlotCapacity)
                .where(
                    SlotCapacity.merchant_id == merchant_id,
                    SlotCapacity.time_slot == slot_start,
                    SlotCapacity.status == "available",
                )
            )
            or 0
        )

    @staticmethod
    def _merchant_dto(row: Merchant, distance: int, available_bays: int) -> MerchantNearbyDto:
        tags = row.tags if isinstance(row.tags, list) else []
        return MerchantNearbyDto(
            id=row.id,
            name=row.name,
            address=row.address,
            phone=row.phone,
            latitude=row.latitude,
            longitude=row.longitude,
            distance_meters=distance,
            available_bays=available_bays,
            bay_count=row.bay_count,
            rating_average=row.rating_average,
            rating_count=row.rating_count,
            service_tags=[str(tag) for tag in tags],
            storefront_photo_url=row.storefront_photo_url,
            operating_hours_start=row.operating_hours_start,
            operating_hours_end=row.operating_hours_end,
        )
