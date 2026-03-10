# PostgreSQL Database — Current Work Status

> **Generated:** March 9, 2026  
> **Last updated:** Post-fix — bugs and gaps below have been addressed.  
> **Scope:** Backend PostgreSQL time-series store (14 tables), TimeSeriesStore, pipeline, jobs, API.

---

## 1. Work completed (done)

### Schema & setup

- **14 tables** defined and created in `backend/setup_databases.py`:
  - `prices_daily`, `derived_metrics_daily`, `technical_indicators`, `ml_features_daily`, `risk_metrics`, `valuation_daily`, `fundamentals_quarterly`, `shareholding_quarterly`, `corporate_actions`, `macro_indicators`, `derivatives_daily`, `intraday_metrics`, `weekly_metrics`, `schema_migrations`
- **43+ indexes** (symbol, date, symbol+date, etc.) for all tables.
- **Auto-create database** if missing (`InvalidCatalogNameError` → create `stockpulse_ts` then connect).
- **Optional TimescaleDB**: when extension is present, `prices_daily` and `technical_indicators` converted to hypertables + compression policies.

### TimeSeriesStore (`backend/services/timeseries_store.py`)

- **Connection pool**: asyncpg, min 2 / max 10, 30s command timeout.
- **12 upsert methods** (ON CONFLICT DO UPDATE): prices, technicals, fundamentals, shareholding, derived_metrics, valuation, ml_features, risk_metrics, macro_indicators, derivatives, intraday_metrics, weekly_metrics.
- **Corporate actions**: `upsert_corporate_action` with `UNIQUE(symbol, action_type, action_date)` and ON CONFLICT DO UPDATE (no duplicate rows on re-run).
- **_parse_date()** helper used across all upsert/get methods — empty-string dates no longer cause `strptime` crashes.
- **17+ read methods**: get_prices (includes adjusted_close), get_weekly_prices, get_monthly_prices (plain-Postgres GROUP BY + ARRAY_AGG when TimescaleDB views absent), get_technicals, get_fundamentals, get_shareholding, get_derived_metrics, get_valuation, get_ml_features, get_risk_metrics, get_corporate_actions, get_macro_indicators, get_derivatives, get_intraday_metrics, get_weekly_metrics, get_screener_data, get_stats.
- **Weekly/monthly aggregation**: Implemented with plain-Postgres GROUP BY + ARRAY_AGG (correct open/close/high/low/volume); no dependency on TimescaleDB continuous aggregates.
- **Screener**: `get_screener_data` does 7-table JOIN with ~50 filter/sort keys in `COLUMN_MAP`.

### Data flow into PostgreSQL

- **Bhavcopy** (`server.py`): writes to `prices_daily` via `_ts_store.upsert_prices(records)` (including `adjusted_close` when provided).
- **Pipeline** (`pipeline_service._persist_to_timeseries`): builds and writes to 9 categories; pipeline price record building includes `adjusted_close`; corporate_actions via `upsert_corporate_action`.
- **Derived metrics job** (`jobs/derive_metrics.py`): reads `prices_daily`, writes `derived_metrics_daily` and `weekly_metrics` (when `--weekly`).
- **Post-pipeline hook**: Auto-derivation after pipeline run — `compute_derived_metrics()` is called for freshly extracted symbols.
- **Macro indicators job** (`jobs/macro_indicators_job.py`): fetches USD/INR, Brent, gold, copper (and optional steel) via yfinance; optional RBI repo/CPI/IIP via env (`MACRO_RBI_REPO_RATE`, `MACRO_CPI_INFLATION`, `MACRO_IIP_GROWTH`). Upserts into `macro_indicators`. Trigger: `POST /api/jobs/run/macro-indicators?days=90` or `python -m jobs.macro_indicators_job --days 90`.
- **Derivatives job** (`jobs/derivatives_job.py`): tries NSE F&O bhavcopy download; on failure, fallback: one row per symbol/date from `prices_daily` (NULL F&O fields). Upserts into `derivatives_daily`. Trigger: `POST /api/jobs/run/derivatives` (optional `?date=YYYY-MM-DD` or `?days=N`) or `python -m jobs.derivatives_job [--date YYYY-MM-DD] [--days N]`.
- **Intraday metrics job** (`jobs/intraday_metrics_job.py`): builds EOD snapshots from `technical_indicators` + `prices_daily` (one row per symbol per day, timestamp = 15:30 IST). Fills `rsi_hourly`, `macd_crossover_hourly`, `vwap_intraday`, `advance_decline_ratio`. Upserts into `intraday_metrics`. Trigger: `POST /api/jobs/run/intraday-metrics?days=1` or `python -m jobs.intraday_metrics_job [--days N]`.

### API & control

- **14 time-series GET endpoints** under `/api/timeseries/`*.
- **Screener**: `POST /api/screener` uses PostgreSQL 7-table JOIN when `_ts_store` is initialized.
- **Health**, **PG Control** (status, toggle, resources, health); frontend `PostgresControl.jsx`.

### Documentation

- `PROMPT_PostgreSQL_Complete_Local_Setup.md` — setup and architecture.
- `DEVELOPMENT_HISTORY.md` — PostgreSQL expansion.
- Doc mismatches corrected: `corporate_actions` and `macro_indicators` PK/constraint descriptions match actual schema.

