#!/usr/bin/env python3
"""
StockPulse Database Setup Script

Creates and verifies all three database layers + filesystem directories:
  1. PostgreSQL  – 4 time-series tables with indexes
  2. MongoDB     – 10 collections with indexes
  3. Redis       – Connectivity verification
  4. Filesystem  – Required local directories

Usage:
    python setup_databases.py              # Setup ALL databases + filesystem
    python setup_databases.py --postgres   # PostgreSQL only
    python setup_databases.py --mongo      # MongoDB only
    python setup_databases.py --redis      # Redis check only
    python setup_databases.py --check      # Verify all connections (read-only)
"""

import asyncio
import argparse
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the same directory as this script
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("setup_databases")


# ================================================================
#  PostgreSQL Schema (raw SQL executed as a single batch)
# ================================================================

POSTGRESQL_SCHEMA = """
-- ==============================================
-- StockPulse Time-Series Schema  (PostgreSQL 14+)
-- ==============================================

-- 1. Prices Daily: OHLCV + delivery data
CREATE TABLE IF NOT EXISTS prices_daily (
    symbol          VARCHAR(20)     NOT NULL,
    date            DATE            NOT NULL,
    open            NUMERIC(12,2),
    high            NUMERIC(12,2),
    low             NUMERIC(12,2),
    close           NUMERIC(12,2),
    last            NUMERIC(12,2),
    prev_close      NUMERIC(12,2),
    volume          BIGINT,
    turnover        NUMERIC(18,2),
    total_trades    INTEGER,
    delivery_qty    BIGINT,
    delivery_pct    NUMERIC(6,2),
    vwap            NUMERIC(12,2),
    isin            VARCHAR(12),
    series          VARCHAR(5)      DEFAULT 'EQ',
    created_at      TIMESTAMPTZ     DEFAULT now(),
    PRIMARY KEY (symbol, date)
);

CREATE INDEX IF NOT EXISTS idx_prices_date ON prices_daily (date DESC);
CREATE INDEX IF NOT EXISTS idx_prices_symbol_date ON prices_daily (symbol, date DESC);

-- 2. Technical Indicators (computed daily from OHLCV)
CREATE TABLE IF NOT EXISTS technical_indicators (
    symbol           VARCHAR(20)     NOT NULL,
    date             DATE            NOT NULL,
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
    created_at       TIMESTAMPTZ     DEFAULT now(),
    PRIMARY KEY (symbol, date)
);

CREATE INDEX IF NOT EXISTS idx_tech_date ON technical_indicators (date DESC);
CREATE INDEX IF NOT EXISTS idx_tech_symbol_date ON technical_indicators (symbol, date DESC);

-- 3. Fundamentals Quarterly (income / balance-sheet / cash-flow)
CREATE TABLE IF NOT EXISTS fundamentals_quarterly (
    symbol              VARCHAR(20)     NOT NULL,
    period_end          DATE            NOT NULL,
    period_type         VARCHAR(10)     NOT NULL DEFAULT 'quarterly',
    revenue             NUMERIC(18,2),
    operating_profit    NUMERIC(18,2),
    operating_margin    NUMERIC(8,4),
    net_profit          NUMERIC(18,2),
    net_profit_margin   NUMERIC(8,4),
    eps                 NUMERIC(10,2),
    ebitda              NUMERIC(18,2),
    total_assets        NUMERIC(18,2),
    total_equity        NUMERIC(18,2),
    total_debt          NUMERIC(18,2),
    cash_and_equiv      NUMERIC(18,2),
    operating_cash_flow NUMERIC(18,2),
    free_cash_flow      NUMERIC(18,2),
    roe                 NUMERIC(8,4),
    debt_to_equity      NUMERIC(8,4),
    interest_coverage   NUMERIC(8,2),
    current_ratio       NUMERIC(8,4),
    created_at          TIMESTAMPTZ     DEFAULT now(),
    PRIMARY KEY (symbol, period_end, period_type)
);

CREATE INDEX IF NOT EXISTS idx_fund_date ON fundamentals_quarterly (period_end DESC);
CREATE INDEX IF NOT EXISTS idx_fund_symbol ON fundamentals_quarterly (symbol, period_end DESC);
CREATE INDEX IF NOT EXISTS idx_fund_period_type ON fundamentals_quarterly (period_type, period_end DESC);

-- 4. Shareholding Quarterly
CREATE TABLE IF NOT EXISTS shareholding_quarterly (
    symbol                  VARCHAR(20)     NOT NULL,
    quarter_end             DATE            NOT NULL,
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
    created_at              TIMESTAMPTZ     DEFAULT now(),
    PRIMARY KEY (symbol, quarter_end)
);

CREATE INDEX IF NOT EXISTS idx_share_date ON shareholding_quarterly (quarter_end DESC);
CREATE INDEX IF NOT EXISTS idx_share_symbol ON shareholding_quarterly (symbol, quarter_end DESC);
"""


