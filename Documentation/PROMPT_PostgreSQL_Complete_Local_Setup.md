# AI Prompt: Complete PostgreSQL for StockPulse (Local Setup, 100% Operational)

Use this prompt to have an AI (or yourself) complete all remaining work so that **PostgreSQL is 100% ready and fully operational** for the StockPulse website, with **Postgres running locally** on the developer's machine.

---

## 1. Context

- **Project:** StockPulse — Indian stock analysis platform (NSE/BSE). Backend: FastAPI (Python). Frontend: React. Other stores: MongoDB (primary entity store), Redis (cache).
- **PostgreSQL role:** Time-series and analytics layer only. It stores:
  - Daily OHLCV prices (+ delivery, VWAP, etc.)
  - Daily technical indicators (SMA, RSI, MACD, etc.)
  - Quarterly fundamentals (revenue, profit, ratios)
  - Quarterly shareholding (promoter, FII, DII)
- **Goal:** Local Postgres instance; all tables created; app connects at startup; data flows in from (1) NSE Bhavcopy API and (2) Groww pipeline; screener and time-series APIs use Postgres; health and dashboard show Postgres status. No cloud or paid services — local only.

---

## 2. What Already Exists (Do Not Duplicate)

- **Schema (SQL):** In `backend/setup_databases.py`, constant `POSTGRESQL_SCHEMA` defines four tables:
  - `prices_daily` — symbol, date (PK), open, high, low, close, last, prev_close, volume, turnover, total_trades, delivery_qty, delivery_pct, vwap, isin, series, created_at. Indexes on (date DESC), (symbol, date DESC).
  - `technical_indicators` — symbol, date (PK), sma_20/50/200, ema_12/26, rsi_14, macd, macd_signal, bollinger_upper/lower, atr_14, adx_14, obv, support_level, resistance_level, created_at. Indexes on (date DESC), (symbol, date DESC).
  - `fundamentals_quarterly` — symbol, period_end, period_type (PK), revenue, operating_profit, operating_margin, net_profit, net_profit_margin, eps, ebitda, total_assets, total_equity, total_debt, cash_and_equiv, operating_cash_flow, free_cash_flow, roe, debt_to_equity, interest_coverage, current_ratio, created_at. Indexes on period_end, (symbol, period_end), (period_type, period_end).
  - `shareholding_quarterly` — symbol, quarter_end (PK), promoter_holding, promoter_pledging, fii_holding, dii_holding, public_holding, promoter_holding_change, fii_holding_change, num_shareholders, mf_holding, insurance_holding, created_at. Indexes on quarter_end, (symbol, quarter_end).
- **Setup script:** `setup_databases.py` has `setup_postgresql()`: connects using `TIMESERIES_DSN`, optionally creates the database if missing, runs `POSTGRESQL_SCHEMA`, verifies tables and indexes. Optional: if TimescaleDB extension is present, converts `prices_daily` and `technical_indicators` to hypertables and adds compression policies. Use: `python setup_databases.py --postgres` (or `--check` for verify-only).
- **TimeSeriesStore (`backend/services/timeseries_store.py`):** Async class using `asyncpg`. Methods: `initialize()` (pool + verify tables), `close()`, `upsert_prices`, `get_prices`, `get_latest_price_date`, `get_price_count`, `get_weekly_prices`, `get_monthly_prices`, `upsert_technicals`, `get_technicals`, `upsert_fundamentals`, `get_fundamentals`, `upsert_shareholding`, `get_shareholding`, `get_screener_data` (4-table JOIN with COLUMN_MAP for filters), `get_stats`. Module-level `init_timeseries_store(dsn)` and `get_timeseries_store()`.
- **Server (`backend/server.py`):** Reads `TIMESERIES_DSN` from env, sets `_ts_store = None`. On startup, calls `_ts_store = await init_timeseries_store(timeseries_dsn)`. Endpoints: `GET /api/database/health` (includes Postgres status and table stats when `_ts_store` is initialized), `GET /api/timeseries/stats`, `GET /api/timeseries/prices/{symbol}` (query params: start_date, end_date, limit), `POST /api/screener` (tries `_ts_store.get_screener_data()` first, then fallback to in-memory). Bhavcopy download endpoint writes to Postgres via `_ts_store.upsert_prices(records)`. Shutdown closes `_ts_store`.
- **Pipeline service (`backend/services/pipeline_service.py`):** Accepts optional `ts_store: TimeSeriesStore`. After a run, calls `_persist_to_timeseries(job.results)`, which builds price/technical/fundamental/shareholding records from the Groww API result dict and calls `ts_store.upsert_prices`, `upsert_technicals`, `upsert_fundamentals`, `upsert_shareholding` as needed. Pipeline is initialized with `ts_store=_ts_store` in server startup.
- **Env:** `backend/.env.example` has `TIMESERIES_DSN=postgresql://localhost:5432/stockpulse_ts`. Backend expects `TIMESERIES_DSN` in `.env`.
- **Tests:** `backend/test_pipeline.py` has `--db-only` mode that checks Postgres (and Mongo, Redis); expects the four tables. Can use `TIMESERIES_DSN` from env.
- **Dashboard:** Database Dashboard service and routes use `ts_store` for table listing and stats when available.

