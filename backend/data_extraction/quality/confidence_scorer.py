"""
Confidence scoring module for data quality assessment.

Computes an overall confidence score based on:
    - Completeness (40%): Percentage of fields populated
    - Freshness (30%): How recently fields were updated
    - Source Agreement (15%): Cross-source validation
    - Validation Pass Rate (15%): Rules passed vs failed

Score ranges:
    90-100: High confidence — safe to use for scoring/decisions
    70-89:  Medium confidence — usable with caveats
    50-69:  Low confidence — missing important data
    0-49:   Very low — insufficient data for meaningful analysis
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ..config.field_definitions import (
    FIELD_DEFINITIONS, FIELD_BY_NAME, CRITICAL_FIELD_NAMES,
    Category, Priority, TOTAL_FIELDS, FIELDS_BY_CATEGORY,
)
from ..models.extraction_models import StockDataRecord, QualityReport

logger = logging.getLogger(__name__)

# Weight configuration for confidence score components
COMPLETENESS_WEIGHT = 0.40
FRESHNESS_WEIGHT = 0.30
SOURCE_AGREEMENT_WEIGHT = 0.15
VALIDATION_WEIGHT = 0.15

# Freshness thresholds (how old before data is considered stale)
FRESHNESS_THRESHOLDS = {
    "daily": timedelta(days=2),
    "weekly": timedelta(days=10),
    "quarterly": timedelta(days=120),
    "annual": timedelta(days=400),
    "on_event": timedelta(days=90),
    "real_time": timedelta(hours=6),
    "continuous": timedelta(hours=1),
    "never": timedelta(days=36500),  # ~100 years
}

# Critical fields that significantly impact confidence
CRITICAL_FIELD_WEIGHT = 2.0
IMPORTANT_FIELD_WEIGHT = 1.5
STANDARD_FIELD_WEIGHT = 1.0
OPTIONAL_FIELD_WEIGHT = 0.5


class ConfidenceScorer:
    """
    Computes data quality and confidence scores for stock records.

    The confidence score is a weighted combination of:
        - Field completeness (how many fields are populated)
        - Data freshness (how recently updated)
        - Source agreement (do multiple sources agree)
        - Validation pass rate (scoring rules passed)
    """

    def score(self, record: StockDataRecord) -> QualityReport:
        """
        Compute the full quality/confidence report for a stock record.
        """
        report = QualityReport(symbol=record.symbol)

        # 1. Completeness score
        report.completeness_score = self._score_completeness(record, report)

        # 2. Freshness score
        report.freshness_score = self._score_freshness(record, report)

        # 3. Source agreement score
        report.source_agreement_score = self._score_source_agreement(record)

        # 4. Validation score
        report.validation_score = self._score_validation(record)

        # Overall confidence (weighted)
        report.overall_confidence = round(
            report.completeness_score * COMPLETENESS_WEIGHT +
            report.freshness_score * FRESHNESS_WEIGHT +
            report.source_agreement_score * SOURCE_AGREEMENT_WEIGHT +
            report.validation_score * VALIDATION_WEIGHT,
            1
        )

        # Category-level coverage
        report.field_coverage_by_category = self._category_coverage(record)

        return report

    def _score_completeness(self, record: StockDataRecord,
                            report: QualityReport) -> float:
        """
        Score field completeness using weighted field priority.

        Critical fields weigh 2x, Important 1.5x, Standard 1x, Optional 0.5x.
        """
        total_weight = 0.0
        populated_weight = 0.0
        missing_critical = []

        for fd in FIELD_DEFINITIONS:
            # Skip metadata fields
            if fd.priority in (Priority.METADATA,):
                continue

            weight = {
                Priority.CRITICAL: CRITICAL_FIELD_WEIGHT,
                Priority.IMPORTANT: IMPORTANT_FIELD_WEIGHT,
                Priority.STANDARD: STANDARD_FIELD_WEIGHT,
                Priority.OPTIONAL: OPTIONAL_FIELD_WEIGHT,
                Priority.QUALITATIVE: OPTIONAL_FIELD_WEIGHT,
            }.get(fd.priority, STANDARD_FIELD_WEIGHT)

            total_weight += weight

            is_available = record.field_availability.get(fd.name, False)
            if is_available:
                populated_weight += weight
            elif fd.priority == Priority.CRITICAL:
                missing_critical.append(fd.name)

        report.missing_critical_fields = missing_critical

        if total_weight == 0:
            return 0.0
        return round((populated_weight / total_weight) * 100, 1)

    def _score_freshness(self, record: StockDataRecord,
                         report: QualityReport) -> float:
        """
        Score how fresh/current the data is.

        Each field is scored based on its expected update frequency.
        """
        now = datetime.utcnow()
        total_fields = 0
        fresh_score_sum = 0.0
        stale_fields = []

        for fd in FIELD_DEFINITIONS:
            if fd.priority in (Priority.METADATA, Priority.QUALITATIVE):
                continue

            last_updated = record.field_last_updated.get(fd.name)
            if last_updated is None:
                continue

            total_fields += 1
            threshold = FRESHNESS_THRESHOLDS.get(
                fd.update_frequency.value, timedelta(days=30)
            )

            age = now - last_updated
            if age <= threshold:
                fresh_score_sum += 100.0
            elif age <= threshold * 2:
                # Linearly decay from 100 to 50 over 1x-2x threshold
                ratio = (age - threshold) / threshold
                fresh_score_sum += max(50.0, 100.0 - 50.0 * ratio)
            else:
                # Stale
                fresh_score_sum += max(0.0, 50.0 - (age / threshold - 2) * 25.0)
                stale_fields.append(fd.name)

        report.stale_fields = stale_fields

        if total_fields == 0:
            return 0.0
        return round(fresh_score_sum / total_fields, 1)

    def _score_source_agreement(self, record: StockDataRecord) -> float:
        """
        Score cross-source agreement for fields with multiple sources.

        Higher score when multiple sources agree on the same value.
        """
        if not record.multi_source_values:
            # No multi-source data available; use neutral score
            return 50.0

        total = 0
        agreed = 0
        for field_name, msv in record.multi_source_values.items():
            if len(msv.values) < 2:
                continue
            total += 1
            if msv.agreement_score > 0.95:
                agreed += 1
            elif msv.agreement_score > 0.80:
                agreed += 0.5

        if total == 0:
            return 50.0
        return round((agreed / total) * 100, 1)

    def _score_validation(self, record: StockDataRecord) -> float:
        """
        Score based on validation rule pass rate.

        Deal-breaker failures have outsized impact.
        """
        validation = record.qualitative_metadata.get("validation_result", {})
        if not validation:
            return 50.0  # Neutral if not yet validated

        if not validation.get("is_investable", True):
            # Deal-breaker triggered — max 30% validation score
            return 30.0

        risk_count = validation.get("risk_penalties_triggered", 0)
        boost_count = validation.get("quality_boosters_triggered", 0)

        # Base 70, -5 per risk, +3 per boost, capped at 0-100
        score = 70 - (risk_count * 5) + (boost_count * 3)
        return max(0.0, min(100.0, float(score)))

    def _category_coverage(self, record: StockDataRecord) -> Dict[str, float]:
        """Calculate field coverage percentage per category."""
        coverage = {}
        for category, fields in FIELDS_BY_CATEGORY.items():
            total = len(fields)
            available = sum(
                1 for f in fields
                if record.field_availability.get(f.name, False)
            )
            coverage[category.value] = round(
                (available / total * 100) if total > 0 else 0.0, 1
            )
        return coverage