# ================================================================
#  MongoDB Collection + Index Definitions
# ================================================================

MONGO_COLLECTIONS = {
    "watchlist": [
        {"keys": [("symbol", 1)], "unique": True},
    ],
    "portfolio": [
        {"keys": [("symbol", 1)], "unique": True},
    ],
    "alerts": [
        {"keys": [("id", 1)], "unique": True},
        {"keys": [("symbol", 1)]},
        {"keys": [("status", 1)]},
        {"keys": [("status", 1), ("symbol", 1)]},
    ],
    "stock_data": [
        {"keys": [("symbol", 1)], "unique": True},
        {"keys": [("last_updated", -1)]},
        {"keys": [("stock_master.sector", 1)]},
        {"keys": [("stock_master.market_cap_category", 1)]},
    ],
    "price_history": [
        {"keys": [("symbol", 1), ("date", -1)], "unique": True},
    ],
    "extraction_log": [
        {"keys": [("symbol", 1), ("source", 1), ("started_at", -1)]},
        {"keys": [("status", 1)]},
    ],
    "quality_reports": [
        {"keys": [("symbol", 1), ("generated_at", -1)]},
    ],
    "pipeline_jobs": [
        {"keys": [("job_id", 1)], "unique": True},
        {"keys": [("created_at", -1)]},
        {"keys": [("status", 1)]},
    ],
    "news_articles": [
        {"keys": [("published_date", -1)]},
        {"keys": [("related_stocks", 1)]},
        {"keys": [("sentiment", 1)]},
        {"keys": [("source", 1), ("published_date", -1)]},
    ],
    "backtest_results": [
        {"keys": [("symbol", 1), ("strategy", 1), ("created_at", -1)]},
        {"keys": [("created_at", -1)]},
    ],
}


# ================================================================
#  PostgreSQL Setup
# ================================================================

