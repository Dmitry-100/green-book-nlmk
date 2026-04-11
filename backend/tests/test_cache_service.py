from app.services import cache as cache_module
from app.services.cache import (
    KeyedTTLCache,
    RedisKeyedTTLCache,
    redis_cache_health_snapshot,
)


class FakeRedisClient:
    def __init__(self):
        self.store: dict[str, str] = {}

    def ping(self):
        return True

    def get(self, key: str):
        return self.store.get(key)

    def set(self, key: str, value: str, ex: int | None = None):
        del ex
        self.store[key] = value
        return True

    def incr(self, key: str):
        current = int(self.store.get(key, "0"))
        current += 1
        self.store[key] = str(current)
        return current

    def delete(self, *keys):
        deleted = 0
        for key in keys:
            if key in self.store:
                deleted += 1
                self.store.pop(key, None)
        return deleted

    def scan_iter(self, match: str, count: int = 500):
        del count
        if match.endswith("*"):
            prefix = match[:-1]
            for key in list(self.store.keys()):
                if key.startswith(prefix):
                    yield key
            return
        if match in self.store:
            yield match


def test_redis_keyed_cache_uses_redis_when_available(monkeypatch):
    fake_client = FakeRedisClient()
    monkeypatch.setattr(cache_module.redis, "from_url", lambda url: fake_client)

    cache = RedisKeyedTTLCache[tuple[str, int], dict](
        redis_url="redis://fake:6379/0",
        key_prefix="test:species",
        ttl_seconds=60,
        fallback_cache=KeyedTTLCache(ttl_seconds=60, max_entries=32),
        enabled=True,
    )

    load_calls = {"count": 0}

    def loader():
        load_calls["count"] += 1
        return {"total": 1}

    first = cache.get_or_set(("birds", 10), loader)
    second = cache.get_or_set(("birds", 10), loader)

    assert first == {"total": 1}
    assert second == {"total": 1}
    assert load_calls["count"] == 1


def test_redis_keyed_cache_falls_back_to_memory_when_redis_unavailable(monkeypatch):
    def broken_from_url(url: str):
        del url
        raise RuntimeError("redis unavailable")

    monkeypatch.setattr(cache_module.redis, "from_url", broken_from_url)

    cache = RedisKeyedTTLCache[tuple[str, int], dict](
        redis_url="redis://broken:6379/0",
        key_prefix="test:species",
        ttl_seconds=60,
        fallback_cache=KeyedTTLCache(ttl_seconds=60, max_entries=32),
        enabled=True,
    )

    load_calls = {"count": 0}

    def loader():
        load_calls["count"] += 1
        return {"ok": True}

    first = cache.get_or_set(("plants", 5), loader)
    second = cache.get_or_set(("plants", 5), loader)

    assert first == {"ok": True}
    assert second == {"ok": True}
    assert load_calls["count"] == 1


def test_redis_keyed_cache_invalidate_uses_version_bump(monkeypatch):
    fake_client = FakeRedisClient()
    monkeypatch.setattr(cache_module.redis, "from_url", lambda url: fake_client)

    cache = RedisKeyedTTLCache[tuple[str, int], dict](
        redis_url="redis://fake:6379/0",
        key_prefix="test:versioned",
        ttl_seconds=60,
        fallback_cache=KeyedTTLCache(ttl_seconds=60, max_entries=32),
        enabled=True,
        namespace="test-v1",
    )

    load_calls = {"count": 0}

    def loader():
        load_calls["count"] += 1
        return {"version": load_calls["count"]}

    first = cache.get_or_set(("birds", 10), loader)
    cache.invalidate()
    second = cache.get_or_set(("birds", 10), loader)

    assert first == {"version": 1}
    assert second == {"version": 2}
    assert load_calls["count"] == 2


def test_redis_keyed_cache_is_shared_between_workers(monkeypatch):
    fake_client = FakeRedisClient()
    monkeypatch.setattr(cache_module.redis, "from_url", lambda url: fake_client)

    worker_a = RedisKeyedTTLCache[tuple[str, int], dict](
        redis_url="redis://fake:6379/0",
        key_prefix="test:shared",
        ttl_seconds=60,
        fallback_cache=KeyedTTLCache(ttl_seconds=60, max_entries=32),
        enabled=True,
        namespace="test-v1",
    )
    worker_b = RedisKeyedTTLCache[tuple[str, int], dict](
        redis_url="redis://fake:6379/0",
        key_prefix="test:shared",
        ttl_seconds=60,
        fallback_cache=KeyedTTLCache(ttl_seconds=60, max_entries=32),
        enabled=True,
        namespace="test-v1",
    )

    worker_a_calls = {"count": 0}
    worker_b_calls = {"count": 0}

    def loader_a():
        worker_a_calls["count"] += 1
        return {"source": "A"}

    def loader_b():
        worker_b_calls["count"] += 1
        return {"source": "B"}

    first = worker_a.get_or_set(("birds", 20), loader_a)
    second = worker_b.get_or_set(("birds", 20), loader_b)

    assert first == {"source": "A"}
    assert second == {"source": "A"}
    assert worker_a_calls["count"] == 1
    assert worker_b_calls["count"] == 0

    worker_a.invalidate()
    third = worker_b.get_or_set(("birds", 20), loader_b)
    assert third == {"source": "B"}
    assert worker_b_calls["count"] == 1


def test_redis_cache_health_snapshot_tracks_degraded_store(monkeypatch):
    def broken_from_url(url: str):
        del url
        raise RuntimeError("redis unavailable")

    monkeypatch.setattr(cache_module.redis, "from_url", broken_from_url)

    cache = RedisKeyedTTLCache[tuple[str, int], dict](
        redis_url="redis://broken:6379/0",
        key_prefix="test:health",
        ttl_seconds=60,
        fallback_cache=KeyedTTLCache(ttl_seconds=60, max_entries=32),
        enabled=True,
        namespace="health-v1",
    )
    cache.get_or_set(("birds", 1), lambda: {"ok": True})

    snapshot = redis_cache_health_snapshot()
    store = next(
        item for item in snapshot["stores"] if item["store"] == "test:health|health-v1"
    )
    assert store["enabled"] is True
    assert store["connect_errors_total"] >= 1
    assert store["degraded"] is True
