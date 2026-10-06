import pytest

import app.core.rate_limit as rate_limit_module
from app.core.rate_limit import TokenBucketLimiter


pytestmark = pytest.mark.unit


async def test_token_bucket_exhausts_and_refills(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = {"value": 100.0}
    monkeypatch.setattr(rate_limit_module.time, "monotonic", lambda: clock["value"])
    limiter = TokenBucketLimiter(capacity=1, refill_per_second=0.5)

    assert await limiter.consume("user-a") is True
    assert await limiter.consume("user-a") is False

    clock["value"] += 2.0
    assert await limiter.consume("user-a") is True


async def test_token_buckets_are_isolated_per_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rate_limit_module.time, "monotonic", lambda: 100.0)
    limiter = TokenBucketLimiter(capacity=1, refill_per_second=0.0)

    assert await limiter.consume("user-a") is True
    assert await limiter.consume("user-a") is False
    assert await limiter.consume("user-b") is True

