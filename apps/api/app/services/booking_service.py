from __future__ import annotations

import secrets
from hmac import compare_digest
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError, ErrorCode
from app.core.security import CurrentUser
from app.db.models import Booking, Merchant, MerchantService, ServiceTemplate, SlotCapacity
from app.db.session import set_local_context
from app.domain.states import BookingState
from app.schemas.marketplace import BookingDto, CreateHoldRequest
from app.services.domain_events import DomainEventRepository
from app.services.idempotency_service import IdempotencyService, IdempotencyStatus

HOLD_DURATION_MINUTES = 30
MAX_ACTIVE_HOLDS_PER_USER = 3
MAX_HOLDS_PER_MERCHANT = 2
ACTIVE_USER_STATUSES = (
    BookingState.held.value,
    BookingState.checked_in.value,
    BookingState.in_progress.value,
    BookingState.awaiting_payment.value,
)


class BookingService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_hold(self, *, current: CurrentUser, request: CreateHoldRequest) -> BookingDto:
        await set_local_context(self.session, tenant_id=current.tenant_id, user_id=current.user_id, role=current.roles[0] if current.roles else None)
        request_body = request.model_dump(mode="json")
        idempotency = IdempotencyService(self.session)
        subject = f"user:{current.user_id}:booking-hold"
        decision = await idempotency.check(
            tenant_id=current.tenant_id,
            subject=subject,
            key=request.idempotency_key,
            body=request_body,
        )
        if decision.status == IdempotencyStatus.replay and decision.response is not None:
            return BookingDto.model_validate(decision.response)

        merchant = await self.session.get(Merchant, request.merchant_id)
        if merchant is None or merchant.tenant_id != current.tenant_id or merchant.deleted_at is not None:
            raise ApiError(ErrorCode.merchant_not_found, detail="Merchant was not found.")
        if merchant.status != "live" or merchant.stale:
            raise ApiError(ErrorCode.merchant_not_found, detail="Merchant is not bookable.")
        if request.bay_number > merchant.bay_count:
            raise ApiError(ErrorCode.invalid_booking_hold, detail="Bay number is outside merchant bay count.", extra={"reason": "bay_out_of_range"})

        service = await self.session.get(MerchantService, request.merchant_service_id)
        if service is None or service.tenant_id != current.tenant_id or service.merchant_id != merchant.id or service.status != "active":
            raise ApiError(ErrorCode.merchant_service_not_found, detail="Merchant service was not found.")
        if service.template_id is not None:
            template = await self.session.get(ServiceTemplate, service.template_id)
            if template is not None and not (template.floor_price <= service.price <= template.ceiling_price):
                raise ApiError(ErrorCode.invalid_booking_hold, detail="Service price is outside template bounds.", extra={"reason": "price_out_of_template_range"})

        active_user_holds = await self._active_hold_count(current.user_id)
        if active_user_holds >= MAX_ACTIVE_HOLDS_PER_USER:
            raise ApiError(ErrorCode.hold_limit_exceeded, detail="User has too many active holds.")

        active_merchant_holds = await self._active_hold_count(current.user_id, merchant_id=merchant.id)
        if active_merchant_holds >= MAX_HOLDS_PER_MERCHANT:
            raise ApiError(ErrorCode.hold_limit_exceeded, detail="User has too many active holds at this merchant.")

        now_at = datetime.now(UTC)
        slot_floor = now_at.replace(minute=(now_at.minute // 30) * 30, second=0, microsecond=0)
        expires_at = now_at + timedelta(minutes=HOLD_DURATION_MINUTES)
        candidate = (
            await self.session.scalars(
                select(SlotCapacity)
                .where(
                    SlotCapacity.tenant_id == current.tenant_id,
                    SlotCapacity.merchant_id == merchant.id,
                    SlotCapacity.bay_number == request.bay_number,
                    SlotCapacity.time_slot >= slot_floor,
                    or_(
                        SlotCapacity.status == "available",
                        and_(SlotCapacity.status == "held", SlotCapacity.expires_at < now_at),
                    ),
                )
                .order_by(SlotCapacity.time_slot)
                .with_for_update(skip_locked=True)
                .limit(1)
            )
        ).first()
        if candidate is None:
            raise ApiError(ErrorCode.slot_full, detail="No available slot for this merchant bay.")

        await self.session.execute(
            update(SlotCapacity)
            .where(SlotCapacity.id == candidate.id)
            .values(
                status="held",
                held_by_user_id=current.user_id,
                held_at=now_at,
                expires_at=expires_at,
            )
        )

        booking = Booking(
            id=uuid4(),
            tenant_id=current.tenant_id,
            user_id=current.user_id,
            merchant_id=merchant.id,
            merchant_service_id=service.id,
            slot_capacity_id=candidate.id,
            bay_number=request.bay_number,
            status=BookingState.held.value,
            held_at=now_at,
            expires_at=expires_at,
            total_amount=service.price,
            discount_amount=0,
            idempotency_key=request.idempotency_key,
            check_in_token=secrets.token_hex(16),
            created_at=now_at,
        )
        self.session.add(booking)
        await self.session.flush()

        dto = self._dto(booking)
        await idempotency.store(
            tenant_id=current.tenant_id,
            subject=subject,
            key=request.idempotency_key,
            body=request_body,
            response=dto.model_dump(mode="json"),
        )
        await DomainEventRepository(self.session).emit(
            tenant_id=current.tenant_id,
            aggregate_type="booking",
            aggregate_id=booking.id,
            event_type="booking.held",
            payload={
                "booking_id": str(booking.id),
                "user_id": str(current.user_id),
                "merchant_id": str(merchant.id),
                "expires_at": expires_at.isoformat(),
                "total_amount": service.price,
                "discount_amount": 0,
                "locale": current.locale or "vi",
            },
            idempotency_key=request.idempotency_key,
        )
        return dto

    async def list_user_bookings(self, *, current: CurrentUser) -> list[BookingDto]:
        await set_local_context(self.session, tenant_id=current.tenant_id, user_id=current.user_id, role=current.roles[0] if current.roles else None)
        rows = (
            await self.session.scalars(
                select(Booking)
                .where(Booking.tenant_id == current.tenant_id, Booking.user_id == current.user_id)
                .order_by(Booking.created_at.desc())
                .limit(50)
            )
        ).all()
        return [self._dto(row) for row in rows]

    async def get_user_booking(self, *, current: CurrentUser, booking_id: UUID) -> BookingDto:
        await set_local_context(self.session, tenant_id=current.tenant_id, user_id=current.user_id, role=current.roles[0] if current.roles else None)
        booking = await self.session.get(Booking, booking_id)
        if booking is None or booking.tenant_id != current.tenant_id or booking.user_id != current.user_id:
            raise ApiError(ErrorCode.booking_not_found, detail="Booking was not found.")
        return self._dto(booking)

    async def cancel(self, *, current: CurrentUser, booking_id: UUID, reason: str) -> BookingDto:
        await set_local_context(self.session, tenant_id=current.tenant_id, user_id=current.user_id, role=current.roles[0] if current.roles else None)
        booking = await self.session.get(Booking, booking_id)
        if booking is None or booking.tenant_id != current.tenant_id or booking.user_id != current.user_id:
            raise ApiError(ErrorCode.booking_not_found, detail="Booking was not found.")
        if booking.status != BookingState.held.value:
            raise ApiError(ErrorCode.invalid_booking_state, detail="Only held bookings can be cancelled.")

        now_at = datetime.now(UTC)
        booking.status = BookingState.cancelled.value
        booking.updated_at = now_at
        booking.check_in_token = ""
        await self.session.execute(
            update(SlotCapacity)
            .where(SlotCapacity.id == booking.slot_capacity_id, SlotCapacity.status == "held")
            .values(status="available", held_by_user_id=None, held_at=None, expires_at=None)
        )
        await DomainEventRepository(self.session).emit(
            tenant_id=current.tenant_id,
            aggregate_type="booking",
            aggregate_id=booking.id,
            event_type="booking.cancelled",
            payload={
                "booking_id": str(booking.id),
                "user_id": str(current.user_id),
                "merchant_id": str(booking.merchant_id),
                "reason": reason,
                "locale": current.locale or "vi",
            },
        )
        await self.session.flush()
        return self._dto(booking)

    async def check_in(self, *, current: CurrentUser, booking_id: UUID, code: str) -> BookingDto:
        await set_local_context(self.session, tenant_id=current.tenant_id, user_id=current.user_id, role=current.roles[0] if current.roles else None)
        booking = await self.session.get(Booking, booking_id)
        if booking is None or booking.tenant_id != current.tenant_id:
            raise ApiError(ErrorCode.booking_not_found, detail="Booking was not found.")
        await self._require_merchant_operator(current=current, merchant_id=booking.merchant_id)
        if booking.status == BookingState.expired.value or booking.expires_at <= datetime.now(UTC):
            raise ApiError(ErrorCode.hold_expired, detail="Booking hold has expired.")
        if booking.status != BookingState.held.value:
            raise ApiError(ErrorCode.invalid_booking_state, detail="Booking is already checked in or no longer checkable.")

        expected = booking.check_in_token or ""
        expected_short = expected[:6].upper()
        supplied = code.strip()
        if not (compare_digest(supplied, expected) or compare_digest(supplied.upper(), expected_short)):
            raise ApiError(ErrorCode.invalid_check_in_code, detail="Check-in code is invalid.")

        now_at = datetime.now(UTC)
        booking.status = BookingState.checked_in.value
        booking.checked_in_at = now_at
        booking.updated_at = now_at
        await DomainEventRepository(self.session).emit(
            tenant_id=current.tenant_id,
            aggregate_type="booking",
            aggregate_id=booking.id,
            event_type="booking.checked_in",
            payload={
                "booking_id": str(booking.id),
                "user_id": str(booking.user_id),
                "merchant_id": str(booking.merchant_id),
                "locale": current.locale or "vi",
            },
        )
        await self.session.flush()
        return self._dto(booking)

    async def start_service(self, *, current: CurrentUser, booking_id: UUID) -> BookingDto:
        return await self._merchant_transition(
            current=current,
            booking_id=booking_id,
            from_status=BookingState.checked_in.value,
            to_status=BookingState.in_progress.value,
            event_type="booking.in_progress",
        )

    async def complete_service(self, *, current: CurrentUser, booking_id: UUID) -> BookingDto:
        return await self._merchant_transition(
            current=current,
            booking_id=booking_id,
            from_status=BookingState.in_progress.value,
            to_status=BookingState.awaiting_payment.value,
            event_type="booking.service_complete",
            stamp_service_completed=True,
        )

    async def merchant_queue(self, *, current: CurrentUser, merchant_id: UUID) -> list[BookingDto]:
        await set_local_context(self.session, tenant_id=current.tenant_id, user_id=current.user_id, role=current.roles[0] if current.roles else None)
        merchant = await self.session.get(Merchant, merchant_id)
        if merchant is None or merchant.tenant_id != current.tenant_id:
            raise ApiError(ErrorCode.merchant_not_found, detail="Merchant was not found.")
        if merchant.user_id != current.user_id and not set(current.roles).intersection({"ops", "admin"}):
            raise ApiError(ErrorCode.forbidden, detail="Merchant queue is available only to the merchant owner or ops.")
        rows = (
            await self.session.scalars(
                select(Booking)
                .where(
                    Booking.tenant_id == current.tenant_id,
                    Booking.merchant_id == merchant_id,
                    Booking.status.in_([BookingState.held.value, BookingState.checked_in.value, BookingState.in_progress.value]),
                )
                .order_by(Booking.held_at)
                .limit(100)
            )
        ).all()
        return [self._dto(row) for row in rows]

    async def _merchant_transition(
        self,
        *,
        current: CurrentUser,
        booking_id: UUID,
        from_status: str,
        to_status: str,
        event_type: str,
        stamp_service_completed: bool = False,
    ) -> BookingDto:
        await set_local_context(self.session, tenant_id=current.tenant_id, user_id=current.user_id, role=current.roles[0] if current.roles else None)
        booking = await self.session.get(Booking, booking_id)
        if booking is None or booking.tenant_id != current.tenant_id:
            raise ApiError(ErrorCode.booking_not_found, detail="Booking was not found.")
        await self._require_merchant_operator(current=current, merchant_id=booking.merchant_id)
        if booking.status != from_status:
            raise ApiError(ErrorCode.invalid_booking_state, detail=f"Booking must be {from_status} before this transition.")

        now_at = datetime.now(UTC)
        booking.status = to_status
        booking.updated_at = now_at
        if stamp_service_completed:
            booking.service_completed_at = now_at
        await DomainEventRepository(self.session).emit(
            tenant_id=current.tenant_id,
            aggregate_type="booking",
            aggregate_id=booking.id,
            event_type=event_type,
            payload={
                "booking_id": str(booking.id),
                "user_id": str(booking.user_id),
                "merchant_id": str(booking.merchant_id),
                "locale": current.locale or "vi",
            },
        )
        await self.session.flush()
        return self._dto(booking)

    async def _require_merchant_operator(self, *, current: CurrentUser, merchant_id: UUID) -> Merchant:
        merchant = await self.session.get(Merchant, merchant_id)
        if merchant is None or merchant.tenant_id != current.tenant_id:
            raise ApiError(ErrorCode.merchant_not_found, detail="Merchant was not found.")
        if merchant.user_id != current.user_id and not set(current.roles).intersection({"ops", "admin"}):
            raise ApiError(ErrorCode.forbidden, detail="Booking belongs to another merchant.")
        return merchant

    async def _active_hold_count(self, user_id: UUID, *, merchant_id: UUID | None = None) -> int:
        stmt = select(func.count()).select_from(Booking).where(Booking.user_id == user_id, Booking.status.in_(ACTIVE_USER_STATUSES))
        if merchant_id is not None:
            stmt = stmt.where(Booking.merchant_id == merchant_id)
        return (await self.session.scalar(stmt)) or 0

    @staticmethod
    def _dto(row: Booking) -> BookingDto:
        return BookingDto(
            id=row.id,
            merchant_id=row.merchant_id,
            merchant_service_id=row.merchant_service_id,
            bay_number=row.bay_number,
            status=row.status,
            total_amount=row.total_amount,
            discount_amount=row.discount_amount,
            deposit_amount=row.deposit_amount,
            held_at=row.held_at,
            expires_at=row.expires_at,
            checked_in_at=row.checked_in_at,
            service_completed_at=row.service_completed_at,
            completed_at=row.completed_at,
            payment_method=row.payment_method,
            payment_status=row.payment_status,
            created_at=row.created_at,
            check_in_token=row.check_in_token or None,
        )