---

## 2. Bugs fixed (completed)


| Issue                                                                     | Fix                                                                                                                 |
| ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| Empty string dates crash (`strptime("")` → ValueError)                    | Added `_parse_date()` helper; replaced all 18 occurrences across upsert/get methods                                 |
| `adjusted_close` never written (schema had it, code didn’t)               | Added to `upsert_prices` INSERT (17 cols), `get_prices` SELECT, and pipeline price record building                  |
| Weekly/monthly aggregation broken (queried nonexistent TimescaleDB views) | Rewrote with plain-Postgres GROUP BY + ARRAY_AGG; verified correct open/close/high/low/volume                       |
| Corporate actions duplicate on re-run (INSERT-only, SERIAL PK)            | Added `UNIQUE(symbol, action_type, action_date)`; converted to `upsert_corporate_action` with ON CONFLICT DO UPDATE |
| No auto-derivation after pipeline                                         | Post-pipeline hook calls `compute_derived_metrics()` for freshly extracted symbols                                  |
| Dead code (derived_records list never populated)                          | Removed unused list and unreachable upsert block                                                                    |
| Doc mismatches (corporate_actions PK, macro PK)                           | Updated both documentation files to match actual schema                                                             |


---

## 3. Test results


| Test                                                          | Result |
| ------------------------------------------------------------- | ------ |
| `setup_databases.py --check` — 14 tables, 43+ indexes         | PASS   |
| `test_pipeline.py --db-only` — all 14 tables verified         | PASS   |
| `upsert_prices` with `adjusted_close`                         | PASS   |
| Empty-string date → graceful skip (0 records, no crash)       | PASS   |
| Weekly aggregation (3 weeks, correct OHLCV)                   | PASS   |
| Monthly aggregation (2 months, correct OHLCV with assertions) | PASS   |
| Corporate action dedup (same id on re-upsert)                 | PASS   |
| Derived metrics auto-computation                              | PASS   |
| Stats endpoint — 14 tables                                    | PASS   |
| PG Control — status, resources, health                        | PASS   |
| All 14 REST time-series endpoints                             | PASS   |
| Screener (7-table JOIN)                                       | PASS   |


---

## 4. Macro, derivatives, intraday — implemented

The three previously “pending” tables are now populated by dedicated jobs:

| Table / Job            | Source / logic                                                                 | Trigger (API)                                      | CLI                                      |
| ---------------------- | ------------------------------------------------------------------------------ | -------------------------------------------------- | ---------------------------------------- |
| **macro_indicators**   | yfinance: USD/INR, Brent, gold, copper; optional env: RBI repo, CPI, IIP       | `POST /api/jobs/run/macro-indicators?days=90`      | `python -m jobs.macro_indicators_job`     |
| **derivatives_daily**  | NSE F&O bhavcopy when available; else fallback from `prices_daily` (symbol+date)| `POST /api/jobs/run/derivatives` or `?date=...&days=` | `python -m jobs.derivatives_job`           |
| **intraday_metrics**  | EOD snapshots from `technical_indicators` + `prices_daily`; advance/decline ratio | `POST /api/jobs/run/intraday-metrics?days=1`        | `python -m jobs.intraday_metrics_job`     |

Optional env (macro): `MACRO_RBI_REPO_RATE`, `MACRO_CPI_INFLATION`, `MACRO_IIP_GROWTH`, `MACRO_STEEL_TICKER`.


---

## 5. Quick reference


| Layer      | File(s)                                                 | Status                                                                            |
| ---------- | ------------------------------------------------------- | --------------------------------------------------------------------------------- |
| Schema     | `setup_databases.py` (POSTGRESQL_SCHEMA)                | Done (14 tables, 43+ indexes)                                                     |
| Store      | `timeseries_store.py`                                   | Done (12 upserts + upsert_corporate_action, _parse_date, plain-PG weekly/monthly) |
| Pipeline   | `pipeline_service.py` (_persist_to_timeseries)          | Done (9 categories + post-pipeline derivation hook)                               |
| Derivation | `jobs/derive_metrics.py`                                | Done; auto-invoked after pipeline                                                 |
| Macro/Derivatives/Intraday | `jobs/macro_indicators_job.py`, `derivatives_job.py`, `intraday_metrics_job.py` | Done; trigger via `POST /api/jobs/run/*` or CLI   |
| API        | `server.py` (timeseries + health + screener + jobs)     | Done                                                                              |
| PG Control | `pg_control_service.py`, routes, PostgresControl.jsx    | Done                                                                              |
| Tests      | `test_pipeline.py` (--db-only), manual/automated checks | PASS (see §3)                                                                     |


---

**Conclusion:** PostgreSQL layer is complete for current scope: schema, store (with all listed fixes), pipeline persistence, auto-derivation after pipeline, weekly/monthly aggregation without TimescaleDB, corporate action dedup, and docs aligned with schema. Macro indicators, derivatives, and intraday metrics are populated by the three jobs above (yfinance + optional RBI for macro; NSE F&O or prices fallback for derivatives; EOD snapshots from daily data for intraday).