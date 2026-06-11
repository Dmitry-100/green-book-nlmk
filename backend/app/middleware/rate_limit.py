import threading
import time

import redis
from fastapi import Request
from jose import JWTError, jwt
from redis.exceptions import RedisError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings


class _InMemoryRateStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._buckets: dict[str, int] = {}

    def increment(self, key: str) -> int:
        with self._lock:
            value = self._buckets.get(key, 0) + 1
            self._buckets[key] = value
            return value

    def clear_expired(self, window_index: int):
        stale_suffix = f":{window_index - 2}"
        with self._lock:
            stale_keys = [k for k in self._buckets if k.endswith(stale_suffix)]
            for key in stale_keys:
                self._buckets.pop(key, None)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        requests_per_window: int,
        window_seconds: int = 60,
        auth_requests_per_window: int | None = None,
        auth_path_prefixes: tuple[str, ...] = ("/api/auth/login", "/api/auth/register"),
        trusted_proxies: tuple[str, ...] = (),
        excluded_prefixes: tuple[str, ...] = ("/api/health", "/docs", "/openapi.json"),
    ):
        super().__init__(app)
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.auth_requests_per_window = auth_requests_per_window
        self.auth_path_prefixes = auth_path_prefixes
        self.trusted_proxies = frozenset(trusted_proxies)
        self.excluded_prefixes = excluded_prefixes
        self._fallback = _InMemoryRateStore()
        self._redis = self._init_redis_client()

    @staticmethod
    def _init_redis_client():
        try:
            client = redis.from_url(settings.redis_url, socket_connect_timeout=0.2, socket_timeout=0.2)
            client.ping()
            return client
        except Exception:
            return None

    def _resolve_network_id(self, request: Request) -> str:
        peer = request.client.host if request.client and request.client.host else None
        forwarded_for = request.headers.get("x-forwarded-for")
        # X-Forwarded-For учитывается, только если запрос пришёл от доверенного
        # прокси: иначе клиент подменяет заголовок и обходит лимит.
        if forwarded_for and peer in self.trusted_proxies:
            hops = [hop.strip() for hop in forwarded_for.split(",") if hop.strip()]
            for hop in reversed(hops):
                if hop not in self.trusted_proxies:
                    return hop
        return peer or "unknown"

    def _resolve_client_id(self, request: Request) -> str:
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
            if token:
                try:
                    payload = jwt.decode(
                        token,
                        settings.auth_secret_key,
                        algorithms=[settings.auth_algorithm],
                    )
                    subject = payload.get("sub")
                    if isinstance(subject, str) and subject:
                        return f"user:{subject}"
                except JWTError:
                    # Fall back to network identity for invalid or unsigned tokens.
                    pass

        return self._resolve_network_id(request)

    def _increment(self, key: str, window_seconds: int, window_index: int) -> int:
        if self._redis is not None:
            try:
                pipe = self._redis.pipeline()
                pipe.incr(key)
                pipe.expire(key, window_seconds + 2)
                count, _ = pipe.execute()
                return int(count)
            except RedisError:
                self._redis = None

        self._fallback.clear_expired(window_index)
        return self._fallback.increment(key)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if any(path.startswith(prefix) for prefix in self.excluded_prefixes):
            return await call_next(request)

        now = time.time()
        window_index = int(now // self.window_seconds)
        window_reset = (window_index + 1) * self.window_seconds

        is_auth_path = self.auth_requests_per_window is not None and any(
            path.startswith(prefix) for prefix in self.auth_path_prefixes
        )
        if is_auth_path:
            # Login/register лимитируются по сетевой идентичности и жёстче:
            # bearer-токен здесь не учитывается, чтобы лимит нельзя было
            # размножить разными токенами.
            limit = self.auth_requests_per_window
            client_id = self._resolve_network_id(request)
            key = f"ratelimit:auth:{client_id}:{window_index}"
        else:
            limit = self.requests_per_window
            client_id = self._resolve_client_id(request)
            key = f"ratelimit:{client_id}:{window_index}"

        current = self._increment(key, self.window_seconds, window_index)
        remaining = max(limit - current, 0)
        reset_in = max(int(window_reset - now), 0)

        if current > limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests"},
                headers={
                    "Retry-After": str(reset_in),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(window_reset),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(window_reset)
        return response
