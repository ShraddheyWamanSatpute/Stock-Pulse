"""
Enhanced yfinance extractor.

Uses the yfinance library to fetch price history, fundamentals, and
corporate info for Indian stocks (via .NS suffix for NSE listings).
"""

import logging
from datetime import datetime, date
from typing import Any, Dict, List, Optional

from .base_extractor import BaseExtractor
from ..config.source_config import YFINANCE_CONFIG
from ..models.extraction_models import ExtractionRecord, ExtractionStatus, StockDataRecord

logger = logging.getLogger(__name__)

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    logger.warning("yfinance not installed - YFinanceExtractor will not work")


# Map common Indian stock symbols to their Yahoo Finance tickers
NSE_SYMBOL_MAP = {
    "RELIANCE": "RELIANCE.NS", "TCS": "TCS.NS", "HDFCBANK": "HDFCBANK.NS",
    "INFY": "INFY.NS", "ICICIBANK": "ICICIBANK.NS", "HINDUNILVR": "HINDUNILVR.NS",
    "ITC": "ITC.NS", "SBIN": "SBIN.NS", "BHARTIARTL": "BHARTIARTL.NS",
    "KOTAKBANK": "KOTAKBANK.NS", "LT": "LT.NS", "AXISBANK": "AXISBANK.NS",
    "WIPRO": "WIPRO.NS", "HCLTECH": "HCLTECH.NS", "ASIANPAINT": "ASIANPAINT.NS",
    "MARUTI": "MARUTI.NS", "SUNPHARMA": "SUNPHARMA.NS", "TITAN": "TITAN.NS",
    "BAJFINANCE": "BAJFINANCE.NS", "BAJAJFINSV": "BAJAJFINSV.NS",
    "NESTLEIND": "NESTLEIND.NS", "ULTRACEMCO": "ULTRACEMCO.NS",
    "TATAMOTORS": "TATAMOTORS.NS", "TATASTEEL": "TATASTEEL.NS",
    "POWERGRID": "POWERGRID.NS", "NTPC": "NTPC.NS", "M&M": "M&M.NS",
    "ONGC": "ONGC.NS", "JSWSTEEL": "JSWSTEEL.NS", "ADANIENT": "ADANIENT.NS",
    "ADANIPORTS": "ADANIPORTS.NS", "TECHM": "TECHM.NS", "COALINDIA": "COALINDIA.NS",
    "DRREDDY": "DRREDDY.NS", "CIPLA": "CIPLA.NS", "DIVISLAB": "DIVISLAB.NS",
    "BRITANNIA": "BRITANNIA.NS", "DABUR": "DABUR.NS", "PIDILITIND": "PIDILITIND.NS",
    "HAVELLS": "HAVELLS.NS", "GODREJCP": "GODREJCP.NS", "VOLTAS": "VOLTAS.NS",
    "HEROMOTOCO": "HEROMOTOCO.NS", "EICHERMOT": "EICHERMOT.NS",
    "TATACONSUM": "TATACONSUM.NS", "APOLLOHOSP": "APOLLOHOSP.NS",
    "ZOMATO": "ZOMATO.NS", "PAYTM": "PAYTM.NS", "NYKAA": "NYKAA.NS",
}


