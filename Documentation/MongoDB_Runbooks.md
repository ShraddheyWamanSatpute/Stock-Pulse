# MongoDB Runbooks — Self-Hosted, 99.9% SLA

> **Scope note:** These runbooks are designed for a future production / public deployment (self-hosted, 99.9% SLA).  
> For the current phase, where MongoDB runs **locally** for your own use, you can treat this document as reference only—no need to implement replica sets, TLS, or multi-node ops yet.

Operational procedures for Stock-Pulse MongoDB. Use with the [MongoDB Production Checklist](MongoDB_Production_Checklist.md).

---

## 1. Restore from backup

**When:** Data loss, corruption, or need to recover to a point-in-time copy.

**Prerequisites:** A recent backup from `backend/scripts/backup_mongodb.py` (mongodump or Python JSON export).

### 1.1 Restore from mongodump (BSON)

```bash
# On the host where MongoDB runs (or a new node you’re restoring to)
cd /path/to/backup_root/mongo_backup_YYYYMMDD_HHMMSS

# Restore full dump into the target database
# Target MongoDB must be stopped or use a separate empty database for restore-then-swap.
mongorestore --uri="mongodb://localhost:27017" --db=stockpulse --gzip ./stockpulse
```

- If using auth: `--uri="mongodb://user:pass@host:27017/stockpulse?authSource=admin"`.
- To restore into a different DB name: `--nsFrom="stockpulse.*" --nsTo="stockpulse_restored.*"` then rename/drop as needed.

### 1.2 Restore from Python JSON export

The backup script writes one JSON file per collection under `backup_root/mongo_backup_YYYYMMDD_HHMMSS/stockpulse/`. Use `mongoimport` or a small script with Motor to re-import:

```bash
# Example: restore one collection
mongoimport --uri="mongodb://localhost:27017" --db=stockpulse --collection=portfolio --file=stockpulse/portfolio.json
```

Repeat for each collection. Ensure collections are empty or dropped before import if you want a clean replace.

### 1.3 After restore

1. Restart the Stock-Pulse API (or point it at the restored DB).
2. Call `GET /api/database/health` and confirm `mongodb.status === "connected"` and expected collection counts.
3. Run a quick smoke test (e.g. load watchlist, portfolio, one backtest result).

---

## 2. Failover (replica set primary down)

**When:** Primary is dead or unreachable; you need a new primary.

### 2.1 Confirm primary is down

- Check app: `GET /api/database/health` → `mongodb.status` may be `"error"`.
- On a Mongo shell connected to any surviving member:
  - `rs.status()` — see who is primary, who is secondary, and replication lag.
  - If the primary is missing or unreachable, the replica set will usually **elect a new primary automatically** (within 10–30 seconds typically).

### 2.2 If automatic failover already happened

- No action. Ensure the app connection string includes **all** replica set members (e.g. `mongodb://m1:27017,m2:27017,m3:27017/stockpulse?replicaSet=rs0`). The driver will discover the new primary.
- Restart the app if it had long-lived connections that are now stale, or rely on driver reconnection (Motor retries).

### 2.3 If no automatic failover (e.g. only 2 nodes and one is down)

- Add an arbiter or a third data-bearing node so you have a majority (2 of 3) for elections.
- If you must force a specific secondary to become primary (last resort), connect to that secondary and run:
  - `rs.stepDown(60)` on the current primary (if still reachable), or
  - On the target secondary: force reconfig to make it primary (e.g. temporarily give it higher priority and trigger election). Prefer fixing the cluster topology over manual reconfig.

### 2.4 After failover

1. Verify new primary: `rs.status()`.
2. Check replication lag on secondaries; wait until lag is near 0 if you care about read-after-write consistency.
3. Confirm app: `GET /api/database/health` and test a write (e.g. add to watchlist).

---

## 3. Index build (new or long-running indexes)

**When:** Adding a new index or rebuilding indexes; you want to avoid blocking the app.

### 3.1 Application-created indexes (Stock-Pulse)

The app creates indexes at startup in `_ensure_mongodb_indexes()`. They are created with default options (background-friendly in modern MongoDB). No extra runbook step unless you see errors in logs.

### 3.2 Manually creating a new index

- Prefer building on a **secondary** first so the primary is not loaded (MongoDB 4.4+ supports this in some topologies).
- Use background build to reduce impact:
  - `db.collection.createIndex({ ... }, { background: true })`
- For very large collections, monitor:
  - `currentOp` for active index builds.
  - Replication lag (secondaries may lag during index build on primary).

### 3.3 If an index build fails or is aborted

- Check logs and `db.currentOp()` for index-related ops.
- Fix the cause (e.g. disk space, memory) and re-run index creation. For idempotent creation (e.g. app startup), restart the app so `_ensure_mongodb_indexes` runs again.

---

## 4. When health is degraded

**When:** `GET /api/database/health` returns `overall: "degraded"` or `mongodb.status: "error"`.

### 4.1 Checklist

| Check | Action |
|-------|--------|
| **MongoDB status "error"** | See [Failover](#2-failover-replica-set-primary-down). Confirm replica set with `rs.status()`, connectivity, auth, and disk. |
| **PostgreSQL not connected** | Verify TIMESERIES_DSN, Postgres process, disk. App can run with Mongo + Redis only but time-series and screener may be limited. |
| **Redis fallback** | Redis down or unreachable; app uses in-memory cache. Restart Redis, fix REDIS_URL; restart app if needed. |
| **High replication lag** | Check disk I/O and network on secondaries; check `rs.status()` for lag. Consider scaling I/O or adding a node. |
| **Recent deployment** | Roll back or fix config (e.g. MONGO_URL, auth, TLS). |
| **Disk full** | Free space on data volume; add capacity. MongoDB needs headroom for compaction. |

### 4.2 Escalation

- If Mongo is down and automatic failover does not occur: restore from backup to a new node and rejoin replica set, or bring the previous primary back and fix the cause.
- If data is corrupted: restore from last known good backup (see [Restore from backup](#1-restore-from-backup)).

---

## Quick reference

| Situation | Runbook |
|-----------|---------|
| Restore after data loss / corruption | §1 Restore from backup |
| Primary down / replica set failover | §2 Failover |
| New or long-running index | §3 Index build |
| Health degraded / Mongo error | §4 When health is degraded |

For 99.9% SLA, ensure backups are automated and off-host, monitoring alerts on health and replica set status, and runbooks are exercised periodically (e.g. restore test monthly).
