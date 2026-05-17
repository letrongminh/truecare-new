from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select, update

from app.db.models import Booking, DomainEvent, Profile, SlotCapacity, WorkerJob, WorkerRun
from app.db.session import get_sessionmaker, set_local_context
from app.domain.states import BookingState
from app.services.domain_events import DomainEventRepository

EXPIRE_STALE_HOLDS_JOB = "expire_stale_holds"
WORKER_LEASE_SECONDS = 60
MAX_EVENT_ATTEMPTS = 3
NO_SHOW_STATUSES = (BookingState.held.value, BookingState.checked_in.value)


async def _ensure_worker_job(session, *, name: str) -> WorkerJob:
    job = await session.get(WorkerJob, name)
    if job is not None:
        return job
    job = WorkerJob(
        name=name,
        tenant_id=None,
        schedule_kind="interval",
        enabled=True,
        next_run_at=datetime.now(UTC),
        max_lag_seconds=120,
    )
    session.add(job)
    await session.flush()
    return job


async def _expire_stale_holds(session, *, owner_id: str, limit: int) -> int:
    now = datetime.now(UTC)
    job = await _ensure_worker_job(session, name=EXPIRE_STALE_HOLDS_JOB)
    run = WorkerRun(
        id=uuid4(),
        tenant_id=None,
        job_name=job.name,
        owner_id=owner_id,
        status="running",
        started_at=now,
        lease_expires_at=now + timedelta(seconds=WORKER_LEASE_SECONDS),
    )
    session.add(run)
    await session.flush()

    rows = list(
        (
            await session.scalars(
                select(Booking)
                .where(Booking.status.in_(NO_SHOW_STATUSES), Booking.expires_at <= now)
                .order_by(Booking.expires_at, Booking.id)
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        ).all()
    )

    events = DomainEventRepository(session)
    for booking in rows:
        await set_local_context(session, tenant_id=booking.tenant_id, user_id=booking.user_id, role="worker")
        previous_status = booking.status
        booking.status = BookingState.no_show.value
        booking.updated_at = now
        booking.check_in_token = ""
        await session.execute(
            update(SlotCapacity)
            .where(SlotCapacity.id == booking.slot_capacity_id, SlotCapacity.status == "held")
            .values(status="available", held_by_user_id=None, held_at=None, expires_at=None)
        )
        profile = await session.get(Profile, booking.user_id)
        if profile is not None:
            profile.no_show_count += 1
            profile.last_no_show_at = now
        await events.emit(
            tenant_id=booking.tenant_id,
            aggregate_type="booking",
            aggregate_id=booking.id,
            event_type="booking.no_show",
            payload={
                "booking_id": str(booking.id),
                "user_id": str(booking.user_id),
                "merchant_id": str(booking.merchant_id),
                "expired_at": now.isoformat(),
                "previous_status": previous_status,
            },
        )

    if rows:
        await set_local_context(session, tenant_id=rows[0].tenant_id, role="worker")
    run.rows_processed = len(rows)
    run.status = "completed"
    run.finished_at = datetime.now(UTC)
    job.last_success_at = run.finished_at
    job.next_run_at = run.finished_at + timedelta(seconds=job.max_lag_seconds)
    return len(rows)


async def _process_domain_event(event: DomainEvent) -> str:
    if event.payload.get("force_error"):
        raise RuntimeError(str(event.payload.get("force_error")))
    return f"{event.event_type}:{event.aggregate_id}:{event.aggregate_version}"


async def drain_once(consumer_name: str, limit: int) -> tuple[int, int, int, int]:
    async with get_sessionmaker()() as session:
        async with session.begin():
            scheduled_rows = await _expire_stale_holds(session, owner_id=consumer_name, limit=limit)
            repository = DomainEventRepository(session)
            events = await repository.claim_batch(consumer_name=consumer_name, limit=limit)
            processed = 0
            dead_letters = 0
            for event in events:
                try:
                    result_hash = await _process_domain_event(event)
                except Exception as exc:
                    if event.attempts >= MAX_EVENT_ATTEMPTS:
                        await repository.mark_dead_letter(event=event, reason=str(exc), consumer_name=consumer_name)
                        dead_letters += 1
                    else:
                        await repository.release_for_retry(event=event, retry_after_seconds=min(300, event.attempts * 30))
                    continue
                await repository.record_processed(consumer_name=consumer_name, event=event, result_hash=result_hash)
                processed += 1
        return len(events), processed, dead_letters, scheduled_rows


async def main_async() -> None:
    parser = argparse.ArgumentParser(description="TrueCare worker skeleton")
    parser.add_argument("--consumer", default="truecare-worker")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    claimed, processed, dead_letters, scheduled_rows = await drain_once(args.consumer, args.limit)
    print(
        f"claimed_domain_events={claimed} "
        f"processed_domain_events={processed} "
        f"dead_lettered_domain_events={dead_letters} "
        f"scheduled_rows_processed={scheduled_rows}"
    )


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
