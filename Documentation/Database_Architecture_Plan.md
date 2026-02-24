# Stock-Pulse Hybrid Database Architecture Plan

## Current State Assessment

The system currently uses **three databases** in various stages of implementation:

| Database | Status | Current Usage |
|----------|--------|---------------|
| **MongoDB** (Motor async) | Active | Watchlist, portfolio, alerts, pipeline jobs, stock_data, extraction logs, quality reports |
| **Redis** | Active (with in-memory fallback) | Caching live prices (60s TTL), analysis results (300s TTL), stock lists (300s TTL), pipeline status (30s TTL) |
| **PostgreSQL** (asyncpg) | Scaffolded, partially active | Time-series OHLCV prices, technical indicators, quarterly fundamentals, quarterly shareholding |

The documentation (architecture docs) recommends PostgreSQL+TimescaleDB as the primary database, but the actual implementation has evolved around MongoDB as the primary store. This plan reconciles the existing codebase with the architectural vision, defining exactly which database handles what, and why.

---

## The Hybrid Architecture: 4 Database Layers

```
┌─────────────────────────────────────────────────────────────┐
│                      STOCK-PULSE                             │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │  Redis    │  │ MongoDB  │  │PostgreSQL│  │ Filesystem  │  │
│  │ (Cache)   │  │ (Entity) │  │(TimeSeries│  │ (Files)    │  │
│  │          │  │          │  │+Analytics)│  │            │  │
│  └────┬─────┘  └────┬─────┘  └─────┬────┘  └─────┬──────┘  │
│       │              │              │              │          │
│  Hot data       Documents &    Time-indexed     PDFs,       │
│  60s-300s TTL   flexible       OHLCV, indicators bhavcopies │
│  session state  schema         fundamentals     model files  │
│  pub/sub        user data      shareholding     logs         │
│                 extraction     cross-table joins              │
└─────────────────────────────────────────────────────────────┘
```

---

## DATABASE 1: Redis — Hot Cache & Real-Time Layer

**Purpose:** Sub-millisecond access to frequently changing data. Acts as L1/L2 cache and real-time pub/sub backbone.

**Why Redis:** The system already has Redis integrated (`backend/services/cache_service.py`). Live stock prices change every few seconds during market hours. Hitting MongoDB or PostgreSQL for every price lookup would add 5-50ms latency per query. Redis delivers <1ms reads.

### What Goes in Redis

| Data Type | Cache Key Pattern | TTL | Justification |
|-----------|-------------------|-----|---------------|
| **Live stock quotes** | `price:{SYMBOL}` | 60s | Prices update every 1-5 seconds during market hours. 60s TTL prevents stale data while reducing API calls |
| **Analysis results** | `analysis:{SYMBOL}` | 300s (5 min) | Scoring engine computations are CPU-heavy. Cache result until underlying data changes |
| **Stock list (all stocks)** | `stock_list` | 300s | The 40+ stock mock data set doesn't change frequently. Avoids regenerating on every request |
| **Market overview** | `market:overview` | 60s | Index values (NIFTY, SENSEX, BANK NIFTY, VIX) refresh every minute |
| **Pipeline status** | `pipeline:status` | 30s | Scheduler state, current job progress — ephemeral data |
| **News feed** | `news:latest` | 180s (3 min) | News doesn't change second-by-second |
| **WebSocket price cache** | `ws:price:{SYMBOL}` | 10s | PriceBroadcaster sends to clients every 5-10s, cache latest for new subscribers |
| **Screener results** | `screener:{hash}` | 120s | Same screener query returns same results for 2 minutes |
| **ML predictions** | `ml:prediction:{SYMBOL}` | 3600s (1 hour) | ML inference is expensive, predictions valid until next batch run |
| **Session/rate limit counters** | `rate:{source}` | Varies | Track API call counts per external source to respect rate limits |

### Redis Data Structures Used

| Structure | Use Case |
|-----------|----------|
| **STRING** (with JSON) | All cache entries above — `SETEX key ttl json_value` |
| **HASH** | Store individual stock fields: `HSET stock:RELIANCE price 2450 change 1.2` — enables partial reads |
| **PUB/SUB** | Real-time price broadcasting — publisher pushes to `channel:prices`, WebSocket manager subscribes |
| **SORTED SET** | Top movers: `ZADD top_gainers score symbol` — sorted by price change percentage |
| **LIST** | Alert notification queue: `RPUSH alert_queue notification_json` — alerts service pops and processes |

