"""
Complete field definitions for all 160 data fields across 13 categories.

Each field definition includes:
    - field_id: Unique numeric identifier (1-160)
    - name: Field name (snake_case)
    - category: One of the 13 data categories
    - data_type: Python type (str, float, int, bool, date, datetime, list, dict)
    - unit: Unit of measurement (currency, percent, shares, etc.)
    - priority: CRITICAL, IMPORTANT, STANDARD, OPTIONAL, METADATA, QUALITATIVE
    - update_frequency: DAILY, WEEKLY, QUARTERLY, ANNUAL, ON_EVENT, REAL_TIME, CONTINUOUS
    - source: Primary data source
    - method: Extraction method (DOWNLOAD, SCRAPE, API, CALCULATED, RSS, MANUAL, AUTO)
    - backup_source: Fallback data source (if any)
    - used_for: What this field is used for in the platform
    - scoring_rules: List of D/R/Q rules that reference this field
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List


class Category(str, Enum):
    STOCK_MASTER = "stock_master"
    PRICE_VOLUME = "price_volume"
    DERIVED_METRICS = "derived_metrics"
    INCOME_STATEMENT = "income_statement"
    BALANCE_SHEET = "balance_sheet"
    CASH_FLOW = "cash_flow"
    FINANCIAL_RATIOS = "financial_ratios"
    VALUATION = "valuation"
    SHAREHOLDING = "shareholding"
    CORPORATE_ACTIONS = "corporate_actions"
    NEWS_SENTIMENT = "news_sentiment"
    TECHNICAL = "technical"
    QUALITATIVE_METADATA = "qualitative_metadata"


class Priority(str, Enum):
    CRITICAL = "critical"
    IMPORTANT = "important"
    STANDARD = "standard"
    OPTIONAL = "optional"
    METADATA = "metadata"
    QUALITATIVE = "qualitative"


class UpdateFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    ON_EVENT = "on_event"
    REAL_TIME = "real_time"
    CONTINUOUS = "continuous"
    NEVER = "never"


class ExtractionMethod(str, Enum):
    DOWNLOAD = "download"
    SCRAPE = "scrape"
    API = "api"
    CALCULATED = "calculated"
    RSS = "rss"
    NLP = "nlp"
    MANUAL = "manual"
    AUTO = "auto"


class DataSource(str, Enum):
    NSE_BSE = "nse_bse"
    NSE_BHAVCOPY = "nse_bhavcopy"
    NSE = "nse"
    BSE = "bse"
    BSE_FILINGS = "bse_filings"
    BSE_ANNOUNCEMENTS = "bse_announcements"
    SCREENER = "screener_in"
    TRENDLYNE = "trendlyne"
    YFINANCE = "yfinance"
    RSS_FEEDS = "rss_feeds"
    RATING_AGENCIES = "rating_agencies"
    SEBI = "sebi"
    PANDAS_TA = "pandas_ta"
    CALCULATED = "calculated"
    MANUAL_LLM = "manual_llm"
    SYSTEM = "system"
    NSE_INDICES = "nse_indices"
    ANNUAL_REPORT = "annual_report"


class FieldType(str, Enum):
    STRING = "string"
    DECIMAL = "decimal"
    INTEGER = "integer"
    DATE = "date"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    ENUM = "enum"
    URL = "url"
    LIST_STRING = "list_string"
    LIST_OBJECT = "list_object"
    DICT_BOOL = "dict_bool"
    DICT_DATETIME = "dict_datetime"
    DICT_DICT = "dict_dict"


@dataclass
class FieldDefinition:
    field_id: int
    name: str
    category: Category
    data_type: FieldType
    unit: str
    priority: Priority
    update_frequency: UpdateFrequency
    source: DataSource
    method: ExtractionMethod
    backup_source: Optional[DataSource] = None
    used_for: str = ""
    scoring_rules: List[str] = field(default_factory=list)
    history_depth: str = "N/A"


# All 160 field definitions
FIELD_DEFINITIONS: List[FieldDefinition] = [
    # ===== CATEGORY 1: STOCK MASTER DATA (14 Fields) =====
    FieldDefinition(1, "symbol", Category.STOCK_MASTER, FieldType.STRING, "",
                    Priority.CRITICAL, UpdateFrequency.ON_EVENT, DataSource.NSE_BSE,
                    ExtractionMethod.DOWNLOAD, used_for="Primary identifier"),
    FieldDefinition(2, "company_name", Category.STOCK_MASTER, FieldType.STRING, "",
                    Priority.CRITICAL, UpdateFrequency.ON_EVENT, DataSource.NSE_BSE,
                    ExtractionMethod.DOWNLOAD, used_for="UI display name"),
    FieldDefinition(3, "isin", Category.STOCK_MASTER, FieldType.STRING, "",
                    Priority.CRITICAL, UpdateFrequency.NEVER, DataSource.NSE_BSE,
                    ExtractionMethod.DOWNLOAD, used_for="Cross-exchange ID"),
    FieldDefinition(4, "nse_code", Category.STOCK_MASTER, FieldType.STRING, "",
                    Priority.CRITICAL, UpdateFrequency.ON_EVENT, DataSource.NSE,
                    ExtractionMethod.DOWNLOAD, used_for="NSE trading symbol"),
    FieldDefinition(5, "bse_code", Category.STOCK_MASTER, FieldType.STRING, "",
                    Priority.IMPORTANT, UpdateFrequency.ON_EVENT, DataSource.BSE,
                    ExtractionMethod.DOWNLOAD, used_for="BSE scrip code"),
    FieldDefinition(6, "sector", Category.STOCK_MASTER, FieldType.STRING, "",
                    Priority.CRITICAL, UpdateFrequency.ON_EVENT, DataSource.SCREENER,
                    ExtractionMethod.SCRAPE, DataSource.TRENDLYNE, "Sector comparison"),
    FieldDefinition(7, "industry", Category.STOCK_MASTER, FieldType.STRING, "",
                    Priority.CRITICAL, UpdateFrequency.ON_EVENT, DataSource.SCREENER,
                    ExtractionMethod.SCRAPE, DataSource.TRENDLYNE, "Industry peer comparison"),
    FieldDefinition(8, "market_cap_category", Category.STOCK_MASTER, FieldType.ENUM, "",
                    Priority.IMPORTANT, UpdateFrequency.DAILY, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="Size classification"),
    FieldDefinition(9, "listing_date", Category.STOCK_MASTER, FieldType.DATE, "",
                    Priority.STANDARD, UpdateFrequency.NEVER, DataSource.NSE_BSE,
                    ExtractionMethod.DOWNLOAD, used_for="Company age analysis"),
    FieldDefinition(10, "face_value", Category.STOCK_MASTER, FieldType.DECIMAL, "INR",
                    Priority.STANDARD, UpdateFrequency.ON_EVENT, DataSource.NSE_BSE,
                    ExtractionMethod.DOWNLOAD, used_for="Corp action adjustment"),
    FieldDefinition(11, "shares_outstanding", Category.STOCK_MASTER, FieldType.INTEGER, "shares",
                    Priority.IMPORTANT, UpdateFrequency.QUARTERLY, DataSource.BSE_FILINGS,
                    ExtractionMethod.SCRAPE, DataSource.SCREENER, "Market cap, EPS calc"),
    FieldDefinition(12, "free_float_shares", Category.STOCK_MASTER, FieldType.INTEGER, "shares",
                    Priority.STANDARD, UpdateFrequency.QUARTERLY, DataSource.BSE_FILINGS,
                    ExtractionMethod.SCRAPE, DataSource.TRENDLYNE, "Float analysis"),
    FieldDefinition(13, "website", Category.STOCK_MASTER, FieldType.URL, "",
                    Priority.OPTIONAL, UpdateFrequency.NEVER, DataSource.SCREENER,
                    ExtractionMethod.SCRAPE, used_for="Company research"),
    FieldDefinition(14, "registered_office", Category.STOCK_MASTER, FieldType.STRING, "",
                    Priority.OPTIONAL, UpdateFrequency.NEVER, DataSource.BSE,
                    ExtractionMethod.SCRAPE, used_for="Company info"),

    # ===== CATEGORY 2: PRICE & VOLUME DATA (13 Fields) =====
    FieldDefinition(15, "date", Category.PRICE_VOLUME, FieldType.DATE, "",
                    Priority.CRITICAL, UpdateFrequency.DAILY, DataSource.NSE_BHAVCOPY,
                    ExtractionMethod.DOWNLOAD, DataSource.YFINANCE, "Time series key",
                    history_depth="10 years"),
    FieldDefinition(16, "open", Category.PRICE_VOLUME, FieldType.DECIMAL, "INR",
                    Priority.CRITICAL, UpdateFrequency.DAILY, DataSource.NSE_BHAVCOPY,
                    ExtractionMethod.DOWNLOAD, DataSource.YFINANCE, "Candlestick, gap analysis",
                    history_depth="10 years"),
    FieldDefinition(17, "high", Category.PRICE_VOLUME, FieldType.DECIMAL, "INR",
                    Priority.CRITICAL, UpdateFrequency.DAILY, DataSource.NSE_BHAVCOPY,
                    ExtractionMethod.DOWNLOAD, DataSource.YFINANCE, "Range, resistance",
                    history_depth="10 years"),
    FieldDefinition(18, "low", Category.PRICE_VOLUME, FieldType.DECIMAL, "INR",
                    Priority.CRITICAL, UpdateFrequency.DAILY, DataSource.NSE_BHAVCOPY,
                    ExtractionMethod.DOWNLOAD, DataSource.YFINANCE, "Range, support",
                    history_depth="10 years"),
    FieldDefinition(19, "close", Category.PRICE_VOLUME, FieldType.DECIMAL, "INR",
                    Priority.CRITICAL, UpdateFrequency.DAILY, DataSource.NSE_BHAVCOPY,
                    ExtractionMethod.DOWNLOAD, DataSource.YFINANCE, "All calculations",
                    history_depth="10 years"),
    FieldDefinition(20, "adjusted_close", Category.PRICE_VOLUME, FieldType.DECIMAL, "INR",
                    Priority.CRITICAL, UpdateFrequency.DAILY, DataSource.YFINANCE,
                    ExtractionMethod.API, used_for="Accurate returns",
                    history_depth="10 years"),
    FieldDefinition(21, "volume", Category.PRICE_VOLUME, FieldType.INTEGER, "shares",
                    Priority.CRITICAL, UpdateFrequency.DAILY, DataSource.NSE_BHAVCOPY,
                    ExtractionMethod.DOWNLOAD, DataSource.YFINANCE, "Liquidity",
                    scoring_rules=["D10"], history_depth="10 years"),
    FieldDefinition(22, "delivery_volume", Category.PRICE_VOLUME, FieldType.INTEGER, "shares",
                    Priority.IMPORTANT, UpdateFrequency.DAILY, DataSource.NSE_BHAVCOPY,
                    ExtractionMethod.DOWNLOAD, used_for="Genuine buying",
                    history_depth="10 years"),
    FieldDefinition(23, "delivery_percentage", Category.PRICE_VOLUME, FieldType.DECIMAL, "%",
                    Priority.IMPORTANT, UpdateFrequency.DAILY, DataSource.NSE_BHAVCOPY,
                    ExtractionMethod.DOWNLOAD, used_for="Buyer conviction",
                    scoring_rules=["R9"], history_depth="10 years"),
    FieldDefinition(24, "turnover", Category.PRICE_VOLUME, FieldType.DECIMAL, "INR_CR",
                    Priority.IMPORTANT, UpdateFrequency.DAILY, DataSource.NSE_BHAVCOPY,
                    ExtractionMethod.DOWNLOAD, used_for="Value traded",
                    history_depth="10 years"),
    FieldDefinition(25, "trades_count", Category.PRICE_VOLUME, FieldType.INTEGER, "",
                    Priority.IMPORTANT, UpdateFrequency.DAILY, DataSource.NSE_BHAVCOPY,
                    ExtractionMethod.DOWNLOAD, used_for="Participation breadth",
                    history_depth="10 years"),
    FieldDefinition(26, "prev_close", Category.PRICE_VOLUME, FieldType.DECIMAL, "INR",
                    Priority.STANDARD, UpdateFrequency.DAILY, DataSource.NSE_BHAVCOPY,
                    ExtractionMethod.DOWNLOAD, used_for="Daily change calc",
                    history_depth="10 years"),
    FieldDefinition(27, "vwap", Category.PRICE_VOLUME, FieldType.DECIMAL, "INR",
                    Priority.STANDARD, UpdateFrequency.DAILY, DataSource.NSE,
                    ExtractionMethod.SCRAPE, used_for="Institutional benchmark",
                    history_depth="1 year"),

    # ===== CATEGORY 3: DERIVED PRICE METRICS (11 Fields) =====
    FieldDefinition(28, "daily_return_pct", Category.DERIVED_METRICS, FieldType.DECIMAL, "%",
                    Priority.CRITICAL, UpdateFrequency.DAILY, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="Return analysis, volatility, ML",
                    history_depth="10 years"),
    FieldDefinition(29, "return_5d_pct", Category.DERIVED_METRICS, FieldType.DECIMAL, "%",
                    Priority.STANDARD, UpdateFrequency.DAILY, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="5-day momentum ML feature",
                    history_depth="10 years"),
    FieldDefinition(30, "return_20d_pct", Category.DERIVED_METRICS, FieldType.DECIMAL, "%",
                    Priority.STANDARD, UpdateFrequency.DAILY, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="20-day momentum ML feature",
                    history_depth="10 years"),
    FieldDefinition(31, "return_60d_pct", Category.DERIVED_METRICS, FieldType.DECIMAL, "%",
                    Priority.STANDARD, UpdateFrequency.DAILY, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="60-day momentum ML feature",
                    history_depth="10 years"),
    FieldDefinition(32, "day_range_pct", Category.DERIVED_METRICS, FieldType.DECIMAL, "%",
                    Priority.STANDARD, UpdateFrequency.DAILY, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="Intraday volatility ML",
                    history_depth="10 years"),
    FieldDefinition(33, "gap_percentage", Category.DERIVED_METRICS, FieldType.DECIMAL, "%",
                    Priority.STANDARD, UpdateFrequency.DAILY, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="Gap detection ML feature",
                    history_depth="10 years"),
    FieldDefinition(34, "week_52_high", Category.DERIVED_METRICS, FieldType.DECIMAL, "INR",
                    Priority.CRITICAL, UpdateFrequency.DAILY, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="Technical analysis",
                    scoring_rules=["Q8"], history_depth="10 years"),
    FieldDefinition(35, "week_52_low", Category.DERIVED_METRICS, FieldType.DECIMAL, "INR",
                    Priority.CRITICAL, UpdateFrequency.DAILY, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="Support detection",
                    history_depth="10 years"),
    FieldDefinition(36, "distance_from_52w_high", Category.DERIVED_METRICS, FieldType.DECIMAL, "%",
                    Priority.IMPORTANT, UpdateFrequency.DAILY, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="R6 penalty (>30%)",
                    scoring_rules=["R6", "Q8"], history_depth="10 years"),
    FieldDefinition(37, "volume_ratio", Category.DERIVED_METRICS, FieldType.DECIMAL, "",
                    Priority.IMPORTANT, UpdateFrequency.DAILY, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="Volume spike ML feature",
                    history_depth="10 years"),
    FieldDefinition(38, "avg_volume_20d", Category.DERIVED_METRICS, FieldType.INTEGER, "shares",
                    Priority.CRITICAL, UpdateFrequency.DAILY, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="D10 deal-breaker (<50k)",
                    scoring_rules=["D10"], history_depth="10 years"),

    # ===== CATEGORY 4: INCOME STATEMENT (18 Fields) =====
    FieldDefinition(39, "revenue", Category.INCOME_STATEMENT, FieldType.DECIMAL, "INR_CR",
                    Priority.CRITICAL, UpdateFrequency.QUARTERLY, DataSource.SCREENER,
                    ExtractionMethod.SCRAPE, DataSource.TRENDLYNE, "Growth, P/S",
                    scoring_rules=["D3"], history_depth="10 years"),
    FieldDefinition(40, "revenue_growth_yoy", Category.INCOME_STATEMENT, FieldType.DECIMAL, "%",
                    Priority.CRITICAL, UpdateFrequency.QUARTERLY, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="D3, scoring (>15%=Q2)",
                    scoring_rules=["D3", "Q2"], history_depth="10 years"),
    FieldDefinition(41, "revenue_growth_qoq", Category.INCOME_STATEMENT, FieldType.DECIMAL, "%",
                    Priority.IMPORTANT, UpdateFrequency.QUARTERLY, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="Quarterly momentum",
                    history_depth="10 years"),
    FieldDefinition(42, "operating_profit", Category.INCOME_STATEMENT, FieldType.DECIMAL, "INR_CR",
                    Priority.CRITICAL, UpdateFrequency.QUARTERLY, DataSource.SCREENER,
                    ExtractionMethod.SCRAPE, DataSource.TRENDLYNE, "Op margin calc",
                    history_depth="10 years"),
    FieldDefinition(43, "operating_margin", Category.INCOME_STATEMENT, FieldType.DECIMAL, "%",
                    Priority.CRITICAL, UpdateFrequency.QUARTERLY, DataSource.SCREENER,
                    ExtractionMethod.SCRAPE, used_for="Q7 (>25%), R7",
                    scoring_rules=["Q7", "R7"], history_depth="10 years"),
    FieldDefinition(44, "gross_profit", Category.INCOME_STATEMENT, FieldType.DECIMAL, "INR_CR",
                    Priority.IMPORTANT, UpdateFrequency.ANNUAL, DataSource.SCREENER,
                    ExtractionMethod.SCRAPE, used_for="Gross margin",
                    history_depth="10 years"),
    FieldDefinition(45, "gross_margin", Category.INCOME_STATEMENT, FieldType.DECIMAL, "%",
                    Priority.IMPORTANT, UpdateFrequency.ANNUAL, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="Pricing power",
                    history_depth="10 years"),
    FieldDefinition(46, "net_profit", Category.INCOME_STATEMENT, FieldType.DECIMAL, "INR_CR",
                    Priority.CRITICAL, UpdateFrequency.QUARTERLY, DataSource.SCREENER,
                    ExtractionMethod.SCRAPE, DataSource.TRENDLYNE, "EPS, P/E",
                    history_depth="10 years"),
    FieldDefinition(47, "net_profit_margin", Category.INCOME_STATEMENT, FieldType.DECIMAL, "%",
                    Priority.CRITICAL, UpdateFrequency.QUARTERLY, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="Profitability",
                    history_depth="10 years"),
    FieldDefinition(48, "eps", Category.INCOME_STATEMENT, FieldType.DECIMAL, "INR",
                    Priority.CRITICAL, UpdateFrequency.QUARTERLY, DataSource.SCREENER,
                    ExtractionMethod.SCRAPE, used_for="P/E, EPS growth",
                    history_depth="10 years"),
    FieldDefinition(49, "eps_growth_yoy", Category.INCOME_STATEMENT, FieldType.DECIMAL, "%",
                    Priority.CRITICAL, UpdateFrequency.QUARTERLY, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="PEG calculation",
                    history_depth="10 years"),
    FieldDefinition(50, "interest_expense", Category.INCOME_STATEMENT, FieldType.DECIMAL, "INR_CR",
                    Priority.CRITICAL, UpdateFrequency.QUARTERLY, DataSource.SCREENER,
                    ExtractionMethod.SCRAPE, used_for="Interest coverage (D1)",
                    scoring_rules=["D1"], history_depth="10 years"),
    FieldDefinition(51, "depreciation", Category.INCOME_STATEMENT, FieldType.DECIMAL, "INR_CR",
                    Priority.IMPORTANT, UpdateFrequency.QUARTERLY, DataSource.SCREENER,
                    ExtractionMethod.SCRAPE, used_for="EBITDA calc",
                    history_depth="10 years"),
    FieldDefinition(52, "ebitda", Category.INCOME_STATEMENT, FieldType.DECIMAL, "INR_CR",
                    Priority.IMPORTANT, UpdateFrequency.QUARTERLY, DataSource.SCREENER,
                    ExtractionMethod.SCRAPE, used_for="EV/EBITDA",
                    history_depth="10 years"),
    FieldDefinition(53, "ebit", Category.INCOME_STATEMENT, FieldType.DECIMAL, "INR_CR",
                    Priority.IMPORTANT, UpdateFrequency.QUARTERLY, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="Interest coverage",
                    history_depth="10 years"),
    FieldDefinition(54, "other_income", Category.INCOME_STATEMENT, FieldType.DECIMAL, "INR_CR",
                    Priority.IMPORTANT, UpdateFrequency.QUARTERLY, DataSource.SCREENER,
                    ExtractionMethod.SCRAPE, used_for="Core vs non-core",
                    history_depth="10 years"),
    FieldDefinition(55, "tax_expense", Category.INCOME_STATEMENT, FieldType.DECIMAL, "INR_CR",
                    Priority.STANDARD, UpdateFrequency.QUARTERLY, DataSource.SCREENER,
                    ExtractionMethod.SCRAPE, used_for="Tax rate",
                    history_depth="10 years"),
    FieldDefinition(56, "effective_tax_rate", Category.INCOME_STATEMENT, FieldType.DECIMAL, "%",
                    Priority.STANDARD, UpdateFrequency.ANNUAL, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="Tax efficiency",
                    history_depth="10 years"),

    # ===== CATEGORY 5: BALANCE SHEET (17 Fields) =====
    FieldDefinition(57, "total_assets", Category.BALANCE_SHEET, FieldType.DECIMAL, "INR_CR",
                    Priority.CRITICAL, UpdateFrequency.ANNUAL, DataSource.SCREENER,
                    ExtractionMethod.SCRAPE, used_for="ROA calculation",
                    history_depth="10 years"),
    FieldDefinition(58, "total_equity", Category.BALANCE_SHEET, FieldType.DECIMAL, "INR_CR",
                    Priority.CRITICAL, UpdateFrequency.ANNUAL, DataSource.SCREENER,
                    ExtractionMethod.SCRAPE, used_for="ROE, D/E, BV",
                    history_depth="10 years"),
    FieldDefinition(59, "total_debt", Category.BALANCE_SHEET, FieldType.DECIMAL, "INR_CR",
                    Priority.CRITICAL, UpdateFrequency.QUARTERLY, DataSource.SCREENER,
                    ExtractionMethod.SCRAPE, used_for="D/E, D8 deal-breaker",
                    scoring_rules=["D8"], history_depth="10 years"),
    FieldDefinition(60, "long_term_debt", Category.BALANCE_SHEET, FieldType.DECIMAL, "INR_CR",
                    Priority.IMPORTANT, UpdateFrequency.ANNUAL, DataSource.SCREENER,
                    ExtractionMethod.SCRAPE, used_for="Debt structure",
                    history_depth="10 years"),
    FieldDefinition(61, "short_term_debt", Category.BALANCE_SHEET, FieldType.DECIMAL, "INR_CR",
                    Priority.IMPORTANT, UpdateFrequency.ANNUAL, DataSource.SCREENER,
                    ExtractionMethod.SCRAPE, used_for="Short-term liquidity",
                    history_depth="10 years"),
    FieldDefinition(62, "cash_and_equivalents", Category.BALANCE_SHEET, FieldType.DECIMAL, "INR_CR",
                    Priority.CRITICAL, UpdateFrequency.QUARTERLY, DataSource.SCREENER,
                    ExtractionMethod.SCRAPE, used_for="Net debt, Q3",
                    scoring_rules=["Q3"], history_depth="10 years"),
    FieldDefinition(63, "net_debt", Category.BALANCE_SHEET, FieldType.DECIMAL, "INR_CR",
                    Priority.IMPORTANT, UpdateFrequency.QUARTERLY, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="EV calculation",
                    history_depth="10 years"),
    FieldDefinition(64, "current_assets", Category.BALANCE_SHEET, FieldType.DECIMAL, "INR_CR",
                    Priority.IMPORTANT, UpdateFrequency.ANNUAL, DataSource.SCREENER,
                    ExtractionMethod.SCRAPE, used_for="Current ratio",
                    history_depth="10 years"),
    FieldDefinition(65, "current_liabilities", Category.BALANCE_SHEET, FieldType.DECIMAL, "INR_CR",
                    Priority.IMPORTANT, UpdateFrequency.ANNUAL, DataSource.SCREENER,
                    ExtractionMethod.SCRAPE, used_for="Current/Quick ratio",
                    history_depth="10 years"),
    FieldDefinition(66, "inventory", Category.BALANCE_SHEET, FieldType.DECIMAL, "INR_CR",
                    Priority.IMPORTANT, UpdateFrequency.ANNUAL, DataSource.SCREENER,
                    ExtractionMethod.SCRAPE, used_for="Quick ratio",
                    history_depth="10 years"),
    FieldDefinition(67, "receivables", Category.BALANCE_SHEET, FieldType.DECIMAL, "INR_CR",
                    Priority.STANDARD, UpdateFrequency.ANNUAL, DataSource.SCREENER,
                    ExtractionMethod.SCRAPE, used_for="Receivables turnover",
                    history_depth="10 years"),
    FieldDefinition(68, "payables", Category.BALANCE_SHEET, FieldType.DECIMAL, "INR_CR",
                    Priority.STANDARD, UpdateFrequency.ANNUAL, DataSource.SCREENER,
                    ExtractionMethod.SCRAPE, used_for="Payables turnover",
                    history_depth="10 years"),
    FieldDefinition(69, "fixed_assets", Category.BALANCE_SHEET, FieldType.DECIMAL, "INR_CR",
                    Priority.STANDARD, UpdateFrequency.ANNUAL, DataSource.SCREENER,
                    ExtractionMethod.SCRAPE, used_for="Asset turnover",
                    history_depth="10 years"),
    FieldDefinition(70, "intangible_assets", Category.BALANCE_SHEET, FieldType.DECIMAL, "INR_CR",
                    Priority.STANDARD, UpdateFrequency.ANNUAL, DataSource.SCREENER,
                    ExtractionMethod.SCRAPE, used_for="Goodwill analysis",
                    history_depth="10 years"),
    FieldDefinition(71, "reserves_and_surplus", Category.BALANCE_SHEET, FieldType.DECIMAL, "INR_CR",
                    Priority.STANDARD, UpdateFrequency.ANNUAL, DataSource.SCREENER,
                    ExtractionMethod.SCRAPE, used_for="Retained earnings",
                    history_depth="10 years"),
    FieldDefinition(72, "book_value_per_share", Category.BALANCE_SHEET, FieldType.DECIMAL, "INR",
                    Priority.IMPORTANT, UpdateFrequency.ANNUAL, DataSource.SCREENER,
                    ExtractionMethod.SCRAPE, DataSource.CALCULATED, "P/B ratio",
                    history_depth="10 years"),
    FieldDefinition(73, "contingent_liabilities", Category.BALANCE_SHEET, FieldType.DECIMAL, "INR_CR",
                    Priority.STANDARD, UpdateFrequency.ANNUAL, DataSource.ANNUAL_REPORT,
                    ExtractionMethod.SCRAPE, DataSource.SCREENER, "R10 penalty",
                    scoring_rules=["R10"], history_depth="10 years"),

    # ===== CATEGORY 6: CASH FLOW STATEMENT (8 Fields) =====
    FieldDefinition(74, "operating_cash_flow", Category.CASH_FLOW, FieldType.DECIMAL, "INR_CR",
                    Priority.CRITICAL, UpdateFrequency.ANNUAL, DataSource.SCREENER,
                    ExtractionMethod.SCRAPE, used_for="OCF > NI check, FCF, D4",
                    scoring_rules=["D4"], history_depth="10 years"),
    FieldDefinition(75, "investing_cash_flow", Category.CASH_FLOW, FieldType.DECIMAL, "INR_CR",
                    Priority.CRITICAL, UpdateFrequency.ANNUAL, DataSource.SCREENER,
                    ExtractionMethod.SCRAPE, used_for="CapEx analysis",
                    history_depth="10 years"),
    FieldDefinition(76, "financing_cash_flow", Category.CASH_FLOW, FieldType.DECIMAL, "INR_CR",
                    Priority.IMPORTANT, UpdateFrequency.ANNUAL, DataSource.SCREENER,
                    ExtractionMethod.SCRAPE, used_for="Debt/equity financing",
                    history_depth="10 years"),
    FieldDefinition(77, "capital_expenditure", Category.CASH_FLOW, FieldType.DECIMAL, "INR_CR",
                    Priority.CRITICAL, UpdateFrequency.ANNUAL, DataSource.SCREENER,
                    ExtractionMethod.SCRAPE, used_for="FCF = OCF - CapEx",
                    history_depth="10 years"),
    FieldDefinition(78, "free_cash_flow", Category.CASH_FLOW, FieldType.DECIMAL, "INR_CR",
                    Priority.CRITICAL, UpdateFrequency.ANNUAL, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="D5, FCF yield, Q9",
                    scoring_rules=["D5", "Q9"], history_depth="10 years"),
    FieldDefinition(79, "dividends_paid", Category.CASH_FLOW, FieldType.DECIMAL, "INR_CR",
                    Priority.IMPORTANT, UpdateFrequency.ANNUAL, DataSource.SCREENER,
                    ExtractionMethod.SCRAPE, used_for="Dividend payout, Q4",
                    scoring_rules=["Q4"], history_depth="10 years"),
    FieldDefinition(80, "debt_repayment", Category.CASH_FLOW, FieldType.DECIMAL, "INR_CR",
                    Priority.STANDARD, UpdateFrequency.ANNUAL, DataSource.SCREENER,
                    ExtractionMethod.SCRAPE, used_for="Debt servicing",
                    history_depth="10 years"),
    FieldDefinition(81, "equity_raised", Category.CASH_FLOW, FieldType.DECIMAL, "INR_CR",
                    Priority.STANDARD, UpdateFrequency.ANNUAL, DataSource.SCREENER,
                    ExtractionMethod.SCRAPE, used_for="Dilution tracking",
                    history_depth="10 years"),

    # ===== CATEGORY 7: FINANCIAL RATIOS (11 Fields) =====
    FieldDefinition(82, "roe", Category.FINANCIAL_RATIOS, FieldType.DECIMAL, "%",
                    Priority.CRITICAL, UpdateFrequency.QUARTERLY, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="Q1 (>20% 5yr), R3 (<10%)",
                    scoring_rules=["Q1", "R3"], history_depth="10 years"),
    FieldDefinition(83, "roa", Category.FINANCIAL_RATIOS, FieldType.DECIMAL, "%",
                    Priority.IMPORTANT, UpdateFrequency.ANNUAL, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="Asset efficiency",
                    history_depth="10 years"),
    FieldDefinition(84, "roic", Category.FINANCIAL_RATIOS, FieldType.DECIMAL, "%",
                    Priority.IMPORTANT, UpdateFrequency.ANNUAL, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="Capital efficiency",
                    history_depth="10 years"),
    FieldDefinition(85, "debt_to_equity", Category.FINANCIAL_RATIOS, FieldType.DECIMAL, "",
                    Priority.CRITICAL, UpdateFrequency.QUARTERLY, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="D8 (>5), R1, Q3 (0)",
                    scoring_rules=["D8", "R1", "Q3"], history_depth="10 years"),
    FieldDefinition(86, "interest_coverage", Category.FINANCIAL_RATIOS, FieldType.DECIMAL, "",
                    Priority.CRITICAL, UpdateFrequency.QUARTERLY, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="D1 (<2x), R2 (2-3x)",
                    scoring_rules=["D1", "R2"], history_depth="10 years"),
    FieldDefinition(87, "current_ratio", Category.FINANCIAL_RATIOS, FieldType.DECIMAL, "",
                    Priority.IMPORTANT, UpdateFrequency.ANNUAL, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="Liquidity (>1.5)",
                    history_depth="10 years"),
    FieldDefinition(88, "quick_ratio", Category.FINANCIAL_RATIOS, FieldType.DECIMAL, "",
                    Priority.STANDARD, UpdateFrequency.ANNUAL, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="Short-term liquidity",
                    history_depth="10 years"),
    FieldDefinition(89, "asset_turnover", Category.FINANCIAL_RATIOS, FieldType.DECIMAL, "",
                    Priority.STANDARD, UpdateFrequency.ANNUAL, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="Efficiency analysis",
                    history_depth="10 years"),
    FieldDefinition(90, "inventory_turnover", Category.FINANCIAL_RATIOS, FieldType.DECIMAL, "",
                    Priority.STANDARD, UpdateFrequency.ANNUAL, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="Working capital",
                    history_depth="10 years"),
    FieldDefinition(91, "receivables_turnover", Category.FINANCIAL_RATIOS, FieldType.DECIMAL, "",
                    Priority.STANDARD, UpdateFrequency.ANNUAL, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="Collection efficiency",
                    history_depth="10 years"),
    FieldDefinition(92, "dividend_payout_ratio", Category.FINANCIAL_RATIOS, FieldType.DECIMAL, "%",
                    Priority.IMPORTANT, UpdateFrequency.ANNUAL, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="Q4 (10yr consecutive)",
                    scoring_rules=["Q4"], history_depth="10 years"),

    # ===== CATEGORY 8: VALUATION METRICS (17 Fields) =====
    FieldDefinition(93, "market_cap", Category.VALUATION, FieldType.DECIMAL, "INR_CR",
                    Priority.CRITICAL, UpdateFrequency.DAILY, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, DataSource.SCREENER, "Size, EV calc",
                    history_depth="10 years"),
    FieldDefinition(94, "enterprise_value", Category.VALUATION, FieldType.DECIMAL, "INR_CR",
                    Priority.CRITICAL, UpdateFrequency.DAILY, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="EV/EBITDA",
                    history_depth="10 years"),
    FieldDefinition(95, "pe_ratio", Category.VALUATION, FieldType.DECIMAL, "",
                    Priority.CRITICAL, UpdateFrequency.DAILY, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, DataSource.SCREENER, "Valuation, R8",
                    scoring_rules=["R8"], history_depth="10 years"),
    FieldDefinition(96, "pe_ratio_forward", Category.VALUATION, FieldType.DECIMAL, "",
                    Priority.CRITICAL, UpdateFrequency.QUARTERLY, DataSource.TRENDLYNE,
                    ExtractionMethod.SCRAPE, used_for="Forward valuation",
                    history_depth="3 years"),
    FieldDefinition(97, "peg_ratio", Category.VALUATION, FieldType.DECIMAL, "",
                    Priority.CRITICAL, UpdateFrequency.QUARTERLY, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="Growth-adjusted val",
                    history_depth="10 years"),
    FieldDefinition(98, "pb_ratio", Category.VALUATION, FieldType.DECIMAL, "",
                    Priority.IMPORTANT, UpdateFrequency.DAILY, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="Asset-based val",
                    history_depth="10 years"),
    FieldDefinition(99, "ps_ratio", Category.VALUATION, FieldType.DECIMAL, "",
                    Priority.IMPORTANT, UpdateFrequency.DAILY, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="Revenue-based val",
                    history_depth="10 years"),
    FieldDefinition(100, "ev_to_ebitda", Category.VALUATION, FieldType.DECIMAL, "",
                    Priority.CRITICAL, UpdateFrequency.QUARTERLY, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="Valuation scoring",
                    history_depth="10 years"),
    FieldDefinition(101, "ev_to_sales", Category.VALUATION, FieldType.DECIMAL, "",
                    Priority.STANDARD, UpdateFrequency.QUARTERLY, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="Revenue-based EV",
                    history_depth="10 years"),
    FieldDefinition(102, "dividend_yield", Category.VALUATION, FieldType.DECIMAL, "%",
                    Priority.IMPORTANT, UpdateFrequency.DAILY, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, DataSource.SCREENER, "Income investing",
                    history_depth="10 years"),
    FieldDefinition(103, "fcf_yield", Category.VALUATION, FieldType.DECIMAL, "%",
                    Priority.IMPORTANT, UpdateFrequency.ANNUAL, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="Q9 booster (>5%)",
                    scoring_rules=["Q9"], history_depth="10 years"),
    FieldDefinition(104, "earnings_yield", Category.VALUATION, FieldType.DECIMAL, "%",
                    Priority.IMPORTANT, UpdateFrequency.DAILY, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="Bond yield comparison",
                    history_depth="10 years"),
    FieldDefinition(105, "sector_avg_pe", Category.VALUATION, FieldType.DECIMAL, "",
                    Priority.IMPORTANT, UpdateFrequency.WEEKLY, DataSource.SCREENER,
                    ExtractionMethod.SCRAPE, DataSource.TRENDLYNE, "R8 (P/E > 2x sector)",
                    scoring_rules=["R8"], history_depth="3 years"),
    FieldDefinition(106, "sector_avg_roe", Category.VALUATION, FieldType.DECIMAL, "%",
                    Priority.IMPORTANT, UpdateFrequency.WEEKLY, DataSource.SCREENER,
                    ExtractionMethod.SCRAPE, DataSource.TRENDLYNE, "Sector benchmark",
                    history_depth="3 years"),
    FieldDefinition(107, "industry_avg_pe", Category.VALUATION, FieldType.DECIMAL, "",
                    Priority.STANDARD, UpdateFrequency.WEEKLY, DataSource.SCREENER,
                    ExtractionMethod.SCRAPE, used_for="Industry comparison",
                    history_depth="3 years"),
    FieldDefinition(108, "historical_pe_median", Category.VALUATION, FieldType.DECIMAL, "",
                    Priority.STANDARD, UpdateFrequency.DAILY, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="Historical valuation",
                    history_depth="5 years"),
    FieldDefinition(109, "sector_performance", Category.VALUATION, FieldType.DECIMAL, "%",
                    Priority.IMPORTANT, UpdateFrequency.DAILY, DataSource.NSE_INDICES,
                    ExtractionMethod.DOWNLOAD, used_for="Sector strength check",
                    history_depth="1 year"),

    # ===== CATEGORY 9: SHAREHOLDING PATTERN (10 Fields) =====
    FieldDefinition(110, "promoter_holding", Category.SHAREHOLDING, FieldType.DECIMAL, "%",
                    Priority.CRITICAL, UpdateFrequency.QUARTERLY, DataSource.BSE_FILINGS,
                    ExtractionMethod.SCRAPE, DataSource.TRENDLYNE, "Ownership, R4",
                    scoring_rules=["R4"], history_depth="7 years"),
    FieldDefinition(111, "promoter_pledging", Category.SHAREHOLDING, FieldType.DECIMAL, "%",
                    Priority.CRITICAL, UpdateFrequency.QUARTERLY, DataSource.BSE_FILINGS,
                    ExtractionMethod.SCRAPE, DataSource.TRENDLYNE, "D7 (>80%), R5",
                    scoring_rules=["D7", "R5"], history_depth="7 years"),
    FieldDefinition(112, "fii_holding", Category.SHAREHOLDING, FieldType.DECIMAL, "%",
                    Priority.CRITICAL, UpdateFrequency.QUARTERLY, DataSource.BSE_FILINGS,
                    ExtractionMethod.SCRAPE, DataSource.TRENDLYNE, "Q6 booster",
                    scoring_rules=["Q6"], history_depth="7 years"),
    FieldDefinition(113, "dii_holding", Category.SHAREHOLDING, FieldType.DECIMAL, "%",
                    Priority.IMPORTANT, UpdateFrequency.QUARTERLY, DataSource.BSE_FILINGS,
                    ExtractionMethod.SCRAPE, used_for="Domestic institutional",
                    history_depth="7 years"),
    FieldDefinition(114, "public_holding", Category.SHAREHOLDING, FieldType.DECIMAL, "%",
                    Priority.IMPORTANT, UpdateFrequency.QUARTERLY, DataSource.BSE_FILINGS,
                    ExtractionMethod.SCRAPE, used_for="Retail participation",
                    history_depth="7 years"),
    FieldDefinition(115, "promoter_holding_change", Category.SHAREHOLDING, FieldType.DECIMAL, "%",
                    Priority.IMPORTANT, UpdateFrequency.QUARTERLY, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="R4 (>5% decline), Q5 (increase)",
                    scoring_rules=["R4", "Q5"], history_depth="7 years"),
    FieldDefinition(116, "fii_holding_change", Category.SHAREHOLDING, FieldType.DECIMAL, "%",
                    Priority.IMPORTANT, UpdateFrequency.QUARTERLY, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="Q6 (increase > 2%)",
                    scoring_rules=["Q6"], history_depth="7 years"),
    FieldDefinition(117, "num_shareholders", Category.SHAREHOLDING, FieldType.INTEGER, "",
                    Priority.STANDARD, UpdateFrequency.QUARTERLY, DataSource.BSE_FILINGS,
                    ExtractionMethod.SCRAPE, used_for="Retail breadth",
                    history_depth="7 years"),
    FieldDefinition(118, "mf_holding", Category.SHAREHOLDING, FieldType.DECIMAL, "%",
                    Priority.STANDARD, UpdateFrequency.QUARTERLY, DataSource.BSE_FILINGS,
                    ExtractionMethod.SCRAPE, used_for="MF interest",
                    history_depth="7 years"),
    FieldDefinition(119, "insurance_holding", Category.SHAREHOLDING, FieldType.DECIMAL, "%",
                    Priority.STANDARD, UpdateFrequency.QUARTERLY, DataSource.BSE_FILINGS,
                    ExtractionMethod.SCRAPE, used_for="Insurance interest",
                    history_depth="7 years"),

    # ===== CATEGORY 10: CORPORATE ACTIONS & EVENTS (10 Fields) =====
    FieldDefinition(120, "dividend_per_share", Category.CORPORATE_ACTIONS, FieldType.DECIMAL, "INR",
                    Priority.IMPORTANT, UpdateFrequency.ON_EVENT, DataSource.BSE_ANNOUNCEMENTS,
                    ExtractionMethod.SCRAPE, DataSource.SCREENER, "Div yield, Q4",
                    scoring_rules=["Q4"], history_depth="10 years"),
    FieldDefinition(121, "ex_dividend_date", Category.CORPORATE_ACTIONS, FieldType.DATE, "",
                    Priority.IMPORTANT, UpdateFrequency.ON_EVENT, DataSource.BSE_ANNOUNCEMENTS,
                    ExtractionMethod.SCRAPE, used_for="Price adjustment",
                    history_depth="10 years"),
    FieldDefinition(122, "stock_split_ratio", Category.CORPORATE_ACTIONS, FieldType.STRING, "",
                    Priority.IMPORTANT, UpdateFrequency.ON_EVENT, DataSource.BSE_ANNOUNCEMENTS,
                    ExtractionMethod.SCRAPE, used_for="Price/shares adjustment",
                    history_depth="10 years"),
    FieldDefinition(123, "bonus_ratio", Category.CORPORATE_ACTIONS, FieldType.STRING, "",
                    Priority.IMPORTANT, UpdateFrequency.ON_EVENT, DataSource.BSE_ANNOUNCEMENTS,
                    ExtractionMethod.SCRAPE, used_for="Shares adjustment",
                    history_depth="10 years"),
    FieldDefinition(124, "rights_issue_ratio", Category.CORPORATE_ACTIONS, FieldType.STRING, "",
                    Priority.STANDARD, UpdateFrequency.ON_EVENT, DataSource.BSE_ANNOUNCEMENTS,
                    ExtractionMethod.SCRAPE, used_for="Dilution tracking",
                    history_depth="10 years"),
    FieldDefinition(125, "buyback_details", Category.CORPORATE_ACTIONS, FieldType.STRING, "",
                    Priority.STANDARD, UpdateFrequency.ON_EVENT, DataSource.BSE_ANNOUNCEMENTS,
                    ExtractionMethod.SCRAPE, used_for="Capital return",
                    history_depth="10 years"),
    FieldDefinition(126, "next_earnings_date", Category.CORPORATE_ACTIONS, FieldType.DATE, "",
                    Priority.IMPORTANT, UpdateFrequency.ON_EVENT, DataSource.BSE_ANNOUNCEMENTS,
                    ExtractionMethod.SCRAPE, used_for="Checklist item",
                    history_depth="current"),
    FieldDefinition(127, "pending_events", Category.CORPORATE_ACTIONS, FieldType.LIST_OBJECT, "",
                    Priority.IMPORTANT, UpdateFrequency.ON_EVENT, DataSource.BSE_ANNOUNCEMENTS,
                    ExtractionMethod.SCRAPE, used_for="Catalyst calendar",
                    history_depth="current"),
    FieldDefinition(128, "stock_status", Category.CORPORATE_ACTIONS, FieldType.ENUM, "",
                    Priority.CRITICAL, UpdateFrequency.ON_EVENT, DataSource.NSE_BSE,
                    ExtractionMethod.DOWNLOAD, used_for="D6 deal-breaker",
                    scoring_rules=["D6"], history_depth="current"),
    FieldDefinition(129, "sebi_investigation", Category.CORPORATE_ACTIONS, FieldType.BOOLEAN, "",
                    Priority.CRITICAL, UpdateFrequency.ON_EVENT, DataSource.SEBI,
                    ExtractionMethod.SCRAPE, DataSource.RSS_FEEDS, "D2 deal-breaker",
                    scoring_rules=["D2"], history_depth="current"),

    # ===== CATEGORY 11: NEWS & SENTIMENT (8 Fields) =====
    FieldDefinition(130, "news_headline", Category.NEWS_SENTIMENT, FieldType.STRING, "",
                    Priority.IMPORTANT, UpdateFrequency.REAL_TIME, DataSource.RSS_FEEDS,
                    ExtractionMethod.RSS, used_for="News display",
                    history_depth="30 days"),
    FieldDefinition(131, "news_body_text", Category.NEWS_SENTIMENT, FieldType.STRING, "",
                    Priority.IMPORTANT, UpdateFrequency.REAL_TIME, DataSource.RSS_FEEDS,
                    ExtractionMethod.RSS, used_for="Full sentiment",
                    history_depth="30 days"),
    FieldDefinition(132, "news_source", Category.NEWS_SENTIMENT, FieldType.STRING, "",
                    Priority.STANDARD, UpdateFrequency.REAL_TIME, DataSource.RSS_FEEDS,
                    ExtractionMethod.RSS, used_for="Source credibility",
                    history_depth="30 days"),
    FieldDefinition(133, "news_timestamp", Category.NEWS_SENTIMENT, FieldType.DATETIME, "",
                    Priority.IMPORTANT, UpdateFrequency.REAL_TIME, DataSource.RSS_FEEDS,
                    ExtractionMethod.RSS, used_for="Recency weight",
                    history_depth="30 days"),
    FieldDefinition(134, "news_sentiment_score", Category.NEWS_SENTIMENT, FieldType.DECIMAL, "",
                    Priority.IMPORTANT, UpdateFrequency.REAL_TIME, DataSource.CALCULATED,
                    ExtractionMethod.NLP, used_for="Sentiment scoring",
                    history_depth="30 days"),
    FieldDefinition(135, "stock_tickers_mentioned", Category.NEWS_SENTIMENT, FieldType.LIST_STRING, "",
                    Priority.STANDARD, UpdateFrequency.REAL_TIME, DataSource.CALCULATED,
                    ExtractionMethod.NLP, used_for="Stock tagging",
                    history_depth="30 days"),
    FieldDefinition(136, "credit_rating", Category.NEWS_SENTIMENT, FieldType.STRING, "",
                    Priority.IMPORTANT, UpdateFrequency.ON_EVENT, DataSource.RATING_AGENCIES,
                    ExtractionMethod.SCRAPE, used_for="D9 deal-breaker",
                    scoring_rules=["D9"], history_depth="current"),
    FieldDefinition(137, "credit_outlook", Category.NEWS_SENTIMENT, FieldType.ENUM, "",
                    Priority.STANDARD, UpdateFrequency.ON_EVENT, DataSource.RATING_AGENCIES,
                    ExtractionMethod.SCRAPE, used_for="Credit trend",
                    history_depth="current"),

    # ===== CATEGORY 12: TECHNICAL INDICATORS (15 Fields) =====
    FieldDefinition(138, "sma_20", Category.TECHNICAL, FieldType.DECIMAL, "INR",
                    Priority.IMPORTANT, UpdateFrequency.DAILY, DataSource.PANDAS_TA,
                    ExtractionMethod.CALCULATED, used_for="Short-term trend",
                    history_depth="10 years"),
    FieldDefinition(139, "sma_50", Category.TECHNICAL, FieldType.DECIMAL, "INR",
                    Priority.CRITICAL, UpdateFrequency.DAILY, DataSource.PANDAS_TA,
                    ExtractionMethod.CALCULATED, used_for="Medium trend, checklist",
                    history_depth="10 years"),
    FieldDefinition(140, "sma_200", Category.TECHNICAL, FieldType.DECIMAL, "INR",
                    Priority.CRITICAL, UpdateFrequency.DAILY, DataSource.PANDAS_TA,
                    ExtractionMethod.CALCULATED, used_for="Long-term trend",
                    history_depth="10 years"),
    FieldDefinition(141, "ema_12", Category.TECHNICAL, FieldType.DECIMAL, "INR",
                    Priority.IMPORTANT, UpdateFrequency.DAILY, DataSource.PANDAS_TA,
                    ExtractionMethod.CALCULATED, used_for="MACD calculation",
                    history_depth="10 years"),
    FieldDefinition(142, "ema_26", Category.TECHNICAL, FieldType.DECIMAL, "INR",
                    Priority.IMPORTANT, UpdateFrequency.DAILY, DataSource.PANDAS_TA,
                    ExtractionMethod.CALCULATED, used_for="MACD calculation",
                    history_depth="10 years"),
    FieldDefinition(143, "rsi_14", Category.TECHNICAL, FieldType.DECIMAL, "",
                    Priority.CRITICAL, UpdateFrequency.DAILY, DataSource.PANDAS_TA,
                    ExtractionMethod.CALCULATED, used_for="Overbought/sold (30-70)",
                    history_depth="10 years"),
    FieldDefinition(144, "macd", Category.TECHNICAL, FieldType.DECIMAL, "",
                    Priority.CRITICAL, UpdateFrequency.DAILY, DataSource.PANDAS_TA,
                    ExtractionMethod.CALCULATED, used_for="Momentum scoring",
                    history_depth="10 years"),
    FieldDefinition(145, "macd_signal", Category.TECHNICAL, FieldType.DECIMAL, "",
                    Priority.CRITICAL, UpdateFrequency.DAILY, DataSource.PANDAS_TA,
                    ExtractionMethod.CALCULATED, used_for="Signal crossovers",
                    history_depth="10 years"),
    FieldDefinition(146, "bollinger_upper", Category.TECHNICAL, FieldType.DECIMAL, "INR",
                    Priority.IMPORTANT, UpdateFrequency.DAILY, DataSource.PANDAS_TA,
                    ExtractionMethod.CALCULATED, used_for="Volatility bands",
                    history_depth="10 years"),
    FieldDefinition(147, "bollinger_lower", Category.TECHNICAL, FieldType.DECIMAL, "INR",
                    Priority.IMPORTANT, UpdateFrequency.DAILY, DataSource.PANDAS_TA,
                    ExtractionMethod.CALCULATED, used_for="Volatility bands",
                    history_depth="10 years"),
    FieldDefinition(148, "atr_14", Category.TECHNICAL, FieldType.DECIMAL, "",
                    Priority.IMPORTANT, UpdateFrequency.DAILY, DataSource.PANDAS_TA,
                    ExtractionMethod.CALCULATED, used_for="Stop-loss calc",
                    history_depth="10 years"),
    FieldDefinition(149, "adx_14", Category.TECHNICAL, FieldType.DECIMAL, "",
                    Priority.STANDARD, UpdateFrequency.DAILY, DataSource.PANDAS_TA,
                    ExtractionMethod.CALCULATED, used_for="Trend strength",
                    history_depth="10 years"),
    FieldDefinition(150, "obv", Category.TECHNICAL, FieldType.INTEGER, "",
                    Priority.STANDARD, UpdateFrequency.DAILY, DataSource.PANDAS_TA,
                    ExtractionMethod.CALCULATED, used_for="Volume confirmation",
                    history_depth="10 years"),
    FieldDefinition(151, "support_level", Category.TECHNICAL, FieldType.DECIMAL, "INR",
                    Priority.IMPORTANT, UpdateFrequency.DAILY, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="Stop-loss, checklist",
                    history_depth="1 year"),
    FieldDefinition(152, "resistance_level", Category.TECHNICAL, FieldType.DECIMAL, "INR",
                    Priority.IMPORTANT, UpdateFrequency.DAILY, DataSource.CALCULATED,
                    ExtractionMethod.CALCULATED, used_for="Target, checklist",
                    history_depth="1 year"),

    # ===== CATEGORY 13: QUALITATIVE & METADATA (8 Fields) =====
    FieldDefinition(153, "moat_assessment", Category.QUALITATIVE_METADATA, FieldType.STRING, "",
                    Priority.QUALITATIVE, UpdateFrequency.ON_EVENT, DataSource.MANUAL_LLM,
                    ExtractionMethod.MANUAL, used_for="Competitive moat"),
    FieldDefinition(154, "management_assessment", Category.QUALITATIVE_METADATA, FieldType.STRING, "",
                    Priority.QUALITATIVE, UpdateFrequency.ON_EVENT, DataSource.MANUAL_LLM,
                    ExtractionMethod.MANUAL, used_for="Management track record"),
    FieldDefinition(155, "industry_growth_assessment", Category.QUALITATIVE_METADATA, FieldType.STRING, "",
                    Priority.QUALITATIVE, UpdateFrequency.ON_EVENT, DataSource.MANUAL_LLM,
                    ExtractionMethod.MANUAL, used_for="Industry tailwinds"),
    FieldDefinition(156, "disruption_risk", Category.QUALITATIVE_METADATA, FieldType.STRING, "",
                    Priority.QUALITATIVE, UpdateFrequency.ON_EVENT, DataSource.MANUAL_LLM,
                    ExtractionMethod.MANUAL, used_for="Existential disruption"),
    FieldDefinition(157, "fraud_history", Category.QUALITATIVE_METADATA, FieldType.BOOLEAN, "",
                    Priority.QUALITATIVE, UpdateFrequency.ON_EVENT, DataSource.MANUAL_LLM,
                    ExtractionMethod.MANUAL, used_for="No accounting fraud"),
    FieldDefinition(158, "field_availability", Category.QUALITATIVE_METADATA, FieldType.DICT_BOOL, "",
                    Priority.METADATA, UpdateFrequency.CONTINUOUS, DataSource.SYSTEM,
                    ExtractionMethod.AUTO, used_for="Confidence: Completeness (40%)"),
    FieldDefinition(159, "field_last_updated", Category.QUALITATIVE_METADATA, FieldType.DICT_DATETIME, "",
                    Priority.METADATA, UpdateFrequency.CONTINUOUS, DataSource.SYSTEM,
                    ExtractionMethod.AUTO, used_for="Confidence: Freshness (30%)"),
    FieldDefinition(160, "multi_source_values", Category.QUALITATIVE_METADATA, FieldType.DICT_DICT, "",
                    Priority.METADATA, UpdateFrequency.CONTINUOUS, DataSource.SYSTEM,
                    ExtractionMethod.AUTO, used_for="Confidence: Source Agreement (15%)"),
]


# Lookup helpers
FIELD_BY_ID = {f.field_id: f for f in FIELD_DEFINITIONS}
FIELD_BY_NAME = {f.name: f for f in FIELD_DEFINITIONS}
FIELDS_BY_CATEGORY = {}
for f in FIELD_DEFINITIONS:
    FIELDS_BY_CATEGORY.setdefault(f.category, []).append(f)
FIELDS_BY_PRIORITY = {}
for f in FIELD_DEFINITIONS:
    FIELDS_BY_PRIORITY.setdefault(f.priority, []).append(f)

CRITICAL_FIELD_NAMES = [f.name for f in FIELD_DEFINITIONS if f.priority == Priority.CRITICAL]
CALCULATED_FIELD_NAMES = [f.name for f in FIELD_DEFINITIONS if f.method == ExtractionMethod.CALCULATED]
SCORING_FIELDS = [f for f in FIELD_DEFINITIONS if f.scoring_rules]

# Category summary counts
CATEGORY_COUNTS = {cat: len(fields) for cat, fields in FIELDS_BY_CATEGORY.items()}
PRIORITY_COUNTS = {p: len(fields) for p, fields in FIELDS_BY_PRIORITY.items()}
TOTAL_FIELDS = len(FIELD_DEFINITIONS)
