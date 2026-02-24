"""
PostgreSQL Time-Series Store for StockPulse

Handles storage and retrieval of time-series data:
- Daily OHLCV prices (prices_daily table)
- Technical indicators (technical_indicators table)
- Quarterly fundamentals (fundamentals_quarterly table)
- Quarterly shareholding (shareholding_quarterly table)

Uses asyncpg for high-performance async PostgreSQL access.
"""

import asyncpg
import logging
from datetime import datetime, date, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TimeSeriesStore:
    """
    Async PostgreSQL storage for time-series financial data.
    
    Uses asyncpg connection pool for efficient async operations.
    Designed to complement MongoDB (entity store) for time-indexed data.
    """
    
    def __init__(self, dsn: str = "postgresql://localhost:5432/stockpulse_ts"):
        self._dsn = dsn
        self._pool: Optional[asyncpg.Pool] = None
        self._is_initialized = False
    
    async def initialize(self):
        """Create connection pool and verify schema."""
        if self._is_initialized:
            return
        
        try:
            self._pool = await asyncpg.create_pool(
                self._dsn,
                min_size=2,
                max_size=10,
                command_timeout=30,
            )
            # Verify connection
            async with self._pool.acquire() as conn:
                version = await conn.fetchval("SELECT version()")
                logger.info(f"✅ PostgreSQL time-series store connected: {version[:50]}...")
                
                # Verify tables exist
                tables = await conn.fetch(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
                )
                table_names = [t["table_name"] for t in tables]
                logger.info(f"Available tables: {table_names}")
            
            self._is_initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize time-series store: {e}")
            raise
    
    async def close(self):
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
        self._is_initialized = False
    
    # ========================
    # Prices Daily
    # ========================
    
    async def upsert_prices(self, records: List[Dict[str, Any]]) -> int:
        """
        Insert or update daily price records.
        
        Args:
            records: List of dicts with keys matching BhavcopyData.to_dict()
                     Required: symbol, date, open, high, low, close, volume
        
        Returns:
            Number of records upserted.
        """
        if not records:
            return 0
        
        query = """
            INSERT INTO prices_daily (
                symbol, date, open, high, low, close, last, prev_close,
                volume, turnover, total_trades, delivery_qty, delivery_pct,
                vwap, isin, series
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
            ON CONFLICT (symbol, date)
            DO UPDATE SET
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                last = EXCLUDED.last,
                prev_close = EXCLUDED.prev_close,
                volume = EXCLUDED.volume,
                turnover = EXCLUDED.turnover,
                total_trades = EXCLUDED.total_trades,
                delivery_qty = EXCLUDED.delivery_qty,
                delivery_pct = EXCLUDED.delivery_pct,
                vwap = EXCLUDED.vwap,
                isin = EXCLUDED.isin,
                series = EXCLUDED.series
        """
        
        count = 0
        async with self._pool.acquire() as conn:
            # Use a transaction for batch insert
            async with conn.transaction():
                for record in records:
                    try:
                        date_val = record.get("date")
                        if isinstance(date_val, str):
                            date_val = datetime.strptime(date_val, "%Y-%m-%d").date()
                        
                        await conn.execute(
                            query,
                            record.get("symbol", ""),
                            date_val,
                            float(record.get("open", 0) or 0),
                            float(record.get("high", 0) or 0),
                            float(record.get("low", 0) or 0),
                            float(record.get("close", 0) or 0),
                            float(record.get("last", 0) or 0),
                            float(record.get("prev_close", 0) or 0),
                            int(record.get("volume", 0) or 0),
                            float(record.get("turnover", 0) or 0),
                            int(record.get("total_trades", 0) or 0),
                            int(record.get("delivery_quantity", record.get("delivery_qty", 0)) or 0),
                            float(record.get("delivery_percentage", record.get("delivery_pct", 0)) or 0),
                            float(record.get("vwap", 0) or 0),
                            record.get("isin", ""),
                            record.get("series", "EQ"),
                        )
                        count += 1
                    except Exception as e:
                        logger.warning(f"Error upserting price for {record.get('symbol')}: {e}")
        
        return count
    
    async def get_prices(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        """
        Get daily price history for a symbol.
        
        Args:
            symbol: Stock symbol
            start_date: Start date (YYYY-MM-DD), inclusive
            end_date: End date (YYYY-MM-DD), inclusive
            limit: Max rows to return
        
        Returns:
            List of price records, newest first
        """
        conditions = ["symbol = $1"]
        params: list = [symbol]
        idx = 2
        
        if start_date:
            conditions.append(f"date >= ${idx}")
            params.append(datetime.strptime(start_date, "%Y-%m-%d").date())
            idx += 1
        if end_date:
            conditions.append(f"date <= ${idx}")
            params.append(datetime.strptime(end_date, "%Y-%m-%d").date())
            idx += 1
        
        where = " AND ".join(conditions)
        query = f"""
            SELECT symbol, date, open, high, low, close, last, prev_close,
                   volume, turnover, total_trades, delivery_qty, delivery_pct,
                   vwap, isin, series
            FROM prices_daily
            WHERE {where}
            ORDER BY date DESC
            LIMIT {limit}
        """
        
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(r) for r in rows]
    
    async def get_latest_price_date(self, symbol: str) -> Optional[date]:
        """Get the most recent date for which we have price data."""
        async with self._pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT MAX(date) FROM prices_daily WHERE symbol = $1", symbol
            )
    
    async def get_price_count(self, symbol: Optional[str] = None) -> int:
        """Get total number of price records."""
        async with self._pool.acquire() as conn:
            if symbol:
                return await conn.fetchval(
                    "SELECT COUNT(*) FROM prices_daily WHERE symbol = $1", symbol
                )
            return await conn.fetchval("SELECT COUNT(*) FROM prices_daily")
    
    # ========================
    # Technical Indicators
    # ========================
    
    async def upsert_technicals(self, records: List[Dict[str, Any]]) -> int:
        """Insert or update technical indicator records."""
        if not records:
            return 0
        
        query = """
            INSERT INTO technical_indicators (
                symbol, date, sma_20, sma_50, sma_200, ema_12, ema_26,
                rsi_14, macd, macd_signal, bollinger_upper, bollinger_lower,
                atr_14, adx_14, obv, support_level, resistance_level
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
            ON CONFLICT (symbol, date)
            DO UPDATE SET
                sma_20 = EXCLUDED.sma_20, sma_50 = EXCLUDED.sma_50,
                sma_200 = EXCLUDED.sma_200, ema_12 = EXCLUDED.ema_12,
                ema_26 = EXCLUDED.ema_26, rsi_14 = EXCLUDED.rsi_14,
                macd = EXCLUDED.macd, macd_signal = EXCLUDED.macd_signal,
                bollinger_upper = EXCLUDED.bollinger_upper,
                bollinger_lower = EXCLUDED.bollinger_lower,
                atr_14 = EXCLUDED.atr_14, adx_14 = EXCLUDED.adx_14,
                obv = EXCLUDED.obv, support_level = EXCLUDED.support_level,
                resistance_level = EXCLUDED.resistance_level
        """
        
        count = 0
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                for r in records:
                    try:
                        date_val = r.get("date")
                        if isinstance(date_val, str):
                            date_val = datetime.strptime(date_val, "%Y-%m-%d").date()
                        
                        await conn.execute(
                            query,
                            r.get("symbol", ""),
                            date_val,
                            r.get("sma_20"), r.get("sma_50"), r.get("sma_200"),
                            r.get("ema_12"), r.get("ema_26"), r.get("rsi_14"),
                            r.get("macd"), r.get("macd_signal"),
                            r.get("bollinger_upper"), r.get("bollinger_lower"),
                            r.get("atr_14"), r.get("adx_14"), r.get("obv"),
                            r.get("support_level"), r.get("resistance_level"),
                        )
                        count += 1
                    except Exception as e:
                        logger.warning(f"Error upserting technicals for {r.get('symbol')}: {e}")
        
        return count
    
    async def get_technicals(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        """Get technical indicators for a symbol."""
        conditions = ["symbol = $1"]
        params: list = [symbol]
        idx = 2
        
        if start_date:
            conditions.append(f"date >= ${idx}")
            params.append(datetime.strptime(start_date, "%Y-%m-%d").date())
            idx += 1
        if end_date:
            conditions.append(f"date <= ${idx}")
            params.append(datetime.strptime(end_date, "%Y-%m-%d").date())
            idx += 1
        
        where = " AND ".join(conditions)
        query = f"""
            SELECT * FROM technical_indicators
            WHERE {where}
            ORDER BY date DESC
            LIMIT {limit}
        """
        
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(r) for r in rows]
    
    # ========================
    # Fundamentals Quarterly
    # ========================
    
    async def upsert_fundamentals(self, records: List[Dict[str, Any]]) -> int:
        """Insert or update quarterly fundamental records."""
        if not records:
            return 0
        
        query = """
            INSERT INTO fundamentals_quarterly (
                symbol, period_end, period_type, revenue, operating_profit,
                operating_margin, net_profit, net_profit_margin, eps, ebitda,
                total_assets, total_equity, total_debt, cash_and_equiv,
                operating_cash_flow, free_cash_flow, roe, debt_to_equity,
                interest_coverage, current_ratio
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20)
            ON CONFLICT (symbol, period_end, period_type)
            DO UPDATE SET
                revenue = EXCLUDED.revenue, operating_profit = EXCLUDED.operating_profit,
                operating_margin = EXCLUDED.operating_margin, net_profit = EXCLUDED.net_profit,
                net_profit_margin = EXCLUDED.net_profit_margin, eps = EXCLUDED.eps,
                ebitda = EXCLUDED.ebitda, total_assets = EXCLUDED.total_assets,
                total_equity = EXCLUDED.total_equity, total_debt = EXCLUDED.total_debt,
                cash_and_equiv = EXCLUDED.cash_and_equiv,
                operating_cash_flow = EXCLUDED.operating_cash_flow,
                free_cash_flow = EXCLUDED.free_cash_flow, roe = EXCLUDED.roe,
                debt_to_equity = EXCLUDED.debt_to_equity,
                interest_coverage = EXCLUDED.interest_coverage,
                current_ratio = EXCLUDED.current_ratio
        """
        
        count = 0
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                for r in records:
                    try:
                        period_end = r.get("period_end")
                        if isinstance(period_end, str):
                            period_end = datetime.strptime(period_end, "%Y-%m-%d").date()
                        
                        await conn.execute(
                            query,
                            r.get("symbol", ""),
                            period_end,
                            r.get("period_type", "quarterly"),
                            r.get("revenue"), r.get("operating_profit"),
                            r.get("operating_margin"), r.get("net_profit"),
                            r.get("net_profit_margin"), r.get("eps"),
                            r.get("ebitda"), r.get("total_assets"),
                            r.get("total_equity"), r.get("total_debt"),
                            r.get("cash_and_equiv"), r.get("operating_cash_flow"),
                            r.get("free_cash_flow"), r.get("roe"),
                            r.get("debt_to_equity"), r.get("interest_coverage"),
                            r.get("current_ratio"),
                        )
                        count += 1
                    except Exception as e:
                        logger.warning(f"Error upserting fundamentals for {r.get('symbol')}: {e}")
        
        return count
    
    async def get_fundamentals(
        self,
        symbol: str,
        period_type: str = "quarterly",
        limit: int = 40,
    ) -> List[Dict[str, Any]]:
        """Get quarterly/annual fundamentals for a symbol."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM fundamentals_quarterly
                WHERE symbol = $1 AND period_type = $2
                ORDER BY period_end DESC
                LIMIT $3
                """,
                symbol, period_type, limit,
            )
            return [dict(r) for r in rows]
    
    # ========================
    # Shareholding Quarterly
    # ========================
    
    async def upsert_shareholding(self, records: List[Dict[str, Any]]) -> int:
        """Insert or update quarterly shareholding records."""
        if not records:
            return 0
        
        query = """
            INSERT INTO shareholding_quarterly (
                symbol, quarter_end, promoter_holding, promoter_pledging,
                fii_holding, dii_holding, public_holding,
                promoter_holding_change, fii_holding_change,
                num_shareholders, mf_holding, insurance_holding
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            ON CONFLICT (symbol, quarter_end)
            DO UPDATE SET
                promoter_holding = EXCLUDED.promoter_holding,
                promoter_pledging = EXCLUDED.promoter_pledging,
                fii_holding = EXCLUDED.fii_holding, dii_holding = EXCLUDED.dii_holding,
                public_holding = EXCLUDED.public_holding,
                promoter_holding_change = EXCLUDED.promoter_holding_change,
                fii_holding_change = EXCLUDED.fii_holding_change,
                num_shareholders = EXCLUDED.num_shareholders,
                mf_holding = EXCLUDED.mf_holding,
                insurance_holding = EXCLUDED.insurance_holding
        """
        
        count = 0
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                for r in records:
                    try:
                        quarter_end = r.get("quarter_end")
                        if isinstance(quarter_end, str):
                            quarter_end = datetime.strptime(quarter_end, "%Y-%m-%d").date()
                        
                        await conn.execute(
                            query,
                            r.get("symbol", ""),
                            quarter_end,
                            r.get("promoter_holding"), r.get("promoter_pledging"),
                            r.get("fii_holding"), r.get("dii_holding"),
                            r.get("public_holding"), r.get("promoter_holding_change"),
                            r.get("fii_holding_change"), r.get("num_shareholders"),
                            r.get("mf_holding"), r.get("insurance_holding"),
                        )
                        count += 1
                    except Exception as e:
                        logger.warning(f"Error upserting shareholding for {r.get('symbol')}: {e}")
        
        return count
    
    async def get_shareholding(
        self,
        symbol: str,
        limit: int = 28,
    ) -> List[Dict[str, Any]]:
        """Get quarterly shareholding for a symbol."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM shareholding_quarterly
                WHERE symbol = $1
                ORDER BY quarter_end DESC
                LIMIT $2
                """,
                symbol, limit,
            )
            return [dict(r) for r in rows]
    
    # ========================
    # Analytics Queries
    # ========================
    
    async def get_screener_data(
        self,
        filters: Optional[List[Dict[str, Any]]] = None,
        symbols: Optional[List[str]] = None,
        sort_by: str = "symbol",
        sort_order: str = "asc",
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        """
        Cross-join latest prices with technicals and fundamentals for screener.
        This is the key advantage of SQL — filtering across multiple data types.

        Args:
            filters: List of filter dicts with keys: metric, operator, value, value2
                     Supported metrics map to columns:
                       - rsi_14, sma_50, sma_200, macd -> technical_indicators
                       - close, volume -> prices_daily
                       - roe, debt_to_equity, eps, revenue, net_profit, current_ratio,
                         operating_margin, net_profit_margin -> fundamentals_quarterly
                       - promoter_holding, fii_holding, dii_holding -> shareholding_quarterly
            symbols: Filter to specific symbols
            sort_by: Column to sort by
            sort_order: 'asc' or 'desc'
            limit: Max results
        """
        conditions = []
        params: list = []
        idx = 1

        # Column mapping: metric name -> SQL alias.column
        COLUMN_MAP = {
            # Price columns (alias: p)
            "close": "p.close", "current_price": "p.close",
            "volume": "p.volume", "prev_close": "p.prev_close",
            # Technical columns (alias: t)
            "rsi_14": "t.rsi_14", "sma_50": "t.sma_50", "sma_200": "t.sma_200",
            "macd": "t.macd", "macd_signal": "t.macd_signal",
            "sma_20": "t.sma_20", "ema_12": "t.ema_12", "ema_26": "t.ema_26",
            "atr_14": "t.atr_14", "adx_14": "t.adx_14",
            "bollinger_upper": "t.bollinger_upper", "bollinger_lower": "t.bollinger_lower",
            # Fundamental columns (alias: f)
            "roe": "f.roe", "debt_to_equity": "f.debt_to_equity",
            "eps": "f.eps", "revenue": "f.revenue",
            "net_profit": "f.net_profit", "operating_margin": "f.operating_margin",
            "net_profit_margin": "f.net_profit_margin", "current_ratio": "f.current_ratio",
            "interest_coverage": "f.interest_coverage",
            "free_cash_flow": "f.free_cash_flow", "operating_cash_flow": "f.operating_cash_flow",
            # Shareholding columns (alias: s)
            "promoter_holding": "s.promoter_holding", "fii_holding": "s.fii_holding",
            "dii_holding": "s.dii_holding", "public_holding": "s.public_holding",
            "promoter_pledging": "s.promoter_pledging",
        }

        if symbols:
            conditions.append(f"p.symbol = ANY(${idx})")
            params.append(symbols)
            idx += 1

        # Process filters
        if filters:
            for f in filters:
                metric = f.get("metric", "")
                col = COLUMN_MAP.get(metric)
                if not col:
                    continue  # Skip unknown metrics

                op = f.get("operator", "gte")
                val = f.get("value", 0)

                if op == "gt":
                    conditions.append(f"{col} > ${idx}")
                    params.append(float(val))
                    idx += 1
                elif op == "lt":
                    conditions.append(f"{col} < ${idx}")
                    params.append(float(val))
                    idx += 1
                elif op == "gte":
                    conditions.append(f"{col} >= ${idx}")
                    params.append(float(val))
                    idx += 1
                elif op == "lte":
                    conditions.append(f"{col} <= ${idx}")
                    params.append(float(val))
                    idx += 1
                elif op == "eq":
                    conditions.append(f"{col} = ${idx}")
                    params.append(float(val))
                    idx += 1
                elif op == "between" and f.get("value2") is not None:
                    conditions.append(f"{col} BETWEEN ${idx} AND ${idx + 1}")
                    params.append(float(val))
                    params.append(float(f["value2"]))
                    idx += 2

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        # Determine sort column
        sort_col = COLUMN_MAP.get(sort_by, "p.symbol")
        sort_dir = "DESC" if sort_order.lower() == "desc" else "ASC"

        query = f"""
            WITH latest_prices AS (
                SELECT DISTINCT ON (symbol)
                    symbol, date, close, volume, prev_close
                FROM prices_daily
                ORDER BY symbol, date DESC
            ),
            latest_tech AS (
                SELECT DISTINCT ON (symbol)
                    symbol, sma_20, sma_50, sma_200, ema_12, ema_26,
                    rsi_14, macd, macd_signal, bollinger_upper, bollinger_lower,
                    atr_14, adx_14
                FROM technical_indicators
                ORDER BY symbol, date DESC
            ),
            latest_fund AS (
                SELECT DISTINCT ON (symbol)
                    symbol, revenue, operating_profit, operating_margin,
                    net_profit, net_profit_margin, eps, roe, debt_to_equity,
                    interest_coverage, current_ratio, free_cash_flow,
                    operating_cash_flow
                FROM fundamentals_quarterly
                WHERE period_type = 'quarterly'
                ORDER BY symbol, period_end DESC
            ),
            latest_share AS (
                SELECT DISTINCT ON (symbol)
                    symbol, promoter_holding, promoter_pledging,
                    fii_holding, dii_holding, public_holding
                FROM shareholding_quarterly
                ORDER BY symbol, quarter_end DESC
            )
            SELECT
                p.symbol, p.date, p.close, p.volume, p.prev_close,
                t.rsi_14, t.sma_20, t.sma_50, t.sma_200,
                t.ema_12, t.ema_26, t.macd, t.macd_signal,
                t.bollinger_upper, t.bollinger_lower, t.atr_14, t.adx_14,
                f.revenue, f.operating_margin, f.net_profit, f.net_profit_margin,
                f.eps, f.roe, f.debt_to_equity, f.interest_coverage,
                f.current_ratio, f.free_cash_flow, f.operating_cash_flow,
                s.promoter_holding, s.promoter_pledging,
                s.fii_holding, s.dii_holding, s.public_holding
            FROM latest_prices p
            LEFT JOIN latest_tech t ON p.symbol = t.symbol
            LEFT JOIN latest_fund f ON p.symbol = f.symbol
            LEFT JOIN latest_share s ON p.symbol = s.symbol
            {where}
            ORDER BY {sort_col} {sort_dir} NULLS LAST
            LIMIT {limit}
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(r) for r in rows]
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get database statistics for monitoring."""
        async with self._pool.acquire() as conn:
            stats = {}
            for table in ["prices_daily", "technical_indicators", "fundamentals_quarterly", "shareholding_quarterly"]:
                row_count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                size = await conn.fetchval(
                    f"SELECT pg_size_pretty(pg_total_relation_size('{table}'))"
                )
                stats[table] = {"rows": row_count, "size": size}
            
            stats["pool"] = {
                "size": self._pool.get_size(),
                "min_size": self._pool.get_min_size(),
                "max_size": self._pool.get_max_size(),
                "free_size": self._pool.get_idle_size(),
            }
            
            return stats


# Module-level singleton
_ts_store: Optional[TimeSeriesStore] = None


async def init_timeseries_store(dsn: str = "postgresql://localhost:5432/stockpulse_ts") -> TimeSeriesStore:
    """Initialize and return the global time-series store singleton."""
    global _ts_store
    _ts_store = TimeSeriesStore(dsn=dsn)
    await _ts_store.initialize()
    return _ts_store


def get_timeseries_store() -> Optional[TimeSeriesStore]:
    """Get the global time-series store instance."""
    return _ts_store
