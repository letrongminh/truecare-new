from fastapi import FastAPI

from app.core.config import get_settings
from app.core.errors import ApiError, api_error_handler, unhandled_error_handler
from app.core.logging import configure_logging, logging_middleware
from app.core.rate_limit import RateLimitConfig, InMemoryRateLimiter, rate_limit_middleware
from app.core.request_id import request_id_middleware
from app.routers.auth import IMPLEMENTED_AUTH_ROUTES
from app.routers.auth import router as auth_router
from app.routers.contract_stubs import build_contract_router
from app.routers.control import router as control_router
from app.routers.marketplace import IMPLEMENTED_MARKETPLACE_ROUTES
from app.routers.marketplace import router as marketplace_router
from app.routers.me import IMPLEMENTED_ME_ROUTES
from app.routers.me import router as me_router
from app.routers.phase23 import IMPLEMENTED_PHASE23_ROUTES
from app.routers.phase23 import router as phase23_router


def _rate_limit_config() -> RateLimitConfig:
    settings = get_settings()
    return RateLimitConfig(
        enabled=settings.rate_limit_enabled,
        global_per_minute=settings.rate_limit_global_per_minute,
        login_limit=settings.rate_limit_login_limit,
        login_window_seconds=settings.rate_limit_login_window_seconds,
        signup_limit=settings.rate_limit_signup_limit,
        signup_window_seconds=settings.rate_limit_signup_window_seconds,
        refresh_limit=settings.rate_limit_refresh_limit,
        refresh_window_seconds=settings.rate_limit_refresh_window_seconds,
    )


def create_app(rate_limit_config: RateLimitConfig | None = None) -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(
        title="TrueCare API",
        version="0.1.0",
        description="Foundation OpenAPI contract for the TrueCare Python port.",
    )
    app.state.rate_limiter = InMemoryRateLimiter()
    app.state.rate_limit_config = rate_limit_config or _rate_limit_config()
    app.middleware("http")(logging_middleware)
    app.middleware("http")(rate_limit_middleware)
    app.middleware("http")(request_id_middleware)
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
    app.include_router(control_router)
    app.include_router(auth_router)
    app.include_router(me_router)
    app.include_router(marketplace_router)
    app.include_router(phase23_router)
    app.include_router(build_contract_router(exclude=IMPLEMENTED_AUTH_ROUTES | IMPLEMENTED_ME_ROUTES | IMPLEMENTED_MARKETPLACE_ROUTES | IMPLEMENTED_PHASE23_ROUTES))
    return app


app = create_app()
