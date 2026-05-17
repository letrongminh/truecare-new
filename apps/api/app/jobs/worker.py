from __future__ import annotations

import argparse
import asyncio

from app.db.session import get_sessionmaker
from app.services.domain_events import DomainEventRepository


async def drain_once(consumer_name: str, limit: int) -> int:
    async with get_sessionmaker()() as session:
        async with session.begin():
            events = await DomainEventRepository(session).claim_batch(consumer_name=consumer_name, limit=limit)
        return len(events)


async def main_async() -> None:
    parser = argparse.ArgumentParser(description="TrueCare worker skeleton")
    parser.add_argument("--consumer", default="truecare-worker")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    claimed = await drain_once(args.consumer, args.limit)
    print(f"claimed_domain_events={claimed}")


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
