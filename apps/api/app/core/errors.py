from enum import StrEnum
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


class ErrorCode(StrEnum):
    not_implemented = "NOT_IMPLEMENTED"
    internal_error = "INTERNAL_ERROR"
    invalid_credentials = "INVALID_CREDENTIALS"
    unauthorized = "UNAUTHORIZED"
    forbidden = "FORBIDDEN"
    token_expired = "TOKEN_EXPIRED"
    token_reused = "TOKEN_REUSED"
    idempotency_mismatch = "IDEMPOTENCY_MISMATCH"
    tenant_context_missing = "TENANT_CONTEXT_MISSING"
    duplicate_identity = "DUPLICATE_IDENTITY"
    merchant_not_found = "MERCHANT_NOT_FOUND"
    merchant_service_not_found = "MERCHANT_SERVICE_NOT_FOUND"
    booking_not_found = "BOOKING_NOT_FOUND"
    slot_full = "SLOT_FULL"
    hold_limit_exceeded = "HOLD_LIMIT_EXCEEDED"
    invalid_booking_hold = "INVALID_BOOKING_HOLD"
    invalid_booking_state = "INVALID_BOOKING_STATE"
    invalid_check_in_code = "INVALID_CHECK_IN_CODE"
    hold_expired = "HOLD_EXPIRED"
    rate_limited = "RATE_LIMITED"
    promo_not_applicable = "PROMO_NOT_APPLICABLE"
    evidence_retry_exhausted = "EVIDENCE_RETRY_EXHAUSTED"
    audit_write_failed = "AUDIT_WRITE_FAILED"


class ErrorDefinition(BaseModel):
    status: int
    type: str
    title_key: str
    detail_key: str
    retryable: bool
    client_action: str


