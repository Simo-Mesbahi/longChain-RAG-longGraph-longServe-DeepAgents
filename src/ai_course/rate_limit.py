"""Thread-safe, bounded sliding-window limiter for a single worker process."""

from collections import OrderedDict, deque
from collections.abc import Callable
from math import ceil
from threading import Lock
from time import monotonic


class RateLimitExceeded(Exception):
    def __init__(self, retry_after: int) -> None:
        self.retry_after = max(1, retry_after)
        super().__init__("Request capacity reached")


class SlidingWindowLimiter:
    """Bound both requests per identity and the number of active identities.

    State is process-local. A distributed deployment needs a shared atomic store.
    Saturation rejects new identities rather than evicting an active quota.
    """

    def __init__(
        self,
        requests: int = 60,
        window_seconds: int = 60,
        *,
        max_keys: int = 10_000,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        for value in (requests, window_seconds, max_keys):
            if type(value) is not int or value < 1:
                raise ValueError("Limiter settings must be positive integers")
        self.requests = requests
        self.window_seconds = window_seconds
        self.max_keys = max_keys
        self._clock = clock
        self._events: OrderedDict[str, deque[float]] = OrderedDict()
        self._lock = Lock()

    def check(self, key: str) -> None:
        with self._lock:
            now = self._clock()
            cutoff = now - self.window_seconds
            # Ordered by the last accepted request, so expired identities are a prefix.
            while self._events:
                oldest = next(iter(self._events))
                if self._events[oldest][-1] > cutoff:
                    break
                del self._events[oldest]
            events = self._events.get(key)
            if events is None:
                if len(self._events) >= self.max_keys:
                    oldest_events = next(iter(self._events.values()))
                    raise RateLimitExceeded(ceil(oldest_events[-1] - cutoff))
                events = deque()
                self._events[key] = events
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= self.requests:
                raise RateLimitExceeded(ceil(events[0] - cutoff))
            events.append(now)
            self._events.move_to_end(key)
