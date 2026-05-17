from dataclasses import dataclass
from re import sub

from fastapi import APIRouter, Request

from app.core.errors import ApiError, ErrorCode, ProblemDetails


@dataclass(frozen=True)
class RouteSpec:
    method: str
    path: str
    tag: str
    summary: str


CONTRACT_ROUTES: tuple[RouteSpec, ...] = (
    RouteSpec("GET", "/v1/search", "search", "Search merchants"),
    RouteSpec("GET", "/v1/service-templates", "search", "List service templates"),
    RouteSpec("POST", "/v1/auth/exists", "auth", "Check whether an auth identity exists"),
    RouteSpec("POST", "/v1/auth/signup", "auth", "Create a user account"),
    RouteSpec("POST", "/v1/auth/login", "auth", "Log in"),
    RouteSpec("POST", "/v1/auth/refresh", "auth", "Refresh access token"),
    RouteSpec("POST", "/v1/auth/logout", "auth", "Log out"),
    RouteSpec("POST", "/v1/auth/logout-all", "auth", "Log out all sessions"),
    RouteSpec("GET", "/v1/auth/me", "auth", "Get current auth principal"),
    RouteSpec("POST", "/v1/auth/forgot-password", "auth", "Create manual password reset request"),
    RouteSpec("GET", "/v1/me/profile", "me", "Get my profile"),
    RouteSpec("PATCH", "/v1/me/profile", "me", "Update my profile"),
    RouteSpec("GET", "/v1/me/vehicles", "me", "List my vehicles"),
    RouteSpec("POST", "/v1/me/vehicles", "me", "Create my vehicle"),
    RouteSpec("PATCH", "/v1/me/vehicles/{id}", "me", "Update my vehicle"),
    RouteSpec("GET", "/v1/me/bookings", "me", "List my bookings"),
    RouteSpec("POST", "/v1/me/data-export", "me", "Request my data export"),
    RouteSpec("GET", "/v1/me/data-export/{job_id}", "me", "Get my data export status"),
    RouteSpec("DELETE", "/v1/me/account", "me", "Request account deletion"),
    RouteSpec("POST", "/v1/me/notifications/register", "me", "Register notification token"),
    RouteSpec("GET", "/v1/me/notifications/preferences", "me", "Get notification preferences"),
    RouteSpec("PATCH", "/v1/me/notifications/preferences", "me", "Update notification preferences"),
    RouteSpec("POST", "/v1/me/password", "me", "Change password"),
    RouteSpec("GET", "/v1/me/sessions", "me", "List sessions"),
    RouteSpec("DELETE", "/v1/me/sessions/{id}", "me", "Revoke session"),
    RouteSpec("POST", "/v1/me/cancel-delete", "me", "Cancel account deletion"),
    RouteSpec("GET", "/v1/merchants/nearby", "merchants", "List nearby merchants"),
    RouteSpec("GET", "/v1/merchants/{id}", "merchants", "Get merchant"),
    RouteSpec("GET", "/v1/merchants/{id}/services", "merchants", "List merchant services"),
    RouteSpec("GET", "/v1/merchants/{id}/bays", "merchants", "List merchant bays"),
    RouteSpec("POST", "/v1/bookings/holds", "bookings", "Create booking hold"),
    RouteSpec("GET", "/v1/bookings", "bookings", "List bookings"),
    RouteSpec("GET", "/v1/bookings/{id}", "bookings", "Get booking"),
    RouteSpec("POST", "/v1/bookings/{id}/cancel", "bookings", "Cancel booking"),
    RouteSpec("POST", "/v1/bookings/{id}/arrived", "bookings", "Mark booking arrived"),
    RouteSpec("POST", "/v1/bookings/{id}/rate", "bookings", "Rate booking"),
    RouteSpec("POST", "/v1/payments/initiate", "payments", "Initiate payment"),
    RouteSpec("GET", "/v1/payments/{id}", "payments", "Get payment"),
    RouteSpec("POST", "/v1/payments/{id}/user-claimed", "payments", "Mark payment user claimed"),
    RouteSpec("POST", "/v1/payments/{id}/merchant-confirmed", "payments", "Merchant confirms payment"),
    RouteSpec("POST", "/v1/payments/{id}/merchant-denied", "payments", "Merchant denies payment"),
    RouteSpec("POST", "/v1/payments/{id}/cash-record", "payments", "Record cash payment"),
    RouteSpec("POST", "/v1/payments/{id}/switch-method", "payments", "Switch payment method"),
    RouteSpec("POST", "/v1/evidence/{booking_id}/presign", "evidence", "Presign evidence upload"),
    RouteSpec("POST", "/v1/evidence/{evidence_id}/confirm", "evidence", "Confirm evidence upload"),
    RouteSpec("GET", "/v1/evidence/{booking_id}", "evidence", "List booking evidence"),
    RouteSpec("POST", "/v1/promo-codes/validate", "promo", "Validate promo code"),
    RouteSpec("GET", "/v1/promo-codes/user", "promo", "List user promo codes"),
    RouteSpec("GET", "/v1/rewards/progress", "rewards", "Get reward progress"),
    RouteSpec("GET", "/v1/rewards/vouchers", "rewards", "List reward vouchers"),
    RouteSpec("POST", "/v1/rewards/vouchers/{id}/reserve", "rewards", "Reserve voucher"),
    RouteSpec("POST", "/v1/rewards/vouchers/{id}/release", "rewards", "Release voucher"),
    RouteSpec("POST", "/v1/rewards/vouchers/{id}/redeem", "rewards", "Redeem voucher"),
    RouteSpec("GET", "/v1/referrals/me", "referrals", "Get referral state"),
    RouteSpec("POST", "/v1/referrals/share-event", "referrals", "Record referral share event"),
    RouteSpec("POST", "/v1/complaints", "complaints", "Create complaint"),
    RouteSpec("GET", "/v1/complaints/{id}", "complaints", "Get complaint"),
    RouteSpec("POST", "/v1/merchants/applications", "merchant", "Create merchant application"),
    RouteSpec("POST", "/v1/merchants/{id}/confirm-photo", "merchant", "Confirm merchant photo"),
    RouteSpec("POST", "/v1/merchants/{id}/payment-setup", "merchant", "Submit merchant payment setup"),
    RouteSpec("GET", "/v1/merchants/{id}/queue", "merchant", "Get merchant queue"),
    RouteSpec("GET", "/v1/merchants/{id}/calendar", "merchant", "Get merchant calendar"),
    RouteSpec("POST", "/v1/merchants/{id}/calendar/maintenance", "merchant", "Create merchant maintenance window"),
    RouteSpec("GET", "/v1/merchants/{id}/golden-hour", "merchant", "Get merchant golden hour"),
    RouteSpec("PUT", "/v1/merchants/{id}/golden-hour", "merchant", "Update merchant golden hour"),
    RouteSpec("GET", "/v1/merchants/{id}/daily-summary", "merchant", "Get merchant daily summary"),
    RouteSpec("GET", "/v1/merchants/{id}/daily-summary.csv", "merchant", "Export merchant daily summary CSV"),
    RouteSpec("POST", "/v1/bookings/{id}/check-in", "merchant", "Merchant checks in booking"),
    RouteSpec("POST", "/v1/bookings/{id}/start-service", "merchant", "Start service"),
    RouteSpec("POST", "/v1/bookings/{id}/complete-service", "merchant", "Complete service"),
    RouteSpec("POST", "/v1/merchant-services", "merchant-services", "Create merchant service"),
    RouteSpec("PATCH", "/v1/merchant-services/{id}", "merchant-services", "Update merchant service"),
    RouteSpec("GET", "/v1/merchant-services/{id}/price-history", "merchant-services", "Get merchant service price history"),
    RouteSpec("POST", "/v1/merchant-services/custom", "merchant-services", "Create custom merchant service"),
    RouteSpec("POST", "/v1/merchant-services/{id}/resubmit", "merchant-services", "Resubmit merchant service"),
    RouteSpec("POST", "/v1/merchants/{id}/ekyc/cmnd", "merchant-ekyc", "Upload merchant CMND"),
    RouteSpec("POST", "/v1/merchants/{id}/ekyc/selfie", "merchant-ekyc", "Upload merchant selfie"),
    RouteSpec("POST", "/v1/merchants/{id}/ekyc/bank", "merchant-ekyc", "Upload merchant bank evidence"),
    RouteSpec("GET", "/v1/merchants/{id}/ekyc/status", "merchant-ekyc", "Get merchant eKYC status"),
    RouteSpec("GET", "/v1/ops/merchants/pending", "ops", "List pending merchants"),
    RouteSpec("POST", "/v1/ops/merchants/{id}/approve", "ops", "Approve merchant"),
    RouteSpec("POST", "/v1/ops/merchants/{id}/reject", "ops", "Reject merchant"),
    RouteSpec("POST", "/v1/ops/merchants/{id}/verify-payment-recipient", "ops", "Verify merchant payment recipient"),
    RouteSpec("POST", "/v1/ops/merchants/{id}/suspend", "ops", "Suspend merchant"),
    RouteSpec("POST", "/v1/ops/promo-codes", "ops", "Create ops promo code"),
    RouteSpec("POST", "/v1/ops/merchant-services/{id}/approve", "ops", "Approve merchant service"),
    RouteSpec("POST", "/v1/ops/merchant-services/{id}/reject", "ops", "Reject merchant service"),
    RouteSpec("GET", "/v1/ops/commission-receivables", "ops", "List commission receivables"),
    RouteSpec("GET", "/v1/ops/data-room/{section}", "ops", "Get ops data room section"),
    RouteSpec("POST", "/v1/ops/exports", "ops", "Create ops export"),
    RouteSpec("GET", "/v1/ops/exports/{job_id}", "ops", "Get ops export"),
    RouteSpec("GET", "/v1/ops/complaints", "ops", "List ops complaints"),
    RouteSpec("PATCH", "/v1/ops/complaints/{id}", "ops", "Update ops complaint"),
    RouteSpec("POST", "/v1/ops/bookings", "ops", "Create ops booking"),
    RouteSpec("POST", "/v1/ops/bookings/{id}/check-in", "ops", "Ops checks in booking"),
    RouteSpec("POST", "/v1/ops/evidence/upload", "ops", "Ops uploads evidence"),
    RouteSpec("POST", "/v1/ops/payments/{id}/confirm", "ops", "Ops confirms payment"),
    RouteSpec("GET", "/v1/ops/users", "ops", "List ops users"),
    RouteSpec("POST", "/v1/ops/users", "ops", "Create ops user"),
    RouteSpec("POST", "/v1/ops/users/{id}/reset-password", "ops", "Reset user password"),
    RouteSpec("POST", "/v1/ops/reward/voucher", "ops", "Mint reward voucher"),
    RouteSpec("GET", "/v1/ops/audit-log", "ops", "List audit log"),
    RouteSpec("POST", "/v1/realtime/token", "realtime", "Create realtime token"),
)


def _operation_id(method: str, path: str) -> str:
    path = sub(r"\{([^}]+)\}", r"by_\1", path.strip("/"))
    cleaned = sub(r"[^a-zA-Z0-9]+", "_", path)
    return f"{method.lower()}_{cleaned}".strip("_")


async def not_implemented(request: Request) -> None:
    raise ApiError(
        ErrorCode.not_implemented,
        detail=f"{request.method} {request.url.path} is in the OpenAPI contract but is not implemented yet.",
        extra={"path": request.url.path, "method": request.method},
    )


def build_contract_router(exclude: set[tuple[str, str]] | None = None) -> APIRouter:
    router = APIRouter()
    excluded = exclude or set()
    for spec in CONTRACT_ROUTES:
        if (spec.method, spec.path) in excluded:
            continue
        router.add_api_route(
            spec.path,
            not_implemented,
            methods=[spec.method],
            tags=[spec.tag],
            summary=spec.summary,
            operation_id=_operation_id(spec.method, spec.path),
            responses={501: {"model": ProblemDetails, "description": "Contract stub not implemented yet"}},
        )
    return router
