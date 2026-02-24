# StockPulse: Complete Data Sources & Extraction Guide

**All 160 Fields - Where to Get Them & How to Extract Them**

Version 1.0 | February 2026

---

## Table of Contents

1. [Quick Reference: Source-to-Fields Map](#1-quick-reference-source-to-fields-map)
2. [Source #1: NSE Bhavcopy (28 fields)](#2-source-1-nse-bhavcopy---28-fields)
3. [Source #2: Screener.in (60+ fields)](#3-source-2-screenerin---60-fields)
4. [Source #3: BSE India Filings (20 fields)](#4-source-3-bse-india-filings---20-fields)
5. [Source #4: yfinance / Yahoo Finance (10 fields)](#5-source-4-yfinance--yahoo-finance---10-fields)
6. [Source #5: Broker APIs - Free Tier (Real-time data)](#6-source-5-broker-apis---free-tier)
7. [Source #6: Trendlyne (8 fields)](#7-source-6-trendlyne---8-fields)
8. [Source #7: RSS Feeds - News & Sentiment (8 fields)](#8-source-7-rss-feeds---news--sentiment)
9. [Source #8: Credit Rating Agencies (3 fields)](#9-source-8-credit-rating-agencies---3-fields)
10. [Source #9: Calculated Fields - pandas-ta & Custom (40+ fields)](#10-source-9-calculated-fields---pandas-ta--custom)
11. [Anti-Bot Measures & How to Handle Them](#11-anti-bot-measures--how-to-handle-them)
12. [Recommended Python Libraries](#12-recommended-python-libraries)
13. [Cost Summary](#13-cost-summary)
14. [Extraction Priority Plan (Phase-wise)](#14-extraction-priority-plan-phase-wise)
15. [Complete Field-to-Source Mapping Table](#15-complete-field-to-source-mapping-table)

---

## 1. Quick Reference: Source-to-Fields Map

| Source | Fields Covered | Cost | Method | Reliability |
|--------|---------------|------|--------|-------------|
| **NSE Bhavcopy** | 15 price/volume fields | FREE | CSV download | High |
| **Screener.in** | 60+ fundamentals | FREE (or Rs 4k/yr) | Web scraping / Export | High |
| **BSE India** | 20 shareholding + corp actions | FREE | API + scraping | High |
| **yfinance** | 10 fields (backup prices) | FREE | Python library | Medium |
| **Broker APIs (Dhan/Angel One)** | Real-time prices | FREE | REST API | Very High |
| **Trendlyne** | 8 institutional fields | FREE (limited) | Web scraping | High |
| **RSS Feeds** | 8 news fields | FREE | RSS/feedparser | Very High |
| **Rating Agencies** | 3 credit fields | FREE (manual) | Web scraping | Medium |
| **pandas-ta** | 15 technical indicators | FREE | Python library | Very High |
| **Custom Calculations** | 25+ derived fields | FREE | Code | Very High |
| **System Generated** | 8 metadata/qualitative | FREE | Internal | Very High |

---

## 2. Source #1: NSE Bhavcopy - 28 Fields

### What It Is
NSE publishes a **Bhavcopy** (Bhav = Price, Copy = Record) file every trading day. It is the official end-of-day (EOD) price and volume data for ALL listed stocks. This is your **primary source** for daily OHLCV data.

### Fields You Get

| # | Field | V2 Field ID | Example |
|---|-------|-------------|---------|
| 1 | date | #15 | 2026-02-10 |
| 2 | open | #16 | 2845.50 |
| 3 | high | #17 | 2878.90 |
| 4 | low | #18 | 2832.15 |
| 5 | close | #19 | 2867.35 |
| 6 | volume | #21 | 8,542,367 |
| 7 | delivery_volume | #22 | 4,521,890 |
| 8 | delivery_percentage | #23 | 52.94% |
| 9 | turnover | #24 | Rs 245.67 Cr |
| 10 | trades_count | #25 | 142,567 |
| 11 | prev_close | #26 | 2845.50 |
| 12 | vwap | #27 | 2856.78 |
| 13 | symbol | #1 | RELIANCE |
| 14 | isin | #3 | INE002A01018 |
| 15 | series | - | EQ |

### How to Download

**URL Pattern for Daily Bhavcopy:**
```
https://archives.nseindia.com/content/historical/EQUITIES/{YYYY}/{MMM}/cm{DD}{MMM}{YYYY}bhav.csv.zip
```

**Example:**
```
https://archives.nseindia.com/content/historical/EQUITIES/2026/FEB/cm24FEB2026bhav.csv.zip
```

**Delivery Data (separate file):**
```
https://archives.nseindia.com/archives/equities/mto/MTO_{DDMMYYYY}.DAT
```

### Extraction Method: Python with jugaad-data (Recommended)

```python
# Install: pip install jugaad-data
from jugaad_data.nse import bhavcopy_save, stock_df
from datetime import date

# Method 1: Download full bhavcopy CSV
bhavcopy_save("/path/to/data/", date(2026, 2, 24))

# Method 2: Get stock-specific historical data
df = stock_df(
    symbol="RELIANCE",
    from_date=date(2016, 1, 1),
    to_date=date(2026, 2, 24),
    series="EQ"
)
# Returns: Date, Open, High, Low, Close, Volume, Turnover, Trades, Deliverable Volume, %Deliverble
```

### Extraction Method: Direct Download with requests

```python
import requests
import zipfile
import io
import pandas as pd
from datetime import date

def download_bhavcopy(dt: date) -> pd.DataFrame:
    """Download NSE Bhavcopy for a given date."""
    month_name = dt.strftime('%b').upper()
    url = (
        f"https://archives.nseindia.com/content/historical/EQUITIES/"
        f"{dt.year}/{month_name}/cm{dt.strftime('%d')}{month_name}{dt.year}bhav.csv.zip"
    )

    session = requests.Session()
    # IMPORTANT: Must set these headers for NSE
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Referer': 'https://www.nseindia.com/',
        'Accept-Language': 'en-US,en;q=0.9',
    })

    # First visit NSE homepage to get cookies
    session.get('https://www.nseindia.com', timeout=10)

    # Download bhavcopy
    response = session.get(url, timeout=30)
    response.raise_for_status()

    # Extract CSV from ZIP
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        csv_name = z.namelist()[0]
        df = pd.read_csv(z.open(csv_name))

    # Filter equity series only
    df = df[df['SERIES'] == 'EQ']
    return df
```

### Rate Limits & Anti-Bot
- NSE uses Cloudflare protection
- **Must** fetch cookies from homepage first
- Limit to **1 request per 10 seconds** for archives
- Historical archives are more lenient than live API
- Use `jugaad-data` library which handles all of this automatically

### Update Frequency
- **Daily** at ~6:30 PM IST (after market close at 3:30 PM)
- Historical data available from **2000 onwards**

---

## 3. Source #2: Screener.in - 60+ Fields

### What It Is
Screener.in is India's most popular fundamental analysis website. It provides **10 years** of financial data (income statement, balance sheet, cash flow) for all listed companies. This is your **primary source** for all fundamental data.

### Fields You Get

**Income Statement (18 fields, IDs #39-56):**
revenue, revenue_growth_yoy, revenue_growth_qoq, operating_profit, operating_margin, gross_profit, gross_margin, net_profit, net_profit_margin, eps, eps_growth_yoy, interest_expense, depreciation, ebitda, ebit, other_income, tax_expense, effective_tax_rate

**Balance Sheet (17 fields, IDs #57-73):**
total_assets, total_equity, total_debt, long_term_debt, short_term_debt, cash_and_equivalents, net_debt, current_assets, current_liabilities, inventory, receivables, payables, fixed_assets, intangible_assets, reserves_and_surplus, book_value_per_share, contingent_liabilities

**Cash Flow (8 fields, IDs #74-81):**
operating_cash_flow, investing_cash_flow, financing_cash_flow, capital_expenditure, free_cash_flow, dividends_paid, debt_repayment, equity_raised

**Stock Master (4 fields):**
sector (#6), industry (#7), company_name (#2), website (#13)

**Valuation (3 fields):**
sector_avg_pe (#105), sector_avg_roe (#106), industry_avg_pe (#107)

### How to Access

**Option A: Free Account + Export to Excel (Easiest)**
1. Create a free account at https://www.screener.in/
2. Search any company (e.g., RELIANCE)
3. Click "Export to Excel" button at bottom of page
4. Downloads all 10 years of quarterly & annual data in Excel format
5. Free accounts get limited exports; paid plan (Rs 4,000/year) gives unlimited exports

**Option B: Web Scraping with Python**

```python
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

class ScreenerScraper:
    BASE_URL = "https://www.screener.in"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml',
        })

    def login(self, username: str, password: str):
        """Login to Screener.in for export access."""
        login_page = self.session.get(f"{self.BASE_URL}/login/")
        soup = BeautifulSoup(login_page.text, 'html.parser')
        csrf = soup.find('input', {'name': 'csrfmiddlewaretoken'})['value']

        self.session.post(f"{self.BASE_URL}/login/", data={
            'csrfmiddlewaretoken': csrf,
            'username': username,
            'password': password,
        })

    def get_financials(self, symbol: str) -> dict:
        """Scrape financial data for a company."""
        url = f"{self.BASE_URL}/company/{symbol}/consolidated/"
        response = self.session.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        data = {}

        # Extract key ratios from the top section
        ratios_list = soup.find('ul', {'id': 'top-ratios'})
        if ratios_list:
            for li in ratios_list.find_all('li'):
                name = li.find('span', class_='name')
                value = li.find('span', class_='number')
                if name and value:
                    data[name.text.strip()] = value.text.strip()

        # Extract quarterly results table
        quarters_section = soup.find('section', {'id': 'quarters'})
        if quarters_section:
            table = quarters_section.find('table')
            if table:
                data['quarterly_results'] = self._parse_table(table)

        # Extract annual profit & loss
        pnl_section = soup.find('section', {'id': 'profit-loss'})
        if pnl_section:
            table = pnl_section.find('table')
            if table:
                data['annual_pnl'] = self._parse_table(table)

        # Extract balance sheet
        bs_section = soup.find('section', {'id': 'balance-sheet'})
        if bs_section:
            table = bs_section.find('table')
            if table:
                data['balance_sheet'] = self._parse_table(table)

        # Extract cash flow
        cf_section = soup.find('section', {'id': 'cash-flow'})
        if cf_section:
            table = cf_section.find('table')
            if table:
                data['cash_flow'] = self._parse_table(table)

        return data

    def _parse_table(self, table) -> pd.DataFrame:
        """Parse an HTML table into a DataFrame."""
        rows = []
        for tr in table.find_all('tr'):
            cells = [td.text.strip() for td in tr.find_all(['th', 'td'])]
            rows.append(cells)
        if rows:
            df = pd.DataFrame(rows[1:], columns=rows[0])
            return df
        return pd.DataFrame()

    def download_excel(self, symbol: str, save_path: str):
        """Download the Excel export (requires login)."""
        url = f"{self.BASE_URL}/company/{symbol}/consolidated/"
        page = self.session.get(url)
        soup = BeautifulSoup(page.text, 'html.parser')

        export_link = soup.find('a', text='Export to Excel')
        if export_link:
            export_url = self.BASE_URL + export_link['href']
            response = self.session.get(export_url)
            with open(save_path, 'wb') as f:
                f.write(response.content)

# Usage:
scraper = ScreenerScraper()
# scraper.login("your_email", "your_password")  # Optional: for Excel export
data = scraper.get_financials("RELIANCE")
time.sleep(2)  # Always add delay between requests
```

**Option C: Screener.in API via Apify (Third-party)**
- Website: https://apify.com/shashwattrivedi/screener-in/api
- Handles all scraping complexity for you
- Free tier available on Apify platform
- Returns structured JSON with all ratios

### Anti-Bot Measures
- **Low protection** - No Cloudflare, no aggressive blocking
- Standard rate limiting applies
- Add 2-3 second delays between requests
- Login required for Excel exports
- **Be respectful** - Screener.in is a valuable free resource

### Update Frequency
- Quarterly results: Updated within 1-2 days of company filing
- Annual results: Updated annually
- Ratios: Recalculated after each quarterly update

### Cost
- **Free tier**: Browse any company, limited Excel exports
- **Premium (Rs 4,000/year)**: Unlimited exports, advanced screener

---

## 4. Source #3: BSE India Filings - 20 Fields

### What It Is
BSE India (Bombay Stock Exchange) publishes corporate filings including **shareholding patterns**, **corporate actions**, **financial results**, and **announcements**. This is your **primary source** for shareholding and corporate action data.

### Fields You Get

**Shareholding Pattern (10 fields, IDs #110-119):**
promoter_holding, promoter_pledging, fii_holding, dii_holding, public_holding, promoter_holding_change, fii_holding_change, num_shareholders, mf_holding, insurance_holding

**Corporate Actions (6 fields, IDs #120-125):**
dividend_per_share, ex_dividend_date, stock_split_ratio, bonus_ratio, rights_issue_ratio, buyback_details

**Corporate Events (4 fields, IDs #126-129):**
next_earnings_date, pending_events, stock_status, sebi_investigation

### How to Access

**Method A: BSE API (Shareholding Pattern)**

```python
import requests
import pandas as pd

class BSEDataFetcher:
    BASE_URL = "https://api.bseindia.com/BseIndiaAPI/api"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Referer': 'https://www.bseindia.com/',
            'Origin': 'https://www.bseindia.com',
        })

    def get_shareholding(self, scrip_code: str, quarter: str = "31-12-2025") -> dict:
        """Get shareholding pattern for a company."""
        url = f"{self.BASE_URL}/ShareholdPatt/w"
        params = {
            'scripcode': scrip_code,
            'qtrid': quarter,
            'strType': 'company'
        }
        response = self.session.get(url, params=params)
        return response.json()

    def get_corporate_actions(self, scrip_code: str) -> list:
        """Get corporate actions (dividends, splits, bonus)."""
        url = f"{self.BASE_URL}/CorporateAction/w"
        params = {
            'scripcode': scrip_code,
            'index': '',
            'segment': 'Equity',
            'status': '',
        }
        response = self.session.get(url, params=params)
        return response.json()

    def get_announcements(self, scrip_code: str) -> list:
        """Get corporate announcements."""
        url = f"{self.BASE_URL}/AnnSubCategoryGetData/w"
        params = {
            'scripcode': scrip_code,
            'strCat': '-1',
            'strPrevDate': '20250101',
            'strScrip': '',
            'strSearch': 'P',
            'strToDate': '20261231',
            'strType': 'C',
        }
        response = self.session.get(url, params=params)
        return response.json()

# Usage:
bse = BSEDataFetcher()
shareholding = bse.get_shareholding("500325")  # Reliance BSE code
actions = bse.get_corporate_actions("500325")
```

**Method B: Using bsedata Python Library**

```python
# Install: pip install bsedata
from bsedata.bse import BSE

b = BSE()

# Get stock quote with basic info
quote = b.getQuote('500325')  # Reliance BSE scrip code
# Returns: companyName, currentValue, change, pChange, 52weekHigh, 52weekLow, etc.

# Get top gainers/losers
gainers = b.topGainers()
losers = b.topLosers()
```

**Method C: BSE Shareholding Direct Page Scraping**

```python
import requests
from bs4 import BeautifulSoup

def get_bse_shareholding(scrip_code: str) -> dict:
    """Scrape shareholding from BSE website."""
    url = f"https://www.bseindia.com/corporates/shpSecurities.html?scripcd={scrip_code}"

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept': 'text/html',
    })

    response = session.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Parse shareholding table
    data = {}
    tables = soup.find_all('table')
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            cols = [td.text.strip() for td in row.find_all('td')]
            if len(cols) >= 2:
                data[cols[0]] = cols[1]

    return data
```

### Key BSE Scrip Codes (Common Stocks)

| Company | BSE Code |
|---------|----------|
| Reliance Industries | 500325 |
| TCS | 532540 |
| Infosys | 500209 |
| HDFC Bank | 500180 |
| ICICI Bank | 532174 |

### Anti-Bot Measures
- BSE is **less aggressive** than NSE with blocking
- API endpoints work well with proper headers
- Add 1-2 second delays between requests
- The API at `api.bseindia.com` is relatively open

### Update Frequency
- Shareholding: **Quarterly** (within 21 days of quarter end)
- Corporate actions: **On event** (as announced)
- Financial results: **Quarterly** (within 45 days)

### Cost
- **FREE** for public data access
- Official data feeds available via datafeed@bseindia.com (paid)

---

## 5. Source #4: yfinance / Yahoo Finance - 10 Fields

### What It Is
Yahoo Finance provides **adjusted close prices** (adjusted for splits and dividends), making it essential for accurate return calculations. It also serves as a **backup source** for daily OHLCV data.

### Fields You Get

| # | Field | V2 Field ID | Note |
|---|-------|-------------|------|
| 1 | adjusted_close | #20 | **Primary source** for this field |
| 2 | open | #16 | Backup for NSE Bhavcopy |
| 3 | high | #17 | Backup |
| 4 | low | #18 | Backup |
| 5 | close | #19 | Backup |
| 6 | volume | #21 | Backup |
| 7 | dividends | #120 | Historical dividend data |
| 8 | stock_splits | #122 | Historical split data |
| 9 | market_cap | #93 | Via .info |
| 10 | sector/industry | #6, #7 | Via .info |

### How to Use

```python
# Install: pip install yfinance
import yfinance as yf

# Indian stocks use .NS (NSE) or .BO (BSE) suffix
ticker = yf.Ticker("RELIANCE.NS")

# 1. Historical OHLCV with adjusted close
df = ticker.history(period="10y")
# Columns: Open, High, Low, Close, Volume, Dividends, Stock Splits

# 2. Download multiple stocks at once
data = yf.download(
    ["RELIANCE.NS", "TCS.NS", "INFY.NS"],
    start="2016-01-01",
    end="2026-02-24",
    group_by='ticker'
)

# 3. Company info (sector, industry, market cap)
info = ticker.info
sector = info.get('sector')
industry = info.get('industry')
market_cap = info.get('marketCap')

# 4. Dividends history
dividends = ticker.dividends

# 5. Stock splits history
splits = ticker.splits
```

### Important: Handling Rate Limits

yfinance is known for aggressive rate limiting (429 errors). Implement these safeguards:

```python
import time
import random
import yfinance as yf

def safe_download(symbol: str, retries: int = 3) -> pd.DataFrame:
    """Download with retry and rate limit handling."""
    for attempt in range(retries):
        try:
            ticker = yf.Ticker(f"{symbol}.NS")
            df = ticker.history(period="10y")
            time.sleep(random.uniform(2, 5))  # Random delay
            return df
        except Exception as e:
            if "429" in str(e) or "Too Many Requests" in str(e):
                wait_time = (attempt + 1) * 30  # Progressive backoff
                print(f"Rate limited. Waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise
    return pd.DataFrame()
```

### Rate Limits
- ~360 requests/hour (unofficial)
- Can be rate-limited after ~50-100 rapid requests
- Use 2-5 second delays between requests
- Implement exponential backoff

### Cost
- **FREE** - No API key required

### Reliability: MEDIUM
- Works well for historical data but can be unreliable for frequent/bulk requests
- Use as **backup**, not primary source
- Yahoo may change endpoints without notice

---

## 6. Source #5: Broker APIs - Free Tier

### Why Broker APIs?
Broker APIs provide the most **reliable real-time data** and are the best option for live stock prices during market hours. Several Indian brokers now offer **free APIs**.

### Option A: Dhan API (Best Free Option)

**Website:** https://dhanhq.co/
**Cost:** FREE (requires Dhan trading account)
**Reliability:** Very High

```python
# Install: pip install dhanhq
from dhanhq import DhanContext, marketfeed

# Initialize
dhan_context = DhanContext("your_client_id", "your_access_token")

# Get live market data
instruments = [(1, "500325")]  # (exchange_segment, security_id)
data = marketfeed.DhanFeed(
    dhan_context,
    instruments,
    marketfeed.Ticker
)
```

**What you get:** Real-time OHLCV, last traded price, bid/ask, volume, market depth

### Option B: Angel One SmartAPI (Free)

**Website:** https://smartapi.angelone.in/
**Cost:** FREE (requires Angel One trading account)

```python
# Install: pip install smartapi-python
from SmartApi import SmartConnect

obj = SmartConnect(api_key="your_api_key")
data = obj.generateSession("client_id", "password", "totp")

# Historical data
params = {
    "exchange": "NSE",
    "symboltoken": "2885",  # RELIANCE token
    "interval": "ONE_DAY",
    "fromdate": "2024-01-01 09:15",
    "todate": "2026-02-24 15:30"
}
candles = obj.getCandleData(params)
```

### Option C: Fyers API (Free)

**Website:** https://fyers.in/
**Cost:** FREE (requires Fyers trading account)

```python
from fyers_apiv3 import fyersModel

fyers = fyersModel.FyersModel(
    client_id="your_app_id",
    token="your_access_token",
    is_async=False
)

# Historical data
data = {
    "symbol": "NSE:RELIANCE-EQ",
    "resolution": "D",
    "date_format": "1",
    "range_from": "2024-01-01",
    "range_to": "2026-02-24",
    "cont_flag": "1"
}
response = fyers.history(data=data)
```

### Option D: Breeze API - ICICI Direct (Free)

**Website:** https://www.icicidirect.com/futures-and-options/api/breeze
**Cost:** FREE (requires ICICI Direct account)

### Comparison Table

| Broker API | Account Required | API Cost | Market Data | Historical Data |
|-----------|-----------------|----------|-------------|-----------------|
| **Dhan** | Dhan account | FREE | Real-time | Yes |
| **Angel One** | Angel One account | FREE | Real-time | Yes (limited) |
| **Fyers** | Fyers account | FREE | Real-time | Yes |
| **Breeze/ICICI** | ICICI Direct account | FREE | Real-time | Yes |
| **Zerodha Kite** | Zerodha account | Rs 500/mo | Real-time | 10yr intraday |
| **Groww** | Groww account | Rs 499/mo | Real-time | Yes |

### Recommendation
Open a **Dhan** or **Angel One** trading account (no minimum deposit required) to get free API access for real-time market data. This is the most reliable method for live prices.

---

## 7. Source #6: Trendlyne - 8 Fields

### What It Is
Trendlyne aggregates institutional trading data (FII/DII), pledging trends, and stock analytics. It's the best source for **institutional flow data**.

### Fields You Get

| # | Field | V2 Field ID |
|---|-------|-------------|
| 1 | promoter_pledging | #111 |
| 2 | fii_holding_change | #116 |
| 3 | pe_ratio_forward | #96 |
| 4 | sector_performance | #109 |
| 5-8 | FII/DII daily activity | Related to #112-114 |

### How to Access

**Method A: Free Web Widgets**
Trendlyne offers embeddable widgets with stock data:
- URL: https://trendlyne.com/web-widget/showcase/
- Can embed in your app for free
- Limited data fields

**Method B: Web Scraping**

```python
import requests
from bs4 import BeautifulSoup
import time

class TrendlyneScraper:
    BASE_URL = "https://trendlyne.com"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept': 'text/html',
        })

    def get_fii_dii_data(self) -> dict:
        """Get latest FII/DII activity data."""
        url = f"{self.BASE_URL}/macro-data/fii-dii/latest/"
        response = self.session.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        # Parse the FII/DII table
        # (Structure changes frequently - inspect page for current layout)
        return self._parse_fii_dii_table(soup)

    def get_pledging_data(self, symbol: str) -> dict:
        """Get promoter pledging data."""
        url = f"{self.BASE_URL}/fundamentals/promoter-pledging/{symbol}/"
        response = self.session.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        return self._parse_pledging(soup)

    def _parse_fii_dii_table(self, soup):
        """Parse FII/DII data from Trendlyne page."""
        data = {}
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cols = [td.text.strip() for td in row.find_all(['th', 'td'])]
                if cols:
                    data[cols[0]] = cols[1:]
        return data

    def _parse_pledging(self, soup):
        """Parse pledging data."""
        data = {}
        # Extract from the page structure
        return data
```

### Anti-Bot Measures
- Moderate protection
- Add 3-5 second delays between requests
- May require login for detailed data
- Free tier limits the number of views per day

### Cost
- **FREE**: Basic data viewing on website
- **Paid (Rs 499+/month)**: Full screener access, downloads, alerts

### Update Frequency
- FII/DII data: **Daily** (after market hours)
- Pledging data: **Quarterly**
- Consensus estimates: **On analyst update**

---

## 8. Source #7: RSS Feeds - News & Sentiment

### What It Is
Financial news RSS feeds provide real-time stock market news from India's top business publications. This is your **primary source** for news and sentiment analysis.

### Fields You Get

| # | Field | V2 Field ID |
|---|-------|-------------|
| 1 | news_headline | #130 |
| 2 | news_body_text | #131 |
| 3 | news_source | #132 |
| 4 | news_timestamp | #133 |
| 5 | news_sentiment_score | #134 (calculated from text) |
| 6 | stock_tickers_mentioned | #135 (extracted from text) |

### Available RSS Feeds

**Moneycontrol:**
```
https://www.moneycontrol.com/rss/latestnews.xml
https://www.moneycontrol.com/rss/marketedge.xml
https://www.moneycontrol.com/rss/business.xml
```

**Economic Times:**
```
https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms
https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms
https://economictimes.indiatimes.com/news/company/corporate-trends/rssfeeds/2143429.cms
```

**Business Standard:**
```
https://www.business-standard.com/rss/markets-106.rss
https://www.business-standard.com/rss/companies-101.rss
https://www.business-standard.com/rss/economy-102.rss
```

**Livemint:**
```
https://www.livemint.com/rss/markets
https://www.livemint.com/rss/companies
```

### How to Extract

```python
# Install: pip install feedparser
import feedparser
from datetime import datetime
import re

class NewsRSSFetcher:
    FEEDS = {
        'moneycontrol': [
            'https://www.moneycontrol.com/rss/latestnews.xml',
            'https://www.moneycontrol.com/rss/marketedge.xml',
        ],
        'economic_times': [
            'https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms',
        ],
        'business_standard': [
            'https://www.business-standard.com/rss/markets-106.rss',
        ],
    }

    # Common NSE stock symbols to detect in headlines
    STOCK_SYMBOLS = [
        'RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK',
        'SBIN', 'BHARTIARTL', 'ITC', 'KOTAKBANK', 'LT',
        'HINDUNILVR', 'BAJFINANCE', 'MARUTI', 'TITAN', 'WIPRO',
        # Add more as needed
    ]

    def fetch_all_news(self) -> list:
        """Fetch news from all RSS feeds."""
        all_articles = []

        for source, urls in self.FEEDS.items():
            for url in urls:
                try:
                    feed = feedparser.parse(url)
                    for entry in feed.entries:
                        article = {
                            'headline': entry.get('title', ''),
                            'body_text': entry.get('summary', ''),
                            'source': source,
                            'url': entry.get('link', ''),
                            'timestamp': entry.get('published', ''),
                            'tickers_mentioned': self._extract_tickers(
                                entry.get('title', '') + ' ' + entry.get('summary', '')
                            ),
                        }
                        all_articles.append(article)
                except Exception as e:
                    print(f"Error fetching {url}: {e}")

        return all_articles

    def _extract_tickers(self, text: str) -> list:
        """Extract stock ticker mentions from text."""
        text_upper = text.upper()
        found = []
        for symbol in self.STOCK_SYMBOLS:
            if symbol in text_upper or symbol.replace('_', ' ') in text_upper:
                found.append(symbol)
        return found

# Usage:
fetcher = NewsRSSFetcher()
news = fetcher.fetch_all_news()
for article in news[:5]:
    print(f"[{article['source']}] {article['headline']}")
    print(f"  Tickers: {article['tickers_mentioned']}")
```

### Sentiment Analysis (Field #134)
You'll calculate `news_sentiment_score` from the headline and body text using NLP:

```python
# Option A: Using VADER (free, fast, no API needed)
# Install: pip install vaderSentiment
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

analyzer = SentimentIntensityAnalyzer()

def get_sentiment(text: str) -> float:
    """Returns sentiment score from -1 (negative) to +1 (positive)."""
    scores = analyzer.polarity_scores(text)
    return scores['compound']  # -1 to +1

# Option B: Using FinBERT (more accurate for financial text)
# Install: pip install transformers torch
from transformers import pipeline

finbert = pipeline("sentiment-analysis", model="ProsusAI/finbert")

def get_financial_sentiment(text: str) -> float:
    """Financial-specific sentiment analysis."""
    result = finbert(text[:512])[0]  # FinBERT has 512 token limit
    label = result['label']  # 'positive', 'negative', 'neutral'
    score = result['score']
    if label == 'negative':
        return -score
    elif label == 'positive':
        return score
    return 0.0
```

### Rate Limits
- RSS feeds have **no rate limits** (poll every 15-30 minutes)
- Very reliable - RSS is a stable standard

### Cost: FREE

---

## 9. Source #8: Credit Rating Agencies - 3 Fields

### What It Is
CRISIL, ICRA, and CARE are India's top credit rating agencies. They rate companies' creditworthiness, which is a key input for risk assessment.

### Fields You Get

| # | Field | V2 Field ID |
|---|-------|-------------|
| 1 | credit_rating | #136 |
| 2 | credit_outlook | #137 |

### Available Sources

| Agency | Website | Lookup Page |
|--------|---------|-------------|
| **CRISIL** | crisil.com | https://www.crisil.com/en/home/our-businesses/ratings/credit-rating-list.html |
| **ICRA** | icra.in | https://www.icra.in/Rating/Search |
| **CARE** | careratings.com | https://www.careratings.com/ratings |
| **India Ratings (Fitch)** | indiaratings.co.in | https://www.indiaratings.co.in/ |

### How to Extract

**Method: Web Scraping (No API available)**

```python
import requests
from bs4 import BeautifulSoup

def get_crisil_rating(company_name: str) -> dict:
    """Search CRISIL for company rating."""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    })

    # CRISIL search
    url = "https://www.crisil.com/en/home/our-businesses/ratings/credit-rating-list.html"
    response = session.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Parse ratings table (structure varies)
    # This is a simplified example - actual implementation depends on page structure
    data = {
        'agency': 'CRISIL',
        'rating': None,
        'outlook': None,
    }
    return data
```

**Alternative: Get Ratings from BSE Filings**
Companies disclose their credit ratings in annual reports filed on BSE. Check the annual report for the latest credit rating.

**Alternative: Get Ratings from Screener.in**
Screener.in sometimes displays credit ratings on company pages.

### Practical Approach
Since rating agencies don't provide APIs:
1. **Manual entry** for your tracked universe (50-100 stocks)
2. **Scrape periodically** (ratings change rarely - once every few months)
3. **Use BSE annual report filings** as the authoritative source

### Cost: FREE (manual lookup)
### Update Frequency: On rating change (rare - 1-2 times per year per company)

---

## 10. Source #9: Calculated Fields - pandas-ta & Custom

### What It Is
Many of the 160 fields are **calculated from raw data** (prices, financials) rather than fetched from external sources. This section covers all calculated fields.

### Technical Indicators (15 fields, IDs #138-152) - Using pandas-ta

```python
# Install: pip install pandas-ta
import pandas as pd
import pandas_ta as ta

def calculate_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate all 15 technical indicators.
    Input df must have columns: Open, High, Low, Close, Volume
    """
    # Moving Averages
    df['sma_20'] = ta.sma(df['Close'], length=20)       # #138
    df['sma_50'] = ta.sma(df['Close'], length=50)       # #139
    df['sma_200'] = ta.sma(df['Close'], length=200)     # #140
    df['ema_12'] = ta.ema(df['Close'], length=12)       # #141
    df['ema_26'] = ta.ema(df['Close'], length=26)       # #142

    # RSI
    df['rsi_14'] = ta.rsi(df['Close'], length=14)       # #143

    # MACD
    macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
    df['macd'] = macd.iloc[:, 0]                         # #144
    df['macd_signal'] = macd.iloc[:, 1]                  # #145

    # Bollinger Bands
    bbands = ta.bbands(df['Close'], length=20, std=2)
    df['bollinger_upper'] = bbands.iloc[:, 2]            # #146
    df['bollinger_lower'] = bbands.iloc[:, 0]            # #147

    # ATR
    df['atr_14'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)  # #148

    # ADX
    adx = ta.adx(df['High'], df['Low'], df['Close'], length=14)
    df['adx_14'] = adx.iloc[:, 0]                        # #149

    # OBV
    df['obv'] = ta.obv(df['Close'], df['Volume'])        # #150

    # Support & Resistance (custom calculation)
    df['support_level'] = df['Low'].rolling(20).min()     # #151
    df['resistance_level'] = df['High'].rolling(20).max() # #152

    return df
```

### Derived Price Metrics (11 fields, IDs #28-38)

```python
def calculate_derived_price_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate all derived price metrics.
    Input df must have columns: Open, High, Low, Close, Volume, Prev_Close
    """
    # Daily return
    df['daily_return_pct'] = ((df['Close'] - df['Close'].shift(1)) / df['Close'].shift(1)) * 100  # #28

    # Multi-period returns
    df['return_5d_pct'] = ((df['Close'] - df['Close'].shift(5)) / df['Close'].shift(5)) * 100     # #29
    df['return_20d_pct'] = ((df['Close'] - df['Close'].shift(20)) / df['Close'].shift(20)) * 100   # #30
    df['return_60d_pct'] = ((df['Close'] - df['Close'].shift(60)) / df['Close'].shift(60)) * 100   # #31

    # Intraday metrics
    df['day_range_pct'] = ((df['High'] - df['Low']) / df['Low']) * 100  # #32
    df['gap_percentage'] = ((df['Open'] - df['Close'].shift(1)) / df['Close'].shift(1)) * 100  # #33

    # 52-week metrics
    df['52_week_high'] = df['High'].rolling(252).max()   # #34
    df['52_week_low'] = df['Low'].rolling(252).min()     # #35
    df['distance_from_52w_high'] = ((df['52_week_high'] - df['Close']) / df['52_week_high']) * 100  # #36

    # Volume metrics
    df['avg_volume_20d'] = df['Volume'].rolling(20).mean()  # #38
    df['volume_ratio'] = df['Volume'] / df['avg_volume_20d']  # #37

    return df
```

### Financial Ratios (11 fields, IDs #82-92)

```python
def calculate_financial_ratios(financials: dict) -> dict:
    """
    Calculate all financial ratios from raw financial data.
    Input: dict with keys from Screener.in data
    """
    ratios = {}

    # Profitability ratios
    total_equity = financials.get('total_equity', 1)
    total_assets = financials.get('total_assets', 1)
    net_profit = financials.get('net_profit', 0)

    ratios['roe'] = (net_profit / total_equity * 100) if total_equity else 0                      # #82
    ratios['roa'] = (net_profit / total_assets * 100) if total_assets else 0                      # #83

    # ROIC = NOPAT / Invested Capital
    ebit = financials.get('ebit', 0)
    tax_rate = financials.get('effective_tax_rate', 25) / 100
    nopat = ebit * (1 - tax_rate)
    invested_capital = total_equity + financials.get('total_debt', 0) - financials.get('cash_and_equivalents', 0)
    ratios['roic'] = (nopat / invested_capital * 100) if invested_capital else 0                  # #84

    # Leverage ratios
    ratios['debt_to_equity'] = financials.get('total_debt', 0) / total_equity if total_equity else 0  # #85
    interest_expense = financials.get('interest_expense', 1)
    ratios['interest_coverage'] = ebit / interest_expense if interest_expense else 0              # #86

    # Liquidity ratios
    current_assets = financials.get('current_assets', 0)
    current_liabilities = financials.get('current_liabilities', 1)
    ratios['current_ratio'] = current_assets / current_liabilities if current_liabilities else 0  # #87
    inventory = financials.get('inventory', 0)
    ratios['quick_ratio'] = (current_assets - inventory) / current_liabilities if current_liabilities else 0  # #88

    # Efficiency ratios
    revenue = financials.get('revenue', 0)
    ratios['asset_turnover'] = revenue / total_assets if total_assets else 0                      # #89
    cogs = revenue - financials.get('gross_profit', 0)
    ratios['inventory_turnover'] = cogs / inventory if inventory else 0                           # #90
    receivables = financials.get('receivables', 1)
    ratios['receivables_turnover'] = revenue / receivables if receivables else 0                  # #91

    # Dividend payout
    dividends = financials.get('dividends_paid', 0)
    ratios['dividend_payout_ratio'] = (abs(dividends) / net_profit * 100) if net_profit else 0   # #92

    return ratios
```

### Valuation Metrics (17 fields, IDs #93-109)

```python
def calculate_valuation_metrics(price: float, financials: dict, shares: int) -> dict:
    """Calculate all valuation metrics."""
    vals = {}

    vals['market_cap'] = price * shares                                                           # #93
    net_debt = financials.get('total_debt', 0) - financials.get('cash_and_equivalents', 0)
    vals['enterprise_value'] = vals['market_cap'] + net_debt                                      # #94

    eps = financials.get('eps', 1)
    vals['pe_ratio'] = price / eps if eps else 0                                                  # #95
    # pe_ratio_forward (#96) comes from Trendlyne (analyst estimates)

    eps_growth = financials.get('eps_growth_yoy', 1)
    vals['peg_ratio'] = vals['pe_ratio'] / eps_growth if eps_growth else 0                       # #97

    bvps = financials.get('book_value_per_share', 1)
    vals['pb_ratio'] = price / bvps if bvps else 0                                               # #98

    revenue_per_share = financials.get('revenue', 0) / shares if shares else 0
    vals['ps_ratio'] = price / revenue_per_share if revenue_per_share else 0                     # #99

    ebitda = financials.get('ebitda', 1)
    vals['ev_to_ebitda'] = vals['enterprise_value'] / ebitda if ebitda else 0                    # #100
    revenue = financials.get('revenue', 1)
    vals['ev_to_sales'] = vals['enterprise_value'] / revenue if revenue else 0                   # #101

    dividend_per_share = financials.get('dividend_per_share', 0)
    vals['dividend_yield'] = (dividend_per_share / price * 100) if price else 0                  # #102

    fcf = financials.get('free_cash_flow', 0)
    fcf_per_share = fcf / shares if shares else 0
    vals['fcf_yield'] = (fcf_per_share / price * 100) if price else 0                           # #103

    vals['earnings_yield'] = (eps / price * 100) if price else 0                                 # #104

    # sector_avg_pe (#105), sector_avg_roe (#106), industry_avg_pe (#107) -> Screener.in
    # historical_pe_median (#108) -> calculated from historical P/E series
    # sector_performance (#109) -> NSE sector indices

    return vals
```

### Qualitative & Metadata Fields (IDs #153-160)

```python
def initialize_metadata_fields(symbol: str) -> dict:
    """Initialize system metadata fields."""
    return {
        'moat_assessment': None,            # #153 - Manual/LLM entry
        'management_assessment': None,      # #154 - Manual/LLM entry
        'industry_growth_assessment': None,  # #155 - Manual/LLM entry
        'disruption_risk': None,            # #156 - Manual/LLM entry
        'fraud_history': False,             # #157 - Manual/News check
        'field_availability': {},           # #158 - Auto-tracked by system
        'field_last_updated': {},           # #159 - Auto-tracked by system
        'multi_source_values': {},          # #160 - Auto-tracked by system
    }
```

---

## 11. Anti-Bot Measures & How to Handle Them

### Overview of Protections by Source

| Source | Protection Level | Technology | Difficulty |
|--------|-----------------|------------|------------|
| **NSE India** | HIGH | Cloudflare, cookies, rate limits | Hard |
| **BSE India** | LOW | Basic rate limiting | Easy |
| **Screener.in** | LOW | Basic session management | Easy |
| **Trendlyne** | MEDIUM | Login walls, rate limits | Medium |
| **Yahoo Finance** | MEDIUM | Rate limiting (429 errors) | Medium |
| **RSS Feeds** | NONE | Standard RSS protocol | Very Easy |
| **Rating Agencies** | LOW | Basic HTML | Easy |

### Universal Best Practices

#### 1. Proper Session Management
```python
import requests

session = requests.Session()

# Set realistic headers
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
})
```

#### 2. Request Throttling (Critical)
```python
import time
import random

def throttled_request(session, url, min_delay=1, max_delay=3):
    """Make a request with random delay."""
    time.sleep(random.uniform(min_delay, max_delay))
    return session.get(url, timeout=30)
```

#### 3. Retry with Exponential Backoff
```python
import time

def fetch_with_retry(session, url, max_retries=3):
    """Fetch with exponential backoff on failure."""
    for attempt in range(max_retries):
        try:
            response = session.get(url, timeout=30)
            if response.status_code == 429:  # Too Many Requests
                wait = (2 ** attempt) * 10  # 10s, 20s, 40s
                print(f"Rate limited. Waiting {wait}s...")
                time.sleep(wait)
                continue
            response.raise_for_status()
            return response
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)
    return None
```

#### 4. NSE-Specific: Cookie Management
```python
def create_nse_session():
    """Create a session with valid NSE cookies."""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.nseindia.com/',
    })

    # Step 1: Visit homepage to get initial cookies
    session.get('https://www.nseindia.com', timeout=10)
    time.sleep(1)

    # Step 2: Visit a data page to get API cookies
    session.get('https://www.nseindia.com/market-data/live-equity-market', timeout=10)
    time.sleep(1)

    return session

# Now use this session for API calls:
session = create_nse_session()
response = session.get(
    'https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%2050',
    timeout=10
)
```

#### 5. Data Caching
```python
import json
import os
from datetime import datetime, timedelta

CACHE_DIR = "./cache"

def get_cached_or_fetch(key: str, fetch_func, ttl_hours: int = 24):
    """Check cache first, fetch if stale."""
    cache_file = os.path.join(CACHE_DIR, f"{key}.json")

    # Check cache
    if os.path.exists(cache_file):
        mtime = datetime.fromtimestamp(os.path.getmtime(cache_file))
        if datetime.now() - mtime < timedelta(hours=ttl_hours):
            with open(cache_file) as f:
                return json.load(f)

    # Fetch fresh data
    data = fetch_func()

    # Save to cache
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(cache_file, 'w') as f:
        json.dump(data, f)

    return data
```

### What NOT To Do
- Do NOT make more than 3 requests/second to any source
- Do NOT scrape during market hours (9:15 AM - 3:30 PM IST) if possible
- Do NOT try to bypass CAPTCHAs or human verification
- Do NOT ignore robots.txt directives
- Do NOT redistribute scraped data commercially without permission
- Do NOT use the data for automated trading without proper licensing

---

## 12. Recommended Python Libraries

### Core Libraries (Must Install)

```bash
# Data extraction
pip install jugaad-data          # NSE historical data (RECOMMENDED)
pip install yfinance             # Yahoo Finance backup
pip install bsedata              # BSE real-time data
pip install feedparser           # RSS news feeds

# Data processing
pip install pandas               # DataFrames
pip install pandas-ta            # Technical indicators (15 fields)
pip install numpy                # Numerical calculations

# Web scraping
pip install requests             # HTTP client
pip install beautifulsoup4       # HTML parsing
pip install lxml                 # Fast XML/HTML parser

# Sentiment analysis
pip install vaderSentiment       # Quick sentiment scoring
pip install transformers         # FinBERT (advanced, optional)

# Environment
pip install python-dotenv        # .env file support
```

### Optional Libraries

```bash
# Broker APIs (pick one based on your account)
pip install dhanhq               # Dhan API (free)
pip install smartapi-python      # Angel One API (free)

# Advanced scraping (only if needed)
pip install playwright           # Browser automation (last resort)
pip install cloudscraper         # Cloudflare bypass

# Database
pip install motor                # Async MongoDB
pip install asyncpg              # Async PostgreSQL
pip install redis                # Redis cache
```

### Library Comparison

| Library | Purpose | Maintained? | Reliability |
|---------|---------|-------------|-------------|
| **jugaad-data** | NSE historical data | Yes (active) | High |
| **nsepython** | NSE live + historical | Yes | High |
| **nsetools** | NSE real-time | Partial | Medium |
| **nsepy** | NSE data | NO (deprecated) | Low |
| **bsedata** | BSE real-time | Yes | Medium |
| **yfinance** | Yahoo Finance | Yes | Medium |
| **pandas-ta** | Technical indicators | Yes | Very High |
| **feedparser** | RSS feeds | Yes (stable) | Very High |

---

## 13. Cost Summary

### Totally Free Stack (Recommended Starting Point)

| Component | Source | Cost |
|-----------|--------|------|
| Daily OHLCV | NSE Bhavcopy via jugaad-data | FREE |
| Adjusted Close | yfinance | FREE |
| Fundamentals | Screener.in (scraping) | FREE |
| Shareholding | BSE India API | FREE |
| Corporate Actions | BSE India API | FREE |
| Real-time Prices | Dhan API or Angel One API | FREE |
| News | RSS feeds | FREE |
| Technical Indicators | pandas-ta | FREE |
| Derived Metrics | Custom calculations | FREE |
| **TOTAL** | | **Rs 0/month** |

### Enhanced Stack (Better Data Quality)

| Component | Source | Cost |
|-----------|--------|------|
| Everything above | Same | FREE |
| + Screener.in Premium | Unlimited exports | Rs 333/month |
| + Zerodha Kite API | Best real-time data | Rs 500/month |
| + Trendlyne Pro | Institutional data | Rs 499/month |
| **TOTAL** | | **~Rs 1,332/month** |

### Summary
You can build the entire 160-field data pipeline for **Rs 0/month** using free sources. The paid options provide convenience (easier data access) and additional data (forward P/E, analyst consensus) but are not required.

---

## 14. Extraction Priority Plan (Phase-wise)

### Phase 1: Critical Fields (58 fields) - Before Go-Live

**Week 1-2: Price & Volume Pipeline**
1. Set up NSE Bhavcopy daily download (jugaad-data) - Fields #15-27
2. Set up yfinance for adjusted close - Field #20
3. Calculate derived price metrics - Fields #28-38
4. Set up broker API (Dhan) for real-time prices

**Week 2-3: Fundamentals Pipeline**
5. Build Screener.in scraper - Fields #39-56 (Income Statement)
6. Scrape Balance Sheet data - Fields #57-73
7. Scrape Cash Flow data - Fields #74-81
8. Calculate financial ratios - Fields #82-92

**Week 3-4: Valuation & Master Data**
9. Calculate valuation metrics - Fields #93-109
10. Build stock master data from NSE/BSE - Fields #1-14
11. Set up corporate actions from BSE - Fields #128-129

### Phase 2: Important Fields (52 fields) - First Month

**Week 4-5: Shareholding & Institutional**
12. BSE shareholding pattern scraper - Fields #110-119
13. Trendlyne pledging data - Field #111
14. Corporate actions (dividends, splits, bonus) - Fields #120-127

**Week 5-6: News & Technical**
15. RSS feed aggregator - Fields #130-135
16. Sentiment analysis pipeline (VADER/FinBERT) - Field #134
17. Technical indicators (pandas-ta) - Fields #138-152

### Phase 3: Standard Fields (35 fields) - Within 3 Months

18. Credit rating scraper - Fields #136-137
19. Sector performance from NSE indices - Field #109
20. Historical P/E median calculations - Field #108
21. System metadata fields - Fields #158-160

### Phase 4: Optional & Qualitative (12 fields) - Future

22. Qualitative assessments (LLM-generated) - Fields #153-157
23. Advanced efficiency ratios - Fields #89-91
24. Contingent liabilities (from annual reports) - Field #73

---

## 15. Complete Field-to-Source Mapping Table

| ID | Field Name | Primary Source | Backup Source | Method | Priority |
|----|-----------|----------------|---------------|--------|----------|
| 1 | symbol | NSE/BSE | - | Master list | Critical |
| 2 | company_name | NSE/BSE | Screener.in | API/Scrape | Critical |
| 3 | isin | NSE Bhavcopy | BSE | CSV column | Critical |
| 4 | nse_code | NSE | - | Master list | Critical |
| 5 | bse_code | BSE | - | Master list | Important |
| 6 | sector | Screener.in | yfinance | Scrape | Critical |
| 7 | industry | Screener.in | yfinance | Scrape | Critical |
| 8 | market_cap_category | Calculated | - | price * shares | Important |
| 9 | listing_date | NSE/BSE | - | Master list | Standard |
| 10 | face_value | NSE/BSE | - | Master list | Standard |
| 11 | shares_outstanding | BSE Filings | Screener.in | Scrape | Important |
| 12 | free_float_shares | BSE Filings | - | Shareholding filing | Standard |
| 13 | website | Screener.in | - | Scrape | Optional |
| 14 | registered_office | BSE | - | Filing data | Optional |
| 15 | date | NSE Bhavcopy | yfinance | CSV/API | Critical |
| 16 | open | NSE Bhavcopy | yfinance | CSV/API | Critical |
| 17 | high | NSE Bhavcopy | yfinance | CSV/API | Critical |
| 18 | low | NSE Bhavcopy | yfinance | CSV/API | Critical |
| 19 | close | NSE Bhavcopy | yfinance | CSV/API | Critical |
| 20 | adjusted_close | yfinance | Calculated | API | Critical |
| 21 | volume | NSE Bhavcopy | yfinance | CSV/API | Critical |
| 22 | delivery_volume | NSE Bhavcopy | - | Delivery CSV | Important |
| 23 | delivery_percentage | NSE Bhavcopy | - | Delivery CSV | Important |
| 24 | turnover | NSE Bhavcopy | - | CSV column | Important |
| 25 | trades_count | NSE Bhavcopy | - | CSV column | Important |
| 26 | prev_close | NSE Bhavcopy | Calculated | CSV/shift(1) | Standard |
| 27 | vwap | NSE | - | CSV/API | Standard |
| 28 | daily_return_pct | Calculated | - | (close-prev)/prev | Critical |
| 29 | return_5d_pct | Calculated | - | 5-day return | Standard |
| 30 | return_20d_pct | Calculated | - | 20-day return | Standard |
| 31 | return_60d_pct | Calculated | - | 60-day return | Standard |
| 32 | day_range_pct | Calculated | - | (high-low)/low | Standard |
| 33 | gap_percentage | Calculated | - | (open-prev)/prev | Standard |
| 34 | 52_week_high | Calculated | - | 252-day max | Critical |
| 35 | 52_week_low | Calculated | - | 252-day min | Critical |
| 36 | distance_from_52w_high | Calculated | - | % from 52w high | Important |
| 37 | volume_ratio | Calculated | - | vol/avg_vol_20d | Important |
| 38 | avg_volume_20d | Calculated | - | 20-day avg vol | Critical |
| 39 | revenue | Screener.in | BSE Filing | Scrape/Export | Critical |
| 40 | revenue_growth_yoy | Calculated | Screener.in | YoY calc | Critical |
| 41 | revenue_growth_qoq | Calculated | - | QoQ calc | Important |
| 42 | operating_profit | Screener.in | BSE Filing | Scrape/Export | Critical |
| 43 | operating_margin | Screener.in | Calculated | Scrape | Critical |
| 44 | gross_profit | Screener.in | - | Scrape/Export | Important |
| 45 | gross_margin | Calculated | Screener.in | gross/revenue | Important |
| 46 | net_profit | Screener.in | BSE Filing | Scrape/Export | Critical |
| 47 | net_profit_margin | Calculated | Screener.in | net/revenue | Critical |
| 48 | eps | Screener.in | Calculated | Scrape/Export | Critical |
| 49 | eps_growth_yoy | Calculated | - | YoY calc | Critical |
| 50 | interest_expense | Screener.in | - | Scrape/Export | Critical |
| 51 | depreciation | Screener.in | - | Scrape/Export | Important |
| 52 | ebitda | Screener.in | Calculated | Scrape/Export | Important |
| 53 | ebit | Calculated | Screener.in | op_profit | Important |
| 54 | other_income | Screener.in | - | Scrape/Export | Important |
| 55 | tax_expense | Screener.in | - | Scrape/Export | Standard |
| 56 | effective_tax_rate | Calculated | - | tax/pretax | Standard |
| 57 | total_assets | Screener.in | BSE Filing | Scrape/Export | Critical |
| 58 | total_equity | Screener.in | BSE Filing | Scrape/Export | Critical |
| 59 | total_debt | Screener.in | BSE Filing | Scrape/Export | Critical |
| 60 | long_term_debt | Screener.in | - | Scrape/Export | Important |
| 61 | short_term_debt | Screener.in | - | Scrape/Export | Important |
| 62 | cash_and_equivalents | Screener.in | - | Scrape/Export | Critical |
| 63 | net_debt | Calculated | - | debt - cash | Important |
| 64 | current_assets | Screener.in | - | Scrape/Export | Important |
| 65 | current_liabilities | Screener.in | - | Scrape/Export | Important |
| 66 | inventory | Screener.in | - | Scrape/Export | Important |
| 67 | receivables | Screener.in | - | Scrape/Export | Standard |
| 68 | payables | Screener.in | - | Scrape/Export | Standard |
| 69 | fixed_assets | Screener.in | - | Scrape/Export | Standard |
| 70 | intangible_assets | Screener.in | - | Scrape/Export | Standard |
| 71 | reserves_and_surplus | Screener.in | - | Scrape/Export | Standard |
| 72 | book_value_per_share | Screener.in | Calculated | Scrape | Important |
| 73 | contingent_liabilities | Annual Report | - | PDF/Manual | Standard |
| 74 | operating_cash_flow | Screener.in | BSE Filing | Scrape/Export | Critical |
| 75 | investing_cash_flow | Screener.in | - | Scrape/Export | Critical |
| 76 | financing_cash_flow | Screener.in | - | Scrape/Export | Important |
| 77 | capital_expenditure | Screener.in | Calculated | Scrape/Export | Critical |
| 78 | free_cash_flow | Calculated | Screener.in | OCF - CapEx | Critical |
| 79 | dividends_paid | Screener.in | - | Scrape/Export | Important |
| 80 | debt_repayment | Screener.in | - | Scrape/Export | Standard |
| 81 | equity_raised | Screener.in | - | Scrape/Export | Standard |
| 82 | roe | Calculated | Screener.in | NP/Equity | Critical |
| 83 | roa | Calculated | - | NP/Assets | Important |
| 84 | roic | Calculated | - | NOPAT/IC | Important |
| 85 | debt_to_equity | Calculated | Screener.in | Debt/Equity | Critical |
| 86 | interest_coverage | Calculated | Screener.in | EBIT/Interest | Critical |
| 87 | current_ratio | Calculated | Screener.in | CA/CL | Important |
| 88 | quick_ratio | Calculated | - | (CA-Inv)/CL | Standard |
| 89 | asset_turnover | Calculated | - | Rev/Assets | Standard |
| 90 | inventory_turnover | Calculated | - | COGS/Inv | Standard |
| 91 | receivables_turnover | Calculated | - | Rev/Recv | Standard |
| 92 | dividend_payout_ratio | Calculated | - | Div/NP | Important |
| 93 | market_cap | Calculated | yfinance | Price*Shares | Critical |
| 94 | enterprise_value | Calculated | - | MCap+NetDebt | Critical |
| 95 | pe_ratio | Calculated | Screener.in | Price/EPS | Critical |
| 96 | pe_ratio_forward | Trendlyne | - | Scrape | Critical |
| 97 | peg_ratio | Calculated | - | PE/Growth | Critical |
| 98 | pb_ratio | Calculated | Screener.in | Price/BV | Important |
| 99 | ps_ratio | Calculated | - | Price/Revenue | Important |
| 100 | ev_to_ebitda | Calculated | Screener.in | EV/EBITDA | Critical |
| 101 | ev_to_sales | Calculated | - | EV/Revenue | Standard |
| 102 | dividend_yield | Calculated | Screener.in | Div/Price | Important |
| 103 | fcf_yield | Calculated | - | FCF/Price | Important |
| 104 | earnings_yield | Calculated | - | EPS/Price | Important |
| 105 | sector_avg_pe | Screener.in | - | Peer comparison | Important |
| 106 | sector_avg_roe | Screener.in | - | Peer comparison | Important |
| 107 | industry_avg_pe | Screener.in | - | Peer comparison | Standard |
| 108 | historical_pe_median | Calculated | - | 5yr median PE | Standard |
| 109 | sector_performance | NSE Indices | - | Index returns | Important |
| 110 | promoter_holding | BSE Filings | Trendlyne | API/Scrape | Critical |
| 111 | promoter_pledging | BSE/Trendlyne | - | API/Scrape | Critical |
| 112 | fii_holding | BSE Filings | Trendlyne | API/Scrape | Critical |
| 113 | dii_holding | BSE Filings | - | API/Scrape | Important |
| 114 | public_holding | BSE Filings | - | API/Scrape | Important |
| 115 | promoter_holding_change | Calculated | - | QoQ change | Important |
| 116 | fii_holding_change | Calculated | Trendlyne | QoQ change | Important |
| 117 | num_shareholders | BSE Filings | - | Shareholding | Standard |
| 118 | mf_holding | BSE Filings | - | Shareholding | Standard |
| 119 | insurance_holding | BSE Filings | - | Shareholding | Standard |
| 120 | dividend_per_share | BSE/NSE | Screener.in | Corp actions | Important |
| 121 | ex_dividend_date | BSE/NSE | - | Corp actions | Important |
| 122 | stock_split_ratio | BSE/NSE | yfinance | Corp actions | Important |
| 123 | bonus_ratio | BSE/NSE | - | Corp actions | Important |
| 124 | rights_issue_ratio | BSE/NSE | - | Corp actions | Standard |
| 125 | buyback_details | BSE/NSE | - | Announcements | Standard |
| 126 | next_earnings_date | BSE Announce | - | Scrape | Important |
| 127 | pending_events | BSE Announce | - | Scrape | Important |
| 128 | stock_status | NSE/BSE | - | Master list | Critical |
| 129 | sebi_investigation | SEBI/News | - | News monitoring | Critical |
| 130 | news_headline | RSS Feeds | - | feedparser | Important |
| 131 | news_body_text | RSS Feeds | - | feedparser | Important |
| 132 | news_source | RSS Feeds | - | feedparser | Standard |
| 133 | news_timestamp | RSS Feeds | - | feedparser | Important |
| 134 | news_sentiment_score | Calculated | - | VADER/FinBERT | Important |
| 135 | stock_tickers_mentioned | Calculated | - | NLP extraction | Standard |
| 136 | credit_rating | Rating Agencies | BSE Annual | Scrape/Manual | Important |
| 137 | credit_outlook | Rating Agencies | - | Scrape/Manual | Standard |
| 138 | sma_20 | pandas-ta | - | SMA(close,20) | Important |
| 139 | sma_50 | pandas-ta | - | SMA(close,50) | Critical |
| 140 | sma_200 | pandas-ta | - | SMA(close,200) | Critical |
| 141 | ema_12 | pandas-ta | - | EMA(close,12) | Important |
| 142 | ema_26 | pandas-ta | - | EMA(close,26) | Important |
| 143 | rsi_14 | pandas-ta | - | RSI(close,14) | Critical |
| 144 | macd | pandas-ta | - | EMA12-EMA26 | Critical |
| 145 | macd_signal | pandas-ta | - | EMA(MACD,9) | Critical |
| 146 | bollinger_upper | pandas-ta | - | SMA20+2*SD | Important |
| 147 | bollinger_lower | pandas-ta | - | SMA20-2*SD | Important |
| 148 | atr_14 | pandas-ta | - | ATR(14) | Important |
| 149 | adx_14 | pandas-ta | - | ADX(14) | Standard |
| 150 | obv | pandas-ta | - | OBV | Standard |
| 151 | support_level | Custom calc | - | Pivot lows | Important |
| 152 | resistance_level | Custom calc | - | Pivot highs | Important |
| 153 | moat_assessment | Manual/LLM | - | Human input | Qualitative |
| 154 | management_assessment | Manual/LLM | - | Human input | Qualitative |
| 155 | industry_growth_assessment | Manual/LLM | - | Human input | Qualitative |
| 156 | disruption_risk | Manual/LLM | - | Human input | Qualitative |
| 157 | fraud_history | Manual/News | - | News check | Qualitative |
| 158 | field_availability | System | - | Auto-tracked | Metadata |
| 159 | field_last_updated | System | - | Auto-tracked | Metadata |
| 160 | multi_source_values | System | - | Auto-tracked | Metadata |

---

## Summary

### The Bottom Line

You can extract **all 160 data fields** for the Indian stock market using **entirely free tools and sources**:

1. **NSE Bhavcopy** (via `jugaad-data`) provides 15 daily price/volume fields
2. **Screener.in** (web scraping) provides 60+ fundamental fields with 10-year history
3. **BSE India** (API + scraping) provides 20 shareholding & corporate action fields
4. **yfinance** provides adjusted close prices as backup
5. **Broker APIs** (Dhan/Angel One - free) provide real-time prices
6. **RSS Feeds** (feedparser) provide 8 news fields
7. **pandas-ta** calculates 15 technical indicators from price data
8. **Custom code** calculates 40+ derived metrics (returns, ratios, valuations)
9. **System tracks** 3 metadata fields automatically
10. **Manual/LLM** covers 5 qualitative assessment fields

**Total cost: Rs 0/month** for the complete pipeline.

The key to success is **being respectful of data sources** - use proper rate limiting, cache data locally, and prefer official APIs over scraping wherever possible.
