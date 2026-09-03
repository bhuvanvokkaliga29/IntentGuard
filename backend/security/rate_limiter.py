"""
IntentGuard — Lightweight In-Memory Sliding-Window Rate Limiter

Protects transaction evaluation and semantic verification endpoints against denial-of-wallet
and brute-force request flooding.
"""

import time
import logging
from collections import defaultdict, deque
from typing import Dict, Deque, Optional
from fastapi import Request, HTTPException, status

from backend.config import get_settings

logger = logging.getLogger("intentguard.security.ratelimit")


class SlidingWindowRateLimiter:
    """Sliding-window request rate limiter with memory bounding."""

    def __init__(self, max_requests: int = 120, window_seconds: int = 60, max_tracked_ips: int = 5000):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.max_tracked_ips = max_tracked_ips
        self._requests: Dict[str, Deque[float]] = defaultdict(deque)

    def is_allowed(self, client_ip: str) -> bool:
        """Check whether a request from client_ip is allowed under rate limits."""
        now = time.time()
        window_start = now - self.window_seconds

        # Bounded cleanup if memory exceeds max tracked IPs
        if len(self._requests) > self.max_tracked_ips:
            # Purge keys older than window
            stale_keys = [ip for ip, timestamps in self._requests.items() if not timestamps or timestamps[-1] < window_start]
            for ip in stale_keys:
                del self._requests[ip]

        timestamps = self._requests[client_ip]

        # Evict timestamps outside current window
        while timestamps and timestamps[0] < window_start:
            timestamps.popleft()

        if len(timestamps) >= self.max_requests:
            return False

        timestamps.append(now)
        return True

    def get_retry_after(self, client_ip: str) -> int:
        """Get seconds until the earliest request expires from the window."""
        timestamps = self._requests.get(client_ip)
        if not timestamps:
            return 1
        now = time.time()
        oldest = timestamps[0]
        remaining = int(self.window_seconds - (now - oldest))
        return max(1, remaining)


_limiter: Optional[SlidingWindowRateLimiter] = None


def get_rate_limiter() -> SlidingWindowRateLimiter:
    """Get or create singleton rate limiter."""
    global _limiter
    if _limiter is None:
        settings = get_settings()
        _limiter = SlidingWindowRateLimiter(
            max_requests=settings.rate_limit_per_minute,
            window_seconds=60,
        )
    return _limiter


async def rate_limit_guard(request: Request):
    """FastAPI dependency to rate limit protected endpoints."""
    settings = get_settings()
    if not settings.rate_limit_enabled:
        return

    # Extract client IP
    client_ip = (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or request.headers.get("X-Real-IP")
        or (request.client.host if request.client else "127.0.0.1")
    )

    limiter = get_rate_limiter()
    if not limiter.is_allowed(client_ip):
        retry_after = limiter.get_retry_after(client_ip)
        logger.warning(f"[RATE_LIMIT] Client {client_ip} exceeded rate limit on {request.url.path}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "RATE_LIMITED",
                "message": f"Rate limit exceeded. Try again in {retry_after} seconds.",
                "retry_after_seconds": retry_after,
            },
            headers={"Retry-After": str(retry_after)},
        )
