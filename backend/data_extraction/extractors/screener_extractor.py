"""
Screener.in Financial Data Extractor
Scrapes fundamental data from Screener.in including:
- Income Statement (Revenue, Profit, EPS, Margins)
- Balance Sheet (Assets, Debt, Equity)
- Cash Flow (OCF, FCF, CapEx)
- Financial Ratios (ROE, ROCE, D/E)
- Shareholding Pattern (Promoter, FII, DII)
"""

import asyncio
import aiohttp
import logging
import re
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class FinancialData:
    """Comprehensive financial data from Screener.in"""
    symbol: str
    company_name: str = ""
    sector: str = ""
    industry: str = ""
    
    # Key Metrics
    market_cap: float = 0.0
    current_price: float = 0.0
    high_low: str = ""
    pe_ratio: float = 0.0
    book_value: float = 0.0
    dividend_yield: float = 0.0
    roce: float = 0.0
    roe: float = 0.0
    face_value: float = 0.0
    
    # Income Statement (Latest)
    revenue: float = 0.0
    revenue_growth_yoy: float = 0.0
    operating_profit: float = 0.0
    operating_margin: float = 0.0
    net_profit: float = 0.0
    net_profit_margin: float = 0.0
    eps: float = 0.0
    eps_growth_yoy: float = 0.0
    
    # Balance Sheet (Latest)
    total_assets: float = 0.0
    total_equity: float = 0.0
    total_debt: float = 0.0
    cash_and_equivalents: float = 0.0
    reserves: float = 0.0
    
    # Cash Flow (Latest)
    operating_cash_flow: float = 0.0
    investing_cash_flow: float = 0.0
    financing_cash_flow: float = 0.0
    free_cash_flow: float = 0.0
    
    # Ratios
    debt_to_equity: float = 0.0
    current_ratio: float = 0.0
    interest_coverage: float = 0.0
    
    # Shareholding
    promoter_holding: float = 0.0
    fii_holding: float = 0.0
    dii_holding: float = 0.0
    public_holding: float = 0.0
    
    # Historical Data
    income_statement_history: List[Dict] = field(default_factory=list)
    balance_sheet_history: List[Dict] = field(default_factory=list)
    cash_flow_history: List[Dict] = field(default_factory=list)
    quarterly_results: List[Dict] = field(default_factory=list)
    shareholding_history: List[Dict] = field(default_factory=list)
    
    # Metadata
    last_updated: str = ""
    data_source: str = "screener.in"
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "company_name": self.company_name,
            "sector": self.sector,
            "industry": self.industry,
            "key_metrics": {
                "market_cap": self.market_cap,
                "current_price": self.current_price,
                "pe_ratio": self.pe_ratio,
                "book_value": self.book_value,
                "dividend_yield": self.dividend_yield,
                "roce": self.roce,
                "roe": self.roe,
                "face_value": self.face_value
            },
            "income_statement": {
                "revenue": self.revenue,
                "revenue_growth_yoy": self.revenue_growth_yoy,
                "operating_profit": self.operating_profit,
                "operating_margin": self.operating_margin,
                "net_profit": self.net_profit,
                "net_profit_margin": self.net_profit_margin,
                "eps": self.eps,
                "eps_growth_yoy": self.eps_growth_yoy
            },
            "balance_sheet": {
                "total_assets": self.total_assets,
                "total_equity": self.total_equity,
                "total_debt": self.total_debt,
                "cash_and_equivalents": self.cash_and_equivalents,
                "reserves": self.reserves
            },
            "cash_flow": {
                "operating_cash_flow": self.operating_cash_flow,
                "investing_cash_flow": self.investing_cash_flow,
                "financing_cash_flow": self.financing_cash_flow,
                "free_cash_flow": self.free_cash_flow
            },
            "ratios": {
                "debt_to_equity": self.debt_to_equity,
                "current_ratio": self.current_ratio,
                "interest_coverage": self.interest_coverage
            },
            "shareholding": {
                "promoter_holding": self.promoter_holding,
                "fii_holding": self.fii_holding,
                "dii_holding": self.dii_holding,
                "public_holding": self.public_holding
            },
            "history": {
                "income_statement": self.income_statement_history[-5:],  # Last 5 years
                "balance_sheet": self.balance_sheet_history[-5:],
                "cash_flow": self.cash_flow_history[-5:],
                "quarterly": self.quarterly_results[-4:],  # Last 4 quarters
                "shareholding": self.shareholding_history[-4:]
            },
            "last_updated": self.last_updated,
            "data_source": self.data_source
        }