### Redis Configuration

```
# From .env
REDIS_URL=redis://localhost:6379/0

# Recommended settings for this scale
maxmemory 256mb
maxmemory-policy allkeys-lru    # Evict least recently used when full
save ""                          # Disable RDB persistence (cache only)
appendonly no                    # No AOF (data is reconstructible)
```

**Memory estimate:** ~150-200 stocks x ~2KB per cached entry = ~400KB for stock data. With all cache types, expect 10-50MB usage. 256MB is generous overhead.

---

## DATABASE 2: MongoDB — Entity Store & Document Layer

**Purpose:** Flexible schema storage for user data, extraction pipeline records, and document-oriented entities where the shape of data varies per source or changes over time.

**Why MongoDB:** The system already uses Motor (async MongoDB driver) extensively in `server.py`. MongoDB excels here because:
1. **Schema flexibility:** The `StockDataRecord` in `extraction_models.py` has 13 category dictionaries that vary per stock and per source. Relational columns would require constant migrations.
2. **User data with nested objects:** Watchlist items have optional nested fields (target_price, stop_loss, notes). Portfolio holdings get enriched with computed P&L. These are natural document shapes.
3. **Pipeline job records:** Each job has variable-length error arrays, nested result objects — perfect for documents.
4. **Extraction audit trail:** Each extraction log has different fields_extracted, fields_failed arrays per run.

### What Goes in MongoDB

#### Collection: `watchlist`
```
Purpose: User's stock watchlist
Current: ACTIVE in server.py lines 566-630

Document shape:
{
  "id": "uuid",
  "symbol": "RELIANCE",
  "name": "Reliance Industries Ltd",
  "added_date": "2026-02-23T...",
  "target_price": 2800.0,       // optional
  "stop_loss": 2300.0,          // optional
  "notes": "Good Q3 results",   // optional
  "alerts_enabled": true
}

Indexes:
  - { "symbol": 1 }  (unique)
```

#### Collection: `portfolio`
```
Purpose: User's portfolio holdings
Current: ACTIVE in server.py lines 634-751

Document shape:
{
  "id": "uuid",
  "symbol": "TCS",
  "name": "TCS Ltd",
  "quantity": 10,
  "avg_buy_price": 3500.0,
  "buy_date": "2025-06-15"
}

Indexes:
  - { "symbol": 1 }  (unique)
```

#### Collection: `alerts`
```
Purpose: Price alert definitions and trigger state
Current: ACTIVE via AlertsService (alerts_service.py)

Document shape:
{
  "id": "alert_abc123",
  "symbol": "INFY",
  "stock_name": "Infosys Ltd",
  "condition": "price_above",
  "target_value": 1900.0,
  "priority": "high",
  "status": "active",
  "created_at": "2026-02-23T...",
  "triggered_at": null,
  "trigger_price": null,
  "trigger_count": 0,
  "repeat": false,
  "expires_at": null
}

Indexes:
  - { "id": 1 }       (unique)
  - { "symbol": 1 }
  - { "status": 1 }
```

#### Collection: `stock_data`
```
Purpose: Complete extracted data for each stock (all 160 fields from field_definitions.py)
Current: ACTIVE via MongoDBStore (mongodb_store.py)

Document shape:
{
  "symbol": "RELIANCE",
  "company_name": "Reliance Industries Limited",
  "last_updated": "2026-02-23T...",
  "stock_master": { "sector": "Energy", "industry": "Oil & Gas", "market_cap_category": "Large", ... },
  "price_volume": { "current_price": 2450.0, "volume": 12500000, ... },
  "derived_metrics": { "price_to_median_pe": 1.2, ... },
  "income_statement": { "revenue_ttm": 950000, "net_profit": 72000, ... },
  "balance_sheet": { "total_assets": 1800000, "total_debt": 320000, ... },
  "cash_flow": { "operating_cash_flow": 95000, "free_cash_flow": 62000, ... },
  "financial_ratios": { "roe": 0.22, "debt_to_equity": 0.45, ... },
  "valuation": { "pe_ratio": 24.5, "pb_ratio": 2.8, ... },
  "shareholding": { "promoter_holding": 50.3, "fii_holding": 23.5, ... },
  "corporate_actions": { ... },
  "news_sentiment": { ... },
  "technical": { "rsi_14": 55, "sma_50": 2380, ... },
  "qualitative_metadata": { ... },
  "field_availability": { "revenue_ttm": true, "roe": true, ... },
  "field_last_updated": { "revenue_ttm": "2026-02-23T...", ... }
}

Indexes:
  - { "symbol": 1 }                        (unique)
  - { "last_updated": -1 }
  - { "stock_master.sector": 1 }
  - { "stock_master.market_cap_category": 1 }
```

