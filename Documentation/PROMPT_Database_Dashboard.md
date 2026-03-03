# Database Dashboard — AI Implementation Prompt

**Instructions for the AI:** Use this entire document as the single source of truth. Build a comprehensive Database Dashboard (or dedicated admin section) for StockPulse that satisfies every requirement below. Do not skip sections; implement all listed features. The app is for single-user use only (not public); authentication can be added later—do not compromise on the rest of the application’s security (validate all inputs, no direct DB access from frontend).

---

## 1. Project context

- **Product:** StockPulse — Indian stock market analysis platform.
- **Frontend:** React (Vite), React Router. Existing pages: Dashboard, Stock Analyzer, Screener, Watchlist, Portfolio, Alerts, Backtest, News Hub, Reports, Data Pipeline.
- **Backend:** FastAPI (Python), REST API under `/api`, WebSocket support.
- **Databases (three stores):**
  - **MongoDB** — Entity/document store. Collections: `watchlist`, `portfolio`, `alerts`, `stock_data`, `price_history`, `extraction_log`, `quality_reports`, `pipeline_jobs`, `news_articles`, `backtest_results`. Some collections have 90-day TTL.
  - **PostgreSQL** — Time-series and analytics. Tables: `prices_daily`, `technical_indicators`, `fundamentals_quarterly`, `shareholding_quarterly`. Optional: TimescaleDB views `prices_weekly`, `prices_monthly`.
  - **Redis** — Cache layer. Key patterns: `price:*`, `analysis:*`, `stock_list`, `market:overview`, `pipeline:*`, `news:*`, `ws:price:*`, `top_gainers`, `top_losers`, `alert_queue`. Optional (in-memory fallback if Redis unavailable).

The **Data Pipeline** page (`/data-pipeline`) already exists for extraction jobs. The **Database Dashboard** must be a **separate, dedicated section** for database visibility, management, monitoring, and control. All dashboard data and actions must go through the FastAPI backend; **no direct database connections from the browser**.

---

## 2. Goal (what to build)

Create a **comprehensive Database Dashboard** that provides:

- **Complete transparency** — see exactly what is stored where and how the system is behaving.
- **Full control** — manually add, update, delete records where safe; manage settings and limits.
- **Operational insight** — real-time activity, errors, alerts, health, and logs in one place.

The interface must be **powerful yet easy to understand**: clean UI, clear visualizations, search and filter, and minimal jargon.

---

## 3. Mandatory requirements (implement all)

### 3.1 Database activity monitoring

- **Real-time view** of how each database is functioning (MongoDB, PostgreSQL, Redis).
- **Live tracking** where feasible:
  - Query count or request rate (e.g. reads/writes per minute from backend or DB stats).
  - Transaction or operation success/failure counts.
  - Performance metrics: response time or latency (e.g. ping/time to first byte), connection pool usage if exposed by the backend.
- Display in a **live-updating** or **refreshable** section (e.g. auto-refresh every 30–60 seconds or manual “Refresh” button).
- Use existing backend health/stats endpoints where possible; add new endpoints only if current APIs do not expose these metrics.

### 3.2 Data structure & storage overview

- **Clear visualization** of which data is stored in which database, and within each store:
  - **MongoDB:** List all collections with document count and optional size; for each collection, show “View sample” and optionally schema (field names / types from sample or from a dedicated schema endpoint).
  - **PostgreSQL:** List all tables with row count and size; for each table, “View sample” and column names (schema).
  - **Redis:** List key patterns or prefixes with key count, type, TTL; optional sample value for non-sensitive keys only.
- **Schema view:** For each collection/table, show field/column names and types (infer from sample or from backend). For PostgreSQL, show **relationships** between tables (e.g. foreign keys, or a simple diagram: which tables reference which).
- **Data flow mapping:** A simple diagram or section explaining how data moves: e.g. “External APIs → Extraction Pipeline → MongoDB (stock_data, extraction_log) + PostgreSQL (prices_daily, …) → Redis (cache) → Frontend.” Text or visual both acceptable; goal is “how data moves through the system.”

### 3.3 Manual data management

- **Add, update, delete** records for:
  - **Watchlist** — full CRUD (use existing `/api/watchlist` endpoints).
  - **Portfolio** — full CRUD (use existing `/api/portfolio` endpoints).
  - **Alerts** — full CRUD (use existing `/api/alerts` endpoints).
  - Optionally: **news_articles**, **backtest_results** (if backend supports safe create/update/delete with validation).
  - For other MongoDB collections (e.g. extraction_log, pipeline_jobs): **view + delete single document by id** only, no arbitrary insert/update unless you add strict server-side validation.
  - PostgreSQL: **read-only** “View sample” by default; if you add edit, restrict to one safe table with parameterized queries and validation.
