import json
from dataclasses import asdict, dataclass
from threading import Lock
from time import monotonic, time
from typing import Callable, Generic, TypeVar

import redis

T = TypeVar("T")
K = TypeVar("K")


@dataclass
class _RedisCacheRuntimeStats:
    store: str
    key_prefix: str
    namespace: str
    enabled: bool
    ttl_seconds: int
    connect_attempts_total: int = 0
    connect_success_total: int = 0
    connect_errors_total: int = 0
    redis_hits_total: int = 0
    redis_misses_total: int = 0
    fallback_hits_total: int = 0
    read_errors_total: int = 0
    write_errors_total: int = 0
    invalidate_all_total: int = 0
    invalidate_key_total: int = 0
    redis_available: bool = False
    last_error: str | None = None
    updated_at_epoch: float = 0.0


_REDIS_CACHE_STATS_LOCK = Lock()
_REDIS_CACHE_STATS: dict[str, _RedisCacheRuntimeStats] = {}


def _redis_cache_store_name(key_prefix: str, namespace: str) -> str:
    return f"{key_prefix}|{namespace}"


def _register_redis_cache_stats(
    *, key_prefix: str, namespace: str, enabled: bool, ttl_seconds: int
) -> _RedisCacheRuntimeStats:
    store = _redis_cache_store_name(key_prefix, namespace)
    with _REDIS_CACHE_STATS_LOCK:
        stats = _REDIS_CACHE_STATS.get(store)
        if stats is None:
            stats = _RedisCacheRuntimeStats(
                store=store,
                key_prefix=key_prefix,
                namespace=namespace,
                enabled=enabled,
                ttl_seconds=ttl_seconds,
                updated_at_epoch=time(),
            )
            _REDIS_CACHE_STATS[store] = stats
            return stats

        stats.enabled = enabled
        stats.ttl_seconds = ttl_seconds
        stats.updated_at_epoch = time()
        return stats


def redis_cache_health_snapshot() -> dict:
    with _REDIS_CACHE_STATS_LOCK:
        stores = [asdict(value) for value in _REDIS_CACHE_STATS.values()]

    stores.sort(key=lambda item: item["store"])
    for store in stores:
        store["degraded"] = bool(
            store["enabled"]
            and store["connect_attempts_total"] > 0
            and not store["redis_available"]
        )

    totals = {
        "stores_total": len(stores),
        "enabled_stores": sum(1 for item in stores if item["enabled"]),
        "degraded_stores": sum(1 for item in stores if item["degraded"]),
        "connect_errors_total": sum(item["connect_errors_total"] for item in stores),
        "read_errors_total": sum(item["read_errors_total"] for item in stores),
        "write_errors_total": sum(item["write_errors_total"] for item in stores),
        "fallback_hits_total": sum(item["fallback_hits_total"] for item in stores),
        "redis_hits_total": sum(item["redis_hits_total"] for item in stores),
        "redis_misses_total": sum(item["redis_misses_total"] for item in stores),
    }
    return {"stores": stores, "totals": totals}


class TTLCache(Generic[T]):
    def __init__(self, ttl_seconds: int):
        self._ttl_seconds = ttl_seconds
        self._value: T | None = None
        self._expires_at = 0.0
        self._lock = Lock()

    def get_or_set(self, loader: Callable[[], T]) -> T:
        now = monotonic()
        if self._value is not None and now < self._expires_at:
            return self._value

        with self._lock:
            now = monotonic()
            if self._value is not None and now < self._expires_at:
                return self._value

            value = loader()
            self._value = value
            self._expires_at = now + self._ttl_seconds
            return value

    def invalidate(self) -> None:
        with self._lock:
            self._value = None
            self._expires_at = 0.0


class KeyedTTLCache(Generic[K, T]):
    def __init__(self, ttl_seconds: int, max_entries: int = 32):
        self._ttl_seconds = ttl_seconds
        self._max_entries = max_entries
        self._entries: dict[K, tuple[float, T]] = {}
        self._lock = Lock()

    def get_or_set(self, key: K, loader: Callable[[], T]) -> T:
        now = monotonic()
        entry = self._entries.get(key)
        if entry is not None:
            expires_at, value = entry
            if now < expires_at:
                return value

        with self._lock:
            now = monotonic()
            entry = self._entries.get(key)
            if entry is not None:
                expires_at, value = entry
                if now < expires_at:
                    return value

            value = loader()
            self._entries[key] = (now + self._ttl_seconds, value)
            if len(self._entries) > self._max_entries:
                # Drop oldest by expiry to keep memory bounded.
                oldest_key = min(self._entries.items(), key=lambda item: item[1][0])[0]
                self._entries.pop(oldest_key, None)
            return value

    def invalidate(self, key: K | None = None) -> None:
        with self._lock:
            if key is None:
                self._entries.clear()
            else:
                self._entries.pop(key, None)


def _stable_redis_key(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )


