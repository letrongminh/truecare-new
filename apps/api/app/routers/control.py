from fastapi import APIRouter, Response
from pydantic import BaseModel

from app.core.config import get_settings

router = APIRouter(tags=["platform"])


class HealthResponse(BaseModel):
    status: str


class ReadyResponse(BaseModel):
    status: str
    checks: dict[str, str]


class VersionCheckResponse(BaseModel):
    minimum_supported_build: int
    latest_supported_build: int
    update_class: str
    app_store_url: str | None = None
    play_store_url: str | None = None
    messages: dict[str, str]


class FlagsResponse(BaseModel):
    flags: dict[str, bool]


@router.get("/healthz", response_model=HealthResponse, operation_id="getHealthz")
async def healthz() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/readyz", response_model=ReadyResponse, operation_id="getReadyz")
async def readyz() -> ReadyResponse:
    settings = get_settings()
    return ReadyResponse(
        status="ok",
        checks={
            "postgres": "configured" if settings.database_url_pooler else "not_configured",
            "storage": "configured" if settings.supabase_url else "not_configured",
            "realtime": "configured" if settings.supabase_url else "not_configured",
        },
    )


@router.get("/metrics", operation_id="getMetrics")
async def metrics() -> Response:
    body = "\n".join(
        [
            "# HELP truecare_build_info TrueCare API build metadata.",
            "# TYPE truecare_build_info gauge",
            'truecare_build_info{service="api",version="0.1.0"} 1',
            "",
        ],
    )
    return Response(content=body, media_type="text/plain; version=0.0.4")


@router.get("/v1/app/version-check", response_model=VersionCheckResponse, operation_id="getVersionCheck")
async def version_check() -> VersionCheckResponse:
    return VersionCheckResponse(
        minimum_supported_build=1,
        latest_supported_build=1,
        update_class="none",
        messages={
            "vi": "truecare.version.ok",
            "en": "truecare.version.ok",
        },
    )


@router.get("/v1/flags", response_model=FlagsResponse, operation_id="getFlags")
async def flags() -> FlagsResponse:
    return FlagsResponse(
        flags={
            "presence": False,
            "search": True,
            "delete_now": False,
            "reward_active": True,
            "promo_active": True,
            "vetc_login_visible": True,
        },
    )