---

## 3. What Must Be Done (Gaps and Completion Criteria)

- **Local Postgres install and database:**
  - Ensure PostgreSQL (e.g. 14+) is installed and running on the machine (e.g. `brew install postgresql` and `brew services start postgresql` on macOS, or equivalent).
  - Ensure a database exists for the app (e.g. `createdb stockpulse_ts`), or document that `setup_databases.py` can create it if the user connects to default `postgres` and DSN points to `stockpulse_ts`.
- **Configuration:**
  - Document or ensure `backend/.env` contains `TIMESERIES_DSN=postgresql://localhost:5432/stockpulse_ts` (or the correct port/user if not default). No cloud URLs — local only.
- **Schema and tables:**
  - Ensure the four tables (and only these, unless explicitly extending) are created by running `python setup_databases.py --postgres` from `backend/`. No table creation in `TimeSeriesStore.initialize()` — that only checks tables exist.
- **Connection and startup:**
  - App must call `init_timeseries_store(timeseries_dsn)` at startup and set the global `_ts_store`. If Postgres is unreachable, the app should log a warning and continue (no crash); `/api/database/health` will show Postgres as not_initialized or error. No requirement for fail-fast on Postgres for this local setup.
- **Data ingestion:**
  - **Bhavcopy:** The endpoint that downloads NSE Bhavcopy and calls `_ts_store.upsert_prices(records)` must receive records in the shape expected by `upsert_prices` (symbol, date, open, high, low, close, last, prev_close, volume, turnover, total_trades, delivery_qty/delivery_quantity, delivery_pct/delivery_percentage, vwap, isin, series). Ensure the Bhavcopy-to-record mapping fills these (or defaults) so inserts succeed.
  - **Groww pipeline:** When pipeline runs and `ts_store` is set, `_persist_to_timeseries` must run and map Groww response fields to the same shapes expected by `upsert_prices`, `upsert_technicals`, `upsert_fundamentals`, `upsert_shareholding`. Fix any missing or wrongly named fields so that no runtime errors occur and data appears in the four tables.
- **Screener:**
  - `get_screener_data` uses a 4-table JOIN (latest_prices, latest_tech, latest_fund, latest_share) with LEFT JOINs so that missing technicals/fundamentals/shareholding do not drop rows. Ensure the API path for screener uses this when `_ts_store` is initialized and returns `source: "postgresql"` when results come from Postgres. Fallback to in-memory when `_ts_store` is None or query fails.
- **Time-series API:**
  - `GET /api/timeseries/prices/{symbol}` must return data from `prices_daily` when Postgres is available (start_date, end_date, limit). Frontend or docs may assume this powers charts; ensure the response shape is consistent.
- **Health and stats:**
  - `GET /api/database/health` must include a `postgresql` section: when connected, status "connected" and table names with row counts (or sizes); when not connected, status "not_initialized" or "error" with a short message. `GET /api/timeseries/stats` must return table stats and pool info when store is initialized.
- **Optional — weekly/monthly aggregates:**
  - `get_weekly_prices` and `get_monthly_prices` in TimeSeriesStore query `prices_weekly` and `prices_monthly`. These are not in the standard schema; they are TimescaleDB continuous aggregates. For 100% local vanilla Postgres, either (a) implement fallbacks that aggregate from `prices_daily` (e.g. GROUP BY week/month) so the methods never fail and return data, or (b) clearly document that weekly/monthly require TimescaleDB and leave the methods returning empty list when views are absent. Prefer (a) for “100% operational” without TimescaleDB.
