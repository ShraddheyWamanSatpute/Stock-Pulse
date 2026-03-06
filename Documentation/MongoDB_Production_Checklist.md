# MongoDB Production Checklist — Self-Hosted, Single Region, 99.9% SLA

> **Scope note:** For the current phase of this project you are the only user and MongoDB runs **locally** (single node, no cloud).  
> This checklist is intentionally **forward-looking** for a future production / public deployment.  
> You can safely skip these items for local development; treat them as a blueprint for when you decide to go live.

Target: **self-hosted MongoDB**, **single region**, **99.9% availability** (~8.76 hours downtime/year, ~43 min/month).

Use this checklist for deployment, hardening, and ongoing operations.

---

## 1. Cluster Topology (Self-Hosted, Single Region)

| Item | Requirement | Status |
|------|-------------|--------|
| **Replica set** | Minimum **3 nodes** (1 primary + 2 secondaries) for automatic failover. Standalone is not acceptable for 99.9%. | ☐ |
| **Odd number of voters** | 3 or 5 voting members to avoid split-brain. In single region, 3 is typical. | ☐ |
| **Arbiter (optional)** | If you only have 2 data-bearing servers, add 1 arbiter for a 3-member set. Prefer 3 data nodes if resources allow. | ☐ |
| **Same AZ/rack** | Single region is fine; avoid putting all nodes on the same physical rack if possible (spread across AZs in the same region if your cloud has them). | ☐ |

**Connection string (app):**

```text
mongodb://<user>:<password>@mongo1:27017,mongo2:27017,mongo3:27017/stockpulse?replicaSet=rs0&authSource=admin
```

- Replace hostnames with your replica set members.
- Use **one** connection string; driver discovers primary and handles failover.

---

## 2. Security (Must-Have for Production)

| Item | Action | Status |
|------|--------|--------|
| **Authentication** | Enable `security.authorization: enabled`. Create an app user with **readWrite** (or least-privilege roles) on `stockpulse` only. | ☐ |
| **TLS** | Use TLS for all client–server and inter-node traffic. Set `net.tls.mode: requireTLS` (or `ssl` in older versions). | ☐ |
| **Certificate** | Use valid certs (internal CA or Let’s Encrypt). Avoid `tlsAllowInvalidCertificates` in production. | ☐ |
| **Network** | Bind to private IPs; expose only necessary ports. Restrict client access (e.g. app servers only) via firewall/security groups. | ☐ |
| **Secrets** | Store `MONGO_URL` (with password) in a secrets manager or env only; never in code or logs. | ☐ |

**Example `mongod.conf` (excerpt):**

```yaml
security:
  authorization: enabled
net:
  tls:
    mode: requireTLS
    certificateKeyFile: /etc/mongodb/ssl/server.pem
    CAFile: /etc/mongodb/ssl/ca.pem
  bindIp: 10.0.1.10
```

---

## 3. Application Configuration

| Item | Action | Status |
|------|--------|--------|
| **MONGO_URL** | Set to replica set URI with auth and (if applicable) TLS options. No default to `localhost` in production. | ☐ |
| **Fail fast** | In production, **abort app startup** if MongoDB is unreachable (see code change below). | ☐ |
| **Read preference** | Default `primary` is correct for consistency. For non-critical reads you could use `primaryPreferred`; document any such usage. | ☐ |
| **Write concern** | For critical collections (e.g. portfolio, backtest_results, pipeline_jobs), use `w: "majority"` so writes survive failover. | ☐ |

**Suggested startup behavior (production):**

- If `ENVIRONMENT=production` (or a dedicated `FAIL_FAST_MONGO=true`):
  - On startup, if `client.admin.command("ping")` fails → **exit process with non-zero code** (do not start API).
- Keeps 99.9% meaningful: app is either healthy or not, instead of “up but broken.”

---

## 4. Durability & Write Concern

| Item | Recommendation | Status |
|------|----------------|--------|
| **Journal** | Keep journaling enabled (default). Ensures durability across restarts. | ☐ |
| **Write concern** | For user and pipeline data, use `w: "majority"` and `j: true` where the driver supports it. | ☐ |
| **Critical collections** | At least: `portfolio`, `watchlist`, `alerts`, `backtest_results`, `pipeline_jobs`, `stock_data`. | ☐ |

In Motor you can set default write concern on the client or per-operation, e.g.:

```python
# When creating client or per-operation
await db.portfolio.insert_one(doc, write_concern=WriteConcern(w="majority", j=True))
```

---

## 5. Backups (Self-Hosted)

| Item | Requirement | Status |
|------|-------------|--------|
| **Schedule** | Automated daily (or more frequent if RPO &lt; 24h). Use cron/systemd timer. | ☐ |
| **Method** | Prefer **mongodump** (or filesystem snapshot of data dirs on a secondary with `fsyncLock`/`fsyncUnlock`) for consistency. | ☐ |
| **Retention** | Keep at least 7 daily + 4 weekly (or 30 days). Align with your existing `backup_mongodb.py --keep`. | ☐ |
| **Off-host copy** | Copy backups to another machine/object storage (different disk/region) so a single host failure doesn’t lose backups. | ☐ |
| **Restore test** | Restore to a test instance at least monthly and verify DB opens and app can read. | ☐ |

