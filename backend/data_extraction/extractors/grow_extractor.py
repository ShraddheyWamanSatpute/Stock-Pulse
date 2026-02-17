"""
Groww API Extractor for Indian Stock Market Data
Implements data extraction with retry mechanism, rate limiting, and comprehensive logging
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
import os
import json
from dataclasses import dataclass, field
from enum import Enum
import time
import hashlib

logger = logging.getLogger(__name__)


class ExtractionStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    RETRYING = "retrying"


class RateLimitError(Exception):
    """Raised when API rate limit is exceeded"""
    pass


class AuthenticationError(Exception):
    """Raised when API authentication fails"""
    pass


@dataclass
class APIMetrics:
    """Tracks API call metrics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    retry_count: int = 0
    rate_limit_hits: int = 0
    total_latency_ms: float = 0
    min_latency_ms: float = float('inf')
    max_latency_ms: float = 0
    last_request_time: Optional[datetime] = None
    errors: List[Dict] = field(default_factory=list)
    
    @property
    def avg_latency_ms(self) -> float:
        if self.total_requests == 0:
            return 0
        return self.total_latency_ms / self.total_requests
    
    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0
        return (self.successful_requests / self.total_requests) * 100
    
    def to_dict(self) -> Dict:
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "retry_count": self.retry_count,
            "rate_limit_hits": self.rate_limit_hits,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "min_latency_ms": round(self.min_latency_ms, 2) if self.min_latency_ms != float('inf') else 0,
            "max_latency_ms": round(self.max_latency_ms, 2),
            "success_rate": round(self.success_rate, 2),
            "last_request_time": self.last_request_time.isoformat() if self.last_request_time else None,
            "recent_errors": self.errors[-10:]  # Last 10 errors
        }


@dataclass
class ExtractionResult:
    """Result of an extraction operation"""
    status: ExtractionStatus
    symbol: str
    data: Optional[Dict] = None
    error: Optional[str] = None
    retries: int = 0
    latency_ms: float = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict:
        return {
            "status": self.status.value,
            "symbol": self.symbol,
            "data": self.data,
            "error": self.error,
            "retries": self.retries,
            "latency_ms": round(self.latency_ms, 2),
            "timestamp": self.timestamp.isoformat()
        }