#### Collection: `extraction_log`
```
Purpose: Audit trail of every extraction attempt
Current: ACTIVE via MongoDBStore

Document shape:
{
  "source": "screener_in",
  "symbol": "TCS",
  "status": "success",
  "fields_extracted": ["revenue_ttm", "net_profit", "roe", ...],
  "fields_failed": ["interest_coverage"],
  "started_at": "2026-02-23T10:00:00",
  "completed_at": "2026-02-23T10:00:02",
  "duration_ms": 2100,
  "retry_count": 0
}

Indexes:
  - { "symbol": 1, "source": 1, "started_at": -1 }
```

#### Collection: `quality_reports`
```
Purpose: Data quality assessment per stock
Current: ACTIVE via MongoDBStore

Document shape:
{
  "symbol": "HDFCBANK",
  "generated_at": "2026-02-23T...",
  "completeness_score": 92.5,
  "freshness_score": 88.0,
  "source_agreement_score": 95.0,
  "validation_score": 90.0,
  "overall_confidence": 91.4,
  "missing_critical_fields": ["peg_ratio"],
  "stale_fields": ["shareholding_q3"],
  "field_coverage_by_category": { "fundamentals": 95, "technicals": 88, ... }
}

Indexes:
  - { "symbol": 1, "generated_at": -1 }
```

#### Collection: `pipeline_jobs`
```
Purpose: Pipeline execution records
Current: ACTIVE via both PipelineOrchestrator and DataPipelineService

Document shape:
{
  "job_id": "abc123",
  "pipeline_type": "quotes",
  "status": "success",
  "symbols": ["RELIANCE", "TCS", "INFY", ...],
  "created_at": "2026-02-23T...",
  "started_at": "2026-02-23T...",
  "completed_at": "2026-02-23T...",
  "total_symbols": 150,
  "processed_symbols": 148,
  "successful_symbols": 145,
  "failed_symbols": 3,
  "errors": [{ "symbol": "PAYTM", "error": "timeout", ... }],
  "duration_seconds": 45.2
}

Indexes:
  - { "job_id": 1 }     (unique)
  - { "created_at": -1 }
```

#### Collection: `news_articles` (NEW — recommended)
```
Purpose: Persisted news articles with sentiment scores
Currently: news is generated from mock_data.py, not persisted

Document shape:
{
  "id": "uuid",
  "title": "Reliance Q3 results beat estimates",
  "summary": "...",
  "source": "moneycontrol",
  "url": "https://...",
  "published_date": "2026-02-23T...",
  "sentiment": "POSITIVE",
  "sentiment_score": 0.85,
  "related_stocks": ["RELIANCE"],
  "full_text": "...",         // optional, for NLP
  "tags": ["earnings", "oil_gas"]
}

Indexes:
  - { "published_date": -1 }
  - { "related_stocks": 1 }
  - { "sentiment": 1 }
```

#### Collection: `backtest_results` (NEW — recommended)
```
Purpose: Persist backtest results for historical comparison
Currently: backtest results are computed on-the-fly and not saved

Document shape:
{
  "id": "uuid",
  "symbol": "RELIANCE",
  "strategy": "sma_crossover",
  "parameters": { "fast_period": 20, "slow_period": 50 },
  "initial_capital": 100000,
  "final_value": 125000,
  "total_return_percent": 25.0,
  "sharpe_ratio": 1.45,
  "max_drawdown": -12.3,
  "win_rate": 58.0,
  "total_trades": 24,
  "created_at": "2026-02-23T...",
  "trades": [...]
}

Indexes:
  - { "symbol": 1, "strategy": 1, "created_at": -1 }
```

