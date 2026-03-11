# Redis Setup & Operations Guide — Stock-Pulse

## 1. Overview

Redis is used as the **hot cache layer** for Stock-Pulse. It caches live prices,
analysis results, market overviews, and supports real-time price broadcasting
via Pub/Sub. The application **falls back to an in-memory cache** automatically
if Redis is unavailable, so Redis is optional for development but recommended
for production.

---

## 2. Installation

### macOS (Homebrew)

```bash
brew install redis
brew services start redis
```

### Ubuntu / Debian

```bash
sudo apt update && sudo apt install redis-server -y
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

### Docker (recommended for consistency)

```bash
docker run -d --name stockpulse-redis \
  -p 6379:6379 \
  --restart unless-stopped \
  redis:7-alpine \
  redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
```

### Docker Compose (if using a compose file)

```yaml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
    restart: unless-stopped
```

---

## 3. Configuration

### Environment variables (`.env`)

```bash
# Required
REDIS_URL=redis://localhost:6379

# For production with authentication:
# REDIS_URL=redis://:your_password@host:6379

# For managed Redis with TLS:
# REDIS_URL=rediss://:your_password@host:6380

# Optional tuning (defaults shown)
REDIS_CONNECT_TIMEOUT=5       # Connection timeout (seconds)
REDIS_SOCKET_TIMEOUT=5        # Socket read/write timeout (seconds)
REDIS_MAX_CONNECTIONS=10      # Connection pool size
REDIS_FALLBACK_MAX_KEYS=10000 # Max keys in fallback in-memory cache
```

### Redis server configuration (`redis.conf`)

For production, ensure these are set in your Redis server config:

```
maxmemory 256mb
maxmemory-policy allkeys-lru
```

These settings ensure Redis evicts the least-recently-used keys when memory is
full, which is the correct behavior for a cache-only deployment.

You can also set them at runtime:

```bash
redis-cli CONFIG SET maxmemory 256mb
redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

---

## 4. Verification

### Step 1: Verify Redis is running

```bash
redis-cli ping
# Expected: PONG
```

### Step 2: Run the setup check

```bash
cd backend
python setup_databases.py --redis
```

Expected output:
```
Redis connected: redis://localhost:6379
  Version : 7.x.x
  Memory  : 1.20M
  Keys    : 0
```

### Step 3: Verify via API (with backend running)

```bash
# Cache stats
curl http://localhost:8000/api/cache/stats

# Database health (includes Redis status)
curl http://localhost:8000/api/database/health
```

Look for `"backend": "redis"` in the cache stats response. If Redis is
unavailable, you'll see `"backend": "in-memory"`.

---

## 5. Key Naming Conventions

| Prefix / Key        | Type       | TTL   | Description                    |
|----------------------|------------|-------|--------------------------------|
| `price:{SYMBOL}`     | String     | 60s   | Live price quote JSON          |
| `analysis:{SYMBOL}`  | String     | 300s  | Analysis result JSON           |
| `stock:{SYMBOL}`     | Hash       | 60s   | Per-field stock data           |
| `stock_list`         | String     | 300s  | Full stock directory           |
| `market:overview`    | String     | 60s   | Market indices overview        |
| `pipeline:*`         | String     | 30s   | Pipeline job status            |
| `news:*`             | String     | 180s  | News cache                     |
| `screener:{hash}`    | String     | 120s  | Screener results by filter     |
| `top_gainers`        | Sorted Set | 60s   | Top gaining symbols            |
| `top_losers`         | Sorted Set | 60s   | Top losing symbols             |
| `ws:price:{SYMBOL}`  | String     | 10s   | WebSocket price cache          |
| `alert_queue`        | List       | None  | Alert notifications (capped)   |
| `channel:prices`     | Pub/Sub    | N/A   | Real-time price broadcast      |

---

## 6. Eviction & Memory Management

- **Eviction policy:** `allkeys-lru` — Redis automatically removes the least
  recently used keys when `maxmemory` is reached. This is ideal for cache-only
  usage where all data can be regenerated.
- **Recommended maxmemory:** 256 MB for small deployments, 512 MB for larger
  stock universes.
- **TTLs:** All cache keys have TTLs (10s–300s). The `alert_queue` LIST is
  capped at 1000 entries via LTRIM.
- **No persistence required:** Redis is used purely as a cache. Data loss on
  restart is acceptable — the application will re-populate from source APIs.

---

## 7. Runbook

### Redis is down or unreachable

1. The app automatically falls back to an in-memory cache (bounded, LRU).
2. Check Redis status: `redis-cli ping` or `systemctl status redis`.
3. Check logs: `journalctl -u redis` or Docker logs.
4. Restart Redis: `systemctl restart redis` / `docker restart stockpulse-redis`.
5. The app will auto-reconnect on the next cache operation attempt.
6. Verify via `/api/cache/stats` — `backend` should show `"redis"` once restored.

### Verify Redis connectivity

```bash
# From the host
redis-cli -u $REDIS_URL ping

# From the app
python -c "
import redis
r = redis.Redis.from_url('redis://localhost:6379', decode_responses=True)
print('PONG' if r.ping() else 'FAIL')
r.close()
"
```

### Safely flush the cache

```bash
# Via API (blocked in production unless ALLOW_CACHE_FLUSH=true)
curl -X DELETE http://localhost:8000/api/cache/flush

# Via CLI (development only)
redis-cli FLUSHDB
```

**Warning:** FLUSHDB removes all keys in the current database. In production,
prefer targeted invalidation (`DEL key` or pattern-based via SCAN).

### Check memory usage

```bash
redis-cli INFO memory | grep used_memory_human
redis-cli INFO memory | grep maxmemory_human
```

### When to restart the app

- After changing `REDIS_URL` in `.env`.
- If the app is stuck in fallback mode and Redis has been restored (though
  auto-reconnect should handle this).

---

## 8. Production Checklist

- [ ] Redis installed and running (or managed Redis provisioned)
- [ ] `maxmemory` set (e.g., 256mb)
- [ ] `maxmemory-policy` set to `allkeys-lru`
- [ ] `REDIS_URL` set in `.env` with password for production
- [ ] TLS enabled if using managed Redis (`rediss://` URL scheme)
- [ ] `/api/cache/stats` shows `"backend": "redis"`
- [ ] `/cache/flush` is blocked in production (`ENVIRONMENT=production`)
- [ ] `setup_databases.py --redis` passes connectivity check
- [ ] Monitoring: check `/api/cache/stats` periodically for hit rate and memory

---

## 9. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `backend: "in-memory"` in stats | Redis unreachable | Check REDIS_URL, Redis process, firewall |
| High error count in stats | Timeout / network issues | Increase REDIS_SOCKET_TIMEOUT |
| Memory growing unbounded | No maxmemory set | Set maxmemory in redis.conf |
| Slow key listing in dashboard | Too many keys | Already uses SCAN (non-blocking) |
| Cache flush rejected | Production guard | Set ALLOW_CACHE_FLUSH=true or use CLI |
