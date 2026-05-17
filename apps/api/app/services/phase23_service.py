from __future__ import annotations

import csv
import io
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import ApiError, ErrorCode
from app.core.security import CurrentUser
from app.db.models import (
    Booking,
    Complaint,
    Evidence,
    Merchant,
    MerchantService,
    Payment,
    PriceChangeLog,
    PromoCode,
    Rating,
    Referral,
    RewardStamp,
    RewardVoucher,
    ServiceTemplate,
)
from app.db.session import set_local_context
from app.domain.states import BookingState, PaymentState
from app.schemas.marketplace import MerchantServiceDto
from app.schemas.phase23 import (
    CommissionReceivableDto,
    ComplaintDto,
    DailySummaryBookingRow,
    DailySummaryResponse,
    EvidenceDto,
    MerchantServiceWriteRequest,
    PaymentDto,
    PriceChangeDto,
    PromoCodeDto,
    PromoValidateRequest,
    PromoValidateResponse,
    RatingDto,
    ReferralDto,
    RewardVoucherDto,
)
from app.services.auth_service import signing_key
from app.services.domain_events import DomainEventRepository

REWARD_THRESHOLD = 5


class Phase23Service:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def presign_evidence(self, *, current: CurrentUser, booking_id: UUID, type: str, content_type: str) -> tuple[EvidenceDto, str, str]:
        await self._context(current)
        booking = await self._booking_for_actor(current, booking_id)
        ext = "png" if content_type == "image/png" else "jpg"
        evidence_id = uuid4()
        object_key = f"evidence/{booking.id}/{type}/{evidence_id}.{ext}"
        photo_url = f"local://truecare/{object_key}"
        evidence = Evidence(
            id=evidence_id,
            tenant_id=current.tenant_id,
            booking_id=booking.id,
            type=type,
            object_key=object_key,
            photo_url=photo_url,
            content_type=content_type,
            status="pending_upload",
            quality="pending",
        )
        self.session.add(evidence)
        await self.session.flush()
        return self._evidence_dto(evidence), object_key, f"http://localhost/storage/{object_key}?signature=local-dev"

    async def confirm_evidence(
        self,
        *,
        current: CurrentUser,
        evidence_id: UUID,
        object_key: str,
        perceptual_hash: str | None,
        latitude: float | None,
        longitude: float | None,
        gps_accuracy_meters: float | None,
    ) -> EvidenceDto:
        await self._context(current)
        evidence = await self.session.get(Evidence, evidence_id)
        if evidence is None or evidence.tenant_id != current.tenant_id:
            raise ApiError(ErrorCode.booking_not_found, detail="Evidence was not found.")
        await self._booking_for_actor(current, evidence.booking_id)
        if object_key != evidence.object_key:
            raise ApiError(ErrorCode.invalid_booking_state, detail="Evidence object key does not match presign.")
        now = datetime.now(UTC)
        evidence.status = "processed"
        evidence.quality = "valid"
        evidence.uploaded_at = now
        evidence.watermarked_at = now
        evidence.exif_stripped = True
        evidence.perceptual_hash = perceptual_hash
        evidence.latitude = latitude
        evidence.longitude = longitude
        evidence.gps_accuracy_meters = gps_accuracy_meters
        await DomainEventRepository(self.session).emit(
            tenant_id=current.tenant_id,
            aggregate_type="evidence",
            aggregate_id=evidence.id,
            event_type="evidence.processed",
            payload={"evidence_id": str(evidence.id), "booking_id": str(evidence.booking_id)},
        )
        await self.session.flush()
        return self._evidence_dto(evidence)

    async def list_evidence(self, *, current: CurrentUser, booking_id: UUID) -> list[EvidenceDto]:
        await self._context(current)
        await self._booking_for_actor(current, booking_id)
        rows = (await self.session.scalars(select(Evidence).where(Evidence.tenant_id == current.tenant_id, Evidence.booking_id == booking_id).order_by(Evidence.created_at))).all()
        return [self._evidence_dto(row) for row in rows]

    async def initiate_payment(self, *, current: CurrentUser, booking_id: UUID, method: str, idempotency_key: str) -> PaymentDto:
        await self._context(current)
        if method == "vetc_wallet":
            raise ApiError(ErrorCode.invalid_booking_state, detail="VETC wallet is a P1 placeholder.")
        booking = await self._booking_for_owner(current, booking_id)
        if booking.status != BookingState.awaiting_payment.value:
            raise ApiError(ErrorCode.invalid_booking_state, detail="Booking is not awaiting payment.")
        existing = await self.session.scalar(
            select(Payment).where(Payment.tenant_id == current.tenant_id, Payment.booking_id == booking_id, Payment.idempotency_key == idempotency_key)
        )
        if existing is not None:
            return self._payment_dto(existing)
        merchant = await self.session.get(Merchant, booking.merchant_id)
        commission_amount = int(booking.total_amount * (merchant.commission_rate if merchant else 0.10)) if method == "qr_transfer" else 0
        payment = Payment(
            id=uuid4(),
            tenant_id=current.tenant_id,
            booking_id=booking.id,
            amount=booking.total_amount,
            method=method,
            status=PaymentState.cash_offered.value if method == "cash" else PaymentState.initiated_qr.value,
            commission_amount=commission_amount,
            commission_status="accrued" if method == "qr_transfer" else "not_applicable",
            idempotency_key=idempotency_key,
        )
        self.session.add(payment)
        booking.payment_method = method
        booking.payment_status = payment.status
        booking.updated_at = datetime.now(UTC)
        await self.session.flush()
        return self._payment_dto(payment)

    async def get_payment(self, *, current: CurrentUser, payment_id: UUID) -> PaymentDto:
        payment, _ = await self._payment_for_actor(current, payment_id)
        return self._payment_dto(payment)

    async def user_claimed_payment(self, *, current: CurrentUser, payment_id: UUID) -> PaymentDto:
        payment, booking = await self._payment_for_actor(current, payment_id, owner_only=True)
        if payment.status == PaymentState.initiated_qr.value:
            payment.status = PaymentState.user_claimed.value
            booking.payment_status = PaymentState.user_claimed.value
            await DomainEventRepository(self.session).emit(
                tenant_id=current.tenant_id,
                aggregate_type="payment",
                aggregate_id=payment.id,
                event_type="payment.user_claimed",
                payload={"payment_id": str(payment.id), "booking_id": str(booking.id)},
            )
            await self.session.flush()
        elif payment.status != PaymentState.user_claimed.value:
            raise ApiError(ErrorCode.invalid_booking_state, detail="Payment cannot be user-claimed from current state.")
        return self._payment_dto(payment)

    async def merchant_confirmed_payment(self, *, current: CurrentUser, payment_id: UUID, ops_confirmed: bool = False) -> PaymentDto:
        payment, booking = await self._payment_for_actor(current, payment_id)
        await self._require_merchant_operator(current=current, merchant_id=booking.merchant_id)
        if payment.status not in {PaymentState.user_claimed.value, PaymentState.cash_offered.value}:
            raise ApiError(ErrorCode.invalid_booking_state, detail="Payment cannot be confirmed from current state.")
        now = datetime.now(UTC)
        payment.status = PaymentState.verified.value
        payment.merchant_confirmed_at = now
        payment.ops_confirmed = ops_confirmed
        booking.status = BookingState.completed.value
        booking.completed_at = now
        booking.payment_status = PaymentState.verified.value
        booking.updated_at = now
        await self._finalize_reward_stamp(current.tenant_id, booking.user_id, booking.id)
        await DomainEventRepository(self.session).emit(
            tenant_id=current.tenant_id,
            aggregate_type="payment",
            aggregate_id=payment.id,
            event_type="payment.verified",
            payload={"payment_id": str(payment.id), "booking_id": str(booking.id)},
        )
        await self.session.flush()
        return self._payment_dto(payment)

    async def merchant_denied_payment(self, *, current: CurrentUser, payment_id: UUID, reason: str | None) -> PaymentDto:
        payment, booking = await self._payment_for_actor(current, payment_id)
        await self._require_merchant_operator(current=current, merchant_id=booking.merchant_id)
        if payment.status != PaymentState.user_claimed.value:
            raise ApiError(ErrorCode.invalid_booking_state, detail="Only user-claimed payment can be denied.")
        payment.status = PaymentState.merchant_denied.value
        payment.merchant_denied_reason = reason or "other"
        booking.payment_status = PaymentState.merchant_denied.value
        booking.updated_at = datetime.now(UTC)
        await self.session.flush()
        return self._payment_dto(payment)

    async def cash_record(self, *, current: CurrentUser, payment_id: UUID) -> PaymentDto:
        payment, _ = await self._payment_for_actor(current, payment_id)
        if payment.method != "cash":
            raise ApiError(ErrorCode.invalid_booking_state, detail="Payment method is not cash.")
        return await self.merchant_confirmed_payment(current=current, payment_id=payment_id)

    async def switch_payment_method(self, *, current: CurrentUser, payment_id: UUID, method: str) -> PaymentDto:
        payment, booking = await self._payment_for_actor(current, payment_id, owner_only=True)
        if payment.status not in {PaymentState.initiated_qr.value, PaymentState.user_claimed.value, PaymentState.cash_offered.value, PaymentState.merchant_denied.value}:
            raise ApiError(ErrorCode.invalid_booking_state, detail="Payment method can no longer be switched.")
        payment.method = method
        payment.status = PaymentState.cash_offered.value if method == "cash" else PaymentState.initiated_qr.value
        payment.commission_amount = 0 if method == "cash" else int(payment.amount * 0.10)
        payment.commission_status = "not_applicable" if method == "cash" else "accrued"
        booking.payment_method = method
        booking.payment_status = payment.status
        booking.updated_at = datetime.now(UTC)
        await self.session.flush()
        return self._payment_dto(payment)

    async def rate_booking(self, *, current: CurrentUser, booking_id: UUID, rating: str, comment: str | None, tip: int | None, reasons: list[str], evidence_urls: list[str]) -> RatingDto:
        await self._context(current)
        booking = await self._booking_for_owner(current, booking_id)
        if booking.status not in {BookingState.awaiting_payment.value, BookingState.completed.value, BookingState.rated.value}:
            raise ApiError(ErrorCode.invalid_booking_state, detail="Booking cannot be rated yet.")
        existing = await self.session.scalar(select(Rating).where(Rating.booking_id == booking_id))
        if existing is not None:
            return self._rating_dto(existing)
        row = Rating(
            id=uuid4(),
            tenant_id=current.tenant_id,
            booking_id=booking_id,
            user_id=current.user_id,
            merchant_id=booking.merchant_id,
            rating=rating,
            comment=comment,
            tip=tip,
            reasons=reasons,
            evidence_urls=evidence_urls,
        )
        self.session.add(row)
        if booking.status == BookingState.completed.value:
            booking.status = BookingState.rated.value
        await self._ensure_reward_stamp(current.tenant_id, current.user_id, booking.id, finalized=booking.status in {BookingState.completed.value, BookingState.rated.value})
        await self.session.flush()
        return self._rating_dto(row)

    async def validate_promo(self, *, current: CurrentUser, request: PromoValidateRequest) -> PromoValidateResponse:
        await self._context(current)
        code = request.code.strip().upper()
        promo = await self.session.scalar(select(PromoCode).where(PromoCode.tenant_id == current.tenant_id, PromoCode.code == code))
        if promo is None or not promo.is_active:
            return PromoValidateResponse(valid=False, code=code, reason="not_found")
        now = datetime.now(UTC)
        if promo.starts_at and promo.starts_at > now:
            return PromoValidateResponse(valid=False, code=code, reason="not_started")
        if promo.expires_at and promo.expires_at < now:
            return PromoValidateResponse(valid=False, code=code, reason="expired")
        if promo.used_count >= promo.usage_limit_total:
            return PromoValidateResponse(valid=False, code=code, reason="exhausted")
        if promo.min_order_amount and request.order_amount < promo.min_order_amount:
            return PromoValidateResponse(valid=False, code=code, reason="min_order_not_met")
        if promo.merchant_id and request.merchant_id and promo.merchant_id != request.merchant_id:
            return PromoValidateResponse(valid=False, code=code, reason="merchant_mismatch")
        discount = request.order_amount * promo.discount_value // 100 if promo.discount_type == "percent" else min(promo.discount_value, request.order_amount)
        if promo.max_discount_amount is not None:
            discount = min(discount, promo.max_discount_amount)
        return PromoValidateResponse(valid=True, code=code, discount_amount=discount)

    async def list_promos(self, *, current: CurrentUser) -> list[PromoCodeDto]:
        await self._context(current)
        rows = (await self.session.scalars(select(PromoCode).where(PromoCode.tenant_id == current.tenant_id, PromoCode.is_active.is_(True)).order_by(PromoCode.created_at.desc()))).all()
        return [self._promo_dto(row) for row in rows]

    async def create_promo(self, *, current: CurrentUser, code: str, discount_type: str, discount_value: int, max_discount_amount: int | None, min_order_amount: int | None, usage_limit_total: int) -> PromoCodeDto:
        await self._require_ops(current)
        promo = PromoCode(
            id=uuid4(),
            tenant_id=current.tenant_id,
            code=code.strip().upper(),
            discount_type=discount_type,
            discount_value=discount_value,
            max_discount_amount=max_discount_amount,
            min_order_amount=min_order_amount,
            usage_limit_total=usage_limit_total,
            created_by_ops=current.user_id,
        )
        self.session.add(promo)
        await self.session.flush()
        return self._promo_dto(promo)

    async def reward_progress(self, *, current: CurrentUser) -> tuple[int, int]:
        await self._context(current)
        finalized = await self.session.scalar(select(func.count()).select_from(RewardStamp).where(RewardStamp.user_id == current.user_id, RewardStamp.status == "finalized")) or 0
        pending = await self.session.scalar(select(func.count()).select_from(RewardStamp).where(RewardStamp.user_id == current.user_id, RewardStamp.status == "pending")) or 0
        return finalized, pending

    async def reward_vouchers(self, *, current: CurrentUser) -> list[RewardVoucherDto]:
        await self._context(current)
        rows = (await self.session.scalars(select(RewardVoucher).where(RewardVoucher.user_id == current.user_id).order_by(RewardVoucher.issued_at.desc()))).all()
        return [self._voucher_dto(row) for row in rows]

    async def reserve_voucher(self, *, current: CurrentUser, voucher_id: UUID, booking_id: UUID | None) -> RewardVoucherDto:
        voucher = await self._voucher_for_owner(current, voucher_id)
        if voucher.status not in {"issued", "released"}:
            raise ApiError(ErrorCode.invalid_booking_state, detail="Voucher is not reservable.")
        voucher.status = "reserved"
        voucher.reserved_booking_id = booking_id
        voucher.reserved_at = datetime.now(UTC)
        await self.session.flush()
        return self._voucher_dto(voucher)

    async def release_voucher(self, *, current: CurrentUser, voucher_id: UUID) -> RewardVoucherDto:
        voucher = await self._voucher_for_owner(current, voucher_id)
        if voucher.status != "reserved":
            raise ApiError(ErrorCode.invalid_booking_state, detail="Voucher is not reserved.")
        voucher.status = "released"
        voucher.released_at = datetime.now(UTC)
        voucher.reserved_booking_id = None
        await self.session.flush()
        return self._voucher_dto(voucher)

    async def redeem_voucher(self, *, current: CurrentUser, voucher_id: UUID, booking_id: UUID | None) -> RewardVoucherDto:
        voucher = await self._voucher_for_owner(current, voucher_id)
        if voucher.status not in {"issued", "reserved"}:
            raise ApiError(ErrorCode.invalid_booking_state, detail="Voucher is not redeemable.")
        voucher.status = "redeemed"
        voucher.redeemed_booking_id = booking_id or voucher.reserved_booking_id
        voucher.redeemed_at = datetime.now(UTC)
        await self.session.flush()
        return self._voucher_dto(voucher)

    async def referrals_me(self, *, current: CurrentUser) -> tuple[str | None, list[ReferralDto]]:
        await self._context(current)
        from app.db.models import User

        user = await self.session.get(User, current.user_id)
        rows = (await self.session.scalars(select(Referral).where(Referral.referrer_id == current.user_id).order_by(Referral.created_at.desc()))).all()
        return user.referral_code if user else None, [self._referral_dto(row) for row in rows]

    async def referral_share(self, *, current: CurrentUser, channel: str) -> None:
        await self._context(current)
        await DomainEventRepository(self.session).emit(
            tenant_id=current.tenant_id,
            aggregate_type="referral",
            aggregate_id=current.user_id,
            event_type="referral.share_event",
            payload={"user_id": str(current.user_id), "channel": channel},
        )

    async def create_complaint(self, *, current: CurrentUser, booking_id: UUID, category: str, description: str, evidence_refs: list[str]) -> ComplaintDto:
        await self._context(current)
        booking = await self._booking_for_owner(current, booking_id)
        complaint = Complaint(
            id=uuid4(),
            tenant_id=current.tenant_id,
            booking_id=booking.id,
            user_id=current.user_id,
            merchant_id=booking.merchant_id,
            category=category,
            description=description,
            evidence_refs=evidence_refs,
            status="created",
        )
        self.session.add(complaint)
        await DomainEventRepository(self.session).emit(
            tenant_id=current.tenant_id,
            aggregate_type="complaint",
            aggregate_id=complaint.id,
            event_type="complaint.created",
            payload={"complaint_id": str(complaint.id), "booking_id": str(booking.id)},
        )
        await self.session.flush()
        return self._complaint_dto(complaint)

    async def get_complaint(self, *, current: CurrentUser, complaint_id: UUID) -> ComplaintDto:
        complaint = await self._complaint_for_actor(current, complaint_id)
        return self._complaint_dto(complaint)

    async def list_ops_complaints(self, *, current: CurrentUser) -> list[ComplaintDto]:
        await self._require_ops(current)
        rows = (await self.session.scalars(select(Complaint).where(Complaint.tenant_id == current.tenant_id).order_by(Complaint.created_at.desc()))).all()
        return [self._complaint_dto(row) for row in rows]

    async def update_ops_complaint(self, *, current: CurrentUser, complaint_id: UUID, **values) -> ComplaintDto:
        await self._require_ops(current)
        complaint = await self.session.get(Complaint, complaint_id)
        if complaint is None or complaint.tenant_id != current.tenant_id:
            raise ApiError(ErrorCode.booking_not_found, detail="Complaint was not found.")
        for key, value in values.items():
            if value is not None:
                setattr(complaint, key, value)
        complaint.updated_at = datetime.now(UTC)
        await self.session.flush()
        return self._complaint_dto(complaint)

    async def create_merchant_service(self, *, current: CurrentUser, request: MerchantServiceWriteRequest, custom: bool = False) -> MerchantServiceDto:
        await self._context(current)
        await self._require_merchant_operator(current=current, merchant_id=request.merchant_id)
        template = await self.session.get(ServiceTemplate, request.template_id) if request.template_id else None
        if not custom and template is None:
            raise ApiError(ErrorCode.merchant_service_not_found, detail="Template was not found.")
        if template and not (template.floor_price <= request.price <= template.ceiling_price):
            raise ApiError(ErrorCode.invalid_booking_hold, detail="Price is outside template bounds.")
        service = MerchantService(
            id=uuid4(),
            tenant_id=current.tenant_id,
            merchant_id=request.merchant_id,
            template_id=template.id if template else None,
            name=request.name or (template.name if template else "Custom service"),
            price=request.price,
            duration_min=request.duration_min,
            duration_max=request.duration_max,
            status="pending_review" if custom else request.status,
            is_custom=custom,
            description=request.description,
        )
        self.session.add(service)
        await self.session.flush()
        return self._merchant_service_dto(service)

    async def update_merchant_service(self, *, current: CurrentUser, service_id: UUID, price: int | None, duration_min: int | None, duration_max: int | None, status: str | None) -> MerchantServiceDto:
        await self._context(current)
        service = await self._merchant_service_for_actor(current, service_id)
        old_price = service.price
        if price is not None:
            service.price = price
        if duration_min is not None:
            service.duration_min = duration_min
        if duration_max is not None:
            service.duration_max = duration_max
        if status is not None:
            service.status = status
        if service.duration_max < service.duration_min:
            raise ApiError(ErrorCode.invalid_booking_hold, detail="Invalid service duration.")
        service.updated_at = datetime.now(UTC)
        if price is not None and price != old_price:
            self.session.add(PriceChangeLog(id=uuid4(), tenant_id=current.tenant_id, merchant_service_id=service.id, old_price=old_price, new_price=price))
        await self.session.flush()
        return self._merchant_service_dto(service)

    async def merchant_service_price_history(self, *, current: CurrentUser, service_id: UUID) -> list[PriceChangeDto]:
        await self._merchant_service_for_actor(current, service_id)
        rows = (await self.session.scalars(select(PriceChangeLog).where(PriceChangeLog.merchant_service_id == service_id).order_by(PriceChangeLog.changed_at.desc()))).all()
        return [PriceChangeDto(old_price=row.old_price, new_price=row.new_price, changed_at=row.changed_at) for row in rows]

    async def resubmit_merchant_service(self, *, current: CurrentUser, service_id: UUID) -> MerchantServiceDto:
        service = await self._merchant_service_for_actor(current, service_id)
        if not service.is_custom or service.status != "rejected" or service.resubmit_count >= 3:
            raise ApiError(ErrorCode.invalid_booking_state, detail="Service is not resubmittable.")
        service.status = "pending_review"
        service.resubmit_count += 1
        service.updated_at = datetime.now(UTC)
        await self.session.flush()
        return self._merchant_service_dto(service)

    async def ops_decide_merchant_service(self, *, current: CurrentUser, service_id: UUID, approved: bool, reason: str | None) -> MerchantServiceDto:
        await self._require_ops(current)
        service = await self.session.get(MerchantService, service_id)
        if service is None or service.tenant_id != current.tenant_id:
            raise ApiError(ErrorCode.merchant_service_not_found, detail="Merchant service was not found.")
        service.status = "active" if approved else "rejected"
        service.ops_reviewed_by = current.user_id
        service.ops_reviewed_at = datetime.now(UTC)
        service.ops_rejection_reason = None if approved else reason
        await self.session.flush()
        return self._merchant_service_dto(service)

    async def daily_summary(self, *, current: CurrentUser, merchant_id: UUID) -> DailySummaryResponse:
        await self._context(current)
        await self._require_merchant_operator(current=current, merchant_id=merchant_id)
        rows = (
            await self.session.execute(
                select(Booking, MerchantService, Payment)
                .join(MerchantService, MerchantService.id == Booking.merchant_service_id)
                .join(Payment, Payment.booking_id == Booking.id, isouter=True)
                .where(Booking.tenant_id == current.tenant_id, Booking.merchant_id == merchant_id)
                .order_by(Booking.created_at.desc())
            )
        ).all()
        bookings = [
            DailySummaryBookingRow(
                time=booking.created_at,
                service_name=service.name,
                amount=booking.total_amount,
                method=payment.method if payment else booking.payment_method,
                status=booking.status,
            )
            for booking, service, payment in rows
        ]
        total_revenue = sum(row.amount for row in bookings if row.status in {"completed", "rated"})
        qr_revenue = sum(row.amount for row in bookings if row.method == "qr_transfer" and row.status in {"completed", "rated"})
        cash_revenue = sum(row.amount for row in bookings if row.method == "cash" and row.status in {"completed", "rated"})
        avg_rating = await self.session.scalar(select(func.avg(case((Rating.rating == "positive", 1.0), else_=0.0))).where(Rating.merchant_id == merchant_id))
        complaint_count = await self.session.scalar(select(func.count()).select_from(Complaint).where(Complaint.merchant_id == merchant_id)) or 0
        return DailySummaryResponse(
            services_completed=sum(1 for row in bookings if row.status in {"completed", "rated"}),
            total_revenue=total_revenue,
            qr_revenue=qr_revenue,
            cash_revenue=cash_revenue,
            promo_discount_total=0,
            average_rating=float(avg_rating or 0),
            complaint_count=complaint_count,
            payout_status="pending",
            bookings=bookings,
        )

    async def daily_summary_csv(self, *, current: CurrentUser, merchant_id: UUID) -> str:
        summary = await self.daily_summary(current=current, merchant_id=merchant_id)
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["time", "service_name", "amount", "method", "promo_code", "status"])
        for row in summary.bookings:
            writer.writerow([row.time.isoformat(), row.service_name, row.amount, row.method or "", row.promo_code or "", row.status])
        return out.getvalue()

    async def commission_receivables(self, *, current: CurrentUser) -> list[CommissionReceivableDto]:
        await self._require_ops(current)
        rows = (
            await self.session.execute(
                select(Merchant, Payment)
                .join(Booking, Booking.merchant_id == Merchant.id)
                .join(Payment, Payment.booking_id == Booking.id)
                .where(Payment.tenant_id == current.tenant_id, Payment.commission_amount > 0)
            )
        ).all()
        grouped: dict[UUID, CommissionReceivableDto] = {}
        for merchant, payment in rows:
            current_row = grouped.setdefault(
                merchant.id,
                CommissionReceivableDto(
                    merchant_id=merchant.id,
                    merchant_name=merchant.name,
                    total_bookings=0,
                    total_revenue=0,
                    commission_receivable=0,
                    commission_status=payment.commission_status,
                ),
            )
            current_row.total_bookings += 1
            current_row.total_revenue += payment.amount
            current_row.commission_receivable += payment.commission_amount
        return list(grouped.values())

    def realtime_token(self, *, current: CurrentUser) -> str:
        now = datetime.now(UTC)
        payload = {
            "iss": get_settings().jwt_issuer,
            "aud": "authenticated",
            "sub": str(current.user_id),
            "tenant_id": str(current.tenant_id),
            "roles": list(current.roles),
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=5)).timestamp()),
            "jti": secrets.token_hex(12),
        }
        return jwt.encode(payload, signing_key(), algorithm="EdDSA", headers={"kid": "local-dev"})

    async def _context(self, current: CurrentUser) -> None:
        await set_local_context(self.session, tenant_id=current.tenant_id, user_id=current.user_id, role=current.roles[0] if current.roles else None)

    async def _booking_for_owner(self, current: CurrentUser, booking_id: UUID) -> Booking:
        booking = await self.session.get(Booking, booking_id)
        if booking is None or booking.tenant_id != current.tenant_id or booking.user_id != current.user_id:
            raise ApiError(ErrorCode.booking_not_found, detail="Booking was not found.")
        return booking

    async def _booking_for_actor(self, current: CurrentUser, booking_id: UUID) -> Booking:
        booking = await self.session.get(Booking, booking_id)
        if booking is None or booking.tenant_id != current.tenant_id:
            raise ApiError(ErrorCode.booking_not_found, detail="Booking was not found.")
        if booking.user_id == current.user_id:
            return booking
        await self._require_merchant_operator(current=current, merchant_id=booking.merchant_id)
        return booking

    async def _payment_for_actor(self, current: CurrentUser, payment_id: UUID, owner_only: bool = False) -> tuple[Payment, Booking]:
        await self._context(current)
        payment = await self.session.get(Payment, payment_id)
        if payment is None or payment.tenant_id != current.tenant_id:
            raise ApiError(ErrorCode.booking_not_found, detail="Payment was not found.")
        booking = await self.session.get(Booking, payment.booking_id)
        if booking is None or booking.tenant_id != current.tenant_id:
            raise ApiError(ErrorCode.booking_not_found, detail="Booking was not found.")
        if owner_only:
            await self._booking_for_owner(current, booking.id)
        elif booking.user_id != current.user_id:
            await self._require_merchant_operator(current=current, merchant_id=booking.merchant_id)
        return payment, booking

    async def _require_merchant_operator(self, *, current: CurrentUser, merchant_id: UUID) -> Merchant:
        merchant = await self.session.get(Merchant, merchant_id)
        if merchant is None or merchant.tenant_id != current.tenant_id:
            raise ApiError(ErrorCode.merchant_not_found, detail="Merchant was not found.")
        if merchant.user_id != current.user_id and not set(current.roles).intersection({"ops", "admin", "finance_ops", "quality_ops"}):
            raise ApiError(ErrorCode.forbidden, detail="Not authorized for this merchant.")
        return merchant

    async def _require_ops(self, current: CurrentUser) -> None:
        await self._context(current)
        if not set(current.roles).intersection({"ops", "admin", "finance_ops", "quality_ops"}):
            raise ApiError(ErrorCode.forbidden, detail="Ops role required.")

    async def _merchant_service_for_actor(self, current: CurrentUser, service_id: UUID) -> MerchantService:
        service = await self.session.get(MerchantService, service_id)
        if service is None or service.tenant_id != current.tenant_id:
            raise ApiError(ErrorCode.merchant_service_not_found, detail="Merchant service was not found.")
        await self._require_merchant_operator(current=current, merchant_id=service.merchant_id)
        return service

    async def _complaint_for_actor(self, current: CurrentUser, complaint_id: UUID) -> Complaint:
        await self._context(current)
        complaint = await self.session.get(Complaint, complaint_id)
        if complaint is None or complaint.tenant_id != current.tenant_id:
            raise ApiError(ErrorCode.booking_not_found, detail="Complaint was not found.")
        if complaint.user_id != current.user_id:
            await self._require_merchant_operator(current=current, merchant_id=complaint.merchant_id)
        return complaint

    async def _voucher_for_owner(self, current: CurrentUser, voucher_id: UUID) -> RewardVoucher:
        await self._context(current)
        voucher = await self.session.get(RewardVoucher, voucher_id)
        if voucher is None or voucher.tenant_id != current.tenant_id or voucher.user_id != current.user_id:
            raise ApiError(ErrorCode.booking_not_found, detail="Voucher was not found.")
        return voucher

    async def _ensure_reward_stamp(self, tenant_id: UUID, user_id: UUID, booking_id: UUID, *, finalized: bool) -> RewardStamp:
        stamp = await self.session.get(RewardStamp, booking_id)
        now = datetime.now(UTC)
        if stamp is None:
            stamp = RewardStamp(booking_id=booking_id, tenant_id=tenant_id, user_id=user_id, status="finalized" if finalized else "pending", finalized_at=now if finalized else None)
            self.session.add(stamp)
        elif finalized and stamp.status != "finalized":
            stamp.status = "finalized"
            stamp.finalized_at = now
        return stamp

    async def _finalize_reward_stamp(self, tenant_id: UUID, user_id: UUID, booking_id: UUID) -> None:
        await self._ensure_reward_stamp(tenant_id, user_id, booking_id, finalized=True)
        finalized = await self.session.scalar(select(func.count()).select_from(RewardStamp).where(RewardStamp.user_id == user_id, RewardStamp.status == "finalized")) or 0
        existing_vouchers = await self.session.scalar(select(func.count()).select_from(RewardVoucher).where(RewardVoucher.user_id == user_id)) or 0
        if finalized >= REWARD_THRESHOLD and existing_vouchers == 0:
            now = datetime.now(UTC)
            self.session.add(
                RewardVoucher(
                    id=uuid4(),
                    tenant_id=tenant_id,
                    user_id=user_id,
                    stamp_threshold_reached_at=now,
                    expires_at=now + timedelta(days=90),
                    status="issued",
                )
            )

    @staticmethod
    def _evidence_dto(row: Evidence) -> EvidenceDto:
        return EvidenceDto(id=row.id, booking_id=row.booking_id, type=row.type, photo_url=row.photo_url, status=row.status, quality=row.quality, latitude=row.latitude, longitude=row.longitude, perceptual_hash=row.perceptual_hash, watermarked_at=row.watermarked_at, exif_stripped=row.exif_stripped)

    @staticmethod
    def _payment_dto(row: Payment) -> PaymentDto:
        return PaymentDto(id=row.id, booking_id=row.booking_id, amount=row.amount, method=row.method, status=row.status, merchant_confirmed_at=row.merchant_confirmed_at, created_at=row.created_at, commission_amount=row.commission_amount, commission_status=row.commission_status)

    @staticmethod
    def _rating_dto(row: Rating) -> RatingDto:
        return RatingDto(id=row.id, booking_id=row.booking_id, rating=row.rating, comment=row.comment, created_at=row.created_at)

    @staticmethod
    def _promo_dto(row: PromoCode) -> PromoCodeDto:
        return PromoCodeDto(id=row.id, code=row.code, discount_type=row.discount_type, discount_value=row.discount_value, max_discount_amount=row.max_discount_amount, min_order_amount=row.min_order_amount, usage_limit_total=row.usage_limit_total, used_count=row.used_count, is_active=row.is_active)

    @staticmethod
    def _voucher_dto(row: RewardVoucher) -> RewardVoucherDto:
        return RewardVoucherDto(id=row.id, status=row.status, issued_at=row.issued_at, expires_at=row.expires_at, reserved_booking_id=row.reserved_booking_id, redeemed_booking_id=row.redeemed_booking_id)

    @staticmethod
    def _referral_dto(row: Referral) -> ReferralDto:
        return ReferralDto(id=row.id, type=row.type, code=row.code, status=row.status, reward_status=row.reward_status, created_at=row.created_at)

    @staticmethod
    def _complaint_dto(row: Complaint) -> ComplaintDto:
        return ComplaintDto(id=row.id, booking_id=row.booking_id, category=row.category, description=row.description, evidence_refs=row.evidence_refs, status=row.status, resolution=row.resolution, refund_approved=row.refund_approved, voucher_action=row.voucher_action, created_at=row.created_at)

    @staticmethod
    def _merchant_service_dto(row: MerchantService) -> MerchantServiceDto:
        return MerchantServiceDto(id=row.id, merchant_id=row.merchant_id, template_id=row.template_id, name=row.name, price=row.price, duration_min=row.duration_min, duration_max=row.duration_max, status=row.status, is_custom=row.is_custom, description=row.description, photo_url=row.photo_url)