### MongoDB Configuration

```
# From .env
MONGO_URL=mongodb://localhost:27017
MONGO_DB_NAME=stockpulse

# Recommended settings
storage:
  wiredTiger:
    engineConfig:
      cacheSizeGB: 0.5    # Single user, 500MB is plenty
```

---

## DATABASE 3: PostgreSQL — Time-Series & Analytical Layer

**Purpose:** High-performance storage and querying of time-indexed numerical data. This is where cross-table analytical queries (JOINs between prices, technicals, and fundamentals) run — something MongoDB handles poorly.

**Why PostgreSQL:** The `timeseries_store.py` already implements this with asyncpg. The architectural docs recommend PostgreSQL+TimescaleDB. The key advantage is SQL's ability to run complex analytical queries like the `get_screener_data()` method — which JOINs latest prices with technical indicators and fundamentals in a single query. MongoDB can't do this efficiently.

### Schema: 4 Tables

#### Table: `prices_daily`
```sql
-- Already implemented in timeseries_store.py:74-145
-- OHLCV data from NSE Bhavcopy, Yahoo Finance, Groww API

CREATE TABLE prices_daily (
    symbol       VARCHAR(20)   NOT NULL,
    date         DATE          NOT NULL,
    open         NUMERIC(12,2),
    high         NUMERIC(12,2),
    low          NUMERIC(12,2),
    close        NUMERIC(12,2),
    last         NUMERIC(12,2),
    prev_close   NUMERIC(12,2),
    volume       BIGINT,
    turnover     NUMERIC(18,2),
    total_trades INTEGER,
    delivery_qty BIGINT,
    delivery_pct NUMERIC(6,2),
    vwap         NUMERIC(12,2),
    isin         VARCHAR(12),
    series       VARCHAR(5)    DEFAULT 'EQ',

    PRIMARY KEY (symbol, date)
);

-- Performance indexes
CREATE INDEX idx_prices_date ON prices_daily (date DESC);
CREATE INDEX idx_prices_symbol_date ON prices_daily (symbol, date DESC);

-- Data volume estimate:
-- 200 stocks x 250 trading days x 5 years = 250,000 rows
-- At ~200 bytes/row = ~50MB (trivial)
```

**Data sources feeding this table:**
- NSE Bhavcopy (EOD) via `nse_bhavcopy_extractor.py`
- Yahoo Finance historical via `market_data_service.py`
- Groww API quotes via `grow_extractor.py`

#### Table: `technical_indicators`
```sql
-- Already implemented in timeseries_store.py:214-296
-- Computed daily from prices_daily data

CREATE TABLE technical_indicators (
    symbol           VARCHAR(20)   NOT NULL,
    date             DATE          NOT NULL,
    sma_20           NUMERIC(12,2),
    sma_50           NUMERIC(12,2),
    sma_200          NUMERIC(12,2),
    ema_12           NUMERIC(12,2),
    ema_26           NUMERIC(12,2),
    rsi_14           NUMERIC(6,2),
    macd             NUMERIC(12,4),
    macd_signal      NUMERIC(12,4),
    bollinger_upper  NUMERIC(12,2),
    bollinger_lower  NUMERIC(12,2),
    atr_14           NUMERIC(12,4),
    adx_14           NUMERIC(6,2),
    obv              BIGINT,
    support_level    NUMERIC(12,2),
    resistance_level NUMERIC(12,2),

    PRIMARY KEY (symbol, date)
);

CREATE INDEX idx_tech_symbol_date ON technical_indicators (symbol, date DESC);
```

**Data source:** Computed by `technical_calculator.py` from `prices_daily` data after each Bhavcopy import.

