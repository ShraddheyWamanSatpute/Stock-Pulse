"""
NSE Bhavcopy Extractor
Downloads and parses NSE daily Bhavcopy files to get:
- Delivery volume and percentage
- VWAP
- Total trades count
- Complete OHLCV data
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import os
import io
import zipfile
import csv
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class BhavcopyData:
    """Data extracted from NSE Bhavcopy"""
    symbol: str
    date: str
    series: str = "EQ"
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    last: float = 0.0
    prev_close: float = 0.0
    volume: int = 0
    turnover: float = 0.0
    total_trades: int = 0
    delivery_quantity: int = 0
    delivery_percentage: float = 0.0
    vwap: float = 0.0
    isin: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "date": self.date,
            "series": self.series,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "last": self.last,
            "prev_close": self.prev_close,
            "volume": self.volume,
            "turnover": self.turnover,
            "total_trades": self.total_trades,
            "delivery_quantity": self.delivery_quantity,
            "delivery_percentage": self.delivery_percentage,
            "vwap": self.vwap,
            "isin": self.isin
        }


@dataclass
class BhavcopyMetrics:
    """Metrics for Bhavcopy extraction"""
    total_downloads: int = 0
    successful_downloads: int = 0
    failed_downloads: int = 0
    total_records_parsed: int = 0
    last_download_time: Optional[datetime] = None
    last_download_date: Optional[str] = None
    errors: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "total_downloads": self.total_downloads,
            "successful_downloads": self.successful_downloads,
            "failed_downloads": self.failed_downloads,
            "total_records_parsed": self.total_records_parsed,
            "last_download_time": self.last_download_time.isoformat() if self.last_download_time else None,
            "last_download_date": self.last_download_date,
            "recent_errors": self.errors[-5:]
        }


class NSEBhavcopyExtractor:
    """
    Extracts daily Bhavcopy data from NSE archives.
    Provides delivery data, VWAP, and trade counts not available in Groww API.
    """
    
    # NSE Bhavcopy URL patterns
    BASE_URL = "https://archives.nseindia.com/content/cm"
    
    # New UDiFF format (post July 2024)
    UDIFF_PATTERN = "BhavCopy_NSE_CM_0_0_0_{date}_F_0000.csv.zip"
    
    # Legacy format (pre July 2024)
    LEGACY_PATTERN = "cm{date}bhav.csv.zip"
    
    # Column mappings for different formats
    UDIFF_COLUMNS = {
        "TckrSymb": "symbol",
        "SctySrs": "series",
        "OpnPric": "open",
        "HghPric": "high",
        "LwPric": "low",
        "ClsPric": "close",
        "LastPric": "last",
        "PrvsClsgPric": "prev_close",
        "TtlTradgVol": "volume",
        "TtlTrfVal": "turnover",
        "TtlNbOfTxsExctd": "total_trades",
        "DlvryQty": "delivery_quantity",
        "DlvryPct": "delivery_percentage",
        "VWAP": "vwap",
        "ISIN": "isin",
        "TradDt": "date"
    }
    
    LEGACY_COLUMNS = {
        "SYMBOL": "symbol",
        "SERIES": "series",
        "OPEN": "open",
        "HIGH": "high",
        "LOW": "low",
        "CLOSE": "close",
        "LAST": "last",
        "PREVCLOSE": "prev_close",
        "TOTTRDQTY": "volume",
        "TOTTRDVAL": "turnover",
        "TOTALTRADES": "total_trades",
        "ISIN": "isin",
        "TIMESTAMP": "date"
    }
    
    # User agent to avoid blocking
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Referer": "https://www.nseindia.com/"
    }
    
    def __init__(self, db=None):
        self.db = db
        self.session: Optional[aiohttp.ClientSession] = None
        self.metrics = BhavcopyMetrics()
        self._cache: Dict[str, Dict[str, BhavcopyData]] = {}  # date -> symbol -> data
        self._is_initialized = False
        
    async def initialize(self):
        """Initialize the HTTP session"""
        if self._is_initialized:
            return
            
        connector = aiohttp.TCPConnector(limit=5, force_close=True)
        timeout = aiohttp.ClientTimeout(total=60)
        
        self.session = aiohttp.ClientSession(
            headers=self.HEADERS,
            connector=connector,
            timeout=timeout
        )
        self._is_initialized = True
        logger.info("NSE Bhavcopy Extractor initialized")
        
    async def close(self):
        """Close the HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
        self._is_initialized = False
    
    def _get_bhavcopy_url(self, date: datetime, use_udiff: bool = True) -> str:
        """Generate the Bhavcopy URL for a given date"""
        if use_udiff:
            # UDiFF format: YYYYMMDD
            date_str = date.strftime("%Y%m%d")
            filename = self.UDIFF_PATTERN.format(date=date_str)
        else:
            # Legacy format: DDMONYYYY (e.g., 10FEB2025)
            date_str = date.strftime("%d%b%Y").upper()
            filename = self.LEGACY_PATTERN.format(date=date_str)
        
        return f"{self.BASE_URL}/{filename}"
    
    async def download_bhavcopy(self, date: datetime) -> Optional[List[BhavcopyData]]:
        """
        Download and parse Bhavcopy for a specific date.
        
        Args:
            date: The date to download Bhavcopy for
            
        Returns:
            List of BhavcopyData objects or None if download failed
        """
        if not self._is_initialized:
            await self.initialize()
        
        date_str = date.strftime("%Y-%m-%d")
        
        # Check cache first
        if date_str in self._cache:
            logger.info(f"Returning cached Bhavcopy data for {date_str}")
            return list(self._cache[date_str].values())
        
        self.metrics.total_downloads += 1
        
        # Try UDiFF format first, then legacy
        for use_udiff in [True, False]:
            url = self._get_bhavcopy_url(date, use_udiff=use_udiff)
            logger.info(f"Downloading Bhavcopy from: {url}")
            
            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        content = await response.read()
                        data = self._parse_bhavcopy_zip(content, date_str, use_udiff)
                        
                        if data:
                            self.metrics.successful_downloads += 1
                            self.metrics.total_records_parsed += len(data)
                            self.metrics.last_download_time = datetime.now(timezone.utc)
                            self.metrics.last_download_date = date_str
                            
                            # Cache the data
                            self._cache[date_str] = {d.symbol: d for d in data}
                            
                            logger.info(f"Successfully parsed {len(data)} records for {date_str}")
                            return data
                    elif response.status == 404:
                        logger.warning(f"Bhavcopy not found at {url}, trying alternative format...")
                        continue
                    else:
                        logger.warning(f"HTTP {response.status} for {url}")
                        
            except asyncio.TimeoutError:
                logger.error(f"Timeout downloading Bhavcopy from {url}")
            except Exception as e:
                logger.error(f"Error downloading Bhavcopy: {e}")
        
        # All attempts failed
        self.metrics.failed_downloads += 1
        self.metrics.errors.append({
            "date": date_str,
            "error": "Failed to download from all URL formats",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return None
    
    def _parse_bhavcopy_zip(self, content: bytes, date_str: str, use_udiff: bool) -> Optional[List[BhavcopyData]]:
        """Parse the ZIP file containing Bhavcopy CSV"""
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                # Get the first CSV file in the zip
                csv_files = [f for f in zf.namelist() if f.endswith('.csv')]
                if not csv_files:
                    logger.error("No CSV file found in Bhavcopy ZIP")
                    return None
                
                csv_filename = csv_files[0]
                with zf.open(csv_filename) as csv_file:
                    content_str = csv_file.read().decode('utf-8')
                    return self._parse_bhavcopy_csv(content_str, date_str, use_udiff)
                    
        except zipfile.BadZipFile:
            logger.error("Invalid ZIP file")
            return None
        except Exception as e:
            logger.error(f"Error parsing Bhavcopy ZIP: {e}")
            return None
    
    def _parse_bhavcopy_csv(self, content: str, date_str: str, use_udiff: bool) -> List[BhavcopyData]:
        """Parse Bhavcopy CSV content"""
        data = []
        column_map = self.UDIFF_COLUMNS if use_udiff else self.LEGACY_COLUMNS
        
        try:
            reader = csv.DictReader(io.StringIO(content))
            
            for row in reader:
                # Skip non-EQ series (we only want equity data)
                series = row.get("SctySrs", row.get("SERIES", "EQ"))
                if series not in ["EQ", "BE", "BZ"]:
                    continue
                
                try:
                    bhavcopy = BhavcopyData(
                        symbol=row.get("TckrSymb", row.get("SYMBOL", "")),
                        date=date_str,
                        series=series,
                        open=self._safe_float(row.get("OpnPric", row.get("OPEN", 0))),
                        high=self._safe_float(row.get("HghPric", row.get("HIGH", 0))),
                        low=self._safe_float(row.get("LwPric", row.get("LOW", 0))),
                        close=self._safe_float(row.get("ClsPric", row.get("CLOSE", 0))),
                        last=self._safe_float(row.get("LastPric", row.get("LAST", 0))),
                        prev_close=self._safe_float(row.get("PrvsClsgPric", row.get("PREVCLOSE", 0))),
                        volume=self._safe_int(row.get("TtlTradgVol", row.get("TOTTRDQTY", 0))),
                        turnover=self._safe_float(row.get("TtlTrfVal", row.get("TOTTRDVAL", 0))),
                        total_trades=self._safe_int(row.get("TtlNbOfTxsExctd", row.get("TOTALTRADES", 0))),
                        delivery_quantity=self._safe_int(row.get("DlvryQty", 0)),
                        delivery_percentage=self._safe_float(row.get("DlvryPct", 0)),
                        vwap=self._safe_float(row.get("VWAP", 0)),
                        isin=row.get("ISIN", "")
                    )
                    
                    # Calculate delivery percentage if not provided
                    if bhavcopy.delivery_percentage == 0 and bhavcopy.volume > 0 and bhavcopy.delivery_quantity > 0:
                        bhavcopy.delivery_percentage = round(
                            (bhavcopy.delivery_quantity / bhavcopy.volume) * 100, 2
                        )
                    
                    # Calculate VWAP if not provided
                    if bhavcopy.vwap == 0 and bhavcopy.volume > 0 and bhavcopy.turnover > 0:
                        bhavcopy.vwap = round(bhavcopy.turnover / bhavcopy.volume, 2)
                    
                    data.append(bhavcopy)
                    
                except Exception as e:
                    logger.warning(f"Error parsing row: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error parsing CSV: {e}")
            
        return data
    
    def _safe_float(self, value) -> float:
        """Safely convert to float"""
        try:
            if value is None or value == "" or value == "-":
                return 0.0
            return float(value)
        except (ValueError, TypeError):
            return 0.0
    
    def _safe_int(self, value) -> int:
        """Safely convert to int"""
        try:
            if value is None or value == "" or value == "-":
                return 0
            return int(float(value))
        except (ValueError, TypeError):
            return 0
    
    async def get_symbol_data(self, symbol: str, date: datetime = None) -> Optional[BhavcopyData]:
        """
        Get Bhavcopy data for a specific symbol.
        
        Args:
            symbol: Stock symbol
            date: Date to get data for (defaults to latest trading day)
            
        Returns:
            BhavcopyData object or None
        """
        if date is None:
            date = self._get_last_trading_day()
        
        date_str = date.strftime("%Y-%m-%d")
        
        # Check cache
        if date_str in self._cache and symbol in self._cache[date_str]:
            return self._cache[date_str][symbol]
        
        # Download if not cached
        data = await self.download_bhavcopy(date)
        
        if data:
            # Find the symbol
            for item in data:
                if item.symbol == symbol:
                    return item
        
        return None
    
    async def get_multiple_symbols(self, symbols: List[str], date: datetime = None) -> Dict[str, BhavcopyData]:
        """
        Get Bhavcopy data for multiple symbols.
        
        Args:
            symbols: List of stock symbols
            date: Date to get data for
            
        Returns:
            Dictionary of symbol -> BhavcopyData
        """
        if date is None:
            date = self._get_last_trading_day()
        
        date_str = date.strftime("%Y-%m-%d")
        
        # Download if not cached
        if date_str not in self._cache:
            await self.download_bhavcopy(date)
        
        result = {}
        if date_str in self._cache:
            for symbol in symbols:
                if symbol in self._cache[date_str]:
                    result[symbol] = self._cache[date_str][symbol]
        
        return result
    
    def _get_last_trading_day(self) -> datetime:
        """Get the last trading day (skip weekends)"""
        today = datetime.now(timezone.utc)
        
        # If it's before market close (3:30 PM IST = 10:00 AM UTC), use previous day
        if today.hour < 10:
            today = today - timedelta(days=1)
        
        # Skip weekends
        while today.weekday() >= 5:  # Saturday = 5, Sunday = 6
            today = today - timedelta(days=1)
        
        return today
    
    async def download_historical(self, start_date: datetime, end_date: datetime = None) -> Dict[str, List[BhavcopyData]]:
        """
        Download historical Bhavcopy data for a date range.
        
        Args:
            start_date: Start date
            end_date: End date (defaults to today)
            
        Returns:
            Dictionary of date -> list of BhavcopyData
        """
        if end_date is None:
            end_date = datetime.now(timezone.utc)
        
        result = {}
        current = start_date
        
        while current <= end_date:
            # Skip weekends
            if current.weekday() < 5:
                date_str = current.strftime("%Y-%m-%d")
                data = await self.download_bhavcopy(current)
                if data:
                    result[date_str] = data
                
                # Rate limiting - don't hammer NSE servers
                await asyncio.sleep(1)
            
            current += timedelta(days=1)
        
        return result
    
    def get_metrics(self) -> Dict:
        """Get extraction metrics"""
        return self.metrics.to_dict()
    
    def get_cached_dates(self) -> List[str]:
        """Get list of dates in cache"""
        return list(self._cache.keys())
    
    def clear_cache(self):
        """Clear the data cache"""
        self._cache.clear()
        logger.info("Bhavcopy cache cleared")


# Global instance
_bhavcopy_extractor: Optional[NSEBhavcopyExtractor] = None


def get_bhavcopy_extractor() -> NSEBhavcopyExtractor:
    """Get the global Bhavcopy extractor instance"""
    global _bhavcopy_extractor
    if _bhavcopy_extractor is None:
        _bhavcopy_extractor = NSEBhavcopyExtractor()
    return _bhavcopy_extractor