class YFinanceExtractor(BaseExtractor):
    """
    Extracts price history, fundamentals, and stock info from Yahoo Finance.

    Provides fields:
        - Price: date, open, high, low, close, adjusted_close, volume (historical)
        - Fundamentals: eps, pe_ratio, pb_ratio, market_cap, dividend_per_share,
                        book_value_per_share, shares_outstanding
        - Info: sector, industry, company_name, website
    """

    def __init__(self):
        super().__init__(YFINANCE_CONFIG)

    def get_source_name(self) -> str:
        return "yfinance"

    def get_provided_fields(self) -> List[str]:
        return [
            "date", "open", "high", "low", "close", "adjusted_close", "volume",
            "eps", "pe_ratio", "pb_ratio", "market_cap", "dividend_per_share",
            "book_value_per_share", "shares_outstanding",
            "sector", "industry", "company_name", "website",
        ]

    async def extract(self, symbol: str, record: StockDataRecord) -> ExtractionRecord:
        """Extract all available data from yfinance for a single symbol."""
        if not YFINANCE_AVAILABLE:
            return self._create_extraction_record(
                symbol, datetime.utcnow(), [], self.get_provided_fields(),
                "yfinance library not installed"
            )

        started_at = datetime.utcnow()
        fields_extracted = []
        fields_failed = []

        try:
            ticker_symbol = self._resolve_ticker(symbol)
            ticker = yf.Ticker(ticker_symbol)

            # Fetch stock info
            info_fields = self._extract_info(ticker, symbol, record)
            fields_extracted.extend(info_fields)

            # Fetch price history
            price_fields = self._extract_price_history(ticker, symbol, record)
            fields_extracted.extend(price_fields)

        except Exception as e:
            logger.error(f"Error extracting yfinance data for {symbol}: {e}")
            fields_failed = [f for f in self.get_provided_fields() if f not in fields_extracted]
            return self._create_extraction_record(
                symbol, started_at, fields_extracted, fields_failed, str(e)
            )

        fields_failed = [f for f in self.get_provided_fields() if f not in fields_extracted]
        return self._create_extraction_record(
            symbol, started_at, fields_extracted, fields_failed
        )

    def _resolve_ticker(self, symbol: str) -> str:
        """Resolve an Indian stock symbol to a Yahoo Finance ticker."""
        if symbol in NSE_SYMBOL_MAP:
            return NSE_SYMBOL_MAP[symbol]
        if not symbol.endswith((".NS", ".BO")):
            return f"{symbol}.NS"
        return symbol

    def _extract_info(self, ticker: Any, symbol: str,
                      record: StockDataRecord) -> List[str]:
        """Extract stock info/fundamentals from yfinance."""
        fields_extracted = []

        try:
            info = ticker.info
            if not info:
                return fields_extracted

            field_map = {
                "company_name": ("longName", "shortName"),
                "sector": ("sector",),
                "industry": ("industry",),
                "website": ("website",),
                "market_cap": ("marketCap",),
                "shares_outstanding": ("sharesOutstanding",),
                "book_value_per_share": ("bookValue",),
                "eps": ("trailingEps",),
                "pe_ratio": ("trailingPE",),
                "pb_ratio": ("priceToBook",),
                "dividend_per_share": ("dividendRate",),
            }

            for field_name, info_keys in field_map.items():
                for key in info_keys:
                    val = info.get(key)
                    if val is not None:
                        # Convert market cap from raw to Crores
                        if field_name == "market_cap" and isinstance(val, (int, float)):
                            val = round(val / 1e7, 2)  # INR to Cr
                        record.set_field(field_name, val, "yfinance")
                        fields_extracted.append(field_name)
                        break

        except Exception as e:
            logger.warning(f"Error fetching yfinance info for {symbol}: {e}")

        return fields_extracted

    def _extract_price_history(self, ticker: Any, symbol: str,
                               record: StockDataRecord,
                               period: str = "2y") -> List[str]:
        """
        Extract price history and set latest price fields + history array.
        """
        fields_extracted = []

        try:
            hist = ticker.history(period=period, auto_adjust=False)
            if hist is None or hist.empty:
                return fields_extracted

            # Build price history array (newest first)
            price_history = []
            for idx in reversed(hist.index):
                row = hist.loc[idx]
                price_history.append({
                    "date": idx.strftime("%Y-%m-%d"),
                    "open": round(float(row.get("Open", 0)), 2),
                    "high": round(float(row.get("High", 0)), 2),
                    "low": round(float(row.get("Low", 0)), 2),
                    "close": round(float(row.get("Close", 0)), 2),
                    "adjusted_close": round(float(row.get("Adj Close", 0)), 2),
                    "volume": int(row.get("Volume", 0)),
                })

            record.price_history = price_history

            # Set latest day's fields
            if price_history:
                latest = price_history[0]
                for field_name in ["date", "open", "high", "low", "close",
                                   "adjusted_close", "volume"]:
                    val = latest.get(field_name)
                    if val is not None:
                        record.set_field(field_name, val, "yfinance")
                        if field_name not in fields_extracted:
                            fields_extracted.append(field_name)

                # Set prev_close from second most recent day
                if len(price_history) > 1:
                    record.set_field("prev_close", price_history[1]["close"], "yfinance")
                    fields_extracted.append("prev_close")

        except Exception as e:
            logger.warning(f"Error fetching yfinance history for {symbol}: {e}")

        return fields_extracted

    async def extract_history(
        self, symbol: str, period: str = "10y"
    ) -> List[Dict[str, Any]]:
        """
        Fetch extended historical data for a symbol.

        Returns list of OHLCV dicts (newest first).
        """
        if not YFINANCE_AVAILABLE:
            return []

        try:
            ticker_symbol = self._resolve_ticker(symbol)
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period=period, auto_adjust=False)

            if hist is None or hist.empty:
                return []

            result = []
            for idx in reversed(hist.index):
                row = hist.loc[idx]
                result.append({
                    "date": idx.strftime("%Y-%m-%d"),
                    "open": round(float(row.get("Open", 0)), 2),
                    "high": round(float(row.get("High", 0)), 2),
                    "low": round(float(row.get("Low", 0)), 2),
                    "close": round(float(row.get("Close", 0)), 2),
                    "adjusted_close": round(float(row.get("Adj Close", 0)), 2),
                    "volume": int(row.get("Volume", 0)),
                })
            return result

        except Exception as e:
            logger.error(f"Error fetching yfinance history for {symbol}: {e}")
            return []
