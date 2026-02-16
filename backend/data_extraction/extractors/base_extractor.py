"""
Abstract base class for all data extraction modules.

Provides common functionality for rate limiting, retry logic, session management,
error handling, and extraction record tracking.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp

from ..config.source_config import SourceConfig, RateLimitConfig
from ..models.extraction_models import ExtractionRecord, ExtractionStatus, StockDataRecord

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token-bucket rate limiter for HTTP requests."""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self._request_times: List[float] = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until a request slot is available."""
        async with self._lock:
            now = time.monotonic()
            # Remove requests older than 60 seconds
            self._request_times = [
                t for t in self._request_times if now - t < 60
            ]
            if len(self._request_times) >= self.config.requests_per_minute:
                sleep_time = 60 - (now - self._request_times[0])
                if sleep_time > 0:
                    logger.debug(f"Rate limit reached, sleeping {sleep_time:.1f}s")
                    await asyncio.sleep(sleep_time)

            # Enforce minimum delay between requests
            if self._request_times:
                elapsed = now - self._request_times[-1]
                if elapsed < self.config.min_delay_seconds:
                    await asyncio.sleep(self.config.min_delay_seconds - elapsed)

            self._request_times.append(time.monotonic())


class BaseExtractor(ABC):
    """
    Abstract base class for all data source extractors.

    Subclasses must implement:
        - extract(): Main extraction logic for a single symbol
        - get_source_name(): Returns the data source identifier
        - get_provided_fields(): Lists which fields this extractor provides
    """

    def __init__(self, config: SourceConfig):
        self.config = config
        self.rate_limiter = RateLimiter(config.rate_limit)
        self._session: Optional[aiohttp.ClientSession] = None
        self._is_initialized = False

    async def initialize(self) -> None:
        """Initialize the HTTP session and any source-specific setup."""
        if not self._is_initialized:
            self._session = aiohttp.ClientSession(
                headers=self.config.headers,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds),
            )
            self._is_initialized = True
            logger.info(f"{self.get_source_name()} extractor initialized")

    async def close(self) -> None:
        """Close the HTTP session and clean up resources."""
        if self._session and not self._session.closed:
            await self._session.close()
        self._is_initialized = False

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    @abstractmethod
    def get_source_name(self) -> str:
        """Return the unique identifier for this data source."""
        ...

    @abstractmethod
    def get_provided_fields(self) -> List[str]:
        """Return list of field names this extractor can provide."""
        ...

    @abstractmethod
    async def extract(self, symbol: str, record: StockDataRecord) -> ExtractionRecord:
        """
        Extract data for a single stock symbol.

        Args:
            symbol: The stock symbol to extract data for
            record: The StockDataRecord to populate

        Returns:
            ExtractionRecord with status and metadata
        """
        ...

    async def extract_batch(
        self, symbols: List[str], records: Dict[str, StockDataRecord]
    ) -> List[ExtractionRecord]:
        """
        Extract data for multiple symbols sequentially with rate limiting.

        Args:
            symbols: List of stock symbols
            records: Dict mapping symbol to StockDataRecord

        Returns:
            List of ExtractionRecords
        """
        results = []
        for symbol in symbols:
            record = records.get(symbol)
            if not record:
                record = StockDataRecord(symbol=symbol, company_name="")
                records[symbol] = record
            try:
                result = await self.extract(symbol, record)
                results.append(result)
            except Exception as e:
                logger.error(f"Error extracting {symbol} from {self.get_source_name()}: {e}")
                results.append(ExtractionRecord(
                    source=self.get_source_name(),
                    symbol=symbol,
                    fields_extracted=[],
                    fields_failed=self.get_provided_fields(),
                    status=ExtractionStatus.FAILED,
                    started_at=datetime.utcnow(),
                    completed_at=datetime.utcnow(),
                    error_message=str(e),
                ))
        return results

    async def _fetch_url(self, url: str, params: Optional[Dict] = None) -> Optional[str]:
        """
        Fetch a URL with rate limiting and retry logic.

        Returns the response text, or None on failure.
        """
        if not self._session:
            await self.initialize()

        for attempt in range(self.config.rate_limit.max_retries + 1):
            try:
                await self.rate_limiter.acquire()
                async with self._session.get(url, params=params) as response:
                    if response.status == 200:
                        return await response.text()
                    elif response.status == 429:
                        # Rate limited - exponential backoff
                        wait = self.config.rate_limit.retry_backoff_factor ** attempt * 2
                        logger.warning(f"Rate limited by {self.get_source_name()}, "
                                       f"waiting {wait:.1f}s (attempt {attempt + 1})")
                        await asyncio.sleep(wait)
                    elif response.status >= 500:
                        # Server error - retry
                        wait = self.config.rate_limit.retry_backoff_factor ** attempt
                        logger.warning(f"Server error {response.status} from "
                                       f"{self.get_source_name()}, retrying in {wait:.1f}s")
                        await asyncio.sleep(wait)
                    else:
                        logger.error(f"HTTP {response.status} from {url}")
                        return None
            except asyncio.TimeoutError:
                logger.warning(f"Timeout fetching {url} (attempt {attempt + 1})")
                if attempt < self.config.rate_limit.max_retries:
                    await asyncio.sleep(self.config.rate_limit.retry_backoff_factor ** attempt)
            except aiohttp.ClientError as e:
                logger.error(f"Client error fetching {url}: {e}")
                if attempt < self.config.rate_limit.max_retries:
                    await asyncio.sleep(self.config.rate_limit.retry_backoff_factor ** attempt)

        return None

    async def _fetch_json(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Fetch a URL and parse as JSON."""
        if not self._session:
            await self.initialize()

        for attempt in range(self.config.rate_limit.max_retries + 1):
            try:
                await self.rate_limiter.acquire()
                async with self._session.get(url, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:
                        wait = self.config.rate_limit.retry_backoff_factor ** attempt * 2
                        await asyncio.sleep(wait)
                    elif response.status >= 500:
                        wait = self.config.rate_limit.retry_backoff_factor ** attempt
                        await asyncio.sleep(wait)
                    else:
                        logger.error(f"HTTP {response.status} from {url}")
                        return None
            except (asyncio.TimeoutError, aiohttp.ClientError) as e:
                logger.warning(f"Error fetching JSON from {url}: {e}")
                if attempt < self.config.rate_limit.max_retries:
                    await asyncio.sleep(self.config.rate_limit.retry_backoff_factor ** attempt)

        return None

    async def _download_file(self, url: str, dest_path: str) -> bool:
        """Download a file (e.g., CSV, ZIP) to disk."""
        if not self._session:
            await self.initialize()

        try:
            await self.rate_limiter.acquire()
            async with self._session.get(url) as response:
                if response.status == 200:
                    with open(dest_path, 'wb') as f:
                        while True:
                            chunk = await response.content.read(8192)
                            if not chunk:
                                break
                            f.write(chunk)
                    return True
                else:
                    logger.error(f"Failed to download {url}: HTTP {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Error downloading {url}: {e}")
            return False

    def _create_extraction_record(
        self,
        symbol: str,
        started_at: datetime,
        fields_extracted: List[str],
        fields_failed: List[str],
        error_message: Optional[str] = None,
    ) -> ExtractionRecord:
        """Helper to create a standardized ExtractionRecord."""
        completed_at = datetime.utcnow()
        duration = int((completed_at - started_at).total_seconds() * 1000)

        if error_message and not fields_extracted:
            status = ExtractionStatus.FAILED
        elif fields_failed:
            status = ExtractionStatus.PARTIAL
        else:
            status = ExtractionStatus.SUCCESS

        return ExtractionRecord(
            source=self.get_source_name(),
            symbol=symbol,
            fields_extracted=fields_extracted,
            fields_failed=fields_failed,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration,
            error_message=error_message,
        )

    @staticmethod
    def safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
        """Safely convert a value to float."""
        if value is None:
            return default
        try:
            if isinstance(value, str):
                value = value.replace(",", "").replace("%", "").strip()
                if not value or value == "-" or value.lower() == "nan":
                    return default
            return float(value)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def safe_int(value: Any, default: Optional[int] = None) -> Optional[int]:
        """Safely convert a value to int."""
        if value is None:
            return default
        try:
            if isinstance(value, str):
                value = value.replace(",", "").strip()
                if not value or value == "-":
                    return default
            return int(float(value))
        except (ValueError, TypeError):
            return default