- **Optional — TimescaleDB:**
  - If the user later installs TimescaleDB, `setup_databases.py` already has logic to create hypertables and compression for `prices_daily` and `technical_indicators`. No change required for “100% complete” if staying vanilla Postgres; only ensure that path does not break when the extension is missing.
- **Documentation / runbook:**
  - Add or update a short runbook or section (e.g. in DEVELOPMENT_HISTORY or a dedicated one-paragraph note) that states: (1) Install and start Postgres locally, (2) Create database `stockpulse_ts` (or rely on setup script), (3) Set `TIMESERIES_DSN` in `backend/.env`, (4) Run `python setup_databases.py --postgres`, (5) Start the backend and verify `GET /api/database/health` shows Postgres connected. Optionally: run `python test_pipeline.py --db-only` and one Bhavcopy download to confirm writes.

---

## 4. Definition of “100% Complete and Operational” (Local Postgres)

- Postgres is installed and running locally; database `stockpulse_ts` exists; `TIMESERIES_DSN` is set in `backend/.env`.
- Running `python setup_databases.py --postgres` creates the four tables and indexes without errors.
- Backend starts without crashing; `_ts_store` is initialized when Postgres is reachable; health endpoint shows `postgresql.status: "connected"` and the four tables with counts/sizes.
- Bhavcopy download endpoint successfully writes to `prices_daily`; `GET /api/timeseries/prices/{symbol}` returns stored data when present.
- When the Groww pipeline runs with `ts_store` set, price/technical/fundamental/shareholding data are persisted to the four tables without errors.
- Screener endpoint uses Postgres when available and returns results with `source: "postgresql"`; fallback to in-memory when Postgres is unavailable.
- Optional: weekly/monthly price APIs work either via aggregation from `prices_daily` or are clearly documented as TimescaleDB-only.
- No new features are required beyond the above; no cloud or paid Postgres; everything runs locally.

---

## 5. Files to Touch (Checklist)

- `backend/.env.example` — ensure `TIMESERIES_DSN` is documented for local only (e.g. `postgresql://localhost:5432/stockpulse_ts`).
- `backend/setup_databases.py` — already has schema and optional TimescaleDB; only fix if something is wrong (e.g. DB creation with special characters, or connection string for local).
- `backend/services/timeseries_store.py` — ensure `initialize()` does not create tables (only verify); fix `get_weekly_prices` / `get_monthly_prices` to work without TimescaleDB (aggregate from `prices_daily`) or document that they require it.
- `backend/server.py` — ensure startup calls `init_timeseries_store(timeseries_dsn)` and assigns `_ts_store`; ensure Bhavcopy and screener and timeseries endpoints use `_ts_store` as described; ensure health and shutdown use `_ts_store`.
- `backend/services/pipeline_service.py` — ensure `_persist_to_timeseries` builds records that match the column names and types expected by `upsert_prices`, `upsert_technicals`, `upsert_fundamentals`, `upsert_shareholding` (e.g. date vs period_end vs quarter_end, and numeric nulls).
- `backend/test_pipeline.py` — ensure `--db-only` checks Postgres and the four tables; use `TIMESERIES_DSN` from env.
- Any short runbook or README section that explains the five-step local Postgres setup (install, create DB, set DSN, run setup script, start app and verify health).

---

## 6. Out of Scope for This Prompt

- Cloud or hosted Postgres (Supabase, Aiven, etc.); only local.
- Changing the four-table schema (e.g. adding new tables or columns) unless necessary to fix persistence or screener.
- MongoDB or Redis setup.
- Frontend UI changes beyond what is needed to display Postgres-backed screener or time-series data.
- Authentication or authorization for the API.
- TimescaleDB installation or tuning; optional and already partially handled in setup script.

---

## 7. Summary for the AI

You are to make PostgreSQL **fully operational locally** for StockPulse: correct env and setup steps, tables created via the existing script, app connecting at startup, Bhavcopy and Groww pipeline writing to the four tables, screener and time-series APIs reading from Postgres, health endpoint reflecting status. Fix any bugs in mapping or connection that prevent this. Optionally add weekly/monthly aggregation from `prices_daily` so those APIs work without TimescaleDB. Add minimal documentation so a developer can install Postgres, create the DB, set `TIMESERIES_DSN`, run the setup script, and confirm everything via health and one or two API calls. Do not add cloud Postgres or new major features; keep scope to “local Postgres 100% complete and operational.”