@dataclass
class ScreenerMetrics:
    """Metrics for Screener.in extraction"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_companies_scraped: int = 0
    last_request_time: Optional[datetime] = None
    errors: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": round((self.successful_requests / self.total_requests * 100) if self.total_requests > 0 else 0, 2),
            "total_companies_scraped": self.total_companies_scraped,
            "last_request_time": self.last_request_time.isoformat() if self.last_request_time else None,
            "recent_errors": self.errors[-5:]
        }


class ScreenerExtractor:
    """
    Extracts financial data from Screener.in
    Provides Income Statement, Balance Sheet, Cash Flow, and Ratios
    """
    
    BASE_URL = "https://www.screener.in/company"
    
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Referer": "https://www.screener.in/"
    }
    
    # Rate limiting
    REQUEST_DELAY = 2  # seconds between requests
    
    def __init__(self, db=None):
        self.db = db
        self.session: Optional[aiohttp.ClientSession] = None
        self.metrics = ScreenerMetrics()
        self._cache: Dict[str, FinancialData] = {}
        self._is_initialized = False
        self._last_request_time = 0
        
    async def initialize(self):
        """Initialize the HTTP session"""
        if self._is_initialized:
            return
            
        connector = aiohttp.TCPConnector(limit=3, force_close=True)
        timeout = aiohttp.ClientTimeout(total=30)
        
        self.session = aiohttp.ClientSession(
            headers=self.HEADERS,
            connector=connector,
            timeout=timeout
        )
        self._is_initialized = True
        logger.info("Screener.in Extractor initialized")
        
    async def close(self):
        """Close the HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
        self._is_initialized = False
    
    async def _rate_limit(self):
        """Enforce rate limiting"""
        import time
        current_time = time.time()
        elapsed = current_time - self._last_request_time
        if elapsed < self.REQUEST_DELAY:
            await asyncio.sleep(self.REQUEST_DELAY - elapsed)
        self._last_request_time = time.time()
    
    async def get_financial_data(self, symbol: str, consolidated: bool = True) -> Optional[FinancialData]:
        """
        Get comprehensive financial data for a stock.
        
        Args:
            symbol: Stock symbol (e.g., "RELIANCE")
            consolidated: Whether to fetch consolidated financials
            
        Returns:
            FinancialData object or None
        """
        if not self._is_initialized:
            await self.initialize()
        
        # Check cache
        cache_key = f"{symbol}_{consolidated}"
        if cache_key in self._cache:
            logger.info(f"Returning cached data for {symbol}")
            return self._cache[cache_key]
        
        await self._rate_limit()
        self.metrics.total_requests += 1
        
        url = f"{self.BASE_URL}/{symbol}/"
        if consolidated:
            url += "consolidated/"
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    data = self._parse_screener_page(html, symbol)
                    
                    if data:
                        self.metrics.successful_requests += 1
                        self.metrics.total_companies_scraped += 1
                        self.metrics.last_request_time = datetime.now(timezone.utc)
                        
                        # Cache the data
                        self._cache[cache_key] = data
                        
                        logger.info(f"Successfully scraped financial data for {symbol}")
                        return data
                    else:
                        self.metrics.failed_requests += 1
                        logger.warning(f"Failed to parse data for {symbol}")
                        
                elif response.status == 404:
                    self.metrics.failed_requests += 1
                    logger.warning(f"Company not found: {symbol}")
                    self.metrics.errors.append({
                        "symbol": symbol,
                        "error": "Company not found",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                else:
                    self.metrics.failed_requests += 1
                    logger.warning(f"HTTP {response.status} for {symbol}")
                    
        except asyncio.TimeoutError:
            self.metrics.failed_requests += 1
            logger.error(f"Timeout fetching data for {symbol}")
            self.metrics.errors.append({
                "symbol": symbol,
                "error": "Request timeout",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        except Exception as e:
            self.metrics.failed_requests += 1
            logger.error(f"Error fetching data for {symbol}: {e}")
            self.metrics.errors.append({
                "symbol": symbol,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        
        return None
    
    def _parse_screener_page(self, html: str, symbol: str) -> Optional[FinancialData]:
        """Parse Screener.in HTML page"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            data = FinancialData(symbol=symbol)
            
            # Parse company name
            title_elem = soup.find('h1')
            if title_elem:
                data.company_name = title_elem.get_text(strip=True)
            
            # Parse key metrics from the top section
            self._parse_key_metrics(soup, data)
            
            # Parse sector/industry
            self._parse_sector_info(soup, data)
            
            # Parse quarterly results
            self._parse_quarterly_results(soup, data)
            
            # Parse profit & loss
            self._parse_profit_loss(soup, data)
            
            # Parse balance sheet
            self._parse_balance_sheet(soup, data)
            
            # Parse cash flow
            self._parse_cash_flow(soup, data)
            
            # Parse ratios
            self._parse_ratios(soup, data)
            
            # Parse shareholding
            self._parse_shareholding(soup, data)
            
            data.last_updated = datetime.now(timezone.utc).isoformat()
            
            return data
            
        except Exception as e:
            logger.error(f"Error parsing page for {symbol}: {e}")
            return None
    
    def _parse_key_metrics(self, soup: BeautifulSoup, data: FinancialData):
        """Parse key metrics from the top section"""
        try:
            # Find all list items with metrics
            metrics_section = soup.find('ul', {'id': 'top-ratios'})
            if not metrics_section:
                # Try alternate structure
                metrics_section = soup.find('div', class_='company-ratios')
            
            if metrics_section:
                items = metrics_section.find_all('li')
                for item in items:
                    name_elem = item.find('span', class_='name')
                    value_elem = item.find('span', class_='value') or item.find('span', class_='number')
                    
                    if name_elem and value_elem:
                        name = name_elem.get_text(strip=True).lower()
                        value_text = value_elem.get_text(strip=True)
                        
                        if 'market cap' in name:
                            data.market_cap = self._parse_number(value_text)
                        elif 'current price' in name:
                            data.current_price = self._parse_number(value_text)
                        elif 'stock p/e' in name or 'pe' in name:
                            data.pe_ratio = self._parse_number(value_text)
                        elif 'book value' in name:
                            data.book_value = self._parse_number(value_text)
                        elif 'dividend yield' in name:
                            data.dividend_yield = self._parse_number(value_text)
                        elif 'roce' in name:
                            data.roce = self._parse_number(value_text)
                        elif 'roe' in name:
                            data.roe = self._parse_number(value_text)
                        elif 'face value' in name:
                            data.face_value = self._parse_number(value_text)
            
            # Try parsing from script data
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and 'var ratios' in script.string:
                    # Extract JSON data
                    match = re.search(r'var ratios\s*=\s*({.*?});', script.string, re.DOTALL)
                    if match:
                        ratios = json.loads(match.group(1))
                        # Process ratios
                        
        except Exception as e:
            logger.warning(f"Error parsing key metrics: {e}")
    
    def _parse_sector_info(self, soup: BeautifulSoup, data: FinancialData):
        """Parse sector and industry information"""
        try:
            peer_section = soup.find('section', {'id': 'peers'})
            if peer_section:
                links = peer_section.find_all('a')
                for link in links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    if '/market/' in href:
                        if not data.sector:
                            data.sector = text
                        elif not data.industry:
                            data.industry = text
                            break
        except Exception as e:
            logger.warning(f"Error parsing sector info: {e}")
    
    def _parse_quarterly_results(self, soup: BeautifulSoup, data: FinancialData):
        """Parse quarterly results table"""
        try:
            quarters_section = soup.find('section', {'id': 'quarters'})
            if quarters_section:
                table = quarters_section.find('table')
                if table:
                    data.quarterly_results = self._parse_table(table)
        except Exception as e:
            logger.warning(f"Error parsing quarterly results: {e}")
    
    def _parse_profit_loss(self, soup: BeautifulSoup, data: FinancialData):
        """Parse profit & loss statement"""
        try:
            pl_section = soup.find('section', {'id': 'profit-loss'})
            if pl_section:
                table = pl_section.find('table')
                if table:
                    history = self._parse_table(table)
                    data.income_statement_history = history
                    
                    if history:
                        latest = history[-1] if history else {}
                        data.revenue = self._safe_float(latest.get('Sales', latest.get('Revenue', 0)))
                        data.operating_profit = self._safe_float(latest.get('Operating Profit', 0))
                        data.net_profit = self._safe_float(latest.get('Net Profit', 0))
                        data.eps = self._safe_float(latest.get('EPS in Rs', latest.get('EPS', 0)))
                        
                        # Calculate margins
                        if data.revenue > 0:
                            data.operating_margin = round((data.operating_profit / data.revenue) * 100, 2)
                            data.net_profit_margin = round((data.net_profit / data.revenue) * 100, 2)
                        
                        # Calculate growth
                        if len(history) >= 2:
                            prev = history[-2]
                            prev_revenue = self._safe_float(prev.get('Sales', prev.get('Revenue', 0)))
                            prev_eps = self._safe_float(prev.get('EPS in Rs', prev.get('EPS', 0)))
                            
                            if prev_revenue > 0:
                                data.revenue_growth_yoy = round(((data.revenue - prev_revenue) / prev_revenue) * 100, 2)
                            if prev_eps > 0:
                                data.eps_growth_yoy = round(((data.eps - prev_eps) / prev_eps) * 100, 2)
                                
        except Exception as e:
            logger.warning(f"Error parsing profit & loss: {e}")
    
    def _parse_balance_sheet(self, soup: BeautifulSoup, data: FinancialData):
        """Parse balance sheet"""
        try:
            bs_section = soup.find('section', {'id': 'balance-sheet'})
            if bs_section:
                table = bs_section.find('table')
                if table:
                    history = self._parse_table(table)
                    data.balance_sheet_history = history
                    
                    if history:
                        latest = history[-1] if history else {}
                        data.total_equity = self._safe_float(latest.get('Reserves', 0)) + self._safe_float(latest.get('Equity Capital', 0))
                        data.total_debt = self._safe_float(latest.get('Borrowings', latest.get('Total Debt', 0)))
                        data.reserves = self._safe_float(latest.get('Reserves', 0))
                        data.total_assets = self._safe_float(latest.get('Total Assets', latest.get('Total Liabilities', 0)))
                        
                        # Calculate D/E ratio
                        if data.total_equity > 0:
                            data.debt_to_equity = round(data.total_debt / data.total_equity, 2)
                            
        except Exception as e:
            logger.warning(f"Error parsing balance sheet: {e}")
    
    def _parse_cash_flow(self, soup: BeautifulSoup, data: FinancialData):
        """Parse cash flow statement"""
        try:
            cf_section = soup.find('section', {'id': 'cash-flow'})
            if cf_section:
                table = cf_section.find('table')
                if table:
                    history = self._parse_table(table)
                    data.cash_flow_history = history
                    
                    if history:
                        latest = history[-1] if history else {}
                        data.operating_cash_flow = self._safe_float(latest.get('Cash from Operating Activity', 0))
                        data.investing_cash_flow = self._safe_float(latest.get('Cash from Investing Activity', 0))
                        data.financing_cash_flow = self._safe_float(latest.get('Cash from Financing Activity', 0))
                        
                        # FCF = OCF - CapEx (approximate from investing activities)
                        data.free_cash_flow = data.operating_cash_flow + min(data.investing_cash_flow, 0)
                        
        except Exception as e:
            logger.warning(f"Error parsing cash flow: {e}")
    
    def _parse_ratios(self, soup: BeautifulSoup, data: FinancialData):
        """Parse financial ratios"""
        try:
            ratios_section = soup.find('section', {'id': 'ratios'})
            if ratios_section:
                table = ratios_section.find('table')
                if table:
                    ratios = self._parse_table(table)
                    if ratios:
                        latest = ratios[-1] if ratios else {}
                        data.roce = data.roce or self._safe_float(latest.get('ROCE %', 0))
        except Exception as e:
            logger.warning(f"Error parsing ratios: {e}")
    
    def _parse_shareholding(self, soup: BeautifulSoup, data: FinancialData):
        """Parse shareholding pattern"""
        try:
            sh_section = soup.find('section', {'id': 'shareholding'})
            if sh_section:
                table = sh_section.find('table')
                if table:
                    history = self._parse_table(table)
                    data.shareholding_history = history
                    
                    if history:
                        latest = history[-1] if history else {}
                        data.promoter_holding = self._safe_float(latest.get('Promoters', '0').replace('%', ''))
                        data.fii_holding = self._safe_float(latest.get('FIIs', '0').replace('%', ''))
                        data.dii_holding = self._safe_float(latest.get('DIIs', '0').replace('%', ''))
                        data.public_holding = self._safe_float(latest.get('Public', '0').replace('%', ''))
                        
        except Exception as e:
            logger.warning(f"Error parsing shareholding: {e}")
    
    def _parse_table(self, table) -> List[Dict]:
        """Parse an HTML table into a list of dictionaries"""
        result = []
        try:
            headers = []
            header_row = table.find('thead')
            if header_row:
                ths = header_row.find_all('th')
                headers = [th.get_text(strip=True) for th in ths]
            
            tbody = table.find('tbody')
            if tbody:
                rows = tbody.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if cells and headers:
                        row_name = cells[0].get_text(strip=True)
                        for i, cell in enumerate(cells[1:], 1):
                            if i < len(headers):
                                period = headers[i]
                                if period not in [r.get('period') for r in result]:
                                    result.append({'period': period})
                                
                                for r in result:
                                    if r.get('period') == period:
                                        r[row_name] = cell.get_text(strip=True)
                                        break
        except Exception as e:
            logger.warning(f"Error parsing table: {e}")
        
        return result
    
    def _parse_number(self, text: str) -> float:
        """Parse a number from text, handling Cr, Lakh, % etc."""
        try:
            text = text.strip().replace(',', '').replace('₹', '').replace('%', '')
            
            multiplier = 1
            if 'Cr' in text:
                multiplier = 1
                text = text.replace('Cr', '').replace('.', '').strip()
            elif 'Lakh' in text or 'L' in text:
                multiplier = 0.01
                text = text.replace('Lakh', '').replace('L', '').strip()
            
            # Extract number
            match = re.search(r'[-+]?\d*\.?\d+', text)
            if match:
                return float(match.group()) * multiplier
                
        except Exception:
            pass
        return 0.0
    
    def _safe_float(self, value) -> float:
        """Safely convert to float"""
        try:
            if isinstance(value, str):
                return self._parse_number(value)
            return float(value) if value else 0.0
        except (ValueError, TypeError):
            return 0.0
    
    async def get_multiple_companies(self, symbols: List[str], consolidated: bool = True) -> Dict[str, FinancialData]:
        """Get financial data for multiple companies"""
        result = {}
        for symbol in symbols:
            data = await self.get_financial_data(symbol, consolidated)
            if data:
                result[symbol] = data
            # Rate limiting is handled in get_financial_data
        return result
    
    def get_metrics(self) -> Dict:
        """Get extraction metrics"""
        return self.metrics.to_dict()
    
    def get_cached_symbols(self) -> List[str]:
        """Get list of cached symbols"""
        return list(set(k.split('_')[0] for k in self._cache.keys()))
    
    def clear_cache(self):
        """Clear the data cache"""
        self._cache.clear()
        logger.info("Screener cache cleared")


# Global instance
_screener_extractor: Optional[ScreenerExtractor] = None


def get_screener_extractor() -> ScreenerExtractor:
    """Get the global Screener extractor instance"""
    global _screener_extractor
    if _screener_extractor is None:
        _screener_extractor = ScreenerExtractor()
    return _screener_extractor
