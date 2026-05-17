from __future__ import annotations

import secrets
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID, uuid4

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError, ErrorCode
from app.core.security import CurrentUser
from app.db.models import (
    AuditLog,
    Booking,
    Complaint,
    DataExportJob,
    Evidence,
    Merchant,
    MerchantGoldenHour,
    MerchantService,
    Payment,
    RewardVoucher,
    ServiceTemplate,
    SlotCapacity,
    User,
)
from app.db.session import set_local_context
from app.domain.states import BookingState
from app.schemas.marketplace import BookingDto, MerchantBayDto
from app.schemas.route_closure import (
    GoldenHourRuleDto,
    GoldenHourRuleWrite,
    OpsDataRoomResponse,
    OpsExportResponse,
    OpsMintVoucherResponse,
    SlotMaintenanceResponse,
)
from app.services.booking_service import HOLD_DURATION_MINUTES, BookingService
from app.services.domain_events import DomainEventRepository
from app.services.phase23_service import Phase23Service

OPS_ROLES = {"ops", "admin", "finance_ops", "quality_ops"}


class RouteClosureService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def me_bookings(self, *, current: CurrentUser) -> list[BookingDto]:
        return await BookingService(self.session).list_user_bookings(current=current)

    async def booking_arrived(self, *, current: CurrentUser, booking_id: UUID) -> BookingDto:
        await self._context(current)
        booking = await self.session.get(Booking, booking_id)
        if booking is None or booking.tenant_id != current.tenant_id or booking.user_id != current.user_id:
            raise ApiError(ErrorCode.booking_not_found, detail="Booking was not found.")
        if booking.status not in {BookingState.held.value, BookingState.checked_in.value, BookingState.in_progress.value}:
            raise ApiError(ErrorCode.invalid_booking_state, detail="Booking is not in an arrival-capable state.")
        booking.updated_at = datetime.now(UTC)
        await DomainEventRepository(self.session).emit(
            tenant_id=current.tenant_id,
            aggregate_type="booking",
            aggregate_id=booking.id,
            event_type="booking.consumer_arrived",
            payload={"booking_id": str(booking.id), "merchant_id": str(booking.merchant_id), "user_id": str(booking.user_id)},
        )
        await self.session.flush()
        return BookingService._dto(booking)

    async def merchant_calendar(self, *, current: CurrentUser, merchant_id: UUID, for_date: date) -> list[MerchantBayDto]:
        await self._context(current)
        await self._require_merchant_operator(current=current, merchant_id=merchant_id)
        start_at = datetime.combine(for_date, time.min, tzinfo=UTC)
        end_at = start_at + timedelta(days=1)
        rows = (
            await self.session.scalars(
                select(SlotCapacity)
                .where(
                    SlotCapacity.tenant_id == current.tenant_id,
                    SlotCapacity.merchant_id == merchant_id,
                    SlotCapacity.time_slot >= start_at,
                    SlotCapacity.time_slot < end_at,
                )
                .order_by(SlotCapacity.time_slot, SlotCapacity.bay_number)
            )
        ).all()
        return [MerchantBayDto(bay_number=row.bay_number, time_slot=row.time_slot, status=row.status) for row in rows]

    async def mark_maintenance(
        self,
        *,
        current: CurrentUser,
        merchant_id: UUID,
        bay_number: int,
        time_slot: datetime,
        status: str,
    ) -> SlotMaintenanceResponse:
        await self._context(current)
        merchant = await self._require_merchant_operator(current=current, merchant_id=merchant_id)
        if bay_number > merchant.bay_count:
            raise ApiError(ErrorCode.invalid_booking_hold, detail="Bay number is outside merchant bay count.", extra={"reason": "bay_out_of_range"})

        target_status = "available" if status == "available" else "closed"
        slot = await self.session.scalar(
            select(SlotCapacity).where(
                SlotCapacity.tenant_id == current.tenant_id,
                SlotCapacity.merchant_id == merchant_id,
                SlotCapacity.bay_number == bay_number,
                SlotCapacity.time_slot == time_slot,
            )
        )
        if slot is None:
            slot = SlotCapacity(
                id=uuid4(),
                tenant_id=current.tenant_id,
                merchant_id=merchant_id,
                bay_number=bay_number,
                time_slot=time_slot,
                status=target_status,
            )
            self.session.add(slot)
        else:
            slot.status = target_status
            slot.held_by_user_id = None
            slot.held_at = None
            slot.expires_at = None
        audit_id = self._audit(
            current=current,
            action="merchant.calendar.maintenance",
            target_kind="slot_capacity",
            target_id=slot.id,
            payload={"merchant_id": str(merchant_id), "bay_number": bay_number, "time_slot": time_slot.isoformat(), "status": target_status},
        )
        await self.session.flush()
        _ = audit_id
        return SlotMaintenanceResponse(updated=1, status=target_status)

    async def list_golden_hours(self, *, current: CurrentUser, merchant_id: UUID) -> list[GoldenHourRuleDto]:
        await self._context(current)
        await self._require_merchant_operator(current=current, merchant_id=merchant_id)
        rows = (
            await self.session.scalars(
                select(MerchantGoldenHour)
                .where(MerchantGoldenHour.tenant_id == current.tenant_id, MerchantGoldenHour.merchant_id == merchant_id)
                .order_by(MerchantGoldenHour.day_of_week)
            )
        ).all()
        return [self._golden_hour_dto(row) for row in rows]

    async def replace_golden_hours(self, *, current: CurrentUser, merchant_id: UUID, rules: list[GoldenHourRuleWrite]) -> list[GoldenHourRuleDto]:
        await self._context(current)
        await self._require_merchant_operator(current=current, merchant_id=merchant_id)
        seen_days: set[int] = set()
        now = datetime.now(UTC)
        for rule in rules:
            if rule.day_of_week in seen_days:
                raise ApiError(ErrorCode.invalid_booking_hold, detail="Duplicate golden hour day.", extra={"day_of_week": rule.day_of_week})
            if rule.end_time <= rule.start_time:
                raise ApiError(ErrorCode.invalid_booking_hold, detail="Golden Hour end time must be after start time.")
            seen_days.add(rule.day_of_week)

        existing = {
            row.day_of_week: row
            for row in (
                await self.session.scalars(
                    select(MerchantGoldenHour).where(MerchantGoldenHour.tenant_id == current.tenant_id, MerchantGoldenHour.merchant_id == merchant_id)
                )
            ).all()
        }
        for day, row in existing.items():
            if day not in seen_days:
                await self.session.delete(row)
        for rule in rules:
            row = existing.get(rule.day_of_week)
            if row is None:
                row = MerchantGoldenHour(
                    id=uuid4(),
                    tenant_id=current.tenant_id,
                    merchant_id=merchant_id,
                    day_of_week=rule.day_of_week,
                    start_time=rule.start_time,
                    end_time=rule.end_time,
                    discount_percent=rule.discount_percent,
                )
                self.session.add(row)
            else:
                row.start_time = rule.start_time
                row.end_time = rule.end_time
                row.discount_percent = rule.discount_percent
                row.updated_at = now
        self._audit(
            current=current,
            action="merchant.golden_hour.update",
            target_kind="merchant",
            target_id=merchant_id,
            payload={"rules": [rule.model_dump() for rule in rules]},
        )
        await self.session.flush()
        return await self.list_golden_hours(current=current, merchant_id=merchant_id)

    async def data_room(self, *, current: CurrentUser, section: str) -> OpsDataRoomResponse:
        await self._require_ops(current)
        generated_at = datetime.now(UTC)
        if section == "bookings":
            total = await self._count(current.tenant_id, Booking)
            completed = await self._count(current.tenant_id, Booking, Booking.status.in_({BookingState.completed.value, BookingState.rated.value}))
            rows = (
                await self.session.scalars(select(Booking).where(Booking.tenant_id == current.tenant_id).order_by(Booking.created_at.desc()).limit(25))
            ).all()
            return OpsDataRoomResponse(
                section=section,
                generated_at=generated_at,
                metrics={"total_bookings": total, "completed_bookings": completed},
                rows=[
                    {
                        "id": str(row.id),
                        "merchant_id": str(row.merchant_id),
                        "user_id": str(row.user_id),
                        "status": row.status,
                        "total_amount": row.total_amount,
                    }
                    for row in rows
                ],
            )
        if section in {"merchant_pipeline", "merchants"}:
            total = await self._count(current.tenant_id, Merchant)
            live = await self._count(current.tenant_id, Merchant, Merchant.status == "live")
            rows = (
                await self.session.scalars(select(Merchant).where(Merchant.tenant_id == current.tenant_id).order_by(Merchant.created_at.desc()).limit(25))
            ).all()
            return OpsDataRoomResponse(
                section=section,
                generated_at=generated_at,
                metrics={"total_merchants": total, "live_merchants": live},
                rows=[{"id": str(row.id), "name": row.name, "status": row.status, "pipeline_status": row.pipeline_status} for row in rows],
            )
        if section in {"commission", "payments"}:
            payments = (
                await self.session.scalars(select(Payment).where(Payment.tenant_id == current.tenant_id).order_by(Payment.created_at.desc()).limit(25))
            ).all()
            return OpsDataRoomResponse(
                section=section,
                generated_at=generated_at,
                metrics={
                    "total_payments": await self._count(current.tenant_id, Payment),
                    "commission_receivable": sum(row.commission_amount for row in payments),
                },
                rows=[{"id": str(row.id), "status": row.status, "amount": row.amount, "commission_amount": row.commission_amount} for row in payments],
            )
        if section == "complaints":
            rows = (
                await self.session.scalars(select(Complaint).where(Complaint.tenant_id == current.tenant_id).order_by(Complaint.created_at.desc()).limit(25))
            ).all()
            return OpsDataRoomResponse(
                section=section,
                generated_at=generated_at,
                metrics={"total_complaints": await self._count(current.tenant_id, Complaint), "open_complaints": await self._count(current.tenant_id, Complaint, Complaint.status != "resolved")},
                rows=[{"id": str(row.id), "status": row.status, "category": row.category, "merchant_id": str(row.merchant_id)} for row in rows],
            )
        if section == "rewards":
            rows = (
                await self.session.scalars(select(RewardVoucher).where(RewardVoucher.tenant_id == current.tenant_id).order_by(RewardVoucher.issued_at.desc()).limit(25))
            ).all()
            return OpsDataRoomResponse(
                section=section,
                generated_at=generated_at,
                metrics={"total_vouchers": await self._count(current.tenant_id, RewardVoucher)},
                rows=[{"id": str(row.id), "user_id": str(row.user_id), "status": row.status, "expires_at": row.expires_at.isoformat()} for row in rows],
            )
        raise ApiError(ErrorCode.resource_not_found, detail="Data room section was not found.")

    async def create_export(self, *, current: CurrentUser, section: str, format: str) -> OpsExportResponse:
        await self._require_ops(current)
        now = datetime.now(UTC)
        row = DataExportJob(
            id=uuid4(),
            tenant_id=current.tenant_id,
            user_id=current.user_id,
            status="completed",
            bundle_url=f"local://exports/ops/{section}/{uuid4().hex}.{format}",
            expires_at=now + timedelta(days=7),
            completed_at=now,
        )
        self.session.add(row)
        self._audit(current=current, action="ops_export.create", target_kind="data_export_job", target_id=row.id, payload={"section": section, "format": format})
        await self.session.flush()
        return OpsExportResponse(job_id=row.id, status=row.status, bundle_url=row.bundle_url, expires_at=row.expires_at)

    async def export_status(self, *, current: CurrentUser, job_id: UUID) -> OpsExportResponse:
        await self._require_ops(current)
        row = await self.session.scalar(select(DataExportJob).where(DataExportJob.id == job_id, DataExportJob.tenant_id == current.tenant_id))
        if row is None:
            raise ApiError(ErrorCode.resource_not_found, detail="Export job was not found.")
        return OpsExportResponse(job_id=row.id, status=row.status, bundle_url=row.bundle_url, expires_at=row.expires_at)

    async def ops_create_booking(
        self,
        *,
        current: CurrentUser,
        user_id: UUID,
        merchant_id: UUID,
        merchant_service_id: UUID,
        bay_number: int,
        reason: str,
    ) -> tuple[BookingDto, UUID]:
        await self._require_ops(current)
        user = await self.session.get(User, user_id)
        if user is None or user.tenant_id != current.tenant_id or user.deleted_at is not None:
            raise ApiError(ErrorCode.resource_not_found, detail="User was not found.")
        merchant = await self.session.get(Merchant, merchant_id)
        if merchant is None or merchant.tenant_id != current.tenant_id or merchant.status != "live":
            raise ApiError(ErrorCode.merchant_not_found, detail="Merchant was not found.")
        service = await self.session.get(MerchantService, merchant_service_id)
        if service is None or service.tenant_id != current.tenant_id or service.merchant_id != merchant_id or service.status != "active":
            raise ApiError(ErrorCode.merchant_service_not_found, detail="Merchant service was not found.")
        if bay_number > merchant.bay_count:
            raise ApiError(ErrorCode.invalid_booking_hold, detail="Bay number is outside merchant bay count.", extra={"reason": "bay_out_of_range"})

        now = datetime.now(UTC)
        slot_floor = now.replace(minute=(now.minute // 30) * 30, second=0, microsecond=0)
        slot = (
            await self.session.scalars(
                select(SlotCapacity)
                .where(
                    SlotCapacity.tenant_id == current.tenant_id,
                    SlotCapacity.merchant_id == merchant_id,
                    SlotCapacity.bay_number == bay_number,
                    SlotCapacity.time_slot >= slot_floor,
                    or_(SlotCapacity.status == "available", and_(SlotCapacity.status == "held", SlotCapacity.expires_at < now)),
                )
                .order_by(SlotCapacity.time_slot)
                .with_for_update(skip_locked=True)
                .limit(1)
            )
        ).first()
        if slot is None:
            raise ApiError(ErrorCode.slot_full, detail="No available slot for this merchant bay.")

        expires_at = now + timedelta(minutes=HOLD_DURATION_MINUTES)
        await self.session.execute(
            update(SlotCapacity)
            .where(SlotCapacity.id == slot.id)
            .values(status="held", held_by_user_id=user.id, held_at=now, expires_at=expires_at)
        )
        booking = Booking(
            id=uuid4(),
            tenant_id=current.tenant_id,
            user_id=user.id,
            merchant_id=merchant_id,
            merchant_service_id=service.id,
            slot_capacity_id=slot.id,
            bay_number=bay_number,
            status=BookingState.held.value,
            held_at=now,
            expires_at=expires_at,
            total_amount=service.price,
            discount_amount=0,
            idempotency_key=f"ops-{uuid4().hex}",
            check_in_token=secrets.token_hex(16),
            created_at=now,
        )
        self.session.add(booking)
        audit_id = self._audit(current=current, action="ops_booking.create", target_kind="booking", target_id=booking.id, payload={"reason": reason, "user_id": str(user.id)})
        await DomainEventRepository(self.session).emit(
            tenant_id=current.tenant_id,
            aggregate_type="booking",
            aggregate_id=booking.id,
            event_type="booking.held_by_ops",
            payload={"booking_id": str(booking.id), "reason": reason},
        )
        await self.session.flush()
        return BookingService._dto(booking), audit_id

    async def ops_check_in(self, *, current: CurrentUser, booking_id: UUID, reason: str) -> tuple[BookingDto, UUID]:
        await self._require_ops(current)
        booking = await self.session.get(Booking, booking_id)
        if booking is None or booking.tenant_id != current.tenant_id:
            raise ApiError(ErrorCode.booking_not_found, detail="Booking was not found.")
        if booking.status == BookingState.expired.value or booking.expires_at <= datetime.now(UTC):
            raise ApiError(ErrorCode.hold_expired, detail="Booking hold has expired.")
        if booking.status != BookingState.held.value:
            raise ApiError(ErrorCode.invalid_booking_state, detail="Booking is already checked in or no longer checkable.")
        now = datetime.now(UTC)
        booking.status = BookingState.checked_in.value
        booking.checked_in_at = now
        booking.updated_at = now
        audit_id = self._audit(current=current, action="ops_booking.check_in", target_kind="booking", target_id=booking.id, payload={"reason": reason})
        await DomainEventRepository(self.session).emit(
            tenant_id=current.tenant_id,
            aggregate_type="booking",
            aggregate_id=booking.id,
            event_type="booking.checked_in_by_ops",
            payload={"booking_id": str(booking.id), "reason": reason},
        )
        await self.session.flush()
        return BookingService._dto(booking), audit_id

    async def ops_upload_evidence(self, *, current: CurrentUser, booking_id: UUID, type: str, photo_key: str, reason: str) -> tuple[UUID, UUID]:
        await self._require_ops(current)
        booking = await self.session.get(Booking, booking_id)
        if booking is None or booking.tenant_id != current.tenant_id:
            raise ApiError(ErrorCode.booking_not_found, detail="Booking was not found.")
        now = datetime.now(UTC)
        evidence = Evidence(
            id=uuid4(),
            tenant_id=current.tenant_id,
            booking_id=booking.id,
            type=type,
            object_key=photo_key,
            photo_url=f"local://truecare/{photo_key}",
            content_type="image/jpeg",
            status="processed",
            quality="valid",
            watermarked_at=now,
            exif_stripped=True,
            uploaded_at=now,
        )
        self.session.add(evidence)
        audit_id = self._audit(current=current, action="ops_evidence.upload", target_kind="evidence", target_id=evidence.id, payload={"reason": reason, "booking_id": str(booking.id)})
        await DomainEventRepository(self.session).emit(
            tenant_id=current.tenant_id,
            aggregate_type="evidence",
            aggregate_id=evidence.id,
            event_type="evidence.uploaded_by_ops",
            payload={"evidence_id": str(evidence.id), "booking_id": str(booking.id), "reason": reason},
        )
        await self.session.flush()
        return evidence.id, audit_id

    async def ops_confirm_payment(self, *, current: CurrentUser, payment_id: UUID, reason: str) -> tuple[UUID, UUID]:
        await self._require_ops(current)
        payment = await Phase23Service(self.session).merchant_confirmed_payment(current=current, payment_id=payment_id, ops_confirmed=True)
        audit_id = self._audit(current=current, action="ops_payment.confirm", target_kind="payment", target_id=payment.id, payload={"reason": reason})
        await self.session.flush()
        return payment.id, audit_id

    async def ops_mint_voucher(self, *, current: CurrentUser, user_id: UUID, voucher_type_code: str | None, reason: str) -> OpsMintVoucherResponse:
        await self._require_ops(current)
        user = await self.session.get(User, user_id)
        if user is None or user.tenant_id != current.tenant_id or user.deleted_at is not None:
            raise ApiError(ErrorCode.resource_not_found, detail="User was not found.")
        template_id = await self._voucher_template_id(voucher_type_code)
        now = datetime.now(UTC)
        voucher = RewardVoucher(
            id=uuid4(),
            tenant_id=current.tenant_id,
            user_id=user.id,
            service_template_id=template_id,
            stamp_threshold_reached_at=now,
            expires_at=now + timedelta(days=90),
            status="issued",
        )
        self.session.add(voucher)
        audit_id = self._audit(current=current, action="ops_reward.voucher", target_kind="reward_voucher", target_id=voucher.id, payload={"reason": reason, "user_id": str(user.id)})
        await self.session.flush()
        return OpsMintVoucherResponse(voucher_id=voucher.id, expires_at=voucher.expires_at, audit_log_id=audit_id)

    async def _voucher_template_id(self, voucher_type_code: str | None) -> UUID | None:
        if not voucher_type_code:
            return None
        try:
            template_id = UUID(voucher_type_code)
        except ValueError:
            template_id = None
        if template_id is not None:
            template = await self.session.get(ServiceTemplate, template_id)
        else:
            template = await self.session.scalar(select(ServiceTemplate).where(func.lower(ServiceTemplate.name) == voucher_type_code.lower()).limit(1))
        return template.id if template is not None else None

    async def _count(self, tenant_id: UUID, model: type, *criteria: object) -> int:
        stmt = select(func.count()).select_from(model).where(model.tenant_id == tenant_id)
        for criterion in criteria:
            stmt = stmt.where(criterion)
        return int(await self.session.scalar(stmt) or 0)

    async def _context(self, current: CurrentUser) -> None:
        await set_local_context(self.session, tenant_id=current.tenant_id, user_id=current.user_id, role=current.roles[0] if current.roles else None)

    async def _require_ops(self, current: CurrentUser) -> None:
        await self._context(current)
        if not set(current.roles).intersection(OPS_ROLES):
            raise ApiError(ErrorCode.forbidden, detail="Ops role required.")

    async def _require_merchant_operator(self, *, current: CurrentUser, merchant_id: UUID) -> Merchant:
        merchant = await self.session.get(Merchant, merchant_id)
        if merchant is None or merchant.tenant_id != current.tenant_id or merchant.deleted_at is not None:
            raise ApiError(ErrorCode.merchant_not_found, detail="Merchant was not found.")
        if merchant.user_id != current.user_id and not set(current.roles).intersection(OPS_ROLES):
            raise ApiError(ErrorCode.forbidden, detail="Not authorized for this merchant.")
        return merchant

    def _audit(self, *, current: CurrentUser, action: str, target_kind: str, target_id: UUID | None, payload: dict[str, object] | None = None) -> UUID:
        audit_id = uuid4()
        self.session.add(
            AuditLog(
                id=audit_id,
                tenant_id=current.tenant_id,
                actor_user_id=current.user_id,
                action=action,
                target_kind=target_kind,
                target_id=target_id,
                payload=payload or {},
            )
        )
        return audit_id

    @staticmethod
    def _golden_hour_dto(row: MerchantGoldenHour) -> GoldenHourRuleDto:
        return GoldenHourRuleDto(
            id=row.id,
            merchant_id=row.merchant_id,
            day_of_week=row.day_of_week,
            start_time=row.start_time,
            end_time=row.end_time,
            discount_percent=row.discount_percent,
            updated_at=row.updated_at,
        )