#### Table: `fundamentals_quarterly`
```sql
-- Already implemented in timeseries_store.py:300-377
-- Quarterly/annual financial data from Screener.in, Groww

CREATE TABLE fundamentals_quarterly (
    symbol           VARCHAR(20) NOT NULL,
    period_end       DATE        NOT NULL,
    period_type      VARCHAR(10) NOT NULL DEFAULT 'quarterly',
    revenue          NUMERIC(18,2),
    operating_profit NUMERIC(18,2),
    operating_margin NUMERIC(8,4),
    net_profit       NUMERIC(18,2),
    net_profit_margin NUMERIC(8,4),
    eps              NUMERIC(10,2),
    ebitda           NUMERIC(18,2),
    total_assets     NUMERIC(18,2),
    total_equity     NUMERIC(18,2),
    total_debt       NUMERIC(18,2),
    cash_and_equiv   NUMERIC(18,2),
    operating_cash_flow NUMERIC(18,2),
    free_cash_flow   NUMERIC(18,2),
    roe              NUMERIC(8,4),
    debt_to_equity   NUMERIC(8,4),
    interest_coverage NUMERIC(8,2),
    current_ratio    NUMERIC(8,4),

    PRIMARY KEY (symbol, period_end, period_type)
);

CREATE INDEX idx_fund_symbol ON fundamentals_quarterly (symbol, period_end DESC);

-- Data volume: 200 stocks x 40 quarters (10 years) = 8,000 rows
```

**Data sources:**
- Screener.in via `screener_extractor.py`
- Groww API fundamentals via `grow_extractor.py`

#### Table: `shareholding_quarterly`
```sql
-- Already implemented in timeseries_store.py:382-448
-- Quarterly shareholding pattern from NSE/BSE

CREATE TABLE shareholding_quarterly (
    symbol                  VARCHAR(20) NOT NULL,
    quarter_end             DATE        NOT NULL,
    promoter_holding        NUMERIC(6,2),
    promoter_pledging       NUMERIC(6,2),
    fii_holding             NUMERIC(6,2),
    dii_holding             NUMERIC(6,2),
    public_holding          NUMERIC(6,2),
    promoter_holding_change NUMERIC(6,2),
    fii_holding_change      NUMERIC(6,2),
    num_shareholders        INTEGER,
    mf_holding              NUMERIC(6,2),
    insurance_holding       NUMERIC(6,2),

    PRIMARY KEY (symbol, quarter_end)
);

CREATE INDEX idx_share_symbol ON shareholding_quarterly (symbol, quarter_end DESC);

-- Data volume: 200 stocks x 28 quarters (7 years) = 5,600 rows
```

### The Key Analytical Query (Why PostgreSQL matters)

This query from `timeseries_store.py:454-509` is impossible in MongoDB without aggregation pipelines that perform poorly:

```sql
-- Cross-join latest prices with technicals for the screener
WITH latest_prices AS (
    SELECT DISTINCT ON (symbol)
        symbol, date, close, volume, prev_close
    FROM prices_daily
    ORDER BY symbol, date DESC
),
latest_tech AS (
    SELECT DISTINCT ON (symbol)
        symbol, rsi_14, sma_50, sma_200, macd, macd_signal
    FROM technical_indicators
    ORDER BY symbol, date DESC
)
SELECT
    p.symbol, p.close, p.volume,
    t.rsi_14, t.sma_50, t.sma_200, t.macd
FROM latest_prices p
LEFT JOIN latest_tech t ON p.symbol = t.symbol
WHERE t.rsi_14 BETWEEN 30 AND 70
ORDER BY p.symbol;
```

### Future: TimescaleDB Extension (Recommended)

When data volume grows, add TimescaleDB for automatic partitioning:

```sql
-- Convert prices_daily to a hypertable
SELECT create_hypertable('prices_daily', 'date',
    chunk_time_interval => INTERVAL '1 month',
    migrate_data => true
);

-- Enable compression for data older than 30 days
ALTER TABLE prices_daily SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol',
    timescaledb.compress_orderby = 'date DESC'
);

SELECT add_compression_policy('prices_daily', INTERVAL '30 days');
```

### PostgreSQL Configuration

```
# From .env
TIMESERIES_DSN=postgresql://localhost:5432/stockpulse_ts

# Recommended for single-user workload
shared_buffers = 256MB
work_mem = 64MB
effective_cache_size = 512MB
maintenance_work_mem = 128MB
```

---

## DATABASE 4: Filesystem — Files & Artifacts

**Purpose:** Store non-queryable binary artifacts.

