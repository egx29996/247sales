"""Token-bucket rate limiter for API calls."""

from __future__ import annotations

import time
import threading


class RateLimiter:
    """Simple token-bucket rate limiter."""

    def __init__(self, max_tokens: int, refill_seconds: float) -> None:
        self.max_tokens = max_tokens
        self.refill_seconds = refill_seconds
        self._tokens = float(max_tokens)
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self.max_tokens, self._tokens + elapsed / self.refill_seconds * self.max_tokens)
        self._last_refill = now

    def acquire(self, timeout: float = 300) -> bool:
        """Block until a token is available. Returns False if timeout exceeded."""
        deadline = time.monotonic() + timeout
        while True:
            with self._lock:
                self._refill()
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(min(1.0, deadline - time.monotonic()))

    def update_from_headers(self, remaining: int | None, reset_time: int | None) -> None:
        """Update limiter state from API response headers."""
        if remaining is not None and reset_time is not None:
            with self._lock:
                self._tokens = float(remaining)
                self._last_refill = time.monotonic()
                wait = max(0, reset_time - int(time.time()))
                if remaining == 0 and wait > 0:
                    self.refill_seconds = wait
