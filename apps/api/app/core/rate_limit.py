from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from math import ceil
from time import monotonic
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.errors import ApiError, ErrorCode, problem_for_error


@dataclass(frozen=True)
class RateLimitRule:
    name: str
    limit: int
    window_seconds: int


@dataclass(frozen=True)
class RateLimitConfig:
    enabled: bool = True
    global_per_minute: int = 100
    login_limit: int = 5
    login_window_seconds: int = 900
    signup_limit: int = 3
    signup_window_seconds: int = 3600
    refresh_limit: int = 20
    refresh_window_seconds: int = 3600

    @property
    def global_rule(self) -> RateLimitRule:
        return RateLimitRule("global", self.global_per_minute, 60)

    @property
    def login_rule(self) -> RateLimitRule:
        return RateLimitRule("auth.login", self.login_limit, self.login_window_seconds)

    @property
    def signup_rule(self) -> RateLimitRule:
        return RateLimitRule("auth.signup", self.signup_limit, self.signup_window_seconds)

    @property
    def refresh_rule(self) -> RateLimitRule:
        return RateLimitRule("auth.refresh", self.refresh_limit, self.refresh_window_seconds)


@dataclass
class RateLimitBucket:
    count: int
    reset_at: float


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after: int
    remaining: int
    limit: int
    window_seconds: int
    rule: str


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, RateLimitBucket] = {}

    def check(self, *, key: str, rule: RateLimitRule, now: float | None = None) -> RateLimitDecision:
        current = monotonic() if now is None else now
        if rule.limit <= 0:
            return RateLimitDecision(True, 0, 0, rule.limit, rule.window_seconds, rule.name)

        bucket_key = f"{rule.name}:{key}"
        bucket = self._buckets.get(bucket_key)
        if bucket is None or bucket.reset_at <= current:
            bucket = RateLimitBucket(count=0, reset_at=current + rule.window_seconds)
            self._buckets[bucket_key] = bucket

        if bucket.count >= rule.limit:
            return RateLimitDecision(
                allowed=False,
                retry_after=max(1, ceil(bucket.reset_at - current)),
                remaining=0,
                limit=rule.limit,
                window_seconds=rule.window_seconds,
                rule=rule.name,
            )

        bucket.count += 1
        return RateLimitDecision(
            allowed=True,
            retry_after=0,
            remaining=max(0, rule.limit - bucket.count),
            limit=rule.limit,
            window_seconds=rule.window_seconds,
            rule=rule.name,
        )


def client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


def subject_hash(value: str) -> str:
    return sha256(value.strip().lower().encode("utf-8")).hexdigest()


def _limiter(request: Request) -> InMemoryRateLimiter:
    limiter = getattr(request.app.state, "rate_limiter", None)
    if limiter is None:
        limiter = InMemoryRateLimiter()
        request.app.state.rate_limiter = limiter
    return limiter


def _config(request: Request) -> RateLimitConfig:
    config = getattr(request.app.state, "rate_limit_config", None)
    if config is None:
        config = RateLimitConfig()
        request.app.state.rate_limit_config = config
    return config


def _extra(decision: RateLimitDecision, subject: str) -> dict[str, Any]:
    return {
        "rule": decision.rule,
        "limit": decision.limit,
        "remaining": decision.remaining,
        "retryAfter": decision.retry_after,
        "subject": subject,
        "windowSeconds": decision.window_seconds,
    }


def check_rate_limit(request: Request, *, rule: RateLimitRule, subject: str) -> RateLimitDecision:
    config = _config(request)
    if not config.enabled:
        return RateLimitDecision(True, 0, rule.limit, rule.limit, rule.window_seconds, rule.name)
    decision = _limiter(request).check(key=subject, rule=rule)
    if not decision.allowed:
        raise ApiError(ErrorCode.rate_limited, detail="Rate limit exceeded.", extra=_extra(decision, subject))
    return decision


def enforce_login_rate_limit(request: Request, identifier: str) -> None:
    subject = f"{client_ip(request)}:{subject_hash(identifier)}"
    check_rate_limit(request, rule=_config(request).login_rule, subject=subject)


def enforce_signup_rate_limit(request: Request, identifier: str) -> None:
    device_id = request.headers.get("x-device-id") or "unknown-device"
    subject = f"{client_ip(request)}:{subject_hash(identifier)}:{subject_hash(device_id)}"
    check_rate_limit(request, rule=_config(request).signup_rule, subject=subject)


def enforce_refresh_rate_limit(request: Request, refresh_token: str) -> None:
    check_rate_limit(request, rule=_config(request).refresh_rule, subject=subject_hash(refresh_token))


async def rate_limit_middleware(request: Request, call_next):
    config = _config(request)
    if not config.enabled:
        return await call_next(request)

    subject = client_ip(request)
    decision = _limiter(request).check(key=subject, rule=config.global_rule)
    if decision.allowed:
        response = await call_next(request)
        response.headers["x-ratelimit-limit"] = str(decision.limit)
        response.headers["x-ratelimit-remaining"] = str(decision.remaining)
        return response

    error = ApiError(ErrorCode.rate_limited, detail="Rate limit exceeded.", extra=_extra(decision, subject))
    problem = problem_for_error(error, request)
    return JSONResponse(
        status_code=problem.status,
        content=problem.model_dump(by_alias=True, mode="json"),
        headers={"retry-after": str(decision.retry_after)},
        media_type="application/problem+json",
    )