| File Type | Location | Generated By |
|-----------|----------|-------------|
| PDF reports | `./reports/` | `pdf_service.py` |
| NSE Bhavcopy CSVs | `./data/bhavcopy/` | `nse_bhavcopy_extractor.py` |
| ML model checkpoints | `./models/` | Future ML training pipeline |
| Scraped HTML (debug) | `./cache/html/` | Future scraper debug mode |
| Backup dumps | `./backups/` | `pg_dump` and `mongodump` scripts |

---

## Data Flow: Which Database Handles What

```
External APIs (Yahoo, Groww, NSE, Screener.in)
         |
         v
+---------------------+
|  Data Extraction     |
|  Pipeline            |
|  (orchestrator.py)   |
+-----+-------+-------+
      |       |
      |       v
      |  +-------------+
      |  |  MongoDB     |  <-- stock_data (160 fields, document per stock)
      |  |              |  <-- extraction_log (audit trail)
      |  |              |  <-- quality_reports
      |  +-------------+
      |
      v
+-------------+
| PostgreSQL   |  <-- prices_daily (OHLCV time-series)
|              |  <-- technical_indicators (computed daily)
|              |  <-- fundamentals_quarterly
|              |  <-- shareholding_quarterly
+------+------+
       |
       v (analytics queries)
+-------------+
| Redis Cache  |  <-- cached analysis results
|              |  <-- cached stock quotes
|              |  <-- WebSocket price buffer
+------+------+
       |
       v
+-------------+
| Frontend     |  <-- Dashboard, Analyzer, Screener, etc.
| (React)      |
+-------------+
```

### Read Path (When frontend requests data)

1. **Dashboard load** -> Redis (`market:overview`, `stock_list`) -> if miss -> MongoDB/PostgreSQL -> cache in Redis
2. **Stock analysis** -> Redis (`analysis:{SYMBOL}`) -> if miss -> MongoDB (`stock_data`) + PostgreSQL (prices, technicals) -> compute score -> cache in Redis
3. **Screener query** -> Redis (`screener:{hash}`) -> if miss -> PostgreSQL (JOIN prices + technicals + fundamentals) -> cache in Redis
4. **Watchlist** -> MongoDB (`watchlist` collection) directly -- small dataset, no caching needed
5. **Portfolio** -> MongoDB (`portfolio` collection) + Redis (live prices for current value computation)
6. **Historical chart** -> PostgreSQL (`prices_daily`) -> Redis for most recent data
7. **Backtest** -> PostgreSQL (`prices_daily` for historical OHLCV) -> compute on-the-fly -> optionally save to MongoDB

### Write Path (When data enters the system)

1. **Groww API extraction** -> MongoDB (`stock_data` upsert, `pipeline_jobs` insert) + PostgreSQL (if price/fundamental data)
2. **NSE Bhavcopy download** -> PostgreSQL (`prices_daily` upsert) -> compute technicals -> PostgreSQL (`technical_indicators` upsert)
3. **Screener.in extraction** -> MongoDB (`stock_data` update with financials) + PostgreSQL (`fundamentals_quarterly` upsert)
4. **User adds to watchlist** -> MongoDB (`watchlist` insert)
5. **User creates alert** -> MongoDB (`alerts` insert)
6. **WebSocket price update** -> Redis (pub/sub + price cache)

---

## Why This Hybrid Over a Single Database

| Scenario | Single-DB Problem | Hybrid Solution |
|----------|-------------------|-----------------|
| "Show me all stocks where RSI < 30 AND debt_to_equity < 0.5" | MongoDB can't efficiently JOIN time-series (technical_indicators) with entity data (stock_data) | PostgreSQL handles the JOIN in <100ms with proper indexes |
| "What's the current price of RELIANCE?" (called 100x/minute via WebSocket) | Hitting any disk-based DB 100x/min adds latency | Redis returns in <1ms, TTL auto-refreshes |
| "Store extracted data where Groww returns 50 fields and Screener returns 80 different fields" | PostgreSQL requires a column for every possible field, constant ALTER TABLE | MongoDB stores variable-shape documents natively |
| "Show 5 years of daily OHLCV for TCS with SMA overlay" | MongoDB stores time-series inefficiently, range queries are slow | PostgreSQL with (symbol, date) index returns ordered data instantly |
| "User adds custom notes to watchlist" | PostgreSQL would need a JSON column or extra table for unstructured fields | MongoDB documents naturally accommodate optional nested fields |

