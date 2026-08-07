from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request


class RateLimiter:
    """Small-process limiter; production proxy should enforce the same limits."""

    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, request: Request, scope: str, limit: int, window_seconds: int) -> None:
        forwarded = request.headers.get("x-forwarded-for", "")
        address = forwarded.split(",", 1)[0].strip() or (request.client.host if request.client else "unknown")
        key = f"{scope}:{address}"
        now = monotonic()
        with self._lock:
            events = self._events[key]
            while events and events[0] <= now - window_seconds:
                events.popleft()
            if len(events) >= limit:
                retry_after = max(1, int(window_seconds - (now - events[0])))
                raise HTTPException(429, "请求过于频繁，请稍后再试", headers={"Retry-After": str(retry_after)})
            events.append(now)

    def clear(self) -> None:
        with self._lock:
            self._events.clear()


limiter = RateLimiter()