async def setup_postgresql(check_only: bool = False) -> bool:
    """Create PostgreSQL tables and indexes, or just verify they exist."""
    dsn = os.environ.get("TIMESERIES_DSN", "postgresql://localhost:5432/stockpulse_ts")

    try:
        import asyncpg
    except ImportError:
        logger.error("asyncpg not installed. Run: pip install asyncpg")
        return False

    try:
        # Try to connect; auto-create the database if it doesn't exist
        try:
            conn = await asyncpg.connect(dsn)
        except asyncpg.InvalidCatalogNameError:
            db_name = dsn.rsplit("/", 1)[-1].split("?")[0]
            base_dsn = dsn.rsplit("/", 1)[0] + "/postgres"
            logger.info(f"Database '{db_name}' doesn't exist — creating it...")
            sys_conn = await asyncpg.connect(base_dsn)
            await sys_conn.execute(f"CREATE DATABASE {db_name}")
            await sys_conn.close()
            logger.info(f"Created database '{db_name}'")
            conn = await asyncpg.connect(dsn)

        logger.info(f"Connected to PostgreSQL: {dsn}")

        if check_only:
            tables = await conn.fetch(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            )
            table_names = [t["table_name"] for t in tables]
            expected = ["prices_daily", "technical_indicators", "fundamentals_quarterly", "shareholding_quarterly"]
            logger.info("PostgreSQL tables:")
            for name in expected:
                if name in table_names:
                    rows = await conn.fetchval(f"SELECT COUNT(*) FROM {name}")
                    size = await conn.fetchval(f"SELECT pg_size_pretty(pg_total_relation_size('{name}'))")
                    logger.info(f"  [OK] {name}: {rows} rows, {size}")
                else:
                    logger.warning(f"  [MISSING] {name}")
            await conn.close()
            return True

        # Execute the full schema (idempotent via IF NOT EXISTS)
        await conn.execute(POSTGRESQL_SCHEMA)

        # Verify
        tables = await conn.fetch(
            """SELECT table_name,
                      (SELECT COUNT(*) FROM information_schema.columns c
                       WHERE c.table_name = t.table_name AND c.table_schema = 'public') as col_count
               FROM information_schema.tables t
               WHERE table_schema = 'public'
               ORDER BY table_name"""
        )
        logger.info("PostgreSQL tables created/verified:")
        for t in tables:
            rows = await conn.fetchval(f"SELECT COUNT(*) FROM {t['table_name']}")
            size = await conn.fetchval(f"SELECT pg_size_pretty(pg_total_relation_size('{t['table_name']}'))")
            logger.info(f"  [OK] {t['table_name']}: {t['col_count']} columns, {rows} rows, {size}")

        indexes = await conn.fetch(
            """SELECT indexname, tablename FROM pg_indexes
               WHERE schemaname = 'public' ORDER BY tablename, indexname"""
        )
        logger.info(f"Indexes: {len(indexes)} total")
        for idx in indexes:
            logger.info(f"  {idx['tablename']}.{idx['indexname']}")

        await conn.close()
        logger.info("PostgreSQL setup complete")
        return True

    except Exception as e:
        logger.error(f"PostgreSQL setup failed: {e}")
        return False


# ================================================================
#  MongoDB Setup
# ================================================================

async def setup_mongodb(check_only: bool = False) -> bool:
    """Create MongoDB collections and indexes, or just verify they exist."""
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("MONGO_DB_NAME", os.environ.get("DB_NAME", "stockpulse"))

    try:
        from motor.motor_asyncio import AsyncIOMotorClient
    except ImportError:
        logger.error("motor not installed. Run: pip install motor")
        return False

    try:
        client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=5000)
        await client.admin.command("ping")
        logger.info(f"Connected to MongoDB: {mongo_url}/{db_name}")

        db = client[db_name]

        if check_only:
            existing = await db.list_collection_names()
            logger.info("MongoDB collections:")
            for name in MONGO_COLLECTIONS:
                if name in existing:
                    count = await db[name].count_documents({})
                    logger.info(f"  [OK] {name}: {count} documents")
                else:
                    logger.warning(f"  [MISSING] {name}")
            client.close()
            return True

        existing = await db.list_collection_names()

        for coll_name, indexes in MONGO_COLLECTIONS.items():
            # Create collection if it doesn't exist
            if coll_name not in existing:
                await db.create_collection(coll_name)
                logger.info(f"  Created collection: {coll_name}")
            else:
                logger.info(f"  Collection exists: {coll_name}")

            # Create indexes
            collection = db[coll_name]
            for idx_conf in indexes:
                try:
                    kwargs = {}
                    if idx_conf.get("unique"):
                        kwargs["unique"] = True
                    await collection.create_index(idx_conf["keys"], **kwargs)
                except Exception as e:
                    logger.warning(f"  Index note for {coll_name}: {e}")

            logger.info(f"    {len(indexes)} index(es) ensured")

        # Final verification
        collections = await db.list_collection_names()
        logger.info(f"MongoDB setup complete. Collections: {sorted(collections)}")
        client.close()
        return True

    except Exception as e:
        logger.error(f"MongoDB setup failed: {e}")
        return False


