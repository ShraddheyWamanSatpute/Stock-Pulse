"""
Source configuration for all data extraction modules.

Defines URLs, rate limits, selectors, headers, and extraction parameters
for each data source used in the pipeline.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class RateLimitConfig:
    requests_per_minute: int = 30
    requests_per_hour: int = 500
    min_delay_seconds: float = 2.0
    max_retries: int = 3
    retry_backoff_factor: float = 2.0


@dataclass
class SourceConfig:
    name: str
    base_url: str
    rate_limit: RateLimitConfig
    headers: Dict[str, str] = field(default_factory=dict)
    requires_auth: bool = False
    timeout_seconds: int = 30
    enabled: bool = True


# NSE Bhavcopy - Daily CSV download
NSE_BHAVCOPY_CONFIG = SourceConfig(
    name="NSE Bhavcopy",
    base_url="https://archives.nseindia.com/content/historical/EQUITIES",
    rate_limit=RateLimitConfig(
        requests_per_minute=10,
        requests_per_hour=100,
        min_delay_seconds=3.0,
    ),
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Referer": "https://www.nseindia.com/",
    },
    timeout_seconds=60,
)

# NSE delivery data
NSE_DELIVERY_CONFIG = SourceConfig(
    name="NSE Delivery",
    base_url="https://archives.nseindia.com/products/content",
    rate_limit=RateLimitConfig(
        requests_per_minute=10,
        requests_per_hour=100,
        min_delay_seconds=3.0,
    ),
    headers=NSE_BHAVCOPY_CONFIG.headers.copy(),
    timeout_seconds=60,
)

# Screener.in - Financial data scraper
SCREENER_CONFIG = SourceConfig(
    name="Screener.in",
    base_url="https://www.screener.in",
    rate_limit=RateLimitConfig(
        requests_per_minute=15,
        requests_per_hour=200,
        min_delay_seconds=4.0,
        max_retries=2,
    ),
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    },
    timeout_seconds=30,
)

# BSE India - Filings and announcements
BSE_CONFIG = SourceConfig(
    name="BSE India",
    base_url="https://api.bseindia.com/BseIndiaAPI/api",
    rate_limit=RateLimitConfig(
        requests_per_minute=20,
        requests_per_hour=300,
        min_delay_seconds=3.0,
    ),
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://www.bseindia.com/",
        "Origin": "https://www.bseindia.com",
    },
    timeout_seconds=30,
)

# Trendlyne - Forward estimates, institutional data
TRENDLYNE_CONFIG = SourceConfig(
    name="Trendlyne",
    base_url="https://trendlyne.com",
    rate_limit=RateLimitConfig(
        requests_per_minute=10,
        requests_per_hour=150,
        min_delay_seconds=5.0,
        max_retries=2,
    ),
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    },
    timeout_seconds=30,
)

# Yahoo Finance via yfinance
YFINANCE_CONFIG = SourceConfig(
    name="Yahoo Finance",
    base_url="https://query2.finance.yahoo.com",
    rate_limit=RateLimitConfig(
        requests_per_minute=30,
        requests_per_hour=500,
        min_delay_seconds=1.0,
    ),
    timeout_seconds=30,
)

# RSS Feeds - Multiple sources
RSS_FEED_URLS = [
    "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "https://www.livemint.com/rss/markets",
    "https://www.moneycontrol.com/rss/marketreports.xml",
    "https://www.business-standard.com/rss/markets-106.rss",
]

RSS_CONFIG = SourceConfig(
    name="RSS Feeds",
    base_url="",
    rate_limit=RateLimitConfig(
        requests_per_minute=60,
        requests_per_hour=1000,
        min_delay_seconds=0.5,
    ),
    headers={
        "User-Agent": "StockPulse/1.0 RSS Reader",
    },
    timeout_seconds=15,
)

# Rating agencies
RATING_AGENCIES_CONFIG = SourceConfig(
    name="Rating Agencies",
    base_url="",
    rate_limit=RateLimitConfig(
        requests_per_minute=5,
        requests_per_hour=50,
        min_delay_seconds=10.0,
    ),
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    },
    timeout_seconds=30,
)

RATING_AGENCY_URLS = {
    "CRISIL": "https://www.crisil.com/en/home/our-analysis/ratings/rating-list.html",
    "ICRA": "https://www.icra.in/Rationale/RatingList",
    "CARE": "https://www.careedge.in/ratings/credit-rating-list",
    "India Ratings": "https://www.indiaratings.co.in/",
}


# NSE Index URLs
NSE_INDEX_CONFIG = SourceConfig(
    name="NSE Indices",
    base_url="https://www.nseindia.com/api",
    rate_limit=RateLimitConfig(
        requests_per_minute=10,
        requests_per_hour=100,
        min_delay_seconds=3.0,
    ),
    headers=NSE_BHAVCOPY_CONFIG.headers.copy(),
    timeout_seconds=30,
)

# Map of sector to NSE sector index symbols
SECTOR_INDEX_MAP = {
    "IT": "NIFTY IT",
    "Banking": "NIFTY BANK",
    "Financial Services": "NIFTY FINANCIAL SERVICES",
    "Pharma": "NIFTY PHARMA",
    "Auto": "NIFTY AUTO",
    "FMCG": "NIFTY FMCG",
    "Metal": "NIFTY METAL",
    "Realty": "NIFTY REALTY",
    "Energy": "NIFTY ENERGY",
    "Infrastructure": "NIFTY INFRA",
    "Media": "NIFTY MEDIA",
    "PSU Bank": "NIFTY PSU BANK",
    "Private Bank": "NIFTY PRIVATE BANK",
}


# Aggregated config lookup
ALL_SOURCES = {
    "nse_bhavcopy": NSE_BHAVCOPY_CONFIG,
    "nse_delivery": NSE_DELIVERY_CONFIG,
    "screener": SCREENER_CONFIG,
    "bse": BSE_CONFIG,
    "trendlyne": TRENDLYNE_CONFIG,
    "yfinance": YFINANCE_CONFIG,
    "rss": RSS_CONFIG,
    "rating_agencies": RATING_AGENCIES_CONFIG,
    "nse_indices": NSE_INDEX_CONFIG,
}
