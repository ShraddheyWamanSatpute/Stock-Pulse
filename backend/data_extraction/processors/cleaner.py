"""
Data cleaning and normalization module.

Handles:
- Type coercion (strings to numbers)
- Unit normalization (Lakhs to Crores, raw to percentages)
- Outlier detection and capping
- Missing value handling
- String normalization (trimming, casing)
"""

import logging
import math
import re
from typing import Any, Dict, List, Optional

from ..config.field_definitions import FIELD_BY_NAME, FieldType
from ..models.extraction_models import StockDataRecord

logger = logging.getLogger(__name__)

# Reasonable bounds for common financial metrics
FIELD_BOUNDS = {
    "pe_ratio": (-1000, 5000),
    "pb_ratio": (-100, 500),
    "roe": (-500, 500),
    "roa": (-200, 200),
    "debt_to_equity": (-10, 100),
    "interest_coverage": (-100, 1000),
    "current_ratio": (0, 100),
    "quick_ratio": (0, 100),
    "operating_margin": (-200, 100),
    "net_profit_margin": (-500, 100),
    "gross_margin": (-100, 100),
    "dividend_yield": (0, 50),
    "promoter_holding": (0, 100),
    "promoter_pledging": (0, 100),
    "fii_holding": (0, 100),
    "dii_holding": (0, 100),
    "public_holding": (0, 100),
    "delivery_percentage": (0, 100),
    "rsi_14": (0, 100),
    "adx_14": (0, 100),
}


class DataCleaner:
    """
    Cleans and normalizes extracted data fields.

    Call clean_record() after extraction and before calculations.
    """

    def clean_record(self, record: StockDataRecord) -> int:
        """
        Clean all fields in a record.

        Returns the number of fields that were modified.
        """
        modified = 0

        # Clean each category's dict
        for category_dict in [
            record.stock_master, record.price_volume,
            record.derived_metrics, record.income_statement,
            record.balance_sheet, record.cash_flow,
            record.financial_ratios, record.valuation,
            record.shareholding, record.corporate_actions,
            record.news_sentiment, record.technical,
        ]:
            for field_name in list(category_dict.keys()):
                original = category_dict[field_name]
                cleaned = self._clean_field(field_name, original)
                if cleaned != original:
                    category_dict[field_name] = cleaned
                    modified += 1

        # Clean price history entries
        for entry in record.price_history:
            for key in ["open", "high", "low", "close", "adjusted_close"]:
                if key in entry:
                    entry[key] = self._coerce_number(entry[key])
            if "volume" in entry:
                entry["volume"] = self._coerce_int(entry["volume"])

        return modified

    def _clean_field(self, field_name: str, value: Any) -> Any:
        """Clean a single field value based on its definition."""
        if value is None:
            return None

        fd = FIELD_BY_NAME.get(field_name)
        if not fd:
            return value

        # Type coercion
        if fd.data_type in (FieldType.DECIMAL,):
            value = self._coerce_number(value)
        elif fd.data_type == FieldType.INTEGER:
            value = self._coerce_int(value)
        elif fd.data_type == FieldType.STRING:
            value = self._clean_string(value)
        elif fd.data_type == FieldType.BOOLEAN:
            value = self._coerce_bool(value)

        # Bounds checking for numeric fields
        if isinstance(value, (int, float)) and field_name in FIELD_BOUNDS:
            low, high = FIELD_BOUNDS[field_name]
            if value < low or value > high:
                logger.warning(
                    f"Field {field_name} value {value} outside bounds "
                    f"[{low}, {high}], capping"
                )
                value = max(low, min(high, value))

        # NaN/Inf check
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return None

        return value

    @staticmethod
    def _coerce_number(value: Any) -> Optional[float]:
        """Convert a value to float, handling common formats."""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            if math.isnan(value) or math.isinf(value):
                return None
            return float(value)
        if isinstance(value, str):
            # Remove common formatting
            cleaned = value.strip().replace(",", "").replace("₹", "").replace("$", "")
            cleaned = cleaned.replace("%", "").replace("Cr", "").replace("Lakh", "")
            cleaned = cleaned.strip()
            if not cleaned or cleaned == "-" or cleaned.lower() in ("nan", "n/a", "null", "none"):
                return None
            try:
                return float(cleaned)
            except ValueError:
                return None
        return None

    @staticmethod
    def _coerce_int(value: Any) -> Optional[int]:
        """Convert a value to int."""
        if value is None:
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            if math.isnan(value) or math.isinf(value):
                return None
            return int(value)
        if isinstance(value, str):
            cleaned = value.strip().replace(",", "")
            if not cleaned or cleaned == "-":
                return None
            try:
                return int(float(cleaned))
            except ValueError:
                return None
        return None

    @staticmethod
    def _clean_string(value: Any) -> Optional[str]:
        """Clean a string value."""
        if value is None:
            return None
        s = str(value).strip()
        if not s or s.lower() in ("nan", "n/a", "null", "none", "-"):
            return None
        # Normalize whitespace
        s = re.sub(r'\s+', ' ', s)
        return s

    @staticmethod
    def _coerce_bool(value: Any) -> Optional[bool]:
        """Convert a value to bool."""
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            lower = value.strip().lower()
            if lower in ("true", "yes", "1", "y"):
                return True
            if lower in ("false", "no", "0", "n"):
                return False
        return None