# ================================================================
#  Redis Check
# ================================================================

def check_redis() -> bool:
    """Verify Redis connectivity and report basic info."""
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")

    try:
        import redis
    except ImportError:
        logger.error("redis not installed. Run: pip install redis")
        return False

    try:
        r = redis.Redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=3)
        r.ping()

        info = r.info("memory")
        logger.info(f"Redis connected: {redis_url}")
        logger.info(f"  Version : {info.get('redis_version', 'N/A')}")
        logger.info(f"  Memory  : {info.get('used_memory_human', 'N/A')}")
        logger.info(f"  Keys    : {r.dbsize()}")

        r.close()
        return True

    except Exception as e:
        logger.warning(f"Redis not available: {e}")
        logger.info("  (Redis is optional — the app falls back to in-memory cache.)")
        return False


# ================================================================
#  Filesystem Setup
# ================================================================

def setup_filesystem() -> bool:
    """Create required local directories for binary artifacts."""
    dirs = [
        ROOT_DIR / os.environ.get("REPORTS_DIR", "./reports"),
        ROOT_DIR / os.environ.get("BHAVCOPY_DIR", "./data/bhavcopy"),
        ROOT_DIR / os.environ.get("MODELS_DIR", "./models"),
        ROOT_DIR / os.environ.get("BACKUPS_DIR", "./backups"),
        ROOT_DIR / "cache" / "html",
    ]

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        # Add .gitkeep so Git tracks empty directories
        gitkeep = d / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()
        logger.info(f"  Directory ready: {d.relative_to(ROOT_DIR)}/")

    logger.info("Filesystem directories created")
    return True


# ================================================================
#  Main
# ================================================================

async def main() -> int:
    parser = argparse.ArgumentParser(description="StockPulse Database Setup")
    parser.add_argument("--postgres", action="store_true", help="Setup PostgreSQL only")
    parser.add_argument("--mongo", action="store_true", help="Setup MongoDB only")
    parser.add_argument("--redis", action="store_true", help="Check Redis only")
    parser.add_argument("--check", action="store_true", help="Verify all connections (read-only)")
    args = parser.parse_args()

    # If no specific flag is passed, do everything
    do_all = not (args.postgres or args.mongo or args.redis)

    logger.info("=" * 60)
    logger.info("StockPulse Database Setup")
    logger.info("=" * 60)

    results = {}

    # --- PostgreSQL ---
    if do_all or args.postgres:
        logger.info("\n--- PostgreSQL Time-Series Store ---")
        results["postgresql"] = await setup_postgresql(check_only=args.check)

    # --- MongoDB ---
    if do_all or args.mongo:
        logger.info("\n--- MongoDB Entity Store ---")
        results["mongodb"] = await setup_mongodb(check_only=args.check)

    # --- Redis ---
    if do_all or args.redis:
        logger.info("\n--- Redis Cache Layer ---")
        results["redis"] = check_redis()

    # --- Filesystem ---
    if do_all:
        logger.info("\n--- Filesystem Directories ---")
        results["filesystem"] = setup_filesystem()

    # --- Summary ---
    logger.info("\n" + "=" * 60)
    logger.info("Setup Summary")
    logger.info("=" * 60)

    all_ok = True
    for name, ok in results.items():
        status = "OK" if ok else "FAIL"
        logger.info(f"  [{status}] {name}")
        # Redis is optional; only count required databases as failures
        if not ok and name != "redis":
            all_ok = False

    if all_ok:
        logger.info("\nAll databases ready! Start the server with:")
        logger.info("  cd backend && uvicorn server:app --reload")
    else:
        logger.warning("\nSome databases failed. Check the errors above.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
