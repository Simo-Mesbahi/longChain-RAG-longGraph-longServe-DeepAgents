from concurrent.futures import ThreadPoolExecutor

import pytest

from ai_course.rate_limit import RateLimitExceeded, SlidingWindowLimiter


def test_expired_identities_are_reclaimed_and_retry_after_is_exact():
    clock = [0.0]
    limiter = SlidingWindowLimiter(2, 10, max_keys=2, clock=lambda: clock[0])
    limiter.check("a")
    limiter.check("a")
    clock[0] = 3.0
    with pytest.raises(RateLimitExceeded) as error:
        limiter.check("a")
    assert error.value.retry_after == 7
    limiter.check("b")
    with pytest.raises(RateLimitExceeded):
        limiter.check("c")
    assert len(limiter._events) == 2
    clock[0] = 10.0
    limiter.check("c")
    assert "a" not in limiter._events


def test_simultaneous_requests_cannot_exceed_the_quota():
    limiter = SlidingWindowLimiter(5, 60)

    def check(_):
        try:
            limiter.check("same-client")
            return 1
        except RateLimitExceeded:
            return 0

    with ThreadPoolExecutor(max_workers=16) as pool:
        assert sum(pool.map(check, range(100))) == 5


@pytest.mark.parametrize("kwargs", [{"requests": 0}, {"window_seconds": -1}, {"max_keys": True}])
def test_invalid_settings_are_rejected(kwargs):
    with pytest.raises(ValueError):
        SlidingWindowLimiter(**kwargs)