- **Inline editing:** Where a list/table of records is shown (e.g. watchlist, portfolio, alerts), support **inline editing** (e.g. click a cell or row to edit in place, then save) in addition to modal/form-based add/edit.
- **Version history and change tracking:** If feasible without large backend changes, show “last updated” or “created_at” per record and, where possible, a simple **change log** (e.g. last N changes: who/what/when—e.g. “Record X updated at 14:30”). If full history is not possible, at least show timestamps and “last modified” for records; document in UI what is available.

### 3.4 Full database visibility

- **Complete overview** of what is stored:
  - Per-store summary (MongoDB: 10 collections + counts; PostgreSQL: 4 tables + row counts/sizes; Redis: key counts by prefix).
  - Drill-down: select a collection/table → see sample rows/documents, schema, and optional “incoming/outgoing” description (e.g. “This collection is written by the extraction pipeline; read by the Stock Analyzer”).
- **Incoming and outgoing data:** For each collection/table, show (in text or a small card):
  - **Sources** — which part of the system writes here (e.g. “Groww pipeline”, “Watchlist API”, “NSE Bhavcopy”).
  - **Consumers** — which part reads (e.g. “Screener”, “Dashboard”, “Backtest”).
- **Logs of database operations and activity history:**
  - Expose **recent activity**: e.g. last N extraction_log entries, last N pipeline_jobs (with status), last N failed operations if available.
  - If the backend can expose a simple “activity log” (recent inserts/updates/deletes per collection), show it; otherwise use extraction_log + pipeline_jobs + any error log as the “activity history” and label it clearly.

### 3.5 Error monitoring & alerts

- **Visual display** of database errors and failed queries:
  - Dedicated section listing **recent errors**: failed pipeline jobs, extraction_log entries with status “failed”, connection errors from health check, and any backend-logged DB errors if exposed via API.
  - Show timestamp, source (e.g. collection/job), and error message; optional severity or type.
- **Alert system for thresholds:** Allow the user to **set and manage** thresholds, for example:
  - **Storage limits** — e.g. “Warn when MongoDB size &gt; X GB” or “Warn when disk &gt; Y%”.
  - **Query limits** — e.g. “Warn when slow query count &gt; N per hour” (if backend exposes this).
  - **Connection limits** — e.g. “Warn when connection pool usage &gt; 80%” or “Warn when Redis/Mongo/Postgres is down”.
- **Customizable alert settings and notification management:**
  - UI to **enable/disable** each threshold, set **numeric limits** (e.g. max size, max slow queries), and optionally **notification channel** (e.g. “Show in dashboard only” for now; later: email/in-app). Store settings in backend (config file or database); no need for email/SMS in v1 if not already in the app.

### 3.6 Connections & system management

- **Overview of active connections and system integrations:**
  - List each store (MongoDB, PostgreSQL, Redis) with status (connected / degraded / disconnected).
  - Show **sanitized** connection info: host, port, database name; **never** show passwords or full connection strings.
  - Show “last checked” or “last ping” time; button to **Recheck** or **Refresh** health.
- **Database health monitoring:** Where the backend or OS can expose it, show:
  - **CPU** — e.g. process CPU or “N/A” if not available.
  - **Memory** — e.g. MongoDB/Redis/Postgres memory usage if exposed; otherwise “N/A”.
  - **Storage** — e.g. disk usage for DB data directories or total DB size; optional “Warn when &gt; X%” linked to alert settings.
- **User access control and permission management:** The app is **single-user**; no multi-tenant roles required. Provide a **read-only** section that describes “Current access: single user (you). Authentication can be added later.” If the backend exposes “current user” or “permissions,” show them; otherwise a short note is enough. Do not build a full RBAC UI unless specified elsewhere.

### 3.7 User-friendly visualization

- **Clean, intuitive UI:** Use the existing app design system (e.g. shadcn/ui, Tailwind). Consistent spacing, typography, and colors. Avoid clutter; use tabs or sections to group content.
- **Graphs, charts, and dashboards:** Include at least:
  - **Performance/usage metrics:** e.g. line or bar chart for “Requests per minute” or “Query count over time” if backend exposes it; or “Cache hit rate over time”; or “Connection status over last 24h” (if you store periodic health snapshots).
  - **Storage usage:** e.g. bar chart or progress bar for “MongoDB size”, “PostgreSQL size”, “Redis memory”, “Disk usage” where available.
  - **Error trend:** e.g. count of errors per day or per collection (from extraction_log / pipeline_jobs failures).