class RedisKeyedTTLCache(Generic[K, T]):
    def __init__(
        self,
        *,
        redis_url: str,
        key_prefix: str,
        ttl_seconds: int,
        fallback_cache: KeyedTTLCache[K, T] | None = None,
        enabled: bool = True,
        namespace: str = "v1",
    ):
        self._redis_url = redis_url
        self._key_prefix = key_prefix
        self._namespace = namespace.strip() or "v1"
        self._ttl_seconds = ttl_seconds
        self._enabled = enabled and ttl_seconds > 0
        self._fallback_cache = fallback_cache
        self._client: redis.Redis | None = None
        self._client_lock = Lock()
        self._stats = _register_redis_cache_stats(
            key_prefix=self._key_prefix,
            namespace=self._namespace,
            enabled=self._enabled,
            ttl_seconds=self._ttl_seconds,
        )

    def _mark_connect_success(self) -> None:
        with _REDIS_CACHE_STATS_LOCK:
            self._stats.connect_attempts_total += 1
            self._stats.connect_success_total += 1
            self._stats.redis_available = True
            self._stats.last_error = None
            self._stats.updated_at_epoch = time()

    def _mark_connect_error(self, exc: Exception) -> None:
        with _REDIS_CACHE_STATS_LOCK:
            self._stats.connect_attempts_total += 1
            self._stats.connect_errors_total += 1
            self._stats.redis_available = False
            self._stats.last_error = str(exc)[:200]
            self._stats.updated_at_epoch = time()

    def _mark_read_error(self, exc: Exception) -> None:
        with _REDIS_CACHE_STATS_LOCK:
            self._stats.read_errors_total += 1
            self._stats.redis_available = False
            self._stats.last_error = str(exc)[:200]
            self._stats.updated_at_epoch = time()

    def _mark_write_error(self, exc: Exception) -> None:
        with _REDIS_CACHE_STATS_LOCK:
            self._stats.write_errors_total += 1
            self._stats.redis_available = False
            self._stats.last_error = str(exc)[:200]
            self._stats.updated_at_epoch = time()

    def _mark_redis_hit(self) -> None:
        with _REDIS_CACHE_STATS_LOCK:
            self._stats.redis_hits_total += 1
            self._stats.updated_at_epoch = time()

    def _mark_redis_miss(self) -> None:
        with _REDIS_CACHE_STATS_LOCK:
            self._stats.redis_misses_total += 1
            self._stats.updated_at_epoch = time()

    def _mark_fallback_hit(self) -> None:
        with _REDIS_CACHE_STATS_LOCK:
            self._stats.fallback_hits_total += 1
            self._stats.updated_at_epoch = time()

    def _mark_invalidate(self, key: K | None) -> None:
        with _REDIS_CACHE_STATS_LOCK:
            if key is None:
                self._stats.invalidate_all_total += 1
            else:
                self._stats.invalidate_key_total += 1
            self._stats.updated_at_epoch = time()

    def _drop_client(self) -> None:
        with self._client_lock:
            self._client = None

    def _connect(self) -> redis.Redis | None:
        if not self._enabled:
            return None
        if self._client is not None:
            return self._client

        with self._client_lock:
            if self._client is not None:
                return self._client
            try:
                client = redis.from_url(self._redis_url)
                # Fail fast if Redis is unreachable; fallback cache will serve requests.
                client.ping()
            except Exception as exc:
                self._mark_connect_error(exc)
                return None
            self._client = client
            self._mark_connect_success()
            return self._client

    def _version_storage_key(self) -> str:
        return f"{self._key_prefix}:{self._namespace}:__version__"

    def _read_version(self, client: redis.Redis) -> int:
        try:
            raw = client.get(self._version_storage_key())
            if raw is None:
                client.set(self._version_storage_key(), "1")
                return 1
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            return max(1, int(raw))
        except Exception:
            return 1

    def _full_key(self, key: K, version: int) -> str:
        return (
            f"{self._key_prefix}:{self._namespace}:v{version}:{_stable_redis_key(key)}"
        )

    def get_or_set(self, key: K, loader: Callable[[], T]) -> T:
        client = self._connect()
        if client is not None:
            version = self._read_version(client)
            full_key = self._full_key(key, version)
            try:
                cached = client.get(full_key)
                if cached is not None:
                    self._mark_redis_hit()
                    return json.loads(cached)
            except Exception as exc:
                # Redis degraded: continue with fallback/source of truth.
                self._mark_read_error(exc)
                self._drop_client()
                client = None

            if client is not None:
                self._mark_redis_miss()
                value = loader()
                try:
                    client.set(
                        full_key,
                        json.dumps(value, ensure_ascii=False),
                        ex=self._ttl_seconds,
                    )
                except Exception as exc:
                    # Write failure should not fail request path.
                    self._mark_write_error(exc)
                    self._drop_client()

                if self._fallback_cache is not None:
                    self._fallback_cache.invalidate(key)
                return value

        self._mark_fallback_hit()
        if self._fallback_cache is not None:
            return self._fallback_cache.get_or_set(key, loader)
        return loader()

    def invalidate(self, key: K | None = None) -> None:
        self._mark_invalidate(key)
        if self._fallback_cache is not None:
            self._fallback_cache.invalidate(key)

        client = self._connect()
        if client is None:
            return

        try:
            if key is None:
                client.incr(self._version_storage_key())
            else:
                version = self._read_version(client)
                client.delete(self._full_key(key, version))
        except Exception as exc:
            self._mark_write_error(exc)
            self._drop_client()
            return
