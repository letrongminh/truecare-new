from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError, ErrorCode
from app.core.security import CurrentUser
from app.db.models import AuditLog, Merchant, MerchantEkycSubmission, MerchantPaymentSetup, TenantMembership, User
from app.db.session import set_local_context
from app.schemas.merchant_admission import (
    MerchantAdmissionDto,
    MerchantApplicationRequest,
    MerchantEkycStatusResponse,
    MerchantEkycSubmissionDto,
    MerchantPaymentSetupRequest,
)

REQUIRED_EKYC_KINDS = {"cmnd", "selfie", "bank"}
OPS_ROLES = {"ops", "admin", "finance_ops", "quality_ops"}


class MerchantAdmissionService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_application(self, *, current: CurrentUser, request: MerchantApplicationRequest) -> MerchantAdmissionDto:
        await self._context(current)
        merchant = Merchant(
            id=uuid4(),
            tenant_id=current.tenant_id,
            user_id=current.user_id,
            name=request.name,
            address=request.address,
            phone=request.phone,
            latitude=request.latitude,
            longitude=request.longitude,
            bay_count=request.bay_count,
            operating_hours_start=request.operating_hours_start,
            operating_hours_end=request.operating_hours_end,
            status="pending_review",
            pipeline_status="pending_setup",
            application_status="pending_review",
            photo_status="missing",
            payment_recipient_status="missing",
            ekyc_status="not_submitted",
            go_live_blockers=[],
        )
        self.session.add(merchant)
        await self._grant_merchant_membership(current)
        await self.session.flush()
        return self._merchant_dto(merchant)

    async def confirm_photo(self, *, current: CurrentUser, merchant_id: UUID, storefront_object_key: str, bay_object_key: str) -> MerchantAdmissionDto:
        merchant = await self._merchant_for_owner(current=current, merchant_id=merchant_id)
        merchant.storefront_photo_url = self._local_object_url(storefront_object_key)
        merchant.bay_photo_url = self._local_object_url(bay_object_key)
        merchant.photo_status = "confirmed"
        merchant.photo_confirmed_at = datetime.now(UTC)
        await self.session.flush()
        return self._merchant_dto(merchant)

    async def submit_payment_setup(self, *, current: CurrentUser, merchant_id: UUID, request: MerchantPaymentSetupRequest) -> MerchantAdmissionDto:
        merchant = await self._merchant_for_owner(current=current, merchant_id=merchant_id)
        existing = await self.session.scalar(select(MerchantPaymentSetup).where(MerchantPaymentSetup.tenant_id == current.tenant_id, MerchantPaymentSetup.merchant_id == merchant.id))
        if existing is None:
            existing = MerchantPaymentSetup(
                id=uuid4(),
                tenant_id=current.tenant_id,
                merchant_id=merchant.id,
                bank_name=request.bank_name,
                account_number=request.account_number,
                account_holder_name=request.account_holder_name,
                qr_object_key=request.qr_object_key,
                status="pending_review",
            )
            self.session.add(existing)
        else:
            existing.bank_name = request.bank_name
            existing.account_number = request.account_number
            existing.account_holder_name = request.account_holder_name
            existing.qr_object_key = request.qr_object_key
            existing.status = "pending_review"
            existing.verified_at = None
            existing.verified_by = None
        merchant.payment_recipient_status = "pending_review"
        merchant.payment_recipient_verified_at = None
        await self.session.flush()
        return self._merchant_dto(merchant)

    async def submit_ekyc(self, *, current: CurrentUser, merchant_id: UUID, kind: str, object_key: str) -> MerchantEkycStatusResponse:
        merchant = await self._merchant_for_owner(current=current, merchant_id=merchant_id)
        existing = await self.session.scalar(select(MerchantEkycSubmission).where(MerchantEkycSubmission.tenant_id == current.tenant_id, MerchantEkycSubmission.merchant_id == merchant.id, MerchantEkycSubmission.kind == kind))
        if existing is None:
            existing = MerchantEkycSubmission(
                id=uuid4(),
                tenant_id=current.tenant_id,
                merchant_id=merchant.id,
                kind=kind,
                object_key=object_key,
                status="submitted",
            )
            self.session.add(existing)
        else:
            existing.object_key = object_key
            existing.status = "submitted"
            existing.reviewed_at = None
        await self.session.flush()
        await self._refresh_ekyc_status(merchant)
        await self.session.flush()
        return await self.ekyc_status(current=current, merchant_id=merchant.id)

    async def ekyc_status(self, *, current: CurrentUser, merchant_id: UUID) -> MerchantEkycStatusResponse:
        merchant = await self._merchant_for_actor(current=current, merchant_id=merchant_id)
        rows = (
            await self.session.scalars(
                select(MerchantEkycSubmission)
                .where(MerchantEkycSubmission.tenant_id == current.tenant_id, MerchantEkycSubmission.merchant_id == merchant.id)
                .order_by(MerchantEkycSubmission.kind)
            )
        ).all()
        return MerchantEkycStatusResponse(
            merchant_id=merchant.id,
            ekyc_status=merchant.ekyc_status,
            submissions=[
                MerchantEkycSubmissionDto(
                    id=row.id,
                    kind=row.kind,
                    object_key=row.object_key,
                    status=row.status,
                    submitted_at=row.submitted_at,
                )
                for row in rows
            ],
        )

    async def list_pending(self, *, current: CurrentUser) -> list[MerchantAdmissionDto]:
        await self._require_ops(current)
        rows = (
            await self.session.scalars(
                select(Merchant)
                .where(Merchant.tenant_id == current.tenant_id, Merchant.status != "live", Merchant.deleted_at.is_(None))
                .order_by(Merchant.created_at.desc())
            )
        ).all()
        return [self._merchant_dto(row) for row in rows]

    async def verify_payment_recipient(self, *, current: CurrentUser, merchant_id: UUID) -> MerchantAdmissionDto:
        merchant = await self._merchant_for_ops(current=current, merchant_id=merchant_id)
        setup = await self.session.scalar(select(MerchantPaymentSetup).where(MerchantPaymentSetup.tenant_id == current.tenant_id, MerchantPaymentSetup.merchant_id == merchant.id))
        if setup is None:
            raise ApiError(ErrorCode.merchant_go_live_blocked, detail="Payment recipient setup is missing.", extra={"blockers": ["payment_recipient_required"]})
        now = datetime.now(UTC)
        setup.status = "verified"
        setup.verified_at = now
        setup.verified_by = current.user_id
        merchant.payment_recipient_status = "verified"
        merchant.payment_recipient_verified_at = now
        self._audit(current=current, action="merchant.payment_recipient.verify", target_kind="merchant", target_id=merchant.id)
        await self.session.flush()
        return self._merchant_dto(merchant)

    async def approve(self, *, current: CurrentUser, merchant_id: UUID) -> MerchantAdmissionDto:
        merchant = await self._merchant_for_ops(current=current, merchant_id=merchant_id)
        blockers = await self._go_live_blockers(merchant)
        if blockers:
            raise ApiError(ErrorCode.merchant_go_live_blocked, detail="Merchant go-live checklist is incomplete.", extra={"blockers": blockers})
        now = datetime.now(UTC)
        merchant.status = "live"
        merchant.pipeline_status = "live_full"
        merchant.application_status = "approved"
        merchant.go_live_blockers = []
        merchant.ops_rejection_reason = None
        merchant.ops_reviewed_by = current.user_id
        merchant.ops_reviewed_at = now
        self._audit(current=current, action="merchant.approve", target_kind="merchant", target_id=merchant.id, payload={"pipeline_status": merchant.pipeline_status})
        await self.session.flush()
        return self._merchant_dto(merchant)

    async def reject(self, *, current: CurrentUser, merchant_id: UUID, reason: str | None) -> MerchantAdmissionDto:
        merchant = await self._merchant_for_ops(current=current, merchant_id=merchant_id)
        merchant.status = "rejected"
        merchant.pipeline_status = "watchlist"
        merchant.application_status = "rejected"
        merchant.ops_rejection_reason = reason
        merchant.ops_reviewed_by = current.user_id
        merchant.ops_reviewed_at = datetime.now(UTC)
        self._audit(current=current, action="merchant.reject", target_kind="merchant", target_id=merchant.id, payload={"reason": reason} if reason else {})
        await self.session.flush()
        return self._merchant_dto(merchant)

    async def suspend(self, *, current: CurrentUser, merchant_id: UUID, reason: str | None) -> MerchantAdmissionDto:
        merchant = await self._merchant_for_ops(current=current, merchant_id=merchant_id)
        merchant.status = "suspended"
        merchant.pipeline_status = "suspended"
        merchant.application_status = "suspended"
        merchant.ops_rejection_reason = reason
        merchant.ops_reviewed_by = current.user_id
        merchant.ops_reviewed_at = datetime.now(UTC)
        self._audit(current=current, action="merchant.suspend", target_kind="merchant", target_id=merchant.id, payload={"reason": reason} if reason else {})
        await self.session.flush()
        return self._merchant_dto(merchant)

    async def _grant_merchant_membership(self, current: CurrentUser) -> None:
        membership = await self.session.get(TenantMembership, (current.user_id, current.tenant_id))
        if membership is None:
            self.session.add(TenantMembership(user_id=current.user_id, tenant_id=current.tenant_id, role="merchant"))
        elif membership.role == "consumer":
            membership.role = "merchant"
        user = await self.session.get(User, current.user_id)
        if user is not None and user.role == "consumer":
            user.role = "merchant"

    async def _refresh_ekyc_status(self, merchant: Merchant) -> None:
        kinds = set(
            (
                await self.session.scalars(
                    select(MerchantEkycSubmission.kind).where(MerchantEkycSubmission.tenant_id == merchant.tenant_id, MerchantEkycSubmission.merchant_id == merchant.id)
                )
            ).all()
        )
        merchant.ekyc_status = "submitted" if REQUIRED_EKYC_KINDS.issubset(kinds) else ("partial" if kinds else "not_submitted")

    async def _go_live_blockers(self, merchant: Merchant) -> list[str]:
        blockers: list[str] = []
        if merchant.application_status not in {"pending_review", "approved"}:
            blockers.append("application_required")
        if merchant.photo_status != "confirmed":
            blockers.append("photo_required")
        if merchant.payment_recipient_status != "verified":
            blockers.append("payment_recipient_required")
        await self._refresh_ekyc_status(merchant)
        if merchant.ekyc_status not in {"submitted", "verified"}:
            blockers.append("ekyc_required")
        return blockers

    async def _merchant_for_owner(self, *, current: CurrentUser, merchant_id: UUID) -> Merchant:
        await self._context(current)
        merchant = await self.session.get(Merchant, merchant_id)
        if merchant is None or merchant.tenant_id != current.tenant_id:
            raise ApiError(ErrorCode.merchant_not_found, detail="Merchant was not found.")
        if merchant.user_id != current.user_id:
            raise ApiError(ErrorCode.forbidden, detail="Not authorized for this merchant.")
        return merchant

    async def _merchant_for_actor(self, *, current: CurrentUser, merchant_id: UUID) -> Merchant:
        await self._context(current)
        merchant = await self.session.get(Merchant, merchant_id)
        if merchant is None or merchant.tenant_id != current.tenant_id:
            raise ApiError(ErrorCode.merchant_not_found, detail="Merchant was not found.")
        if merchant.user_id != current.user_id and not set(current.roles).intersection(OPS_ROLES):
            raise ApiError(ErrorCode.forbidden, detail="Not authorized for this merchant.")
        return merchant

    async def _merchant_for_ops(self, *, current: CurrentUser, merchant_id: UUID) -> Merchant:
        await self._require_ops(current)
        merchant = await self.session.get(Merchant, merchant_id)
        if merchant is None or merchant.tenant_id != current.tenant_id:
            raise ApiError(ErrorCode.merchant_not_found, detail="Merchant was not found.")
        return merchant

    async def _require_ops(self, current: CurrentUser) -> None:
        await self._context(current)
        if not set(current.roles).intersection(OPS_ROLES):
            raise ApiError(ErrorCode.forbidden, detail="Ops role required.")

    async def _context(self, current: CurrentUser) -> None:
        await set_local_context(self.session, tenant_id=current.tenant_id, user_id=current.user_id, role=current.roles[0] if current.roles else None)

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

    def _merchant_dto(self, merchant: Merchant) -> MerchantAdmissionDto:
        return MerchantAdmissionDto(
            id=merchant.id,
            tenant_id=merchant.tenant_id,
            user_id=merchant.user_id,
            name=merchant.name,
            address=merchant.address,
            phone=merchant.phone,
            latitude=merchant.latitude,
            longitude=merchant.longitude,
            bay_count=merchant.bay_count,
            status=merchant.status,
            pipeline_status=merchant.pipeline_status,
            application_status=merchant.application_status,
            photo_status=merchant.photo_status,
            payment_recipient_status=merchant.payment_recipient_status,
            ekyc_status=merchant.ekyc_status,
            go_live_blockers=list(merchant.go_live_blockers or []),
            storefront_photo_url=merchant.storefront_photo_url,
            bay_photo_url=merchant.bay_photo_url,
            ops_rejection_reason=merchant.ops_rejection_reason,
            ops_reviewed_by=merchant.ops_reviewed_by,
            ops_reviewed_at=merchant.ops_reviewed_at,
            created_at=merchant.created_at,
        )

    def _local_object_url(self, object_key: str) -> str:
        return f"local://truecare/{object_key}"