class GrowwAPIExtractor:
    """
    Groww API Extractor with comprehensive error handling,
    retry mechanism, and monitoring capabilities
    """
    
    # API Configuration
    BASE_URL = "https://api.groww.in/v1"
    
    # Rate Limits (per API documentation)
    RATE_LIMITS = {
        "live_data": {"per_second": 10, "per_minute": 300},
        "orders": {"per_second": 10, "per_minute": 250},
        "non_trading": {"per_second": 20, "per_minute": 500}
    }
    
    # Retry Configuration
    MAX_RETRIES = 5
    INITIAL_BACKOFF_SECONDS = 2
    MAX_BACKOFF_SECONDS = 60
    BACKOFF_MULTIPLIER = 2
    
    def __init__(self, api_key: str, db=None):
        """
        Initialize the Groww API extractor
        
        Args:
            api_key: Groww API authentication token
            db: MongoDB database instance for storing results
        """
        self.api_key = api_key
        self.db = db
        self.metrics = APIMetrics()
        self.session: Optional[aiohttp.ClientSession] = None
        self._request_timestamps: List[float] = []
        self._last_request_time = 0
        self._is_initialized = False
        
        # Extraction state tracking
        self._extraction_jobs: Dict[str, Dict] = {}
        self._extraction_history: List[Dict] = []
        
    async def initialize(self):
        """Initialize the HTTP session and validate API key"""
        if self._is_initialized:
            return
            
        self.session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            timeout=aiohttp.ClientTimeout(total=30)
        )
        
        # Validate API key with a test request
        try:
            test_result = await self._test_api_connection()
            if not test_result["success"]:
                logger.warning(f"API validation warning: {test_result.get('message', 'Unknown issue')}")
            else:
                logger.info("Groww API connection validated successfully")
        except Exception as e:
            logger.warning(f"API validation skipped due to error: {e}")
        
        self._is_initialized = True
        
    async def close(self):
        """Close the HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
        self._is_initialized = False
    
    async def _test_api_connection(self) -> Dict:
        """Test API connection and validate credentials"""
        try:
            # Try to get a simple quote to validate the API key
            start_time = time.time()
            async with self.session.get(
                f"{self.BASE_URL}/data/quote",
                params={"exchange": "NSE", "segment": "CASH", "trading_symbol": "RELIANCE"}
            ) as response:
                latency = (time.time() - start_time) * 1000
                
                if response.status == 200:
                    return {"success": True, "latency_ms": latency, "message": "API connection successful"}
                elif response.status == 401:
                    return {"success": False, "message": "Authentication failed - invalid API key"}
                elif response.status == 403:
                    return {"success": False, "message": "Access forbidden - check API permissions"}
                else:
                    text = await response.text()
                    return {"success": False, "message": f"API returned status {response.status}: {text[:200]}"}
        except asyncio.TimeoutError:
            return {"success": False, "message": "Connection timeout"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def _calculate_backoff(self, retry_count: int) -> float:
        """Calculate exponential backoff with jitter"""
        import random
        backoff = min(
            self.INITIAL_BACKOFF_SECONDS * (self.BACKOFF_MULTIPLIER ** retry_count),
            self.MAX_BACKOFF_SECONDS
        )
        # Add jitter (±25%)
        jitter = backoff * 0.25 * (random.random() * 2 - 1)
        return backoff + jitter
    
    async def _rate_limit_check(self):
        """Check and enforce rate limiting"""
        current_time = time.time()
        
        # Clean old timestamps (older than 60 seconds)
        self._request_timestamps = [
            ts for ts in self._request_timestamps
            if current_time - ts < 60
        ]
        
        # Check per-minute limit
        if len(self._request_timestamps) >= self.RATE_LIMITS["live_data"]["per_minute"]:
            self.metrics.rate_limit_hits += 1
            wait_time = 60 - (current_time - self._request_timestamps[0])
            if wait_time > 0:
                logger.warning(f"Rate limit reached, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
        
        # Check per-second limit (at least 100ms between requests)
        time_since_last = current_time - self._last_request_time
        if time_since_last < 0.1:
            await asyncio.sleep(0.1 - time_since_last)
        
        self._request_timestamps.append(time.time())
        self._last_request_time = time.time()
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Tuple[bool, Dict, float]:
        """
        Make an API request with rate limiting
        
        Returns:
            Tuple of (success, response_data, latency_ms)
        """
        if not self._is_initialized:
            await self.initialize()
        
        await self._rate_limit_check()
        
        url = f"{self.BASE_URL}{endpoint}"
        start_time = time.time()
        
        try:
            if method.upper() == "GET":
                async with self.session.get(url, params=params) as response:
                    latency = (time.time() - start_time) * 1000
                    return await self._process_response(response, latency)
            elif method.upper() == "POST":
                async with self.session.post(url, json=data, params=params) as response:
                    latency = (time.time() - start_time) * 1000
                    return await self._process_response(response, latency)
        except asyncio.TimeoutError:
            latency = (time.time() - start_time) * 1000
            return False, {"error": "Request timeout"}, latency
        except aiohttp.ClientError as e:
            latency = (time.time() - start_time) * 1000
            return False, {"error": f"Client error: {str(e)}"}, latency
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            return False, {"error": f"Unexpected error: {str(e)}"}, latency
    
    async def _process_response(self, response: aiohttp.ClientResponse, latency: float) -> Tuple[bool, Dict, float]:
        """Process API response and handle errors"""
        self.metrics.total_requests += 1
        self.metrics.total_latency_ms += latency
        self.metrics.min_latency_ms = min(self.metrics.min_latency_ms, latency)
        self.metrics.max_latency_ms = max(self.metrics.max_latency_ms, latency)
        self.metrics.last_request_time = datetime.now(timezone.utc)
        
        try:
            if response.status == 200:
                self.metrics.successful_requests += 1
                data = await response.json()
                return True, data, latency
            elif response.status == 429:
                # Rate limit exceeded
                self.metrics.rate_limit_hits += 1
                self.metrics.failed_requests += 1
                return False, {"error": "Rate limit exceeded", "code": 429}, latency
            elif response.status == 401:
                self.metrics.failed_requests += 1
                return False, {"error": "Authentication failed", "code": 401}, latency
            else:
                self.metrics.failed_requests += 1
                text = await response.text()
                return False, {"error": f"API error: {text[:500]}", "code": response.status}, latency
        except Exception as e:
            self.metrics.failed_requests += 1
            return False, {"error": f"Response processing error: {str(e)}"}, latency
    
    async def get_stock_quote(
        self,
        symbol: str,
        exchange: str = "NSE",
        segment: str = "CASH"
    ) -> ExtractionResult:
        """
        Get real-time stock quote with retry mechanism
        
        Args:
            symbol: Stock trading symbol (e.g., "RELIANCE")
            exchange: Exchange ("NSE" or "BSE")
            segment: Market segment ("CASH", "FNO", etc.)
        """
        retries = 0
        last_error = None
        
        while retries <= self.MAX_RETRIES:
            try:
                start_time = time.time()
                
                success, data, latency = await self._make_request(
                    "GET",
                    "/data/quote",
                    params={
                        "exchange": exchange,
                        "segment": segment,
                        "trading_symbol": symbol
                    }
                )
                
                if success:
                    return ExtractionResult(
                        status=ExtractionStatus.SUCCESS,
                        symbol=symbol,
                        data=self._transform_quote_data(data, symbol),
                        retries=retries,
                        latency_ms=latency
                    )
                elif data.get("code") == 429:
                    # Rate limit - wait and retry
                    retries += 1
                    self.metrics.retry_count += 1
                    backoff = self._calculate_backoff(retries)
                    logger.warning(f"Rate limit for {symbol}, retry {retries}/{self.MAX_RETRIES} after {backoff:.2f}s")
                    await asyncio.sleep(backoff)
                    continue
                else:
                    last_error = data.get("error", "Unknown error")
                    retries += 1
                    self.metrics.retry_count += 1
                    
                    if retries <= self.MAX_RETRIES:
                        backoff = self._calculate_backoff(retries)
                        logger.warning(f"Request failed for {symbol}: {last_error}, retry {retries}/{self.MAX_RETRIES} after {backoff:.2f}s")
                        await asyncio.sleep(backoff)
                        
            except Exception as e:
                last_error = str(e)
                retries += 1
                self.metrics.retry_count += 1
                
                if retries <= self.MAX_RETRIES:
                    backoff = self._calculate_backoff(retries)
                    logger.warning(f"Exception for {symbol}: {e}, retry {retries}/{self.MAX_RETRIES} after {backoff:.2f}s")
                    await asyncio.sleep(backoff)
        
        # All retries exhausted
        self.metrics.errors.append({
            "symbol": symbol,
            "error": last_error,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return ExtractionResult(
            status=ExtractionStatus.FAILED,
            symbol=symbol,
            error=last_error,
            retries=retries - 1,
            latency_ms=0
        )
    
    async def get_historical_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d",
        exchange: str = "NSE"
    ) -> ExtractionResult:
        """
        Get historical OHLCV data with retry mechanism
        
        Args:
            symbol: Stock trading symbol
            start_date: Start date for historical data
            end_date: End date for historical data
            interval: Candle interval ("1", "5", "10", "60", "1440" for 1d)
            exchange: Exchange ("NSE" or "BSE")
        """
        # Map interval to minutes
        interval_map = {
            "1m": "1",
            "5m": "5",
            "10m": "10",
            "1h": "60",
            "4h": "240",
            "1d": "1440",
            "1w": "10080"
        }
        candle_interval = interval_map.get(interval, interval)
        
        retries = 0
        last_error = None
        
        while retries <= self.MAX_RETRIES:
            try:
                success, data, latency = await self._make_request(
                    "GET",
                    "/historical/candles",
                    params={
                        "exchange": exchange,
                        "segment": "CASH",
                        "trading_symbol": symbol,
                        "start_time": start_date.strftime("%Y-%m-%d %H:%M:%S"),
                        "end_time": end_date.strftime("%Y-%m-%d %H:%M:%S"),
                        "candle_interval": candle_interval
                    }
                )
                
                if success:
                    return ExtractionResult(
                        status=ExtractionStatus.SUCCESS,
                        symbol=symbol,
                        data=self._transform_historical_data(data, symbol),
                        retries=retries,
                        latency_ms=latency
                    )
                elif data.get("code") == 429:
                    retries += 1
                    self.metrics.retry_count += 1
                    backoff = self._calculate_backoff(retries)
                    logger.warning(f"Rate limit for historical {symbol}, retry {retries}/{self.MAX_RETRIES}")
                    await asyncio.sleep(backoff)
                    continue
                else:
                    last_error = data.get("error", "Unknown error")
                    retries += 1
                    self.metrics.retry_count += 1
                    
                    if retries <= self.MAX_RETRIES:
                        backoff = self._calculate_backoff(retries)
                        await asyncio.sleep(backoff)
                        
            except Exception as e:
                last_error = str(e)
                retries += 1
                self.metrics.retry_count += 1
                
                if retries <= self.MAX_RETRIES:
                    backoff = self._calculate_backoff(retries)
                    await asyncio.sleep(backoff)
        
        self.metrics.errors.append({
            "symbol": symbol,
            "error": last_error,
            "type": "historical",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return ExtractionResult(
            status=ExtractionStatus.FAILED,
            symbol=symbol,
            error=last_error,
            retries=retries - 1,
            latency_ms=0
        )
    
    def _transform_quote_data(self, raw_data: Dict, symbol: str) -> Dict:
        """Transform raw quote data to standardized format"""
        try:
            return {
                "symbol": symbol,
                "last_price": raw_data.get("last_price", raw_data.get("ltp", 0)),
                "open": raw_data.get("open", 0),
                "high": raw_data.get("high", 0),
                "low": raw_data.get("low", 0),
                "close": raw_data.get("close", 0),
                "prev_close": raw_data.get("prev_close", raw_data.get("previous_close", 0)),
                "volume": raw_data.get("volume", 0),
                "change": raw_data.get("change", 0),
                "change_percent": raw_data.get("change_percent", raw_data.get("pct_change", 0)),
                "bid": raw_data.get("bid", 0),
                "ask": raw_data.get("ask", 0),
                "upper_circuit": raw_data.get("upper_circuit_limit", 0),
                "lower_circuit": raw_data.get("lower_circuit_limit", 0),
                "oi": raw_data.get("oi", raw_data.get("open_interest", 0)),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "raw_response": raw_data
            }
        except Exception as e:
            logger.error(f"Error transforming quote data for {symbol}: {e}")
            return {"symbol": symbol, "error": str(e), "raw_response": raw_data}
    
    def _transform_historical_data(self, raw_data: Dict, symbol: str) -> Dict:
        """Transform raw historical data to standardized format"""
        try:
            candles = raw_data.get("candles", [])
            transformed_candles = []
            
            for candle in candles:
                # Candles format: [timestamp, open, high, low, close, volume]
                if isinstance(candle, list) and len(candle) >= 6:
                    transformed_candles.append({
                        "timestamp": candle[0],
                        "open": candle[1],
                        "high": candle[2],
                        "low": candle[3],
                        "close": candle[4],
                        "volume": candle[5]
                    })
            
            return {
                "symbol": symbol,
                "start_time": raw_data.get("start_time"),
                "end_time": raw_data.get("end_time"),
                "interval": raw_data.get("interval_in_minutes"),
                "candle_count": len(transformed_candles),
                "candles": transformed_candles,
                "extracted_at": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Error transforming historical data for {symbol}: {e}")
            return {"symbol": symbol, "error": str(e), "raw_response": raw_data}
    
    async def extract_bulk_quotes(
        self,
        symbols: List[str],
        exchange: str = "NSE"
    ) -> Dict[str, ExtractionResult]:
        """
        Extract quotes for multiple symbols with progress tracking
        
        Args:
            symbols: List of stock symbols to extract
            exchange: Exchange to query
            
        Returns:
            Dictionary of symbol -> ExtractionResult
        """
        job_id = hashlib.md5(f"{symbols}{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        
        self._extraction_jobs[job_id] = {
            "id": job_id,
            "status": "running",
            "total_symbols": len(symbols),
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None
        }
        
        results = {}
        
        for i, symbol in enumerate(symbols):
            result = await self.get_stock_quote(symbol, exchange=exchange)
            results[symbol] = result
            
            self._extraction_jobs[job_id]["processed"] = i + 1
            if result.status == ExtractionStatus.SUCCESS:
                self._extraction_jobs[job_id]["successful"] += 1
            else:
                self._extraction_jobs[job_id]["failed"] += 1
        
        self._extraction_jobs[job_id]["status"] = "completed"
        self._extraction_jobs[job_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
        
        # Add to history
        self._extraction_history.append({
            **self._extraction_jobs[job_id],
            "results_summary": {
                s: r.status.value for s, r in results.items()
            }
        })
        
        # Keep only last 100 jobs in history
        if len(self._extraction_history) > 100:
            self._extraction_history = self._extraction_history[-100:]
        
        return results
    
    def get_metrics(self) -> Dict:
        """Get current API metrics"""
        return self.metrics.to_dict()
    
    def get_extraction_jobs(self) -> List[Dict]:
        """Get list of extraction jobs"""
        return list(self._extraction_jobs.values())
    
    def get_extraction_history(self) -> List[Dict]:
        """Get extraction history"""
        return self._extraction_history
    
    def reset_metrics(self):
        """Reset API metrics"""
        self.metrics = APIMetrics()
