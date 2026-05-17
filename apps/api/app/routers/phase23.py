from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, require_user
from app.db.session import get_session
from app.schemas.marketplace import BookingDto, MerchantServiceDto
from app.schemas.phase23 import (
    CommissionReceivablesResponse,
    ComplaintDto,
    ComplaintListResponse,
    CreateComplaintRequest,
    CreatePromoCodeRequest,
    CreateRatingRequest,
    DailySummaryResponse,
    EvidenceConfirmRequest,
    EvidenceDto,
    EvidenceListResponse,
    EvidencePresignRequest,
    EvidencePresignResponse,
    InitiatePaymentRequest,
    MerchantDeniedPaymentRequest,
    MerchantServiceUpdateRequest,
    MerchantServiceWriteRequest,
    OpsComplaintUpdateRequest,
    OpsMerchantServiceDecisionRequest,
    PaymentDto,
    PriceHistoryResponse,
    PromoListResponse,
    PromoValidateRequest,
    PromoValidateResponse,
    RatingDto,
    RealtimeTokenResponse,
    ReferralMeResponse,
    ReferralShareEventRequest,
    ReferralShareEventResponse,
    RewardProgressResponse,
    RewardVoucherDto,
    RewardVoucherListResponse,
    SwitchPaymentMethodRequest,
    VoucherBookingRequest,
)
from app.services.phase23_service import REWARD_THRESHOLD, Phase23Service

router = APIRouter(tags=["phase2-phase3"])

IMPLEMENTED_PHASE23_ROUTES = {
    ("POST", "/v1/evidence/{booking_id}/presign"),
    ("POST", "/v1/evidence/{evidence_id}/confirm"),
    ("GET", "/v1/evidence/{booking_id}"),
    ("POST", "/v1/payments/initiate"),
    ("GET", "/v1/payments/{id}"),
    ("POST", "/v1/payments/{id}/user-claimed"),
    ("POST", "/v1/payments/{id}/merchant-confirmed"),
    ("POST", "/v1/payments/{id}/merchant-denied"),
    ("POST", "/v1/payments/{id}/cash-record"),
    ("POST", "/v1/payments/{id}/switch-method"),
    ("POST", "/v1/bookings/{id}/rate"),
    ("POST", "/v1/promo-codes/validate"),
    ("GET", "/v1/promo-codes/user"),
    ("GET", "/v1/rewards/progress"),
    ("GET", "/v1/rewards/vouchers"),
    ("POST", "/v1/rewards/vouchers/{id}/reserve"),
    ("POST", "/v1/rewards/vouchers/{id}/release"),
    ("POST", "/v1/rewards/vouchers/{id}/redeem"),
    ("GET", "/v1/referrals/me"),
    ("POST", "/v1/referrals/share-event"),
    ("POST", "/v1/complaints"),
    ("GET", "/v1/complaints/{id}"),
    ("POST", "/v1/merchant-services"),
    ("PATCH", "/v1/merchant-services/{id}"),
    ("GET", "/v1/merchant-services/{id}/price-history"),
    ("POST", "/v1/merchant-services/custom"),
    ("POST", "/v1/merchant-services/{id}/resubmit"),
    ("GET", "/v1/merchants/{id}/daily-summary"),
    ("GET", "/v1/merchants/{id}/daily-summary.csv"),
    ("POST", "/v1/ops/promo-codes"),
    ("POST", "/v1/ops/merchant-services/{id}/approve"),
    ("POST", "/v1/ops/merchant-services/{id}/reject"),
    ("GET", "/v1/ops/commission-receivables"),
    ("GET", "/v1/ops/complaints"),
    ("PATCH", "/v1/ops/complaints/{id}"),
    ("POST", "/v1/realtime/token"),
}


