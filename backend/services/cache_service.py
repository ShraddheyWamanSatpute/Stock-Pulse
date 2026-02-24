"""
Redis Cache Service for StockPulse

Provides centralized caching with TTL-based expiry for:
- Live stock quotes (60s TTL)
- Stock analysis results (300s TTL)
- Pipeline status (30s TTL)
- General purpose caching

Falls back to in-memory caching if Redis is unavailable.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# TTL Constants (seconds)
PRICE_CACHE_TTL = 60        # 1 minute for live price quotes
ANALYSIS_CACHE_TTL = 300    # 5 minutes for analysis results
STOCK_LIST_CACHE_TTL = 300  # 5 minutes for stock list/mock data
PIPELINE_CACHE_TTL = 30     # 30 seconds for pipeline status
NEWS_CACHE_TTL = 180        # 3 minutes for news items
DEFAULT_CACHE_TTL = 120     # 2 minutes default

# Cache key prefixes
PREFIX_PRICE = "price:"
PREFIX_ANALYSIS = "analysis:"
PREFIX_STOCK = "stock:"
PREFIX_STOCK_LIST = "stock_list"
PREFIX_PIPELINE = "pipeline:"
PREFIX_NEWS = "news:"
PREFIX_MARKET = "market:"


class CacheService:
    """
    Redis-backed cache service with in-memory fallback.
    
    Uses the synchronous redis-py client for simplicity since cache
    operations are fast (~1ms) and don't benefit much from async overhead.
    For async support, this can be upgraded to redis.asyncio.
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379", db: int = 0):
        self._redis = None
        self._redis_available = False
        self._fallback_cache: Dict[str, Dict[str, Any]] = {}
        self._redis_url = redis_url
        self._db = db
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "errors": 0,
        }
        
    def initialize(self):
        """Initialize Redis connection. Safe to call multiple times."""
        try:
            import redis
            self._redis = redis.Redis.from_url(
                self._redis_url,
                db=self._db,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=1,
                retry_on_timeout=True,
            )
            # Test connection
            self._redis.ping()
            self._redis_available = True
            logger.info("✅ Redis cache connected successfully")
        except ImportError:
            logger.warning("redis package not installed, using in-memory cache fallback")
            self._redis_available = False
        except Exception as e:
            logger.warning(f"Redis not available ({e}), using in-memory cache fallback")
            self._redis_available = False
    
    @property
    def is_redis_available(self) -> bool:
        return self._redis_available
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache. Returns None on miss."""
        try:
            if self._redis_available:
                data = self._redis.get(key)
                if data is not None:
                    self._stats["hits"] += 1
                    return json.loads(data)
                self._stats["misses"] += 1
                return None
            else:
                # Fallback: in-memory cache with manual TTL check
                entry = self._fallback_cache.get(key)
                if entry is None:
                    self._stats["misses"] += 1
                    return None
                if datetime.now(timezone.utc).timestamp() > entry["expires_at"]:
                    del self._fallback_cache[key]
                    self._stats["misses"] += 1
                    return None
                self._stats["hits"] += 1
                return entry["value"]
        except Exception as e:
            self._stats["errors"] += 1
            logger.debug(f"Cache get error for {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = DEFAULT_CACHE_TTL) -> bool:
        """Set a value in cache with TTL (seconds). Returns True on success."""
        try:
            serialized = json.dumps(value, default=str)
            if self._redis_available:
                self._redis.setex(key, ttl, serialized)
            else:
                self._fallback_cache[key] = {
                    "value": value,
                    "expires_at": datetime.now(timezone.utc).timestamp() + ttl,
                }
            self._stats["sets"] += 1
            return True
        except Exception as e:
            self._stats["errors"] += 1
            logger.debug(f"Cache set error for {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        try:
            if self._redis_available:
                self._redis.delete(key)
            else:
                self._fallback_cache.pop(key, None)
            return True
        except Exception as e:
            logger.debug(f"Cache delete error for {key}: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern (e.g., 'price:*'). Returns count deleted."""
        try:
            if self._redis_available:
                keys = self._redis.keys(pattern)
                if keys:
                    return self._redis.delete(*keys)
                return 0
            else:
                to_delete = [k for k in self._fallback_cache if self._match_pattern(k, pattern)]
                for k in to_delete:
                    del self._fallback_cache[k]
                return len(to_delete)
        except Exception as e:
            logger.debug(f"Cache delete_pattern error for {pattern}: {e}")
            return 0
    
    @staticmethod
    def _match_pattern(key: str, pattern: str) -> bool:
        """Simple glob pattern matching for fallback cache."""
        if pattern.endswith("*"):
            return key.startswith(pattern[:-1])
        return key == pattern
    
    # ========================
    # Domain-specific helpers
    # ========================
    
    def get_price(self, symbol: str) -> Optional[Dict]:
        """Get cached live price quote for a symbol."""
        return self.get(f"{PREFIX_PRICE}{symbol}")
    
    def set_price(self, symbol: str, data: Dict) -> bool:
        """Cache live price quote for a symbol."""
        return self.set(f"{PREFIX_PRICE}{symbol}", data, PRICE_CACHE_TTL)
    
    def get_analysis(self, symbol: str) -> Optional[Dict]:
        """Get cached analysis result for a symbol."""
        return self.get(f"{PREFIX_ANALYSIS}{symbol}")
    
    def set_analysis(self, symbol: str, data: Dict) -> bool:
        """Cache analysis result for a symbol."""
        return self.set(f"{PREFIX_ANALYSIS}{symbol}", data, ANALYSIS_CACHE_TTL)
    
    def get_stock_list(self) -> Optional[Dict]:
        """Get cached stock list (all stocks data)."""
        return self.get(PREFIX_STOCK_LIST)
    
    def set_stock_list(self, data: Dict) -> bool:
        """Cache stock list (all stocks data)."""
        return self.set(PREFIX_STOCK_LIST, data, STOCK_LIST_CACHE_TTL)
    
    def get_market_overview(self) -> Optional[Dict]:
        """Get cached market overview."""
        return self.get(f"{PREFIX_MARKET}overview")
    
    def set_market_overview(self, data: Dict) -> bool:
        """Cache market overview."""
        return self.set(f"{PREFIX_MARKET}overview", data, PRICE_CACHE_TTL)
    
    def invalidate_stock(self, symbol: str):
        """Invalidate all caches for a specific stock."""
        self.delete(f"{PREFIX_PRICE}{symbol}")
        self.delete(f"{PREFIX_ANALYSIS}{symbol}")
        self.delete(f"{PREFIX_STOCK}{symbol}")
    
    def invalidate_all(self):
        """Invalidate all caches."""
        if self._redis_available:
            try:
                self._redis.flushdb()
            except Exception as e:
                logger.warning(f"Failed to flush Redis: {e}")
        else:
            self._fallback_cache.clear()
    
    def get_stats(self) -> Dict:
        """Get cache statistics."""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0
        
        stats = {
            **self._stats,
            "hit_rate_percent": round(hit_rate, 2),
            "backend": "redis" if self._redis_available else "in-memory",
        }
        
        if self._redis_available:
            try:
                info = self._redis.info("memory")
                stats["redis_memory_used"] = info.get("used_memory_human", "N/A")
                stats["redis_keys"] = self._redis.dbsize()
            except Exception:
                pass
        else:
            stats["in_memory_keys"] = len(self._fallback_cache)
        
        return stats
    
    def close(self):
        """Close Redis connection."""
        if self._redis:
            try:
                self._redis.close()
            except Exception:
                pass
    
    # ========================
    # HASH — per-field stock data
    # ========================
    
    def set_stock_hash(self, symbol: str, fields: Dict[str, Any]) -> bool:
        """Store individual stock fields as a Redis HASH (enables partial reads)."""
        try:
            if self._redis_available:
                key = f"stock:{symbol}"
                # Convert all values to strings for Redis HASH
                str_fields = {k: json.dumps(v, default=str) for k, v in fields.items()}
                self._redis.hset(key, mapping=str_fields)
                self._redis.expire(key, PRICE_CACHE_TTL)
                self._stats["sets"] += 1
                return True
            return False
        except Exception as e:
            self._stats["errors"] += 1
            logger.debug(f"HASH set error for {symbol}: {e}")
            return False
    
    def get_stock_field(self, symbol: str, field: str) -> Optional[Any]:
        """Get a single field from a stock's HASH (e.g., just the price)."""
        try:
            if self._redis_available:
                data = self._redis.hget(f"stock:{symbol}", field)
                if data:
                    self._stats["hits"] += 1
                    return json.loads(data)
                self._stats["misses"] += 1
            return None
        except Exception as e:
            self._stats["errors"] += 1
            return None
    
    def get_stock_fields(self, symbol: str, fields: List[str]) -> Dict[str, Any]:
        """Get multiple fields from a stock's HASH."""
        try:
            if self._redis_available:
                values = self._redis.hmget(f"stock:{symbol}", fields)
                result = {}
                for f, v in zip(fields, values):
                    if v is not None:
                        result[f] = json.loads(v)
                if result:
                    self._stats["hits"] += 1
                else:
                    self._stats["misses"] += 1
                return result
            return {}
        except Exception:
            return {}
    
    # ========================
    # SORTED SET — top movers
    # ========================
    
    def update_top_movers(self, gainers: Dict[str, float], losers: Dict[str, float]) -> bool:
        """
        Update top gainers and losers using Redis SORTED SETs.
        
        Args:
            gainers: Dict of {symbol: price_change_percent} for gainers
            losers: Dict of {symbol: price_change_percent} for losers
        """
        try:
            if self._redis_available:
                if gainers:
                    self._redis.zadd("top_gainers", gainers)
                    self._redis.expire("top_gainers", PRICE_CACHE_TTL)
                if losers:
                    # Store as positive values, sorted ascending → worst first
                    self._redis.zadd("top_losers", {k: abs(v) for k, v in losers.items()})
                    self._redis.expire("top_losers", PRICE_CACHE_TTL)
                return True
            return False
        except Exception as e:
            logger.debug(f"ZSET update error: {e}")
            return False
    
    def get_top_gainers(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get top N gainers from SORTED SET (highest change % first)."""
        try:
            if self._redis_available:
                results = self._redis.zrevrange("top_gainers", 0, count - 1, withscores=True)
                return [{"symbol": sym, "change_pct": score} for sym, score in results]
            return []
        except Exception:
            return []
    
    def get_top_losers(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get top N losers from SORTED SET (biggest loss first)."""
        try:
            if self._redis_available:
                results = self._redis.zrevrange("top_losers", 0, count - 1, withscores=True)
                return [{"symbol": sym, "change_pct": -score} for sym, score in results]
            return []
        except Exception:
            return []
    
    # ========================
    # PUB/SUB — real-time prices
    # ========================
    
    def publish_price(self, symbol: str, price_data: Dict) -> bool:
        """Publish a price update to the Redis PUB/SUB channel."""
        try:
            if self._redis_available:
                channel = f"channel:prices"
                payload = json.dumps({"symbol": symbol, **price_data}, default=str)
                self._redis.publish(channel, payload)
                return True
            return False
        except Exception as e:
            logger.debug(f"PUB/SUB publish error: {e}")
            return False
    
    def publish_alert(self, alert_data: Dict) -> bool:
        """Push an alert notification to the Redis alert queue (LIST)."""
        try:
            if self._redis_available:
                payload = json.dumps(alert_data, default=str)
                self._redis.rpush("alert_queue", payload)
                return True
            return False
        except Exception as e:
            logger.debug(f"Alert queue push error: {e}")
            return False


# Module-level singleton
_cache_service: Optional[CacheService] = None


def init_cache_service(redis_url: str = "redis://localhost:6379") -> CacheService:
    """Initialize and return the global cache service singleton."""
    global _cache_service
    _cache_service = CacheService(redis_url=redis_url)
    _cache_service.initialize()
    return _cache_service


def get_cache_service() -> Optional[CacheService]:
    """Get the global cache service instance."""
    return _cache_service