Your existing script: `backend/scripts/backup_mongodb.py` — wire it to cron and add an off-host copy step (e.g. `rsync`/`rclone`/S3).

---

## 6. Monitoring & Alerting (99.9% SLA)

| Item | What to do | Status |
|------|------------|--------|
| **Liveness** | Probe `/api/database/health` (or a dedicated `/api/health/mongo`) every 30–60s. Fail if MongoDB section is not `connected`. | ☐ |
| **Replica set** | Monitor replica set status: primary present, majority of nodes up, no long-lasting elections. Use `GET /api/database/health` → `mongodb.replica_set` when connected to a replica set, or Prometheus MongoDB exporter. | ☐ |
| **Replication lag** | Alert if secondary lag &gt; 10s (tune to your tolerance). Prevents serving stale reads and indicates replication issues. | ☐ |
| **Connections** | Alert on connection pool exhaustion or rapid growth (e.g. `maxPoolSize` approached). | ☐ |
| **Disk** | Alert when free space &lt; 20% on data volume. MongoDB needs headroom for compaction and growth. | ☐ |
| **Oplog** | Ensure oplog window is at least 24–48 hours so secondaries can catch up after downtime. | ☐ |

**SLA math:** 99.9% = 43 min/month. Budget time for planned maintenance (e.g. upgrades, index builds) and ensure unplanned outages stay under the remainder.

---

## 7. Operational Runbooks

| Runbook | Purpose | Status |
|---------|---------|--------|
| **Restore from backup** | Steps to restore from `mongodump` or snapshot to a new/current node and re-add to replica set if needed. | ✅ [MongoDB_Runbooks.md](MongoDB_Runbooks.md#1-restore-from-backup) |
| **Failover** | Document: how to confirm primary is down, how to force re-election or promote a secondary (prefer automatic). | ✅ [MongoDB_Runbooks.md](MongoDB_Runbooks.md#2-failover-replica-set-primary-down) |
| **Index build** | For long-running index builds, use `background: true` and monitor; in 4.4+ consider resumable index builds. | ✅ [MongoDB_Runbooks.md](MongoDB_Runbooks.md#3-index-build-new-or-long-running-indexes) |
| **When health is degraded** | Check: replica set status, disk, logs, recent deployments; escalate if replication lag or auth errors. | ✅ [MongoDB_Runbooks.md](MongoDB_Runbooks.md#4-when-health-is-degraded) |

---

## 8. Application-Level Checklist (Stock-Pulse)

| Item | Status |
|------|--------|
| Indexes created at startup (`_ensure_mongodb_indexes`) | ✅ In place |
| TTL indexes for logs (extraction_log, quality_reports, pipeline_jobs) | ✅ In place |
| Input sanitization (symbols, update whitelist) | ✅ In place |
| Health endpoint includes Mongo (collections + counts) | ✅ In place |
| Backup script with rotation | ✅ In place |
| Fail fast on Mongo down in production | ✅ In place |
| Explicit write concern `w: "majority"` for critical writes | ✅ In place (`server.py` + `mongodb_store.py`) |
| No default `localhost` when `ENVIRONMENT=production` | ✅ In place |

---

## 9. Quick Reference: 99.9% Single-Region Mongo

- **Topology:** 3-node replica set, same region.
- **Security:** Auth on, TLS on, app user with minimal rights, secrets in env/vault.
- **App:** Replica set URI, fail fast if Mongo down in prod, majority write concern for critical data.
- **Backup:** Daily (or better), off-host copy, monthly restore test.
- **Monitoring:** Liveness, replica set status, replication lag, disk, connections; alert and fix before budget is exceeded.

Completing the unchecked items above will align your self-hosted MongoDB with a 99.9% SLA in a single region.

---

## 10. Implementation Notes (Stock-Pulse Backend)

### 10.1 Production URL and fail-fast (recommended)

In production, the app should:

1. **Refuse to use default `localhost`** when `ENVIRONMENT=production`.
2. **Exit on startup** if MongoDB is unreachable in production (fail fast).

In `backend/server.py`:

- **Mongo URL (after `load_dotenv`):**  
  If `ENVIRONMENT=production`, require `MONGO_URL` to be set and not point at `localhost` (e.g. reject `mongodb://localhost` and `mongodb://127.0.0.1`). Otherwise log a warning and continue for non-prod.

- **Startup (in `startup_event`):**  
  If `ENVIRONMENT=production` and the MongoDB `ping` fails, **log the error and call `sys.exit(1)`** (or `raise SystemExit(1)`) so the process does not start. In non-production, keep current behavior (log and continue).

### 10.2 Write concern (implemented)

Critical collections use **majority write concern** so writes survive replica set failover:

- **`server.py`:** After creating `db`, the following collections are replaced with `db.get_collection(name, write_concern=WriteConcern(w="majority", j=True))`: `watchlist`, `portfolio`, `news_articles`, `backtest_results`, `alerts`, `pipeline_jobs`, `stock_data`. All existing code that uses `db.watchlist`, `db.portfolio`, etc. automatically uses these.
- **`data_extraction/storage/mongodb_store.py`:** Uses `getattr(db, "stock_data", db["stock_data"])` and `getattr(db, "pipeline_jobs", db["pipeline_jobs"])` so when the store is given the app’s `db`, it uses the same write-concern collections.
