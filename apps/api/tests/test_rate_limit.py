from fastapi.testclient import TestClient

from app.core.rate_limit import InMemoryRateLimiter, RateLimitConfig, RateLimitRule
from app.main import create_app


def test_in_memory_rate_limiter_blocks_after_limit() -> None:
    limiter = InMemoryRateLimiter()
    rule = RateLimitRule(name="test", limit=2, window_seconds=60)

    assert limiter.check(key="subject", rule=rule, now=100).allowed is True
    assert limiter.check(key="subject", rule=rule, now=101).allowed is True
    blocked = limiter.check(key="subject", rule=rule, now=102)

    assert blocked.allowed is False
    assert blocked.retry_after == 58


def test_global_rate_limit_returns_problem_details() -> None:
    client = TestClient(create_app(rate_limit_config=RateLimitConfig(global_per_minute=2)))

    assert client.get("/healthz", headers={"x-forwarded-for": "203.0.113.10"}).status_code == 200
    assert client.get("/healthz", headers={"x-forwarded-for": "203.0.113.10"}).status_code == 200
    response = client.get("/healthz", headers={"x-forwarded-for": "203.0.113.10", "x-request-id": "rate-limit-test"})

    assert response.status_code == 429
    assert response.headers["retry-after"]
    assert response.json()["code"] == "RATE_LIMITED"
    assert response.json()["requestId"] == "rate-limit-test"
    assert response.json()["extra"]["rule"] == "global"
