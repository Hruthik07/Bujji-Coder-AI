"""
Rate Limiting Module
Implements rate limiting using in-memory storage (can be extended to Redis)
"""

import time
from typing import Dict, Tuple, Optional, Any
from collections import defaultdict
from datetime import datetime, timedelta
from fastapi import HTTPException, status, Request
from functools import wraps
import asyncio

# Rate limit storage (in-memory, can be replaced with Redis)
_rate_limit_storage: Dict[str, Dict[str, list]] = defaultdict(lambda: defaultdict(list))
_rate_limit_lock = asyncio.Lock()


class RateLimiter:
    """Rate limiter with configurable limits"""

    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        requests_per_day: int = 10000,
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.requests_per_day = requests_per_day

    def _get_identifier(self, request: Request, user_id: Optional[str] = None) -> str:
        """Get identifier for rate limiting (user_id or IP address)"""
        if user_id:
            return f"user:{user_id}"

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        # Check for forwarded IP (behind proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()

        return f"ip:{client_ip}"

    async def _check_rate_limit(
        self, identifier: str, window: str, limit: int
    ) -> Tuple[bool, int, int]:
        """
        Check if rate limit is exceeded
        Returns: (is_allowed, remaining, reset_time)
        """
        async with _rate_limit_lock:
            now = time.time()
            window_key = f"{identifier}:{window}"

            # Get requests in this window
            requests = _rate_limit_storage[identifier][window_key]

            # Remove expired requests
            requests[:] = [
                req_time
                for req_time in requests
                if now - req_time < self._get_window_seconds(window)
            ]

            # Check if limit exceeded
            if len(requests) >= limit:
                reset_time = (
                    int(requests[0] + self._get_window_seconds(window))
                    if requests
                    else int(now)
                )
                return False, 0, reset_time

            # Add current request
            requests.append(now)

            # Calculate remaining and reset time
            remaining = limit - len(requests)
            reset_time = int(now + self._get_window_seconds(window))

            return True, remaining, reset_time

    def _get_window_seconds(self, window: str) -> int:
        """Get window size in seconds"""
        if window == "minute":
            return 60
        elif window == "hour":
            return 3600
        elif window == "day":
            return 86400
        return 60

    async def check_rate_limit(
        self, request: Request, user_id: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check rate limits for all windows
        Returns: (is_allowed, rate_limit_info)
        """
        identifier = self._get_identifier(request, user_id)

        # Check all windows
        checks = {
            "minute": await self._check_rate_limit(
                identifier, "minute", self.requests_per_minute
            ),
            "hour": await self._check_rate_limit(
                identifier, "hour", self.requests_per_hour
            ),
            "day": await self._check_rate_limit(
                identifier, "day", self.requests_per_day
            ),
        }

        # Check if any limit is exceeded
        is_allowed = all(allowed for allowed, _, _ in checks.values())

        # Get the most restrictive limit info
        rate_limit_info = {
            "limit": {
                "minute": self.requests_per_minute,
                "hour": self.requests_per_hour,
                "day": self.requests_per_day,
            },
            "remaining": {
                "minute": checks["minute"][1],
                "hour": checks["hour"][1],
                "day": checks["day"][1],
            },
            "reset": {
                "minute": checks["minute"][2],
                "hour": checks["hour"][2],
                "day": checks["day"][2],
            },
        }

        return is_allowed, rate_limit_info


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get or create rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        import os

        requests_per_minute = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
        requests_per_hour = int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))
        requests_per_day = int(os.getenv("RATE_LIMIT_PER_DAY", "10000"))
        _rate_limiter = RateLimiter(
            requests_per_minute=requests_per_minute,
            requests_per_hour=requests_per_hour,
            requests_per_day=requests_per_day,
        )
    return _rate_limiter


def rate_limit(
    requests_per_minute: Optional[int] = None,
    requests_per_hour: Optional[int] = None,
    requests_per_day: Optional[int] = None,
):
    """Decorator for rate limiting endpoints"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get request object
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request:
                # Try to get from kwargs
                request = kwargs.get("request")

            if not request:
                # If no request found, skip rate limiting
                return await func(*args, **kwargs)

            # Get user_id if available
            user_id = None
            current_user = kwargs.get("current_user")
            if current_user and hasattr(current_user, "id"):
                user_id = current_user.id

            # Create custom rate limiter if limits are specified
            if requests_per_minute or requests_per_hour or requests_per_day:
                limiter = RateLimiter(
                    requests_per_minute=requests_per_minute or 60,
                    requests_per_hour=requests_per_hour or 1000,
                    requests_per_day=requests_per_day or 10000,
                )
            else:
                limiter = get_rate_limiter()

            # Check rate limit
            is_allowed, rate_limit_info = await limiter.check_rate_limit(
                request, user_id
            )

            if not is_allowed:
                # Find which limit was exceeded
                exceeded_window = None
                for window, (allowed, remaining, reset) in [
                    (
                        "minute",
                        limiter._check_rate_limit(
                            limiter._get_identifier(request, user_id),
                            "minute",
                            limiter.requests_per_minute,
                        ),
                    ),
                    (
                        "hour",
                        limiter._check_rate_limit(
                            limiter._get_identifier(request, user_id),
                            "hour",
                            limiter.requests_per_hour,
                        ),
                    ),
                    (
                        "day",
                        limiter._check_rate_limit(
                            limiter._get_identifier(request, user_id),
                            "day",
                            limiter.requests_per_day,
                        ),
                    ),
                ]:
                    if not allowed:
                        exceeded_window = window
                        break

                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Please try again later.",
                    headers={
                        "X-RateLimit-Limit": str(
                            rate_limit_info["limit"].get(exceeded_window, "unknown")
                        ),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(
                            rate_limit_info["reset"].get(
                                exceeded_window, int(time.time())
                            )
                        ),
                    },
                )

            # Add rate limit info to response headers
            response = await func(*args, **kwargs)
            if hasattr(response, "headers"):
                response.headers["X-RateLimit-Limit-Minute"] = str(
                    rate_limit_info["limit"]["minute"]
                )
                response.headers["X-RateLimit-Remaining-Minute"] = str(
                    rate_limit_info["remaining"]["minute"]
                )
                response.headers["X-RateLimit-Reset-Minute"] = str(
                    rate_limit_info["reset"]["minute"]
                )

            return response

        return wrapper

    return decorator
