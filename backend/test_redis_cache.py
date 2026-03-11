"""
Tests for Redis CacheService — connectivity, cache ops, fallback, and SCAN.

Run: python test_redis_cache.py
"""

import json
import logging
import os
import sys
import time

# Ensure backend is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.cache_service import CacheService, _LRUFallbackCache, ALERT_QUEUE_MAX_LENGTH

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

passed = 0
failed = 0


def assert_eq(label, actual, expected):
    global passed, failed
    if actual == expected:
        passed += 1
        logger.info(f"  PASS  {label}")
    else:
        failed += 1
        logger.error(f"  FAIL  {label}: expected {expected!r}, got {actual!r}")


def assert_true(label, value):
    assert_eq(label, bool(value), True)


def assert_false(label, value):
    assert_eq(label, bool(value), False)


# ================================================================
#  1. In-memory fallback (LRU) tests — no Redis needed
# ================================================================
def test_lru_fallback():
    logger.info("--- LRU Fallback Cache ---")

    cache = _LRUFallbackCache(max_keys=5)

    # Basic set/get
    cache.set("a", {"price": 100}, ttl=60)
    assert_eq("get existing key", cache.get("a"), {"price": 100})
    assert_eq("get missing key", cache.get("z"), None)

    # TTL expiry
    cache.set("expire_me", "val", ttl=1)
    assert_eq("before expiry", cache.get("expire_me"), "val")
    time.sleep(1.1)
    assert_eq("after expiry", cache.get("expire_me"), None)

    # LRU eviction (max_keys=5)
    for i in range(6):
        cache.set(f"k{i}", i, ttl=300)
    assert_eq("evicted oldest (k0 gone after a was evicted)", cache.get("a"), None)
    assert_eq("newest key present", cache.get("k5"), 5)
    assert_eq("cache size capped", len(cache) <= 5, True)

    # Pattern delete
    cache.clear()
    cache.set("price:AAPL", 1, ttl=60)
    cache.set("price:GOOG", 2, ttl=60)
    cache.set("analysis:AAPL", 3, ttl=60)
    deleted = cache.match_delete("price:*")
    assert_eq("pattern delete count", deleted, 2)
    assert_eq("price:AAPL gone", cache.get("price:AAPL"), None)
    assert_eq("analysis:AAPL still there", cache.get("analysis:AAPL"), 3)

    # Clear
    cache.clear()
    assert_eq("cleared", len(cache), 0)


# ================================================================
#  2. CacheService with in-memory fallback (no Redis)
# ================================================================
def test_cache_service_fallback():
    logger.info("--- CacheService (in-memory fallback) ---")

    svc = CacheService(redis_url="redis://localhost:1")  # intentionally bad port
    svc.initialize()  # will fail to connect, use fallback

    assert_false("redis not available", svc.is_redis_available)

    # Basic ops
    assert_true("set price", svc.set_price("AAPL", {"ltp": 150}))
    assert_eq("get price", svc.get_price("AAPL"), {"ltp": 150})
    assert_eq("get missing", svc.get_price("MISSING"), None)

    # Analysis
    assert_true("set analysis", svc.set_analysis("GOOG", {"score": 8}))
    assert_eq("get analysis", svc.get_analysis("GOOG"), {"score": 8})

    # Market overview
    assert_true("set market overview", svc.set_market_overview({"nifty": 22000}))
    assert_eq("get market overview", svc.get_market_overview(), {"nifty": 22000})

    # Stock list
    assert_true("set stock list", svc.set_stock_list({"count": 50}))
    assert_eq("get stock list", svc.get_stock_list(), {"count": 50})

    # Invalidate single stock
    svc.set_price("INFY", {"ltp": 1500})
    svc.set_analysis("INFY", {"score": 7})
    svc.invalidate_stock("INFY")
    assert_eq("price invalidated", svc.get_price("INFY"), None)
    assert_eq("analysis invalidated", svc.get_analysis("INFY"), None)

    # Delete pattern
    svc.set_price("A", {"ltp": 1})
    svc.set_price("B", {"ltp": 2})
    count = svc.delete_pattern("price:*")
    assert_true("delete_pattern count > 0", count > 0)

    # Stats
    stats = svc.get_stats()
    assert_eq("stats backend", stats["backend"], "in-memory")
    assert_true("stats has hits", stats["hits"] >= 0)

    # Invalidate all
    svc.invalidate_all()
    assert_eq("all cleared", svc.get_price("AAPL"), None)

    svc.close()


