from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, require_user
from app.db.session import get_session
from app.schemas.merchant_admission import (
    MerchantAdmissionDto,
    MerchantApplicationRequest,
    MerchantEkycStatusResponse,
    MerchantEkycSubmitRequest,
    MerchantPaymentSetupRequest,
    MerchantPhotoConfirmRequest,
    OpsMerchantDecisionRequest,
    PendingMerchantsResponse,
)
from app.services.merchant_admission_service import MerchantAdmissionService

router = APIRouter(tags=["merchant-admission"])

IMPLEMENTED_MERCHANT_ADMISSION_ROUTES = {
    ("POST", "/v1/merchants/applications"),
    ("POST", "/v1/merchants/{id}/confirm-photo"),
    ("POST", "/v1/merchants/{id}/payment-setup"),
    ("POST", "/v1/merchants/{id}/ekyc/cmnd"),
    ("POST", "/v1/merchants/{id}/ekyc/selfie"),
    ("POST", "/v1/merchants/{id}/ekyc/bank"),
    ("GET", "/v1/merchants/{id}/ekyc/status"),
    ("GET", "/v1/ops/merchants/pending"),
    ("POST", "/v1/ops/merchants/{id}/approve"),
    ("POST", "/v1/ops/merchants/{id}/reject"),
    ("POST", "/v1/ops/merchants/{id}/verify-payment-recipient"),
    ("POST", "/v1/ops/merchants/{id}/suspend"),
}


@router.post("/v1/merchants/applications", response_model=MerchantAdmissionDto, status_code=status.HTTP_201_CREATED, operation_id="post_v1_merchants_applications", tags=["merchant"])
async def create_application(request: MerchantApplicationRequest, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> MerchantAdmissionDto:
    async with session.begin():
        return await MerchantAdmissionService(session).create_application(current=current, request=request)


@router.post("/v1/merchants/{id}/confirm-photo", response_model=MerchantAdmissionDto, operation_id="post_v1_merchants_by_id_confirm_photo", tags=["merchant"])
async def confirm_photo(id: UUID, request: MerchantPhotoConfirmRequest, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> MerchantAdmissionDto:
    async with session.begin():
        return await MerchantAdmissionService(session).confirm_photo(current=current, merchant_id=id, storefront_object_key=request.storefront_object_key, bay_object_key=request.bay_object_key)


@router.post("/v1/merchants/{id}/payment-setup", response_model=MerchantAdmissionDto, operation_id="post_v1_merchants_by_id_payment_setup", tags=["merchant"])
async def payment_setup(id: UUID, request: MerchantPaymentSetupRequest, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> MerchantAdmissionDto:
    async with session.begin():
        return await MerchantAdmissionService(session).submit_payment_setup(current=current, merchant_id=id, request=request)


@router.post("/v1/merchants/{id}/ekyc/cmnd", response_model=MerchantEkycStatusResponse, operation_id="post_v1_merchants_by_id_ekyc_cmnd", tags=["merchant-ekyc"])
async def ekyc_cmnd(id: UUID, request: MerchantEkycSubmitRequest, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> MerchantEkycStatusResponse:
    async with session.begin():
        return await MerchantAdmissionService(session).submit_ekyc(current=current, merchant_id=id, kind="cmnd", object_key=request.object_key)


@router.post("/v1/merchants/{id}/ekyc/selfie", response_model=MerchantEkycStatusResponse, operation_id="post_v1_merchants_by_id_ekyc_selfie", tags=["merchant-ekyc"])
async def ekyc_selfie(id: UUID, request: MerchantEkycSubmitRequest, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> MerchantEkycStatusResponse:
    async with session.begin():
        return await MerchantAdmissionService(session).submit_ekyc(current=current, merchant_id=id, kind="selfie", object_key=request.object_key)


@router.post("/v1/merchants/{id}/ekyc/bank", response_model=MerchantEkycStatusResponse, operation_id="post_v1_merchants_by_id_ekyc_bank", tags=["merchant-ekyc"])
async def ekyc_bank(id: UUID, request: MerchantEkycSubmitRequest, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> MerchantEkycStatusResponse:
    async with session.begin():
        return await MerchantAdmissionService(session).submit_ekyc(current=current, merchant_id=id, kind="bank", object_key=request.object_key)


@router.get("/v1/merchants/{id}/ekyc/status", response_model=MerchantEkycStatusResponse, operation_id="get_v1_merchants_by_id_ekyc_status", tags=["merchant-ekyc"])
async def ekyc_status(id: UUID, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> MerchantEkycStatusResponse:
    async with session.begin():
        return await MerchantAdmissionService(session).ekyc_status(current=current, merchant_id=id)


@router.get("/v1/ops/merchants/pending", response_model=PendingMerchantsResponse, operation_id="get_v1_ops_merchants_pending", tags=["ops"])
async def ops_pending_merchants(current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> PendingMerchantsResponse:
    async with session.begin():
        merchants = await MerchantAdmissionService(session).list_pending(current=current)
    return PendingMerchantsResponse(merchants=merchants)


@router.post("/v1/ops/merchants/{id}/approve", response_model=MerchantAdmissionDto, operation_id="post_v1_ops_merchants_by_id_approve", tags=["ops"])
async def ops_approve_merchant(id: UUID, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> MerchantAdmissionDto:
    async with session.begin():
        return await MerchantAdmissionService(session).approve(current=current, merchant_id=id)


@router.post("/v1/ops/merchants/{id}/reject", response_model=MerchantAdmissionDto, operation_id="post_v1_ops_merchants_by_id_reject", tags=["ops"])
async def ops_reject_merchant(id: UUID, request: OpsMerchantDecisionRequest, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> MerchantAdmissionDto:
    async with session.begin():
        return await MerchantAdmissionService(session).reject(current=current, merchant_id=id, reason=request.reason)


@router.post("/v1/ops/merchants/{id}/verify-payment-recipient", response_model=MerchantAdmissionDto, operation_id="post_v1_ops_merchants_by_id_verify_payment_recipient", tags=["ops"])
async def ops_verify_payment_recipient(id: UUID, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> MerchantAdmissionDto:
    async with session.begin():
        return await MerchantAdmissionService(session).verify_payment_recipient(current=current, merchant_id=id)


@router.post("/v1/ops/merchants/{id}/suspend", response_model=MerchantAdmissionDto, operation_id="post_v1_ops_merchants_by_id_suspend", tags=["ops"])
async def ops_suspend_merchant(id: UUID, request: OpsMerchantDecisionRequest, current: CurrentUser = Depends(require_user), session: AsyncSession = Depends(get_session)) -> MerchantAdmissionDto:
    async with session.begin():
        return await MerchantAdmissionService(session).suspend(current=current, merchant_id=id, reason=request.reason)
