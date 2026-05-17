from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError, ErrorCode
from app.db.models import IdempotencyKey


class IdempotencyStatus(StrEnum):
    proceed = "proceed"
    replay = "replay"


@dataclass(frozen=True)
class IdempotencyDecision:
    status: IdempotencyStatus
    response: dict[str, Any] | None = None


def canonical_body_hash(body: Any) -> str:
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class IdempotencyService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def check(self, *, tenant_id: UUID, subject: str, key: str, body: Any) -> IdempotencyDecision:
        body_hash = canonical_body_hash(body)
        existing = await self.session.get(IdempotencyKey, {"tenant_id": tenant_id, "subject": subject, "key": key})
        if existing is None or existing.expires_at <= datetime.now(UTC):
            return IdempotencyDecision(status=IdempotencyStatus.proceed)
        if existing.body_hash != body_hash:
            raise ApiError(ErrorCode.idempotency_mismatch, detail="Same Idempotency-Key was reused with a different request body.")
        return IdempotencyDecision(status=IdempotencyStatus.replay, response=existing.response)

    async def store(
        self,
        *,
        tenant_id: UUID,
        subject: str,
        key: str,
        body: Any,
        response: dict[str, Any],
        ttl_hours: int = 24,
    ) -> None:
        existing = await self.session.get(IdempotencyKey, {"tenant_id": tenant_id, "subject": subject, "key": key})
        if existing is not None:
            return
        self.session.add(
            IdempotencyKey(
                tenant_id=tenant_id,
                subject=subject,
                key=key,
                body_hash=canonical_body_hash(body),
                response=response,
                expires_at=datetime.now(UTC) + timedelta(hours=ttl_hours),
            )
        )
        await self.session.flush()
