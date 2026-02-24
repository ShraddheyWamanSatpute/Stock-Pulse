#!/usr/bin/env python3
"""
StockPulse Database Setup Script

Initializes all three database layers:
1. PostgreSQL - Creates time-series tables with indexes
2. MongoDB - Creates collections and ensures indexes
3. Redis - Verifies connectivity

Usage:
    python setup_databases.py              # Setup all databases
    python setup_databases.py --postgres   # PostgreSQL only
    python setup_databases.py --mongo      # MongoDB only
    python setup_databases.py --redis      # Redis check only
    python setup_databases.py --check      # Verify all connections without creating
"""

import asyncio
import argparse
Creates and verifies all database schemas:
- PostgreSQL: 4 time-series tables with indexes
- MongoDB: Indexes for 9 collections

Usage:
    python setup_databases.py
    python setup_databases.py --pg-only
    python setup_databases.py --mongo-only
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Load .env
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / '.env')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("setup_databases")


# ================================================================
# PostgreSQL Setup
# ================================================================

POSTGRES_TABLES = {
    "prices_daily": """
        CREATE TABLE IF NOT EXISTS prices_daily (
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
    """,

    "technical_indicators": """
        CREATE TABLE IF NOT EXISTS technical_indicators (
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
    """,

    "fundamentals_quarterly": """
        CREATE TABLE IF NOT EXISTS fundamentals_quarterly (
            symbol            VARCHAR(20) NOT NULL,
            period_end        DATE        NOT NULL,
            period_type       VARCHAR(10) NOT NULL DEFAULT 'quarterly',
            revenue           NUMERIC(18,2),
            operating_profit  NUMERIC(18,2),
            operating_margin  NUMERIC(8,4),
            net_profit        NUMERIC(18,2),
            net_profit_margin NUMERIC(8,4),
            eps               NUMERIC(10,2),
            ebitda            NUMERIC(18,2),
            total_assets      NUMERIC(18,2),
            total_equity      NUMERIC(18,2),
            total_debt        NUMERIC(18,2),
            cash_and_equiv    NUMERIC(18,2),
            operating_cash_flow NUMERIC(18,2),
            free_cash_flow    NUMERIC(18,2),
            roe               NUMERIC(8,4),
            debt_to_equity    NUMERIC(8,4),
            interest_coverage NUMERIC(8,2),
            current_ratio     NUMERIC(8,4),

            PRIMARY KEY (symbol, period_end, period_type)
        );
    """,

    "shareholding_quarterly": """
        CREATE TABLE IF NOT EXISTS shareholding_quarterly (
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
    """,
}

POSTGRES_INDEXES = [
    # Prices
    "CREATE INDEX IF NOT EXISTS idx_prices_date ON prices_daily (date DESC);",
    "CREATE INDEX IF NOT EXISTS idx_prices_symbol_date ON prices_daily (symbol, date DESC);",

    # Technical Indicators
    "CREATE INDEX IF NOT EXISTS idx_tech_symbol_date ON technical_indicators (symbol, date DESC);",

    # Fundamentals
    "CREATE INDEX IF NOT EXISTS idx_fund_symbol ON fundamentals_quarterly (symbol, period_end DESC);",
    "CREATE INDEX IF NOT EXISTS idx_fund_period_type ON fundamentals_quarterly (period_type, period_end DESC);",

    # Shareholding
    "CREATE INDEX IF NOT EXISTS idx_share_symbol ON shareholding_quarterly (symbol, quarter_end DESC);",
]


async def setup_postgresql(dsn: str, check_only: bool = False):
    """Create PostgreSQL tables and indexes."""
# ==========================================
# PostgreSQL Schema
# ==========================================

