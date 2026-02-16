"""
Validation engine for scoring rules (D1-D10, R1-R10, Q1-Q10).

Evaluates all deal-breakers, risk penalties, and quality boosters
against a stock's data record and produces a comprehensive validation report.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..config.validation_rules import (
    ALL_RULES,
    DEAL_BREAKER_RULES,
    RISK_PENALTY_RULES,
    QUALITY_BOOSTER_RULES,
    RuleType,
    ValidationRule,
)
from ..models.extraction_models import StockDataRecord, ValidationResult

logger = logging.getLogger(__name__)

# Below-investment-grade ratings
BELOW_INVESTMENT_GRADE = {"BB+", "BB", "BB-", "B+", "B", "B-",
                          "CCC+", "CCC", "CCC-", "CC", "C", "D"}


class ValidationEngine:
    """
    Evaluates all 30 scoring rules against a stock's data.

    Returns:
        - List of triggered deal-breakers (auto-fail)
        - List of triggered risk penalties (score deductions)
        - List of triggered quality boosters (score additions)
        - Overall validation summary
    """

    def validate_all(self, record: StockDataRecord) -> Dict[str, Any]:
        """
        Run all validation rules against a stock record.

        Returns a dict with keys:
            deal_breakers: List[ValidationResult]
            risk_penalties: List[ValidationResult]
            quality_boosters: List[ValidationResult]
            is_investable: bool (False if any deal-breaker triggered)
            total_penalty: float
            total_boost: float
            net_adjustment: float
        """
        deal_breakers = self._check_deal_breakers(record)
        risk_penalties = self._check_risk_penalties(record)
        quality_boosters = self._check_quality_boosters(record)

        triggered_dbs = [r for r in deal_breakers if not r.is_valid]
        triggered_risks = [r for r in risk_penalties if not r.is_valid]
        triggered_boosts = [r for r in quality_boosters if r.is_valid]

        total_penalty = sum(
            abs(r.actual_value) if isinstance(r.actual_value, (int, float)) else 0
            for r in triggered_risks
        )
        total_boost = sum(
            r.actual_value if isinstance(r.actual_value, (int, float)) else 0
            for r in triggered_boosts
        )

        return {
            "deal_breakers": deal_breakers,
            "risk_penalties": risk_penalties,
            "quality_boosters": quality_boosters,
            "triggered_deal_breakers": triggered_dbs,
            "triggered_risk_penalties": triggered_risks,
            "triggered_quality_boosters": triggered_boosts,
            "is_investable": len(triggered_dbs) == 0,
            "total_penalty": total_penalty,
            "total_boost": total_boost,
            "net_adjustment": total_boost - total_penalty,
        }

    def _check_deal_breakers(self, record: StockDataRecord) -> List[ValidationResult]:
        """Check all 10 deal-breaker rules."""
        results = []

        # D1: Interest Coverage < 2.0
        results.append(self._check_d1(record))
        # D2: SEBI Investigation
        results.append(self._check_d2(record))
        # D3: Revenue declining 3+ quarters
        results.append(self._check_d3(record))
        # D4: Negative OCF 3+ years
        results.append(self._check_d4(record))
        # D5: Negative FCF 5+ years
        results.append(self._check_d5(record))
        # D6: Trading Suspension
        results.append(self._check_d6(record))
        # D7: Promoter Pledging > 80%
        results.append(self._check_d7(record))
        # D8: Debt-to-Equity > 5.0
        results.append(self._check_d8(record))
        # D9: Below Investment Grade
        results.append(self._check_d9(record))
        # D10: Avg Volume < 50,000
        results.append(self._check_d10(record))

        return results

    def _check_risk_penalties(self, record: StockDataRecord) -> List[ValidationResult]:
        """Check all 10 risk penalty rules."""
        results = []

        results.append(self._check_r1(record))
        results.append(self._check_r2(record))
        results.append(self._check_r3(record))
        results.append(self._check_r4(record))
        results.append(self._check_r5(record))
        results.append(self._check_r6(record))
        results.append(self._check_r7(record))
        results.append(self._check_r8(record))
        results.append(self._check_r9(record))
        results.append(self._check_r10(record))

        return results

    def _check_quality_boosters(self, record: StockDataRecord) -> List[ValidationResult]:
        """Check all 10 quality booster rules."""
        results = []

        results.append(self._check_q1(record))
        results.append(self._check_q2(record))
        results.append(self._check_q3(record))
        results.append(self._check_q4(record))
        results.append(self._check_q5(record))
        results.append(self._check_q6(record))
        results.append(self._check_q7(record))
        results.append(self._check_q8(record))
        results.append(self._check_q9(record))
        results.append(self._check_q10(record))

        return results

    # ===== DEAL-BREAKERS =====

    def _check_d1(self, r: StockDataRecord) -> ValidationResult:
        ic = r.get_field("interest_coverage")
        if ic is None:
            return ValidationResult("interest_coverage", True, "D1",
                                    "Interest coverage check", severity="info",
                                    message="Interest coverage data not available")
        triggered = ic < 2.0
        return ValidationResult(
            "interest_coverage", not triggered, "D1",
            "Interest coverage >= 2.0x",
            actual_value=ic, expected_range=">=2.0",
            severity="critical" if triggered else "pass",
            message=f"Interest coverage {ic:.1f}x {'< 2.0x DEAL-BREAKER' if triggered else 'OK'}"
        )

    def _check_d2(self, r: StockDataRecord) -> ValidationResult:
        investigation = r.get_field("sebi_investigation")
        if investigation is None:
            return ValidationResult("sebi_investigation", True, "D2",
                                    "SEBI investigation check", severity="info",
                                    message="SEBI data not available")
        triggered = investigation is True
        return ValidationResult(
            "sebi_investigation", not triggered, "D2",
            "No active SEBI investigation",
            actual_value=investigation,
            severity="critical" if triggered else "pass",
            message="Active SEBI investigation DEAL-BREAKER" if triggered else "No SEBI action"
        )

    def _check_d3(self, r: StockDataRecord) -> ValidationResult:
        results = r.quarterly_results
        if len(results) < 8:
            return ValidationResult("revenue_growth_yoy", True, "D3",
                                    "Revenue decline check", severity="info",
                                    message="Insufficient quarterly data")
        decline_count = 0
        for i in range(min(len(results) - 4, 4)):
            curr = _safe_val(results[i], "revenue")
            prev_yr = _safe_val(results[i + 4], "revenue")
            if curr is not None and prev_yr is not None and prev_yr > 0:
                if curr < prev_yr:
                    decline_count += 1
                else:
                    break
            else:
                break
        triggered = decline_count >= 3
        return ValidationResult(
            "revenue_growth_yoy", not triggered, "D3",
            "Revenue not declining 3+ quarters",
            actual_value=decline_count, expected_range="<3 consecutive declines",
            severity="critical" if triggered else "pass",
            message=f"{decline_count} quarters of YoY revenue decline"
        )

    def _check_d4(self, r: StockDataRecord) -> ValidationResult:
        annual = r.annual_results
        if len(annual) < 3:
            return ValidationResult("operating_cash_flow", True, "D4",
                                    "Negative OCF check", severity="info",
                                    message="Insufficient annual data")
        neg_count = 0
        for yr in annual[:5]:
            ocf = _safe_val(yr, "operating_cash_flow")
            if ocf is not None and ocf < 0:
                neg_count += 1
            else:
                break
        triggered = neg_count >= 3
        return ValidationResult(
            "operating_cash_flow", not triggered, "D4",
            "OCF not negative 3+ consecutive years",
            actual_value=neg_count,
            severity="critical" if triggered else "pass",
            message=f"{neg_count} years of negative OCF"
        )

    def _check_d5(self, r: StockDataRecord) -> ValidationResult:
        annual = r.annual_results
        if len(annual) < 5:
            return ValidationResult("free_cash_flow", True, "D5",
                                    "Negative FCF check", severity="info",
                                    message="Insufficient annual data")
        neg_count = 0
        for yr in annual[:7]:
            fcf = _safe_val(yr, "free_cash_flow")
            if fcf is not None and fcf < 0:
                neg_count += 1
            else:
                break
        triggered = neg_count >= 5
        return ValidationResult(
            "free_cash_flow", not triggered, "D5",
            "FCF not negative 5+ consecutive years",
            actual_value=neg_count,
            severity="critical" if triggered else "pass",
            message=f"{neg_count} years of negative FCF"
        )

    def _check_d6(self, r: StockDataRecord) -> ValidationResult:
        status = r.get_field("stock_status")
        if status is None:
            return ValidationResult("stock_status", True, "D6",
                                    "Trading status check", severity="info",
                                    message="Stock status data not available")
        triggered = str(status).upper() == "SUSPENDED"
        return ValidationResult(
            "stock_status", not triggered, "D6",
            "Stock not suspended from trading",
            actual_value=status,
            severity="critical" if triggered else "pass",
            message=f"Stock status: {status}"
        )

    def _check_d7(self, r: StockDataRecord) -> ValidationResult:
        pledging = r.get_field("promoter_pledging")
        if pledging is None:
            return ValidationResult("promoter_pledging", True, "D7",
                                    "Promoter pledging check", severity="info",
                                    message="Pledging data not available")
        triggered = pledging > 80.0
        return ValidationResult(
            "promoter_pledging", not triggered, "D7",
            "Promoter pledging <= 80%",
            actual_value=pledging, expected_range="<=80%",
            severity="critical" if triggered else "pass",
            message=f"Promoter pledging {pledging:.1f}%"
        )

    def _check_d8(self, r: StockDataRecord) -> ValidationResult:
        de = r.get_field("debt_to_equity")
        if de is None:
            return ValidationResult("debt_to_equity", True, "D8",
                                    "Debt-to-equity check", severity="info",
                                    message="D/E data not available")
        triggered = de > 5.0
        return ValidationResult(
            "debt_to_equity", not triggered, "D8",
            "Debt-to-equity <= 5.0",
            actual_value=de, expected_range="<=5.0",
            severity="critical" if triggered else "pass",
            message=f"D/E ratio {de:.2f}"
        )

    def _check_d9(self, r: StockDataRecord) -> ValidationResult:
        rating = r.get_field("credit_rating")
        if rating is None:
            return ValidationResult("credit_rating", True, "D9",
                                    "Credit rating check", severity="info",
                                    message="Credit rating not available")
        base_rating = str(rating).split("(")[0].strip().upper()
        triggered = base_rating in BELOW_INVESTMENT_GRADE
        return ValidationResult(
            "credit_rating", not triggered, "D9",
            "Credit rating is investment grade",
            actual_value=rating,
            severity="critical" if triggered else "pass",
            message=f"Credit rating: {rating}"
        )

    def _check_d10(self, r: StockDataRecord) -> ValidationResult:
        avg_vol = r.get_field("avg_volume_20d")
        if avg_vol is None:
            return ValidationResult("avg_volume_20d", True, "D10",
                                    "Liquidity check", severity="info",
                                    message="Volume data not available")
        triggered = avg_vol < 50000
        return ValidationResult(
            "avg_volume_20d", not triggered, "D10",
            "Avg daily volume >= 50,000",
            actual_value=avg_vol, expected_range=">=50,000",
            severity="critical" if triggered else "pass",
            message=f"Avg 20d volume: {avg_vol:,}"
        )

    # ===== RISK PENALTIES =====

    def _check_r1(self, r: StockDataRecord) -> ValidationResult:
        de = r.get_field("debt_to_equity")
        if de is None:
            return ValidationResult("debt_to_equity", True, "R1",
                                    "High D/E check", severity="info",
                                    message="D/E not available")
        triggered = 2.0 < de <= 5.0
        return ValidationResult(
            "debt_to_equity", not triggered, "R1",
            "Debt-to-equity not between 2.0-5.0",
            actual_value=-10 if triggered else 0,
            severity="high" if triggered else "pass",
            message=f"D/E {de:.2f}: {'-10 penalty' if triggered else 'OK'}"
        )

    def _check_r2(self, r: StockDataRecord) -> ValidationResult:
        ic = r.get_field("interest_coverage")
        if ic is None:
            return ValidationResult("interest_coverage", True, "R2",
                                    "Low IC check", severity="info",
                                    message="IC not available")
        triggered = 2.0 <= ic < 3.0
        return ValidationResult(
            "interest_coverage", not triggered, "R2",
            "Interest coverage not 2.0-3.0x",
            actual_value=-8 if triggered else 0,
            severity="high" if triggered else "pass",
            message=f"IC {ic:.1f}x: {'-8 penalty' if triggered else 'OK'}"
        )

    def _check_r3(self, r: StockDataRecord) -> ValidationResult:
        roe = r.get_field("roe")
        if roe is None:
            return ValidationResult("roe", True, "R3", "Low ROE check",
                                    severity="info", message="ROE not available")
        triggered = roe < 10.0
        return ValidationResult(
            "roe", not triggered, "R3",
            "ROE >= 10%",
            actual_value=-5 if triggered else 0,
            severity="medium" if triggered else "pass",
            message=f"ROE {roe:.1f}%: {'-5 penalty' if triggered else 'OK'}"
        )

    def _check_r4(self, r: StockDataRecord) -> ValidationResult:
        change = r.get_field("promoter_holding_change")
        if change is None:
            return ValidationResult("promoter_holding_change", True, "R4",
                                    "Promoter decline check", severity="info",
                                    message="Promoter change not available")
        triggered = change < -5.0
        return ValidationResult(
            "promoter_holding_change", not triggered, "R4",
            "Promoter holding decline <= 5%",
            actual_value=-8 if triggered else 0,
            severity="high" if triggered else "pass",
            message=f"Promoter change {change:+.1f}%: {'-8 penalty' if triggered else 'OK'}"
        )

    def _check_r5(self, r: StockDataRecord) -> ValidationResult:
        pledging = r.get_field("promoter_pledging")
        if pledging is None:
            return ValidationResult("promoter_pledging", True, "R5",
                                    "Pledging penalty check", severity="info",
                                    message="Pledging not available")
        triggered = 20.0 < pledging <= 80.0
        return ValidationResult(
            "promoter_pledging", not triggered, "R5",
            "Promoter pledging not 20-80%",
            actual_value=-10 if triggered else 0,
            severity="high" if triggered else "pass",
            message=f"Pledging {pledging:.1f}%: {'-10 penalty' if triggered else 'OK'}"
        )

    def _check_r6(self, r: StockDataRecord) -> ValidationResult:
        dist = r.get_field("distance_from_52w_high")
        if dist is None:
            return ValidationResult("distance_from_52w_high", True, "R6",
                                    "52W high distance check", severity="info",
                                    message="52W data not available")
        triggered = dist < -30.0
        return ValidationResult(
            "distance_from_52w_high", not triggered, "R6",
            "Not >30% below 52W high",
            actual_value=-5 if triggered else 0,
            severity="medium" if triggered else "pass",
            message=f"Distance from 52W high: {dist:.1f}%"
        )

    def _check_r7(self, r: StockDataRecord) -> ValidationResult:
        results = r.quarterly_results
        if len(results) < 3:
            return ValidationResult("operating_margin", True, "R7",
                                    "Margin decline check", severity="info",
                                    message="Insufficient quarterly data")
        decline_count = 0
        for i in range(min(len(results) - 1, 3)):
            curr_m = _safe_val(results[i], "operating_margin")
            prev_m = _safe_val(results[i + 1], "operating_margin")
            if curr_m is not None and prev_m is not None and curr_m < prev_m:
                decline_count += 1
            else:
                break
        triggered = decline_count >= 2
        return ValidationResult(
            "operating_margin", not triggered, "R7",
            "Margin not declining 2+ quarters",
            actual_value=-5 if triggered else 0,
            severity="medium" if triggered else "pass",
            message=f"{decline_count} quarters of declining margin"
        )

    def _check_r8(self, r: StockDataRecord) -> ValidationResult:
        pe = r.get_field("pe_ratio")
        sector_pe = r.get_field("sector_avg_pe")
        if pe is None or sector_pe is None or sector_pe <= 0:
            return ValidationResult("pe_ratio", True, "R8",
                                    "Valuation premium check", severity="info",
                                    message="PE/sector PE not available")
        triggered = pe > 2.0 * sector_pe
        return ValidationResult(
            "pe_ratio", not triggered, "R8",
            "PE not >2x sector average",
            actual_value=-8 if triggered else 0,
            severity="high" if triggered else "pass",
            message=f"PE {pe:.1f} vs sector {sector_pe:.1f} (2x = {2*sector_pe:.1f})"
        )

    def _check_r9(self, r: StockDataRecord) -> ValidationResult:
        dp = r.get_field("delivery_percentage")
        if dp is None:
            return ValidationResult("delivery_percentage", True, "R9",
                                    "Delivery percentage check", severity="info",
                                    message="Delivery data not available")
        triggered = dp < 30.0
        return ValidationResult(
            "delivery_percentage", not triggered, "R9",
            "Delivery percentage >= 30%",
            actual_value=-3 if triggered else 0,
            severity="medium" if triggered else "pass",
            message=f"Delivery {dp:.1f}%"
        )

    def _check_r10(self, r: StockDataRecord) -> ValidationResult:
        cl = r.get_field("contingent_liabilities")
        eq = r.get_field("total_equity")
        if cl is None or eq is None or eq <= 0:
            return ValidationResult("contingent_liabilities", True, "R10",
                                    "Contingent liabilities check", severity="info",
                                    message="Contingent liabilities not available")
        ratio = cl / eq
        triggered = ratio > 0.5
        return ValidationResult(
            "contingent_liabilities", not triggered, "R10",
            "Contingent liabilities <= 50% of equity",
            actual_value=-5 if triggered else 0,
            severity="medium" if triggered else "pass",
            message=f"Contingent liabilities {ratio*100:.0f}% of equity"
        )

    # ===== QUALITY BOOSTERS =====

    def _check_q1(self, r: StockDataRecord) -> ValidationResult:
        annual = r.annual_results
        if len(annual) < 5:
            return ValidationResult("roe", False, "Q1", "Consistent ROE check",
                                    severity="info", message="Insufficient annual data")
        high_count = 0
        for yr in annual[:5]:
            roe = _safe_val(yr, "roe")
            if roe is not None and roe > 20.0:
                high_count += 1
            else:
                break
        triggered = high_count >= 5
        return ValidationResult(
            "roe", triggered, "Q1",
            "ROE >20% for 5 years",
            actual_value=10 if triggered else 0,
            severity="positive" if triggered else "pass",
            message=f"{high_count}/5 years with ROE >20%"
        )

    def _check_q2(self, r: StockDataRecord) -> ValidationResult:
        annual = r.annual_results
        if len(annual) < 4:
            return ValidationResult("revenue_growth_yoy", False, "Q2",
                                    "Revenue growth check", severity="info",
                                    message="Insufficient annual data")
        growth_count = 0
        for i in range(min(len(annual) - 1, 3)):
            curr = _safe_val(annual[i], "revenue")
            prev = _safe_val(annual[i + 1], "revenue")
            if curr is not None and prev is not None and prev > 0:
                growth = (curr - prev) / prev * 100
                if growth > 15.0:
                    growth_count += 1
                else:
                    break
        triggered = growth_count >= 3
        return ValidationResult(
            "revenue_growth_yoy", triggered, "Q2",
            "Revenue growth >15% for 3+ years",
            actual_value=8 if triggered else 0,
            severity="positive" if triggered else "pass",
            message=f"{growth_count} years with >15% revenue growth"
        )

    def _check_q3(self, r: StockDataRecord) -> ValidationResult:
        de = r.get_field("debt_to_equity")
        if de is None:
            return ValidationResult("debt_to_equity", False, "Q3",
                                    "Zero debt check", severity="info",
                                    message="D/E not available")
        triggered = de < 0.1
        return ValidationResult(
            "debt_to_equity", triggered, "Q3",
            "Zero/negligible debt (D/E < 0.1)",
            actual_value=8 if triggered else 0,
            severity="positive" if triggered else "pass",
            message=f"D/E {de:.2f}: {'Zero debt bonus' if triggered else 'Has debt'}"
        )

    def _check_q4(self, r: StockDataRecord) -> ValidationResult:
        annual = r.annual_results
        if len(annual) < 10:
            return ValidationResult("dividends_paid", False, "Q4",
                                    "Dividend consistency check", severity="info",
                                    message="Need 10 years of data")
        div_count = 0
        for yr in annual[:10]:
            div = _safe_val(yr, "dividends_paid")
            if div is not None and div > 0:
                div_count += 1
            else:
                break
        triggered = div_count >= 10
        return ValidationResult(
            "dividends_paid", triggered, "Q4",
            "10+ years of consecutive dividends",
            actual_value=5 if triggered else 0,
            severity="positive" if triggered else "pass",
            message=f"{div_count}/10 years of dividends paid"
        )

    def _check_q5(self, r: StockDataRecord) -> ValidationResult:
        history = r.shareholding_history
        if len(history) < 3:
            return ValidationResult("promoter_holding_change", False, "Q5",
                                    "Promoter increase check", severity="info",
                                    message="Insufficient shareholding data")
        increase_count = 0
        for i in range(min(len(history) - 1, 4)):
            curr = _safe_val(history[i], "promoter_holding")
            prev = _safe_val(history[i + 1], "promoter_holding")
            if curr is not None and prev is not None and curr > prev:
                increase_count += 1
            else:
                break
        triggered = increase_count >= 2
        return ValidationResult(
            "promoter_holding_change", triggered, "Q5",
            "Promoter increased 2+ quarters",
            actual_value=5 if triggered else 0,
            severity="positive" if triggered else "pass",
            message=f"{increase_count} quarters of promoter increase"
        )

    def _check_q6(self, r: StockDataRecord) -> ValidationResult:
        change = r.get_field("fii_holding_change")
        if change is None:
            return ValidationResult("fii_holding_change", False, "Q6",
                                    "FII interest check", severity="info",
                                    message="FII change not available")
        triggered = change > 2.0
        return ValidationResult(
            "fii_holding_change", triggered, "Q6",
            "FII holding increased >2%",
            actual_value=5 if triggered else 0,
            severity="positive" if triggered else "pass",
            message=f"FII holding change: {change:+.1f}%"
        )

    def _check_q7(self, r: StockDataRecord) -> ValidationResult:
        margin = r.get_field("operating_margin")
        if margin is None:
            return ValidationResult("operating_margin", False, "Q7",
                                    "High margin check", severity="info",
                                    message="Margin not available")
        triggered = margin > 25.0
        return ValidationResult(
            "operating_margin", triggered, "Q7",
            "Operating margin >25%",
            actual_value=5 if triggered else 0,
            severity="positive" if triggered else "pass",
            message=f"Operating margin {margin:.1f}%"
        )

    def _check_q8(self, r: StockDataRecord) -> ValidationResult:
        dist = r.get_field("distance_from_52w_high")
        if dist is None:
            return ValidationResult("distance_from_52w_high", False, "Q8",
                                    "Near high check", severity="info",
                                    message="52W data not available")
        triggered = dist > -5.0
        return ValidationResult(
            "distance_from_52w_high", triggered, "Q8",
            "Within 5% of 52W high",
            actual_value=3 if triggered else 0,
            severity="positive" if triggered else "pass",
            message=f"Distance from 52W high: {dist:.1f}%"
        )

    def _check_q9(self, r: StockDataRecord) -> ValidationResult:
        fcf_yield = r.get_field("fcf_yield")
        if fcf_yield is None:
            return ValidationResult("fcf_yield", False, "Q9",
                                    "FCF yield check", severity="info",
                                    message="FCF yield not available")
        triggered = fcf_yield > 5.0
        return ValidationResult(
            "fcf_yield", triggered, "Q9",
            "FCF yield >5%",
            actual_value=5 if triggered else 0,
            severity="positive" if triggered else "pass",
            message=f"FCF yield {fcf_yield:.1f}%"
        )

    def _check_q10(self, r: StockDataRecord) -> ValidationResult:
        annual = r.annual_results
        if len(annual) < 4:
            return ValidationResult("current_ratio", False, "Q10",
                                    "Working capital check", severity="info",
                                    message="Insufficient data")
        improving_count = 0
        for i in range(min(len(annual) - 1, 3)):
            curr = _safe_val(annual[i], "current_ratio")
            prev = _safe_val(annual[i + 1], "current_ratio")
            if curr is not None and prev is not None and curr > prev:
                improving_count += 1
            else:
                break
        triggered = improving_count >= 3
        return ValidationResult(
            "current_ratio", triggered, "Q10",
            "Current ratio improving 3 years",
            actual_value=3 if triggered else 0,
            severity="positive" if triggered else "pass",
            message=f"{improving_count} years of improving current ratio"
        )


def _safe_val(d: Dict[str, Any], key: str) -> Optional[float]:
    """Safely get a numeric value from a dict."""
    val = d.get(key)
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None