ERROR_REGISTRY: dict[ErrorCode, ErrorDefinition] = {
    ErrorCode.not_implemented: ErrorDefinition(
        status=501,
        type="https://truecare.vn/problems/not-implemented",
        title_key="errors.not_implemented.title",
        detail_key="errors.not_implemented.detail",
        retryable=False,
        client_action="wait_for_api_implementation",
    ),
    ErrorCode.internal_error: ErrorDefinition(
        status=500,
        type="https://truecare.vn/problems/internal-error",
        title_key="errors.internal_error.title",
        detail_key="errors.internal_error.detail",
        retryable=True,
        client_action="retry_later_or_contact_support",
    ),
    ErrorCode.invalid_credentials: ErrorDefinition(
        status=401,
        type="https://truecare.vn/problems/invalid-credentials",
        title_key="errors.invalid_credentials.title",
        detail_key="errors.invalid_credentials.detail",
        retryable=False,
        client_action="check_credentials",
    ),
    ErrorCode.unauthorized: ErrorDefinition(
        status=401,
        type="https://truecare.vn/problems/unauthorized",
        title_key="errors.unauthorized.title",
        detail_key="errors.unauthorized.detail",
        retryable=False,
        client_action="sign_in",
    ),
    ErrorCode.forbidden: ErrorDefinition(
        status=403,
        type="https://truecare.vn/problems/forbidden",
        title_key="errors.forbidden.title",
        detail_key="errors.forbidden.detail",
        retryable=False,
        client_action="contact_support",
    ),
    ErrorCode.token_expired: ErrorDefinition(
        status=401,
        type="https://truecare.vn/problems/token-expired",
        title_key="errors.token_expired.title",
        detail_key="errors.token_expired.detail",
        retryable=True,
        client_action="refresh_token",
    ),
    ErrorCode.token_reused: ErrorDefinition(
        status=401,
        type="https://truecare.vn/problems/token-reused",
        title_key="errors.token_reused.title",
        detail_key="errors.token_reused.detail",
        retryable=False,
        client_action="sign_in_again",
    ),
    ErrorCode.idempotency_mismatch: ErrorDefinition(
        status=422,
        type="https://truecare.vn/problems/idempotency-mismatch",
        title_key="errors.idempotency_mismatch.title",
        detail_key="errors.idempotency_mismatch.detail",
        retryable=False,
        client_action="generate_new_idempotency_key",
    ),
    ErrorCode.tenant_context_missing: ErrorDefinition(
        status=500,
        type="https://truecare.vn/problems/tenant-context-missing",
        title_key="errors.tenant_context_missing.title",
        detail_key="errors.tenant_context_missing.detail",
        retryable=False,
        client_action="contact_support",
    ),
    ErrorCode.duplicate_identity: ErrorDefinition(
        status=409,
        type="https://truecare.vn/problems/duplicate-identity",
        title_key="errors.duplicate_identity.title",
        detail_key="errors.duplicate_identity.detail",
        retryable=False,
        client_action="log_in_or_use_different_identifier",
    ),
    ErrorCode.merchant_not_found: ErrorDefinition(
        status=404,
        type="https://truecare.vn/problems/merchant-not-found",
        title_key="errors.merchant_not_found.title",
        detail_key="errors.merchant_not_found.detail",
        retryable=False,
        client_action="choose_another_merchant",
    ),
    ErrorCode.merchant_service_not_found: ErrorDefinition(
        status=404,
        type="https://truecare.vn/problems/merchant-service-not-found",
        title_key="errors.merchant_service_not_found.title",
        detail_key="errors.merchant_service_not_found.detail",
        retryable=False,
        client_action="refresh_merchant_services",
    ),
    ErrorCode.booking_not_found: ErrorDefinition(
        status=404,
        type="https://truecare.vn/problems/booking-not-found",
        title_key="errors.booking_not_found.title",
        detail_key="errors.booking_not_found.detail",
        retryable=False,
        client_action="refresh_bookings",
    ),
    ErrorCode.slot_full: ErrorDefinition(
        status=409,
        type="https://truecare.vn/problems/slot-full",
        title_key="errors.slot_full.title",
        detail_key="errors.slot_full.detail",
        retryable=True,
        client_action="choose_another_slot",
    ),
    ErrorCode.hold_limit_exceeded: ErrorDefinition(
        status=429,
        type="https://truecare.vn/problems/hold-limit-exceeded",
        title_key="errors.hold_limit_exceeded.title",
        detail_key="errors.hold_limit_exceeded.detail",
        retryable=False,
        client_action="release_existing_hold",
    ),
    ErrorCode.invalid_booking_hold: ErrorDefinition(
        status=409,
        type="https://truecare.vn/problems/invalid-booking-hold",
        title_key="errors.invalid_booking_hold.title",
        detail_key="errors.invalid_booking_hold.detail",
        retryable=False,
        client_action="change_booking_request",
    ),
    ErrorCode.invalid_booking_state: ErrorDefinition(
        status=409,
        type="https://truecare.vn/problems/invalid-booking-state",
        title_key="errors.invalid_booking_state.title",
        detail_key="errors.invalid_booking_state.detail",
        retryable=False,
        client_action="refresh_booking",
    ),
    ErrorCode.invalid_check_in_code: ErrorDefinition(
        status=403,
        type="https://truecare.vn/problems/invalid-check-in-code",
        title_key="errors.invalid_check_in_code.title",
        detail_key="errors.invalid_check_in_code.detail",
        retryable=False,
        client_action="scan_or_enter_code_again",
    ),
    ErrorCode.hold_expired: ErrorDefinition(
        status=410,
        type="https://truecare.vn/problems/hold-expired",
        title_key="errors.hold_expired.title",
        detail_key="errors.hold_expired.detail",
        retryable=False,
        client_action="create_new_booking_hold",
    ),
    ErrorCode.rate_limited: ErrorDefinition(
        status=429,
        type="https://truecare.vn/problems/rate-limited",
        title_key="errors.rate_limited.title",
        detail_key="errors.rate_limited.detail",
        retryable=True,
        client_action="wait_and_retry",
    ),
    ErrorCode.promo_not_applicable: ErrorDefinition(
        status=422,
        type="https://truecare.vn/problems/promo-not-applicable",
        title_key="errors.promo_not_applicable.title",
        detail_key="errors.promo_not_applicable.detail",
        retryable=False,
        client_action="choose_another_promo",
    ),
    ErrorCode.evidence_retry_exhausted: ErrorDefinition(
        status=409,
        type="https://truecare.vn/problems/evidence-retry-exhausted",
        title_key="errors.evidence_retry_exhausted.title",
        detail_key="errors.evidence_retry_exhausted.detail",
        retryable=False,
        client_action="request_ops_review",
    ),
    ErrorCode.audit_write_failed: ErrorDefinition(
        status=500,
        type="https://truecare.vn/problems/audit-write-failed",
        title_key="errors.audit_write_failed.title",
        detail_key="errors.audit_write_failed.detail",
        retryable=True,
        client_action="retry_later_or_contact_support",
    ),
}


class ProblemDetails(BaseModel):
    type: str
    title: str
    status: int
    detail: str
    code: ErrorCode
    retryable: bool
    client_action: str = Field(alias="clientAction")
    request_id: str | None = Field(default=None, alias="requestId")
    extra: dict[str, Any] = Field(default_factory=dict)


class ApiError(Exception):
    def __init__(self, code: ErrorCode, *, detail: str | None = None, extra: dict[str, Any] | None = None):
        self.code = code
        self.detail = detail
        self.extra = extra or {}
        super().__init__(code.value)


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def problem_for_error(error: ApiError, request: Request) -> ProblemDetails:
    definition = ERROR_REGISTRY[error.code]
    return ProblemDetails(
        type=definition.type,
        title=definition.title_key,
        status=definition.status,
        detail=error.detail or definition.detail_key,
        code=error.code,
        retryable=definition.retryable,
        clientAction=definition.client_action,
        requestId=_request_id(request),
        extra=error.extra,
    )


async def api_error_handler(request: Request, error: ApiError) -> JSONResponse:
    problem = problem_for_error(error, request)
    return JSONResponse(
        status_code=problem.status,
        content=problem.model_dump(by_alias=True, mode="json"),
        media_type="application/problem+json",
    )


async def unhandled_error_handler(request: Request, error: Exception) -> JSONResponse:
    problem = problem_for_error(
        ApiError(ErrorCode.internal_error, detail="errors.internal_error.detail"),
        request,
    )
    return JSONResponse(
        status_code=problem.status,
        content=problem.model_dump(by_alias=True, mode="json"),
        media_type="application/problem+json",
    )