POSTGRESQL_SCHEMA = """
-- ==========================================
-- StockPulse Time-Series Schema
-- PostgreSQL 16+
-- ==========================================

-- Prices Daily: OHLCV + delivery data
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

-- Technical Indicators (computed daily from OHLCV)
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

-- Fundamentals Quarterly (income/BS/CF per quarter)
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

-- Shareholding Quarterly
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


async def setup_postgresql():
    """Create PostgreSQL tables and indexes."""
    dsn = os.environ.get('TIMESERIES_DSN', 'postgresql://localhost:5432/stockpulse_ts')
    
    try:
        import asyncpg
    except ImportError:
        logger.error("asyncpg not installed. Run: pip install asyncpg")
        return False

    try:
        # Try to connect to the database
        try:
            conn = await asyncpg.connect(dsn)
        except asyncpg.InvalidCatalogNameError:
            # Database doesn't exist - create it
            db_name = dsn.rsplit('/', 1)[-1].split('?')[0]
            base_dsn = dsn.rsplit('/', 1)[0] + '/postgres'
            logger.info(f"Database '{db_name}' doesn't exist, creating it...")

            sys_conn = await asyncpg.connect(base_dsn)
            await sys_conn.execute(f'CREATE DATABASE {db_name}')
            await sys_conn.close()
            logger.info(f"Created database '{db_name}'")

            conn = await asyncpg.connect(dsn)

        if check_only:
            # Just verify tables exist
            tables = await conn.fetch(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            )
            table_names = [t["table_name"] for t in tables]
            logger.info(f"PostgreSQL tables found: {table_names}")

            for expected in POSTGRES_TABLES.keys():
                if expected in table_names:
                    count = await conn.fetchval(f"SELECT COUNT(*) FROM {expected}")
                    logger.info(f"  - {expected}: {count} rows")
                else:
                    logger.warning(f"  - {expected}: MISSING")

            await conn.close()
            return True

        # Create tables
        for table_name, ddl in POSTGRES_TABLES.items():
            await conn.execute(ddl)
            logger.info(f"Created/verified table: {table_name}")

        # Create indexes
        for idx_sql in POSTGRES_INDEXES:
            await conn.execute(idx_sql)
        logger.info(f"Created/verified {len(POSTGRES_INDEXES)} indexes")

        # Verify
        tables = await conn.fetch(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        )
        table_names = [t["table_name"] for t in tables]
        logger.info(f"PostgreSQL setup complete. Tables: {table_names}")

        await conn.close()
        return True

    except Exception as e:
        logger.error(f"PostgreSQL setup failed: {e}")
        return False


# ================================================================
# MongoDB Setup
# ================================================================

MONGO_COLLECTIONS = {
    "watchlist": {
        "indexes": [
            {"keys": [("symbol", 1)], "unique": True},
        ]
    },
    "portfolio": {
        "indexes": [
            {"keys": [("symbol", 1)], "unique": True},
        ]
    },
    "alerts": {
        "indexes": [
            {"keys": [("id", 1)], "unique": True},
            {"keys": [("symbol", 1)]},
            {"keys": [("status", 1)]},
            {"keys": [("status", 1), ("symbol", 1)]},
        ]
    },
    "stock_data": {
        "indexes": [
            {"keys": [("symbol", 1)], "unique": True},
            {"keys": [("last_updated", -1)]},
            {"keys": [("stock_master.sector", 1)]},
            {"keys": [("stock_master.market_cap_category", 1)]},
        ]
    },
    "price_history": {
        "indexes": [
            {"keys": [("symbol", 1), ("date", -1)], "unique": True},
        ]
    },
    "extraction_log": {
        "indexes": [
            {"keys": [("symbol", 1), ("source", 1), ("started_at", -1)]},
            {"keys": [("status", 1)]},
        ]
    },
    "quality_reports": {
        "indexes": [
            {"keys": [("symbol", 1), ("generated_at", -1)]},
        ]
    },
    "pipeline_jobs": {
        "indexes": [
            {"keys": [("job_id", 1)], "unique": True},
            {"keys": [("created_at", -1)]},
            {"keys": [("status", 1)]},
        ]
    },
    "news_articles": {
        "indexes": [
            {"keys": [("published_date", -1)]},
            {"keys": [("related_stocks", 1)]},
            {"keys": [("sentiment", 1)]},
            {"keys": [("source", 1), ("published_date", -1)]},
        ]
    },
    "backtest_results": {
        "indexes": [
            {"keys": [("symbol", 1), ("strategy", 1), ("created_at", -1)]},
            {"keys": [("created_at", -1)]},
        ]
    },
}


async def setup_mongodb(mongo_url: str, db_name: str, check_only: bool = False):
    """Create MongoDB collections and indexes."""
    
    try:
        conn = await asyncpg.connect(dsn)
        logger.info(f"Connected to PostgreSQL: {dsn}")
        
        # Execute schema
        await conn.execute(POSTGRESQL_SCHEMA)
        
        # Verify tables
        tables = await conn.fetch(
            """SELECT table_name, 
                      (SELECT COUNT(*) FROM information_schema.columns c 
                       WHERE c.table_name = t.table_name AND c.table_schema = 'public') as col_count
               FROM information_schema.tables t
               WHERE table_schema = 'public'
               ORDER BY table_name"""
        )
        
        logger.info("PostgreSQL tables:")
        for t in tables:
            size = await conn.fetchval(
                f"SELECT pg_size_pretty(pg_total_relation_size('{t['table_name']}'))"
            )
            rows = await conn.fetchval(f"SELECT COUNT(*) FROM {t['table_name']}")
            logger.info(f"  ✅ {t['table_name']}: {t['col_count']} columns, {rows} rows, {size}")
        
        # Verify indexes
        indexes = await conn.fetch(
            """SELECT indexname, tablename
               FROM pg_indexes 
               WHERE schemaname = 'public'
               ORDER BY tablename, indexname"""
        )
        logger.info(f"PostgreSQL indexes: {len(indexes)} total")
        for idx in indexes:
            logger.info(f"  📇 {idx['tablename']}.{idx['indexname']}")
        
        await conn.close()
        logger.info("✅ PostgreSQL setup complete")
        return True
    except Exception as e:
        logger.error(f"❌ PostgreSQL setup failed: {e}")
        return False


async def setup_mongodb():
    """Create MongoDB indexes for all collections."""
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    db_name = os.environ.get('MONGO_DB_NAME', os.environ.get('DB_NAME', 'stockpulse'))
    
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
    except ImportError:
        logger.error("motor not installed. Run: pip install motor")
        return False

    try:
        client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=5000)

        # Test connection
        await client.admin.command('ping')
        logger.info(f"MongoDB connected: {mongo_url}")

        db = client[db_name]

        if check_only:
            collections = await db.list_collection_names()
            logger.info(f"MongoDB collections found: {collections}")

            for expected in MONGO_COLLECTIONS.keys():
                if expected in collections:
                    count = await db[expected].count_documents({})
                    logger.info(f"  - {expected}: {count} documents")
                else:
                    logger.warning(f"  - {expected}: MISSING")

            client.close()
            return True

        # Create collections and indexes
        existing = await db.list_collection_names()

        for coll_name, config in MONGO_COLLECTIONS.items():
            # Create collection if it doesn't exist
            if coll_name not in existing:
                await db.create_collection(coll_name)
                logger.info(f"Created collection: {coll_name}")
            else:
                logger.info(f"Collection exists: {coll_name}")

            # Create indexes
            collection = db[coll_name]
            for idx_config in config["indexes"]:
                try:
                    kwargs = {}
                    if idx_config.get("unique"):
                        kwargs["unique"] = True

                    await collection.create_index(idx_config["keys"], **kwargs)
                except Exception as e:
                    logger.warning(f"Index creation note for {coll_name}: {e}")

            logger.info(f"  Indexes created for {coll_name}: {len(config['indexes'])}")

        # Verify
        collections = await db.list_collection_names()
        logger.info(f"MongoDB setup complete. Collections: {sorted(collections)}")

        client.close()
        return True

    except Exception as e:
        logger.error(f"MongoDB setup failed: {e}")
        return False


# ================================================================
# Redis Check
# ================================================================

def check_redis(redis_url: str):
    """Verify Redis connectivity."""
    try:
        import redis
    except ImportError:
        logger.error("redis not installed. Run: pip install redis")
        return False

    try:
        r = redis.Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=3,
        )
        r.ping()

        info = r.info("memory")
        logger.info(f"Redis connected: {redis_url}")
        logger.info(f"  Memory used: {info.get('used_memory_human', 'N/A')}")
        logger.info(f"  Keys: {r.dbsize()}")
        logger.info(f"  Version: {info.get('redis_version', 'N/A')}")

        r.close()
        return True

    except Exception as e:
        logger.warning(f"Redis not available: {e}")
        logger.info("  Note: Redis is optional. The app falls back to in-memory cache.")
        return False


# ================================================================
# Filesystem Setup
# ================================================================

def setup_filesystem():
    """Create required directories for file storage."""
    dirs = {
        "reports": os.environ.get("REPORTS_DIR", "./reports"),
        "bhavcopy": os.environ.get("BHAVCOPY_DIR", "./data/bhavcopy"),
        "models": os.environ.get("MODELS_DIR", "./models"),
        "backups": os.environ.get("BACKUPS_DIR", "./backups"),
    }

    for name, path in dirs.items():
        full_path = ROOT_DIR / path
        full_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Directory ready: {name} -> {full_path}")

    return True


# ================================================================
# Main
# ================================================================

async def main():
    parser = argparse.ArgumentParser(description="StockPulse Database Setup")
    parser.add_argument("--postgres", action="store_true", help="Setup PostgreSQL only")
    parser.add_argument("--mongo", action="store_true", help="Setup MongoDB only")
    parser.add_argument("--redis", action="store_true", help="Check Redis only")
    parser.add_argument("--check", action="store_true", help="Check all connections (no modifications)")
    args = parser.parse_args()

    # If no specific flags, do everything
    do_all = not (args.postgres or args.mongo or args.redis)

    logger.info("=" * 60)
    logger.info("StockPulse Database Setup")
    logger.info("=" * 60)

    results = {}

    # PostgreSQL
    if do_all or args.postgres:
        logger.info("\n--- PostgreSQL Time-Series Store ---")
        dsn = os.environ.get("TIMESERIES_DSN", "postgresql://localhost:5432/stockpulse_ts")
        results["postgresql"] = await setup_postgresql(dsn, check_only=args.check)

    # MongoDB
    if do_all or args.mongo:
        logger.info("\n--- MongoDB Entity Store ---")
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        db_name = os.environ.get("MONGO_DB_NAME", "stockpulse")
        results["mongodb"] = await setup_mongodb(mongo_url, db_name, check_only=args.check)

    # Redis
    if do_all or args.redis:
        logger.info("\n--- Redis Cache Layer ---")
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
        results["redis"] = check_redis(redis_url)

    # Filesystem
    if do_all:
        logger.info("\n--- Filesystem Directories ---")
        results["filesystem"] = setup_filesystem()

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Setup Summary")
    logger.info("=" * 60)

    all_ok = True
    for db, status in results.items():
        icon = "pass" if status else "FAIL"
        logger.info(f"  [{icon}] {db}")
        if not status and db != "redis":  # Redis is optional
            all_ok = False

    if all_ok:
        logger.info("\nAll databases ready! You can start the server with: uvicorn server:app --reload")
    else:
        logger.warning("\nSome databases could not be set up. Check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
    
    try:
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        
        # Ping to verify connection
        await client.admin.command('ping')
        logger.info(f"Connected to MongoDB: {mongo_url}/{db_name}")
        
        # ---- watchlist ----
        await db.watchlist.create_index("symbol", unique=True)
        logger.info("  ✅ watchlist: index on symbol (unique)")
        
        # ---- portfolio ----
        await db.portfolio.create_index("symbol", unique=True)
        logger.info("  ✅ portfolio: index on symbol (unique)")
        
        # ---- alerts ----
        await db.alerts.create_index("id", unique=True)
        await db.alerts.create_index("symbol")
        await db.alerts.create_index("status")
        logger.info("  ✅ alerts: indexes on id (unique), symbol, status")
        
        # ---- stock_data ----
        await db.stock_data.create_index("symbol", unique=True)
        await db.stock_data.create_index("last_updated", sparse=True)
        await db.stock_data.create_index("stock_master.sector", sparse=True)
        await db.stock_data.create_index("stock_master.market_cap_category", sparse=True)
        logger.info("  ✅ stock_data: indexes on symbol (unique), last_updated, sector, cap_category")
        
        # ---- price_history (MongoDB legacy — will migrate to PostgreSQL) ----
        await db.price_history.create_index(
            [("symbol", 1), ("date", -1)], unique=True
        )
        logger.info("  ✅ price_history: compound index on (symbol, date)")
        
        # ---- extraction_log ----
        await db.extraction_log.create_index(
            [("symbol", 1), ("source", 1), ("started_at", -1)]
        )
        logger.info("  ✅ extraction_log: compound index on (symbol, source, started_at)")
        
        # ---- quality_reports ----
        await db.quality_reports.create_index(
            [("symbol", 1), ("generated_at", -1)]
        )
        logger.info("  ✅ quality_reports: compound index on (symbol, generated_at)")
        
        # ---- pipeline_jobs ----
        await db.pipeline_jobs.create_index("job_id", unique=True)
        await db.pipeline_jobs.create_index("created_at", sparse=True)
        logger.info("  ✅ pipeline_jobs: indexes on job_id (unique), created_at")
        
        # ---- news_articles (NEW) ----
        await db.news_articles.create_index("published_date", sparse=True)
        await db.news_articles.create_index("related_stocks", sparse=True)
        await db.news_articles.create_index("sentiment", sparse=True)
        logger.info("  ✅ news_articles: indexes on published_date, related_stocks, sentiment")
        
        # ---- backtest_results (NEW) ----
        await db.backtest_results.create_index(
            [("symbol", 1), ("strategy", 1), ("created_at", -1)]
        )
        logger.info("  ✅ backtest_results: compound index on (symbol, strategy, created_at)")
        
        # List all collections
        collections = await db.list_collection_names()
        logger.info(f"MongoDB collections: {sorted(collections)}")
        
        client.close()
        logger.info("✅ MongoDB setup complete")
        return True
    except Exception as e:
        logger.error(f"❌ MongoDB setup failed: {e}")
        return False


def setup_filesystem():
    """Create organized directory structure."""
    base = Path(__file__).parent
    dirs = [
        base / "reports",
        base / "data" / "bhavcopy",
        base / "models",
        base / "cache" / "html",
        base / "backups",
    ]
    
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        logger.info(f"  📁 {d.relative_to(base)}/")
    
    # Add .gitkeep to empty dirs so they're tracked by git
    for d in dirs:
        gitkeep = d / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()
    
    logger.info("✅ Filesystem directories created")
    return True


async def main():
    """Run all database setup steps."""
    mode = sys.argv[1] if len(sys.argv) > 1 else "--all"
    
    results = {}
    
    logger.info("=" * 60)
    logger.info("StockPulse Database Setup")
    logger.info("=" * 60)
    
    if mode in ("--all", "--pg-only"):
        logger.info("\n📊 Setting up PostgreSQL...")
        results["postgresql"] = await setup_postgresql()
    
    if mode in ("--all", "--mongo-only"):
        logger.info("\n📦 Setting up MongoDB...")
        results["mongodb"] = await setup_mongodb()
    
    if mode in ("--all", "--fs-only"):
        logger.info("\n📁 Setting up Filesystem...")
        results["filesystem"] = setup_filesystem()
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Setup Summary:")
    for name, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        logger.info(f"  {name}: {status}")
    logger.info("=" * 60)
    
    if all(results.values()):
        logger.info("All database setup completed successfully! 🎉")
        return 0
    else:
        logger.error("Some setup steps failed. Check logs above.")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
