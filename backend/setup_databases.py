#!/usr/bin/env python3
"""
StockPulse Database Setup Script

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

# Load .env
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / '.env')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("setup_databases")


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