@router.post("/v1/evidence/{booking_id}/presign", response_model=EvidencePresignResponse, operation_id="post_v1_evidence_by_booking_id_presign", tags=["evidence"])
async def presign_evidence(
    booking_id: UUID,
    request: EvidencePresignRequest,
    current: CurrentUser = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> EvidencePresignResponse:
    async with session.begin():
        evidence, object_key, upload_url = await Phase23Service(session).presign_evidence(current=current, booking_id=booking_id, type=request.type, content_type=request.content_type)
    return EvidencePresignResponse(evidence_id=evidence.id, object_key=object_key, upload_url=upload_url)


@router.post("/v1/evidence/{evidence_id}/confirm", response_model=EvidenceDto, operation_id="post_v1_evidence_by_evidence_id_confirm", tags=["evidence"])
async def confirm_evidence(
    evidence_id: UUID,
    request: EvidenceConfirmRequest,
    current: CurrentUser = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> EvidenceDto:
    async with session.begin():
        return await Phase23Service(session).confirm_evidence(
            current=current,
            evidence_id=evidence_id,
            object_key=request.object_key,
            perceptual_hash=request.perceptual_hash,
            latitude=request.latitude,
            longitude=request.longitude,
            gps_accuracy_meters=request.gps_accuracy_meters,
        )


@router.get("/v1/evidence/{booking_id}", response_model=EvidenceListResponse, operation_id="get_v1_evidence_by_booking_id", tags=["evidence"])
async def list_evidence(booking_id: UUID, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> EvidenceListResponse:
    async with session.begin():
        evidence = await Phase23Service(session).list_evidence(current=current, booking_id=booking_id)
    return EvidenceListResponse(evidence=evidence)


@router.post("/v1/payments/initiate", response_model=PaymentDto, operation_id="post_v1_payments_initiate", tags=["payments"])
async def initiate_payment(request: InitiatePaymentRequest, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> PaymentDto:
    async with session.begin():
        return await Phase23Service(session).initiate_payment(current=current, booking_id=request.booking_id, method=request.method, idempotency_key=request.idempotency_key)


@router.get("/v1/payments/{id}", response_model=PaymentDto, operation_id="get_v1_payments_by_id", tags=["payments"])
async def get_payment(id: UUID, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> PaymentDto:
    async with session.begin():
        return await Phase23Service(session).get_payment(current=current, payment_id=id)


@router.post("/v1/payments/{id}/user-claimed", response_model=PaymentDto, operation_id="post_v1_payments_by_id_user_claimed", tags=["payments"])
async def user_claimed_payment(id: UUID, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> PaymentDto:
    async with session.begin():
        return await Phase23Service(session).user_claimed_payment(current=current, payment_id=id)


@router.post("/v1/payments/{id}/merchant-confirmed", response_model=PaymentDto, operation_id="post_v1_payments_by_id_merchant_confirmed", tags=["payments"])
async def merchant_confirmed_payment(id: UUID, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> PaymentDto:
    async with session.begin():
        return await Phase23Service(session).merchant_confirmed_payment(current=current, payment_id=id)


@router.post("/v1/payments/{id}/merchant-denied", response_model=PaymentDto, operation_id="post_v1_payments_by_id_merchant_denied", tags=["payments"])
async def merchant_denied_payment(id: UUID, request: MerchantDeniedPaymentRequest, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> PaymentDto:
    async with session.begin():
        return await Phase23Service(session).merchant_denied_payment(current=current, payment_id=id, reason=request.reason)


@router.post("/v1/payments/{id}/cash-record", response_model=PaymentDto, operation_id="post_v1_payments_by_id_cash_record", tags=["payments"])
async def cash_record(id: UUID, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> PaymentDto:
    async with session.begin():
        return await Phase23Service(session).cash_record(current=current, payment_id=id)


@router.post("/v1/payments/{id}/switch-method", response_model=PaymentDto, operation_id="post_v1_payments_by_id_switch_method", tags=["payments"])
async def switch_payment_method(id: UUID, request: SwitchPaymentMethodRequest, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> PaymentDto:
    async with session.begin():
        return await Phase23Service(session).switch_payment_method(current=current, payment_id=id, method=request.method)


@router.post("/v1/bookings/{id}/rate", response_model=RatingDto, operation_id="post_v1_bookings_by_id_rate", tags=["bookings"])
async def rate_booking(id: UUID, request: CreateRatingRequest, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> RatingDto:
    async with session.begin():
        return await Phase23Service(session).rate_booking(current=current, booking_id=id, rating=request.rating, comment=request.comment, tip=request.tip, reasons=request.reasons, evidence_urls=request.evidence_urls)


@router.post("/v1/promo-codes/validate", response_model=PromoValidateResponse, operation_id="post_v1_promo_codes_validate", tags=["promo"])
async def validate_promo(request: PromoValidateRequest, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> PromoValidateResponse:
    async with session.begin():
        return await Phase23Service(session).validate_promo(current=current, request=request)


@router.get("/v1/promo-codes/user", response_model=PromoListResponse, operation_id="get_v1_promo_codes_user", tags=["promo"])
async def user_promos(current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> PromoListResponse:
    async with session.begin():
        promo_codes = await Phase23Service(session).list_promos(current=current)
    return PromoListResponse(promo_codes=promo_codes)


@router.get("/v1/rewards/progress", response_model=RewardProgressResponse, operation_id="get_v1_rewards_progress", tags=["rewards"])
async def reward_progress(current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> RewardProgressResponse:
    async with session.begin():
        finalized, pending = await Phase23Service(session).reward_progress(current=current)
    return RewardProgressResponse(finalized_stamps=finalized, pending_stamps=pending, next_reward_at=max(REWARD_THRESHOLD - finalized, 0))


@router.get("/v1/rewards/vouchers", response_model=RewardVoucherListResponse, operation_id="get_v1_rewards_vouchers", tags=["rewards"])
async def reward_vouchers(current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> RewardVoucherListResponse:
    async with session.begin():
        vouchers = await Phase23Service(session).reward_vouchers(current=current)
    return RewardVoucherListResponse(vouchers=vouchers)


@router.post("/v1/rewards/vouchers/{id}/reserve", response_model=RewardVoucherDto, operation_id="post_v1_rewards_vouchers_by_id_reserve", tags=["rewards"])
async def reserve_voucher(id: UUID, request: VoucherBookingRequest, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> RewardVoucherDto:
    async with session.begin():
        return await Phase23Service(session).reserve_voucher(current=current, voucher_id=id, booking_id=request.booking_id)


@router.post("/v1/rewards/vouchers/{id}/release", response_model=RewardVoucherDto, operation_id="post_v1_rewards_vouchers_by_id_release", tags=["rewards"])
async def release_voucher(id: UUID, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> RewardVoucherDto:
    async with session.begin():
        return await Phase23Service(session).release_voucher(current=current, voucher_id=id)


@router.post("/v1/rewards/vouchers/{id}/redeem", response_model=RewardVoucherDto, operation_id="post_v1_rewards_vouchers_by_id_redeem", tags=["rewards"])
async def redeem_voucher(id: UUID, request: VoucherBookingRequest, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> RewardVoucherDto:
    async with session.begin():
        return await Phase23Service(session).redeem_voucher(current=current, voucher_id=id, booking_id=request.booking_id)


@router.get("/v1/referrals/me", response_model=ReferralMeResponse, operation_id="get_v1_referrals_me", tags=["referrals"])
async def referrals_me(current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> ReferralMeResponse:
    async with session.begin():
        referral_code, referrals = await Phase23Service(session).referrals_me(current=current)
    return ReferralMeResponse(referral_code=referral_code, referrals=referrals)


@router.post("/v1/referrals/share-event", response_model=ReferralShareEventResponse, operation_id="post_v1_referrals_share_event", tags=["referrals"])
async def referral_share_event(request: ReferralShareEventRequest, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> ReferralShareEventResponse:
    async with session.begin():
        await Phase23Service(session).referral_share(current=current, channel=request.channel)
    return ReferralShareEventResponse(recorded=True)


@router.post("/v1/complaints", response_model=ComplaintDto, status_code=status.HTTP_201_CREATED, operation_id="post_v1_complaints", tags=["complaints"])
async def create_complaint(request: CreateComplaintRequest, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> ComplaintDto:
    async with session.begin():
        return await Phase23Service(session).create_complaint(current=current, booking_id=request.booking_id, category=request.category, description=request.description, evidence_refs=request.evidence_refs)


@router.get("/v1/complaints/{id}", response_model=ComplaintDto, operation_id="get_v1_complaints_by_id", tags=["complaints"])
async def get_complaint(id: UUID, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> ComplaintDto:
    async with session.begin():
        return await Phase23Service(session).get_complaint(current=current, complaint_id=id)


@router.post("/v1/merchant-services", response_model=MerchantServiceDto, operation_id="post_v1_merchant_services", tags=["merchant-services"])
async def create_merchant_service(request: MerchantServiceWriteRequest, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> MerchantServiceDto:
    async with session.begin():
        return await Phase23Service(session).create_merchant_service(current=current, request=request)


@router.patch("/v1/merchant-services/{id}", response_model=MerchantServiceDto, operation_id="patch_v1_merchant_services_by_id", tags=["merchant-services"])
async def update_merchant_service(id: UUID, request: MerchantServiceUpdateRequest, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> MerchantServiceDto:
    async with session.begin():
        return await Phase23Service(session).update_merchant_service(current=current, service_id=id, price=request.price, duration_min=request.duration_min, duration_max=request.duration_max, status=request.status)


@router.get("/v1/merchant-services/{id}/price-history", response_model=PriceHistoryResponse, operation_id="get_v1_merchant_services_by_id_price_history", tags=["merchant-services"])
async def price_history(id: UUID, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> PriceHistoryResponse:
    async with session.begin():
        price_changes = await Phase23Service(session).merchant_service_price_history(current=current, service_id=id)
    return PriceHistoryResponse(price_changes=price_changes)


@router.post("/v1/merchant-services/custom", response_model=MerchantServiceDto, operation_id="post_v1_merchant_services_custom", tags=["merchant-services"])
async def create_custom_merchant_service(request: MerchantServiceWriteRequest, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> MerchantServiceDto:
    async with session.begin():
        return await Phase23Service(session).create_merchant_service(current=current, request=request, custom=True)


@router.post("/v1/merchant-services/{id}/resubmit", response_model=MerchantServiceDto, operation_id="post_v1_merchant_services_by_id_resubmit", tags=["merchant-services"])
async def resubmit_merchant_service(id: UUID, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> MerchantServiceDto:
    async with session.begin():
        return await Phase23Service(session).resubmit_merchant_service(current=current, service_id=id)


@router.get("/v1/merchants/{id}/daily-summary", response_model=DailySummaryResponse, operation_id="get_v1_merchants_by_id_daily_summary", tags=["merchant"])
async def daily_summary(id: UUID, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> DailySummaryResponse:
    async with session.begin():
        return await Phase23Service(session).daily_summary(current=current, merchant_id=id)


@router.get("/v1/merchants/{id}/daily-summary.csv", operation_id="get_v1_merchants_by_id_daily_summary_csv", tags=["merchant"])
async def daily_summary_csv(id: UUID, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> Response:
    async with session.begin():
        csv_body = await Phase23Service(session).daily_summary_csv(current=current, merchant_id=id)
    return Response(csv_body, media_type="text/csv")


@router.post("/v1/ops/promo-codes", response_model=PromoValidateResponse, operation_id="post_v1_ops_promo_codes", tags=["ops"])
async def ops_create_promo(request: CreatePromoCodeRequest, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> PromoValidateResponse:
    async with session.begin():
        promo = await Phase23Service(session).create_promo(current=current, code=request.code, discount_type=request.discount_type, discount_value=request.discount_value, max_discount_amount=request.max_discount_amount, min_order_amount=request.min_order_amount, usage_limit_total=request.usage_limit_total)
    return PromoValidateResponse(valid=True, code=promo.code)


@router.post("/v1/ops/merchant-services/{id}/approve", response_model=MerchantServiceDto, operation_id="post_v1_ops_merchant_services_by_id_approve", tags=["ops"])
async def ops_approve_merchant_service(id: UUID, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> MerchantServiceDto:
    async with session.begin():
        return await Phase23Service(session).ops_decide_merchant_service(current=current, service_id=id, approved=True, reason=None)


@router.post("/v1/ops/merchant-services/{id}/reject", response_model=MerchantServiceDto, operation_id="post_v1_ops_merchant_services_by_id_reject", tags=["ops"])
async def ops_reject_merchant_service(id: UUID, request: OpsMerchantServiceDecisionRequest, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> MerchantServiceDto:
    async with session.begin():
        return await Phase23Service(session).ops_decide_merchant_service(current=current, service_id=id, approved=False, reason=request.reason)


@router.get("/v1/ops/commission-receivables", response_model=CommissionReceivablesResponse, operation_id="get_v1_ops_commission_receivables", tags=["ops"])
async def commission_receivables(current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> CommissionReceivablesResponse:
    async with session.begin():
        receivables = await Phase23Service(session).commission_receivables(current=current)
    return CommissionReceivablesResponse(receivables=receivables)


@router.get("/v1/ops/complaints", response_model=ComplaintListResponse, operation_id="get_v1_ops_complaints", tags=["ops"])
async def ops_complaints(current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> ComplaintListResponse:
    async with session.begin():
        complaints = await Phase23Service(session).list_ops_complaints(current=current)
    return ComplaintListResponse(complaints=complaints)


@router.patch("/v1/ops/complaints/{id}", response_model=ComplaintDto, operation_id="patch_v1_ops_complaints_by_id", tags=["ops"])
async def ops_update_complaint(id: UUID, request: OpsComplaintUpdateRequest, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> ComplaintDto:
    async with session.begin():
        return await Phase23Service(session).update_ops_complaint(current=current, complaint_id=id, status=request.status, resolution=request.resolution, refund_approved=request.refund_approved, voucher_action=request.voucher_action)


@router.post("/v1/realtime/token", response_model=RealtimeTokenResponse, operation_id="post_v1_realtime_token", tags=["realtime"])
async def realtime_token(current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> RealtimeTokenResponse:
    return RealtimeTokenResponse(token=Phase23Service(session).realtime_token(current=current))
