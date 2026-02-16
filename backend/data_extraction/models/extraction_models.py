"""
Data models for the extraction pipeline.

Defines the data structures for raw extraction records, processed stock data,
metadata tracking, and pipeline execution state.
"""

from datetime import datetime, date
from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


class ExtractionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"


class DataQuality(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNVERIFIED = "unverified"


@dataclass
class ExtractionRecord:
    """Record of a single extraction attempt from a source."""
    source: str
    symbol: str
    fields_extracted: List[str]
    fields_failed: List[str]
    status: ExtractionStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: int = 0
    error_message: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None
    retry_count: int = 0


@dataclass
class FieldValue:
    """A single field value with metadata tracking."""
    field_name: str
    value: Any
    source: str
    extracted_at: datetime
    quality: DataQuality = DataQuality.UNVERIFIED
    confidence: float = 0.0
    is_calculated: bool = False
    calculation_inputs: Optional[List[str]] = None


@dataclass
class MultiSourceValue:
    """Values from multiple sources for cross-validation."""
    field_name: str
    values: Dict[str, Any]  # source -> value
    timestamps: Dict[str, datetime]  # source -> extraction time
    agreed_value: Optional[Any] = None
    agreement_score: float = 0.0


@dataclass
class StockDataRecord:
    """Complete data record for a single stock with all fields."""
    symbol: str
    company_name: str
    last_updated: datetime = field(default_factory=datetime.utcnow)

    # Category data (all optional, populated progressively)
    stock_master: Dict[str, Any] = field(default_factory=dict)
    price_volume: Dict[str, Any] = field(default_factory=dict)
    derived_metrics: Dict[str, Any] = field(default_factory=dict)
    income_statement: Dict[str, Any] = field(default_factory=dict)
    balance_sheet: Dict[str, Any] = field(default_factory=dict)
    cash_flow: Dict[str, Any] = field(default_factory=dict)
    financial_ratios: Dict[str, Any] = field(default_factory=dict)
    valuation: Dict[str, Any] = field(default_factory=dict)
    shareholding: Dict[str, Any] = field(default_factory=dict)
    corporate_actions: Dict[str, Any] = field(default_factory=dict)
    news_sentiment: Dict[str, Any] = field(default_factory=dict)
    technical: Dict[str, Any] = field(default_factory=dict)
    qualitative_metadata: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    field_availability: Dict[str, bool] = field(default_factory=dict)
    field_last_updated: Dict[str, datetime] = field(default_factory=dict)
    multi_source_values: Dict[str, MultiSourceValue] = field(default_factory=dict)
    extraction_history: List[ExtractionRecord] = field(default_factory=list)

    # Price history (time series data stored separately)
    price_history: List[Dict[str, Any]] = field(default_factory=list)
    quarterly_results: List[Dict[str, Any]] = field(default_factory=list)
    annual_results: List[Dict[str, Any]] = field(default_factory=list)
    shareholding_history: List[Dict[str, Any]] = field(default_factory=list)

    def set_field(self, field_name: str, value: Any, source: str) -> None:
        """Set a field value and update metadata."""
        from ..config.field_definitions import FIELD_BY_NAME, Category
        fd = FIELD_BY_NAME.get(field_name)
        if not fd:
            return

        category_map = {
            Category.STOCK_MASTER: self.stock_master,
            Category.PRICE_VOLUME: self.price_volume,
            Category.DERIVED_METRICS: self.derived_metrics,
            Category.INCOME_STATEMENT: self.income_statement,
            Category.BALANCE_SHEET: self.balance_sheet,
            Category.CASH_FLOW: self.cash_flow,
            Category.FINANCIAL_RATIOS: self.financial_ratios,
            Category.VALUATION: self.valuation,
            Category.SHAREHOLDING: self.shareholding,
            Category.CORPORATE_ACTIONS: self.corporate_actions,
            Category.NEWS_SENTIMENT: self.news_sentiment,
            Category.TECHNICAL: self.technical,
            Category.QUALITATIVE_METADATA: self.qualitative_metadata,
        }

        target = category_map.get(fd.category)
        if target is not None:
            target[field_name] = value
            self.field_availability[field_name] = True
            self.field_last_updated[field_name] = datetime.utcnow()
            self.last_updated = datetime.utcnow()

    def get_field(self, field_name: str) -> Optional[Any]:
        """Get a field value from the appropriate category."""
        from ..config.field_definitions import FIELD_BY_NAME, Category
        fd = FIELD_BY_NAME.get(field_name)
        if not fd:
            return None

        category_map = {
            Category.STOCK_MASTER: self.stock_master,
            Category.PRICE_VOLUME: self.price_volume,
            Category.DERIVED_METRICS: self.derived_metrics,
            Category.INCOME_STATEMENT: self.income_statement,
            Category.BALANCE_SHEET: self.balance_sheet,
            Category.CASH_FLOW: self.cash_flow,
            Category.FINANCIAL_RATIOS: self.financial_ratios,
            Category.VALUATION: self.valuation,
            Category.SHAREHOLDING: self.shareholding,
            Category.CORPORATE_ACTIONS: self.corporate_actions,
            Category.NEWS_SENTIMENT: self.news_sentiment,
            Category.TECHNICAL: self.technical,
            Category.QUALITATIVE_METADATA: self.qualitative_metadata,
        }

        target = category_map.get(fd.category, {})
        return target.get(field_name)

    def get_completeness(self) -> float:
        """Calculate field completeness as a percentage."""
        from ..config.field_definitions import TOTAL_FIELDS
        available = sum(1 for v in self.field_availability.values() if v)
        return (available / TOTAL_FIELDS) * 100.0 if TOTAL_FIELDS > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage."""
        return {
            "symbol": self.symbol,
            "company_name": self.company_name,
            "last_updated": self.last_updated.isoformat(),
            "stock_master": self.stock_master,
            "price_volume": self.price_volume,
            "derived_metrics": self.derived_metrics,
            "income_statement": self.income_statement,
            "balance_sheet": self.balance_sheet,
            "cash_flow": self.cash_flow,
            "financial_ratios": self.financial_ratios,
            "valuation": self.valuation,
            "shareholding": self.shareholding,
            "corporate_actions": self.corporate_actions,
            "news_sentiment": self.news_sentiment,
            "technical": self.technical,
            "qualitative_metadata": self.qualitative_metadata,
            "field_availability": self.field_availability,
            "field_last_updated": {
                k: v.isoformat() for k, v in self.field_last_updated.items()
            },
            "price_history": self.price_history,
            "quarterly_results": self.quarterly_results,
            "annual_results": self.annual_results,
            "shareholding_history": self.shareholding_history,
        }


@dataclass
class PipelineJob:
    """Represents a single pipeline execution job."""
    job_id: str
    symbols: List[str]
    sources: List[str]
    status: ExtractionStatus = ExtractionStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_symbols: int = 0
    processed_symbols: int = 0
    failed_symbols: int = 0
    extraction_records: List[ExtractionRecord] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def progress_pct(self) -> float:
        if self.total_symbols == 0:
            return 0.0
        return (self.processed_symbols / self.total_symbols) * 100.0


@dataclass
class ValidationResult:
    """Result of field validation."""
    field_name: str
    is_valid: bool
    rule_id: str
    rule_description: str
    actual_value: Any = None
    expected_range: Optional[str] = None
    severity: str = "warning"  # "error", "warning", "info"
    message: str = ""


@dataclass
class QualityReport:
    """Quality assessment report for a stock's data."""
    symbol: str
    generated_at: datetime = field(default_factory=datetime.utcnow)
    completeness_score: float = 0.0
    freshness_score: float = 0.0
    source_agreement_score: float = 0.0
    validation_score: float = 0.0
    overall_confidence: float = 0.0
    missing_critical_fields: List[str] = field(default_factory=list)
    stale_fields: List[str] = field(default_factory=list)
    validation_failures: List[ValidationResult] = field(default_factory=list)
    field_coverage_by_category: Dict[str, float] = field(default_factory=dict)