- **Search and filter:** For any list of records (collections, tables, sample data, logs, errors):
  - **Search** — text search on key fields (e.g. symbol, id, message).
  - **Filter** — e.g. by date range, by status (success/failed), by collection/table. Provide “Clear filters” and sensible defaults.

---

## 4. Technical & non-functional constraints

### 4.1 Platform & security

- **Frontend:** React (Vite), React Router. Add a new route (e.g. `/database` or `/db-dashboard`) and a new page component. Add a navigation entry in the app layout (e.g. in `Layout.jsx`) with an appropriate icon (e.g. Database, Server, Settings).
- **Backend:** FastAPI. All data and actions for the dashboard must go through the backend. **No direct database connections from the browser.**
- **Security:** Validate all inputs on the backend; use existing `mongo_utils` (e.g. `sanitize_symbol`, `validate_update_fields`, `is_safe_value`) for MongoDB updates. Do not expose secrets (passwords, full connection strings) in any API response or log used by the dashboard.
- **Existing endpoints to use where relevant:**  
  `GET /api/database/health`, `GET /api/cache/stats`, `DELETE /api/cache/flush`, `GET /api/timeseries/stats`,  
  `GET/POST/PUT/DELETE /api/watchlist`, `GET/POST/PUT/DELETE /api/portfolio`, `GET/POST/PUT/DELETE /api/alerts` (and alerts by id).
- **New endpoints:** Add only what is needed for the above requirements, e.g.:
  - Aggregated overview (counts, status, last error).
  - Sample documents/rows per collection/table.
  - Redis key list (prefix, type, TTL; optional value for safe keys).
  - Activity log or recent errors endpoint.
  - Settings for alerts/limits (GET/PATCH) if stored server-side.
  - Optional: schema or relationship info for PostgreSQL tables.
  - Any endpoint that modifies data must validate input and use whitelists/validation; return clear error messages.

### 4.2 Non-functional requirements (very important)

- **Performance:**
  - Dashboard pages should **load in under 2–3 seconds** for normal data sizes (single-user usage: up to a few hundred symbols and a few years of history).
  - All dashboard API calls must be **paginated** and **bounded** (see §4.3) to avoid loading unbounded data.
  - Expensive operations (e.g. full activity history, large logs) should be explicitly triggered by the user (e.g. “Load more”) and not auto-run on every page load.
- **Scalability:**
  - Design endpoints and queries so that increasing data (more symbols, more logs) mainly increases **pages** fetched, not per-request latency (indexes must be used).
  - Avoid N+1 query patterns from the dashboard (fetch aggregated stats in batches, not per-row).
- **Error handling:**
  - All backend errors must return **structured JSON** with an error code and message; the frontend must display user-friendly error messages (no raw stack traces).
  - The dashboard should clearly indicate when a section cannot load (e.g. MongoDB down) and allow retry.
- **Rate limiting:**
  - If the backend has or gains rate limiting, the dashboard should **batch** health/stat requests instead of hammering endpoints.
  - Auto-refresh intervals (e.g. for health/activity) should be **no faster than every 15–30 seconds** by default.
- **Logging policy:**
  - All dashboard-related backend endpoints should log requests and important events (especially manual edits and errors) in a structured way, without logging secrets or PII.

### 4.3 Pagination rules (critical)

Apply these rules consistently across the dashboard:

- **Sample rows/documents:**
  - Default page size: **20–50 items** (choose a sensible default and make it configurable via query param, e.g. `page_size`).
  - Maximum page size: **100** to prevent accidental huge responses.
  - Support `page`/`page_size` or `offset`/`limit` parameters on backend endpoints; the frontend must use them.
- **Logs and activity history (extraction_log, pipeline_jobs, errors):**
  - Default: show the **most recent 50** entries.
  - Allow pagination (“Next/Previous” or infinite scroll) but **never** load more than 500 entries in one request.
  - Provide simple filters (e.g. by status or date range) to limit what is returned.

### 4.4 Schema handling

- **Schema inference:**
  - The backend may infer schema dynamically (from DB metadata or from representative documents), but should **cache** results in memory for at least a few minutes or until restart to avoid heavy repeated introspection.
  - For PostgreSQL, prefer using database metadata (information_schema or system catalogs) rather than inferring from sample rows.
  - For MongoDB, simple field lists and types can be inferred from sample documents plus any existing JSON schema validators.
- **Frontend expectations:**
  - The frontend should **not** infer schema itself; it should call schema/metadata endpoints and render what the backend returns.

### 4.5 Redis value visibility policy

- **Sensitive vs safe keys:**
  - Treat keys under prefixes like `price:*`, `analysis:*`, `stock_list`, `market:overview`, `pipeline:*`, `news:*`, `ws:price:*`, `top_gainers`, `top_losers`, `alert_queue` as **safe for value preview**, unless they start containing secrets in the future.
  - Any keys that might contain secrets (API tokens, session data, user credentials) must **never** have their raw values shown; only show key name, type, and TTL.