---

## Migration Steps — Implementation Status

### Phase 1: Formalize Existing Setup -- COMPLETED
- [x] MongoDB indexes added to `server.py` startup via `_ensure_mongodb_indexes()` — all 10 collections indexed
- [x] Created `setup_databases.py` script — initializes PostgreSQL tables, MongoDB collections + indexes, Redis check, filesystem dirs
- [x] `.env.example` updated with `REDIS_URL`, `TIMESERIES_DSN`, `GROW_TOTP_TOKEN`, `GROW_SECRET_KEY`, filesystem paths

### Phase 2: Wire PostgreSQL into Pipeline -- COMPLETED
- [x] `DataPipelineService` now accepts `ts_store` parameter
- [x] `_persist_to_timeseries()` method extracts price/technical/fundamental/shareholding data from Groww API results and upserts into PostgreSQL
- [x] `server.py` startup passes `_ts_store` to `init_pipeline_service()`
- [x] Data flows: Extraction -> MongoDB (entity store) + PostgreSQL (time-series)

### Phase 3: Add New Collections -- COMPLETED
- [x] `news_articles` collection — full CRUD endpoints: `GET/POST /api/news/articles`, bulk insert, single article GET/DELETE, stats/summary
- [x] `backtest_results` collection — auto-persist on `/api/backtest/run`, history endpoint `GET /api/backtest/history`, single result GET/DELETE
- [x] MongoDB indexes created at startup for both collections

### Phase 4: Optimize Screener to Use PostgreSQL -- COMPLETED
- [x] `TimeSeriesStore.get_screener_data()` enhanced with full 4-table JOIN (prices + technicals + fundamentals + shareholding)
- [x] Supports all filter operators: gt, lt, gte, lte, eq, between
- [x] Supports 30+ filterable metrics across all 4 tables
- [x] `/api/screener` endpoint tries PostgreSQL first with Redis caching (2 min TTL), falls back to in-memory filtering
- [x] Response includes `source` field indicating which path was used

### Phase 4.5: Redis Pub/Sub for WebSocket -- COMPLETED
- [x] `PriceBroadcaster` now publishes to Redis `channel:prices` via pub/sub
- [x] Per-symbol price cache: `ws:price:{SYMBOL}` with 10s TTL
- [x] Graceful degradation if Redis unavailable

### Phase 5: TimescaleDB (Future — When Scale Demands)
- [ ] Install TimescaleDB extension
- [ ] Convert `prices_daily` to hypertable
- [ ] Enable compression for data older than 30 days
- [ ] Add continuous aggregates for weekly/monthly OHLCV rollups

---

## Summary Table

| Data Domain | Database | Justification |
|-------------|----------|---------------|
| Live prices, cached scores, session data | **Redis** | Sub-ms latency, TTL-based expiry, pub/sub for WebSocket |
| Watchlist, portfolio, alerts | **MongoDB** | User-facing CRUD with flexible schema, optional fields |
| Stock entity data (160 fields) | **MongoDB** | Variable shape per stock/source, progressive population |
| Extraction logs, quality reports | **MongoDB** | Append-only documents with variable structure |
| Pipeline jobs | **MongoDB** | Nested error arrays, variable result objects |
| News articles | **MongoDB** | Semi-structured, variable tags/stocks, full-text search |
| Backtest results | **MongoDB** | Nested trade arrays, variable strategy parameters |
| Daily OHLCV prices | **PostgreSQL** | Time-series queries, range scans, JOINs with technicals |
| Technical indicators | **PostgreSQL** | Computed from prices, queried together with prices via JOIN |
| Quarterly fundamentals | **PostgreSQL** | Structured numeric data, cross-stock comparison queries |
| Quarterly shareholding | **PostgreSQL** | Structured numeric data, trend analysis queries |
| Screener analytics | **PostgreSQL** | Complex multi-table JOINs with WHERE clauses |
| PDF reports, bhavcopies | **Filesystem** | Binary files, not queryable |
