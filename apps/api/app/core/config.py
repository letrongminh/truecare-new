from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    public_api_base_url: str = Field(default="http://127.0.0.1:8000", alias="PUBLIC_API_BASE_URL")
    sentry_environment: str = Field(default="local", alias="SENTRY_ENVIRONMENT")
    log_level: str = Field(default="info", alias="LOG_LEVEL")
    database_url_pooler: str | None = Field(default=None, alias="DATABASE_URL_POOLER")
    database_url_direct: str | None = Field(default=None, alias="DATABASE_URL_DIRECT")
    supabase_url: str | None = Field(default=None, alias="SUPABASE_URL")
    jwt_signing_private_jwk: str | None = Field(default=None, alias="JWT_SIGNING_PRIVATE_JWK")
    jwt_signing_public_jwks: str | None = Field(default=None, alias="JWT_SIGNING_PUBLIC_JWKS")
    jwt_issuer: str = Field(default="truecare-new-api", alias="JWT_ISSUER")
    jwt_audience: str = Field(default="truecare-new", alias="JWT_AUDIENCE")
    default_tenant_name: str = "TrueCare Pilot"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
