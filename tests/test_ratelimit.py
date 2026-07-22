"""Tests for the sliding-window rate limiter."""

from core.api.ratelimit import SlidingWindowLimiter


class TestSlidingWindowLimiter:
    def test_zero_max_is_unlimited(self):
        limiter = SlidingWindowLimiter(max_events=0, window_seconds=60)
        assert all(limiter.check_and_record("ip", now=t) for t in range(100))
        assert limiter.remaining("ip") == -1

    def test_blocks_after_limit(self):
        limiter = SlidingWindowLimiter(max_events=3, window_seconds=60)
        assert limiter.check_and_record("ip", now=0)
        assert limiter.check_and_record("ip", now=1)
        assert limiter.check_and_record("ip", now=2)
        assert not limiter.check_and_record("ip", now=3)  # 4th within window blocked

    def test_window_slides(self):
        limiter = SlidingWindowLimiter(max_events=2, window_seconds=60)
        assert limiter.check_and_record("ip", now=0)
        assert limiter.check_and_record("ip", now=10)
        assert not limiter.check_and_record("ip", now=20)   # still within 60s window
        assert limiter.check_and_record("ip", now=61)       # first hit (t=0) expired

    def test_keys_are_independent(self):
        limiter = SlidingWindowLimiter(max_events=1, window_seconds=60)
        assert limiter.check_and_record("a", now=0)
        assert limiter.check_and_record("b", now=0)         # different key, own budget
        assert not limiter.check_and_record("a", now=1)

    def test_remaining_counts_down(self):
        limiter = SlidingWindowLimiter(max_events=2, window_seconds=60)
        assert limiter.remaining("ip", now=0) == 2
        limiter.check_and_record("ip", now=0)
        assert limiter.remaining("ip", now=1) == 1
        limiter.check_and_record("ip", now=1)
        assert limiter.remaining("ip", now=2) == 0
