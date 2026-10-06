"""Fixed-window rate limiter. Uses Redis when REDIS_URL is set, otherwise in-process memory."""

import threading
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import get_settings


class _MemoryStore:
    def __init__(self) -> None:
        self._data: dict[str, tuple[int, float]] = {}
        self._lock = threading.Lock()

    def incr(self, key: str, window: int) -> int:
        now = time.time()
        with self._lock:
            count, expires = self._data.get(key, (0, now + window))
            if now > expires:
                count, expires = 0, now + window
            count += 1
            self._data[key] = (count, expires)
            return count


class _RedisStore:
    def __init__(self, url: str) -> None:
        import redis

        self._r = redis.Redis.from_url(url)

    def incr(self, key: str, window: int) -> int:
        pipe = self._r.pipeline()
        pipe.incr(key)
        pipe.expire(key, window, nx=True)
        count, _ = pipe.execute()
        return int(count)


def _make_store():
    url = get_settings().redis_url
    if url:
        try:
            store = _RedisStore(url)
            store._r.ping()
            return store
        except Exception:  # pragma: no cover - fall back if redis unavailable
            pass
    return _MemoryStore()


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.store = _make_store()

    def _limit_for(self, path: str) -> tuple[str, int]:
        s = get_settings()
        if "/auth/" in path:
            return "auth", s.rate_limit_auth
        if path.endswith("/answer") or "/ai/" in path or "/analyze" in path:
            return "ai", s.rate_limit_ai
        return "default", s.rate_limit_default

    async def dispatch(self, request: Request, call_next):
        s = get_settings()
        if s.is_test or request.method == "OPTIONS" or not request.url.path.startswith(s.api_prefix):
            return await call_next(request)
        bucket, limit = self._limit_for(request.url.path)
        ident = request.cookies.get(s.cookie_name) or request.headers.get("authorization") or (
            request.client.host if request.client else "anon"
        )
        key = f"rl:{bucket}:{hash(ident)}:{int(time.time() // 60)}"
        try:
            count = self.store.incr(key, 60)
        except Exception:
            return await call_next(request)
        if count > limit:
            return JSONResponse({"detail": "Too many requests"}, status_code=429, headers={"Retry-After": "60"})
        return await call_next(request)
