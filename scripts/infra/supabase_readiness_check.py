from __future__ import annotations

import asyncio
import os

import asyncpg


REQUIRED_EXTENSIONS = ("postgis", "pg_trgm", "pgcrypto")
FORBIDDEN_EXTENSIONS = ("timescaledb", "vector", "h3")
REQUIRED_BUCKETS = ("evidence", "merchant-qr", "exports")


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL_DIRECT")
    if not url:
        raise SystemExit("DATABASE_URL_DIRECT is required")
    if url.startswith("postgresql+asyncpg://"):
        return "postgresql://" + url.removeprefix("postgresql+asyncpg://")
    return url


async def _require_value(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


async def main() -> None:
    if not os.environ.get("SUPABASE_PROJECT_REF"):
        raise SystemExit("SUPABASE_PROJECT_REF is required")

    conn = await asyncpg.connect(_database_url())
    try:
        for ext in REQUIRED_EXTENSIONS:
            exists = await conn.fetchval("select exists(select 1 from pg_extension where extname = $1)", ext)
            await _require_value(bool(exists), f"missing required extension: {ext}")

        if os.environ.get("ALLOW_EXTRA_DB_EXTENSIONS") != "1":
            forbidden = await conn.fetchval(
                "select string_agg(extname, ',') from pg_extension where extname = any($1::text[])",
                list(FORBIDDEN_EXTENSIONS),
            )
            await _require_value(not forbidden, f"forbidden extension(s) installed without ALLOW_EXTRA_DB_EXTENSIONS=1: {forbidden}")

        service_bypass = await conn.fetchval("select coalesce((select rolbypassrls::text from pg_roles where rolname = 'service_role'), 'missing')")
        await _require_value(service_bypass == "true", f"service_role must exist and bypass RLS; got {service_bypass}")

        realtime_messages = await conn.fetchval("select to_regclass('realtime.messages') is not null")
        await _require_value(bool(realtime_messages), "realtime.messages table is missing")

        storage_buckets = await conn.fetchval("select to_regclass('storage.buckets') is not null")
        await _require_value(bool(storage_buckets), "storage.buckets table is missing")

        missing_buckets = await conn.fetchval(
            """
            with required(id) as (
              select unnest($1::text[])
            )
            select string_agg(required.id, ',')
            from required
            left join storage.buckets b on b.id = required.id
            where b.id is null
            """,
            list(REQUIRED_BUCKETS),
        )
        await _require_value(not missing_buckets, f"missing storage bucket(s): {missing_buckets}")
    finally:
        await conn.close()

    print("ok")


if __name__ == "__main__":
    asyncio.run(main())