- **Implementation:**
  - The backend should maintain an **allowlist** of prefixes for which value previews are allowed; all other prefixes should default to “name + TTL + type only.”
  - The UI should clearly label when a value is partially or fully hidden for security.

### 4.6 Audit logging (very important)

- All **manual add/update/delete operations** initiated from the Database Dashboard must be logged to an **`audit_log` collection** (in MongoDB) or an equivalent audit trail.
- Each audit entry should include at least:
  - `action` (e.g. `create`, `update`, `delete`)
  - `store` (e.g. `mongodb`, `postgres`, `redis`)
  - `collection_or_table` (e.g. `watchlist`, `portfolio`, `prices_daily`)
  - `record_id` (e.g. symbol, _id, primary key)
  - `timestamp`
  - `initiator` (e.g. `\"dashboard\"` / user-id if available)
  - `previous_value` and/or `new_value` when feasible (can be partial for large documents)
- The audit log itself should be **viewable (read-only)** from the dashboard with pagination and filters.

### 4.7 “Safe Mode” for production

- Implement a **“Safe Mode” toggle** in the dashboard (default: **ON**):
  - When **Safe Mode is ON**:
    - Destructive actions (e.g. bulk delete, Postgres row delete, dropping collections/tables) must be **disabled or require an additional explicit override**.
    - Any single-record delete must show a clear **confirmation dialog** describing what will be deleted.
  - When **Safe Mode is OFF**:
    - Destructive actions can be enabled but must still require confirmation dialogs.
- The Safe Mode state can be stored in a simple backend setting (e.g. `db_settings` collection in MongoDB) and loaded on dashboard initialization.

### 4.8 Alert storage location

- Store alert thresholds and dashboard-specific settings (e.g. Safe Mode, default refresh interval) in a dedicated **MongoDB configuration collection**, e.g. `db_settings` or `app_settings`.
- The backend should expose:
  - `GET /api/database/settings` — returns current DB-related settings (alert thresholds, Safe Mode state, default page size/refresh, etc.).
  - `PATCH /api/database/settings` — updates allowed fields with validation.
- Do **not** hard-code thresholds only in `.env` if they need to be changeable from the UI; `.env` can provide defaults, while the config collection stores the current values.

---

## 5. Data reference (what lives where)

- **MongoDB:** watchlist, portfolio, alerts, stock_data, price_history, extraction_log, quality_reports, pipeline_jobs, news_articles, backtest_results. TTL (90 days) on extraction_log, quality_reports, pipeline_jobs.
- **PostgreSQL:** prices_daily, technical_indicators, fundamentals_quarterly, shareholding_quarterly; optional TimescaleDB views.
- **Redis:** Cache keys by prefix (price:*, analysis:*, stock_list, market:overview, pipeline:*, etc.); values are JSON or strings; some keys may be sensitive—do not display raw values for those.

---

## 6. Deliverables

1. **Frontend:** One cohesive Database Dashboard page (with tabs or sections) that implements every requirement in Section 3 (activity monitoring, data structure overview, manual CRUD with inline edit, full visibility, error monitoring & alerts, connections & health, and user-friendly charts/search/filter).
2. **Backend:** New or extended endpoints required for the dashboard, with validation and error handling; no direct DB access from frontend.
3. **Documentation:** Short README or in-app help describing each section of the dashboard (what it shows, how to use it, and what each chart/setting means).

---

## 7. Summary checklist for the AI

Before considering the task complete, verify:

- [ ] **Activity monitoring** — real-time/live view of DB function; query/transaction/performance metrics where feasible.
- [ ] **Data structure & storage** — which data in which DB/table/collection; schema view; relationships (Postgres); data flow mapping.
- [ ] **Manual data management** — add/update/delete for watchlist, portfolio, alerts (and optionally news/backtest); inline editing; version/change tracking if possible.
- [ ] **Full visibility** — complete overview; incoming/outgoing data description; logs of DB operations and activity history.
- [ ] **Error monitoring & alerts** — visual display of errors/failed queries; threshold alerts (storage, query, connection); customizable alert settings and notification management.
- [ ] **Connections & system management** — active connections (sanitized); DB health (CPU, memory, storage where available); user/access note (single user).
- [ ] **User-friendly visualization** — clean UI; graphs/charts for performance and usage; search and filter on lists.
- [ ] All actions and data go through the backend; no direct DB connection from frontend; input validation and no secret leakage.

Implement the Database Dashboard to provide **complete transparency, control, and operational insight** over the database system, in a **powerful yet easy-to-understand** way.
