from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from typing import Dict, Callable
import time
import asyncio


class RateLimiter:
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, list] = {}
        self._lock = asyncio.Lock()

    async def is_allowed(self, key: str) -> bool:
        now = time.time()

        async with self._lock:
            if key not in self._requests:
                self._requests[key] = []

            self._requests[key] = [
                t for t in self._requests[key]
                if now - t < self.window_seconds
            ]

            if len(self._requests[key]) >= self.max_requests:
                return False

            self._requests[key].append(now)
            return True

    def is_allowed_sync(self, key: str) -> bool:
        now = time.time()

        if key not in self._requests:
            self._requests[key] = []

        self._requests[key] = [
            t for t in self._requests[key]
            if now - t < self.window_seconds
        ]

        if len(self._requests[key]) >= self.max_requests:
            return False

        self._requests[key].append(now)
        return True


global_web_limiter = RateLimiter(max_requests=120, window_seconds=60)
global_api_limiter = RateLimiter(max_requests=300, window_seconds=60)
critical_limiter = RateLimiter(max_requests=10, window_seconds=60)
download_limiter = RateLimiter(max_requests=20, window_seconds=60)
upload_limiter = RateLimiter(max_requests=10, window_seconds=60)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limiter: RateLimiter, key_func: Callable = None):
        super().__init__(app)
        self.limiter = limiter
        self.key_func = key_func or (lambda request: request.client.host if request.client else "unknown")

    async def dispatch(self, request: Request, call_next):
        key = f"{self.key_func(request)}"
        if not await self.limiter.is_allowed(key):
            return JSONResponse(status_code=429, content={"detail": "Too many requests, please try again later"})

        response = await call_next(request)
        return response


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    return request.client.host if request.client else "unknown"


async def global_web_rate_limit(request: Request, call_next):
    client_ip = get_client_ip(request)
    if not await global_web_limiter.is_allowed(f"web:{client_ip}"):
        raise HTTPException(status_code=429, detail="Too many requests")
    return await call_next(request)


async def global_api_rate_limit(request: Request, call_next):
    client_ip = get_client_ip(request)
    if not await global_api_limiter.is_allowed(f"api:{client_ip}"):
        raise HTTPException(status_code=429, detail="Too many requests")
    return await call_next(request)


async def critical_rate_limit(request: Request, call_next):
    client_ip = get_client_ip(request)
    if not await critical_limiter.is_allowed(f"critical:{client_ip}"):
        raise HTTPException(status_code=429, detail="Too many requests")
    return await call_next(request)