# ================================================================
#  3. CacheService with real Redis (if available)
# ================================================================
def test_cache_service_redis():
    logger.info("--- CacheService (Redis) ---")

    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    svc = CacheService(redis_url=redis_url)
    svc.initialize()

    if not svc.is_redis_available:
        logger.info("  SKIP  Redis not available, skipping Redis-specific tests")
        return

    assert_true("redis available", svc.is_redis_available)

    # Basic string ops
    svc.set("test:redis:key1", {"hello": "world"}, ttl=10)
    assert_eq("get string", svc.get("test:redis:key1"), {"hello": "world"})
    svc.delete("test:redis:key1")
    assert_eq("deleted", svc.get("test:redis:key1"), None)

    # SCAN-based delete_pattern
    svc.set("test:scan:a", 1, ttl=10)
    svc.set("test:scan:b", 2, ttl=10)
    svc.set("test:scan:c", 3, ttl=10)
    deleted = svc.delete_pattern("test:scan:*")
    assert_eq("scan delete count", deleted, 3)
    assert_eq("scan deleted a", svc.get("test:scan:a"), None)

    # HASH ops
    svc.set_stock_hash("TEST", {"ltp": 100, "volume": 5000})
    field_val = svc.get_stock_field("TEST", "ltp")
    assert_eq("hash get field", field_val, 100)
    fields = svc.get_stock_fields("TEST", ["ltp", "volume"])
    assert_eq("hash get fields", fields, {"ltp": 100, "volume": 5000})
    full_hash = svc.get_stock_hash("TEST")
    assert_true("hash get full", full_hash is not None)
    assert_eq("hash full ltp", full_hash.get("ltp"), 100)
    svc.delete("stock:TEST")

    # SORTED SET ops
    svc.update_top_movers(
        gainers={"AAPL": 5.2, "GOOG": 3.1},
        losers={"META": -2.5, "NFLX": -1.8},
    )
    gainers = svc.get_top_gainers(2)
    assert_eq("top gainers count", len(gainers), 2)
    assert_eq("top gainer symbol", gainers[0]["symbol"], "AAPL")
    losers = svc.get_top_losers(2)
    assert_eq("top losers count", len(losers), 2)
    # Clean up
    svc.delete("top_gainers")
    svc.delete("top_losers")

    # Alert queue with LTRIM cap
    for i in range(5):
        svc.publish_alert({"alert_id": i, "msg": f"test alert {i}"})
    # Verify queue exists and is capped
    import redis
    r = redis.Redis.from_url(redis_url, decode_responses=True)
    qlen = r.llen("alert_queue")
    assert_true("alert queue has entries", qlen > 0)
    assert_true("alert queue capped", qlen <= ALERT_QUEUE_MAX_LENGTH)
    r.delete("alert_queue")
    r.close()

    # Dashboard helper: scan_keys
    svc.set("test:dash:x", "x", ttl=10)
    svc.set("test:dash:y", "y", ttl=10)
    keys = svc.scan_keys(pattern="test:dash:*")
    assert_true("scan_keys found keys", len(keys) >= 2)
    svc.delete_pattern("test:dash:*")

    # Dashboard helper: get_redis_info
    info = svc.get_redis_info("memory")
    assert_true("redis info returned", info is not None)
    assert_true("redis info has used_memory", "used_memory" in info)

    # Dashboard helper: get_dbsize
    dbsize = svc.get_dbsize()
    assert_true("dbsize >= 0", dbsize >= 0)

    # Dashboard helper: get_key_info
    svc.set("test:keyinfo", "val", ttl=10)
    ki = svc.get_key_info("test:keyinfo")
    assert_eq("key info type", ki["type"], "string")
    assert_true("key info ttl", ki["ttl"] is not None and ki["ttl"] > 0)
    svc.delete("test:keyinfo")

    # Dashboard helper: get_key_value_preview
    svc.set("test:preview", {"foo": "bar"}, ttl=10)
    preview = svc.get_key_value_preview("test:preview")
    assert_true("preview has value_preview", "value_preview" in preview)
    svc.delete("test:preview")

    # Stats
    stats = svc.get_stats()
    assert_eq("stats backend redis", stats["backend"], "redis")
    assert_true("stats has redis_keys", "redis_keys" in stats)

    svc.close()
    logger.info("  Redis tests completed")


# ================================================================
#  4. Connection retry test
# ================================================================
def test_connection_retry():
    logger.info("--- Connection Retry ---")

    # Bad URL should retry 3 times and fall back gracefully
    start = time.time()
    svc = CacheService(redis_url="redis://localhost:1")
    svc.initialize()
    elapsed = time.time() - start

    assert_false("bad url -> fallback", svc.is_redis_available)

    # If redis package is installed, retries take time (backoff 1s + 2s ~ 3s).
    # If redis package is NOT installed, ImportError is caught immediately.
    try:
        import redis as _redis_check
        assert_true("retry took time (backoff)", elapsed >= 2.5)
    except ImportError:
        logger.info("  SKIP  redis not installed, retry backoff not testable")

    svc.close()


# ================================================================
#  Main
# ================================================================
if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("  Redis CacheService Test Suite")
    logger.info("=" * 60)

    test_lru_fallback()
    test_cache_service_fallback()
    test_cache_service_redis()
    test_connection_retry()

    logger.info("=" * 60)
    logger.info(f"  Results: {passed} passed, {failed} failed")
    logger.info("=" * 60)

    sys.exit(1 if failed > 0 else 0)
