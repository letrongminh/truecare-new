from fastapi import FastAPI

from app.core.errors import ApiError, api_error_handler, unhandled_error_handler
from app.core.request_id import request_id_middleware
from app.routers.auth import IMPLEMENTED_AUTH_ROUTES
from app.routers.auth import router as auth_router
from app.routers.contract_stubs import build_contract_router
from app.routers.control import router as control_router
from app.routers.marketplace import IMPLEMENTED_MARKETPLACE_ROUTES
from app.routers.marketplace import router as marketplace_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="TrueCare API",
        version="0.1.0",
        description="Foundation OpenAPI contract for the TrueCare Python port.",
    )
    app.middleware("http")(request_id_middleware)
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
    app.include_router(control_router)
    app.include_router(auth_router)
    app.include_router(marketplace_router)
    app.include_router(build_contract_router(exclude=IMPLEMENTED_AUTH_ROUTES | IMPLEMENTED_MARKETPLACE_ROUTES))
    return app


app = create_app()
