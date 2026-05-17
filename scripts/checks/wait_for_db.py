#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import os
import sys
from time import monotonic

from sqlalchemy import text

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(ROOT, "apps", "api"))

from app.db.session import get_engine, normalize_database_url  # noqa: E402


async def main() -> int:
    url = normalize_database_url(os.environ.get("DATABASE_URL_DIRECT", "postgresql+asyncpg://truecare:truecare@127.0.0.1:55432/truecare"))
    deadline = monotonic() + 30
    last_error: Exception | None = None
    while monotonic() < deadline:
        engine = get_engine(url)
        try:
            async with engine.connect() as conn:
                await conn.execute(text("select 1"))
            await engine.dispose()
            print("ok")
            return 0
        except Exception as exc:  # pragma: no cover - only used by local make target
            last_error = exc
            await engine.dispose()
            await asyncio.sleep(1)
    print(f"database did not become ready: {last_error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
