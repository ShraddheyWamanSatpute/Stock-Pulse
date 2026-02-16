"""
Validation rules configuration for the scoring system.

Implements all Deal-breakers (D1-D10), Risk penalties (R1-R10),
and Quality boosters (Q1-Q10) from the scoring framework.
"""

from dataclasses import dataclass
from typing import Any, Callable, Optional
from enum import Enum


class RuleType(str, Enum):
    DEAL_BREAKER = "deal_breaker"
    RISK_PENALTY = "risk_penalty"
    QUALITY_BOOSTER = "quality_booster"


class RuleSeverity(str, Enum):
    CRITICAL = "critical"    # Deal-breakers: auto-fail
    HIGH = "high"            # Risk penalties: score deduction
    MEDIUM = "medium"        # Minor penalties
    POSITIVE = "positive"    # Quality boosters: score addition


@dataclass
class ValidationRule:
    rule_id: str
    name: str
    rule_type: RuleType
    severity: RuleSeverity
    description: str
    required_fields: list
    threshold: Any = None
    score_impact: float = 0.0
    condition_description: str = ""


# ===== DEAL-BREAKERS (D1-D10): Auto-fail triggers =====
DEAL_BREAKER_RULES = [
    ValidationRule(
        rule_id="D1",
        name="Interest Coverage Failure",
        rule_type=RuleType.DEAL_BREAKER,
        severity=RuleSeverity.CRITICAL,
        description="Interest coverage ratio below 2.0x indicates inability to service debt",
        required_fields=["interest_coverage"],
        threshold=2.0,
        score_impact=-100,
        condition_description="interest_coverage < 2.0",
    ),
    ValidationRule(
        rule_id="D2",
        name="Regulatory Action",
        rule_type=RuleType.DEAL_BREAKER,
        severity=RuleSeverity.CRITICAL,
        description="Active SEBI investigation or regulatory action",
        required_fields=["sebi_investigation"],
        threshold=True,
        score_impact=-100,
        condition_description="sebi_investigation == True",
    ),
    ValidationRule(
        rule_id="D3",
        name="Revenue Decline",
        rule_type=RuleType.DEAL_BREAKER,
        severity=RuleSeverity.CRITICAL,
        description="Revenue declining for 3+ consecutive quarters YoY",
        required_fields=["revenue_growth_yoy"],
        threshold=-3,
        score_impact=-100,
        condition_description="3+ quarters of negative YoY revenue growth",
    ),
    ValidationRule(
        rule_id="D4",
        name="Negative Operating Cash Flow",
        rule_type=RuleType.DEAL_BREAKER,
        severity=RuleSeverity.CRITICAL,
        description="Negative operating cash flow for 3+ consecutive years",
        required_fields=["operating_cash_flow"],
        threshold=-3,
        score_impact=-100,
        condition_description="3+ years of negative OCF",
    ),
    ValidationRule(
        rule_id="D5",
        name="Negative Free Cash Flow",
        rule_type=RuleType.DEAL_BREAKER,
        severity=RuleSeverity.CRITICAL,
        description="Negative free cash flow for 5+ consecutive years",
        required_fields=["free_cash_flow"],
        threshold=-5,
        score_impact=-100,
        condition_description="5+ years of negative FCF",
    ),
    ValidationRule(
        rule_id="D6",
        name="Trading Suspension",
        rule_type=RuleType.DEAL_BREAKER,
        severity=RuleSeverity.CRITICAL,
        description="Stock is suspended from trading",
        required_fields=["stock_status"],
        threshold="SUSPENDED",
        score_impact=-100,
        condition_description="stock_status == 'SUSPENDED'",
    ),
    ValidationRule(
        rule_id="D7",
        name="Extreme Promoter Pledging",
        rule_type=RuleType.DEAL_BREAKER,
        severity=RuleSeverity.CRITICAL,
        description="Promoter pledging exceeds 80% of holdings",
        required_fields=["promoter_pledging"],
        threshold=80.0,
        score_impact=-100,
        condition_description="promoter_pledging > 80%",
    ),
    ValidationRule(
        rule_id="D8",
        name="Extreme Leverage",
        rule_type=RuleType.DEAL_BREAKER,
        severity=RuleSeverity.CRITICAL,
        description="Debt-to-equity ratio exceeds 5.0x",
        required_fields=["debt_to_equity"],
        threshold=5.0,
        score_impact=-100,
        condition_description="debt_to_equity > 5.0",
    ),
    ValidationRule(
        rule_id="D9",
        name="Credit Downgrade",
        rule_type=RuleType.DEAL_BREAKER,
        severity=RuleSeverity.CRITICAL,
        description="Credit rating downgraded to below investment grade (BB or lower)",
        required_fields=["credit_rating"],
        threshold="BB",
        score_impact=-100,
        condition_description="credit_rating in ['BB', 'B', 'C', 'D']",
    ),
    ValidationRule(
        rule_id="D10",
        name="Illiquid Stock",
        rule_type=RuleType.DEAL_BREAKER,
        severity=RuleSeverity.CRITICAL,
        description="Average daily volume below 50,000 shares",
        required_fields=["avg_volume_20d"],
        threshold=50000,
        score_impact=-100,
        condition_description="avg_volume_20d < 50,000",
    ),
]

# ===== RISK PENALTIES (R1-R10): Score deductions =====
RISK_PENALTY_RULES = [
    ValidationRule(
        rule_id="R1",
        name="High Debt-to-Equity",
        rule_type=RuleType.RISK_PENALTY,
        severity=RuleSeverity.HIGH,
        description="Debt-to-equity between 2.0-5.0x",
        required_fields=["debt_to_equity"],
        threshold=(2.0, 5.0),
        score_impact=-10,
        condition_description="2.0 < debt_to_equity <= 5.0",
    ),
    ValidationRule(
        rule_id="R2",
        name="Low Interest Coverage",
        rule_type=RuleType.RISK_PENALTY,
        severity=RuleSeverity.HIGH,
        description="Interest coverage between 2.0x and 3.0x",
        required_fields=["interest_coverage"],
        threshold=(2.0, 3.0),
        score_impact=-8,
        condition_description="2.0 <= interest_coverage < 3.0",
    ),
    ValidationRule(
        rule_id="R3",
        name="Low ROE",
        rule_type=RuleType.RISK_PENALTY,
        severity=RuleSeverity.MEDIUM,
        description="Return on equity below 10%",
        required_fields=["roe"],
        threshold=10.0,
        score_impact=-5,
        condition_description="roe < 10%",
    ),
    ValidationRule(
        rule_id="R4",
        name="Promoter Holding Decline",
        rule_type=RuleType.RISK_PENALTY,
        severity=RuleSeverity.HIGH,
        description="Promoter holding declined by more than 5% in last year",
        required_fields=["promoter_holding_change"],
        threshold=-5.0,
        score_impact=-8,
        condition_description="promoter_holding_change < -5%",
    ),
    ValidationRule(
        rule_id="R5",
        name="Significant Promoter Pledging",
        rule_type=RuleType.RISK_PENALTY,
        severity=RuleSeverity.HIGH,
        description="Promoter pledging between 20-80%",
        required_fields=["promoter_pledging"],
        threshold=(20.0, 80.0),
        score_impact=-10,
        condition_description="20% < promoter_pledging <= 80%",
    ),
    ValidationRule(
        rule_id="R6",
        name="Far From 52-Week High",
        rule_type=RuleType.RISK_PENALTY,
        severity=RuleSeverity.MEDIUM,
        description="Stock price more than 30% below 52-week high",
        required_fields=["distance_from_52w_high"],
        threshold=-30.0,
        score_impact=-5,
        condition_description="distance_from_52w_high < -30%",
    ),
    ValidationRule(
        rule_id="R7",
        name="Declining Operating Margin",
        rule_type=RuleType.RISK_PENALTY,
        severity=RuleSeverity.MEDIUM,
        description="Operating margin declining for 2+ consecutive quarters",
        required_fields=["operating_margin"],
        threshold=-2,
        score_impact=-5,
        condition_description="2+ quarters of declining operating margin",
    ),
    ValidationRule(
        rule_id="R8",
        name="Extreme Valuation Premium",
        rule_type=RuleType.RISK_PENALTY,
        severity=RuleSeverity.HIGH,
        description="P/E ratio more than 2x sector average",
        required_fields=["pe_ratio", "sector_avg_pe"],
        threshold=2.0,
        score_impact=-8,
        condition_description="pe_ratio > 2x sector_avg_pe",
    ),
    ValidationRule(
        rule_id="R9",
        name="Low Delivery Percentage",
        rule_type=RuleType.RISK_PENALTY,
        severity=RuleSeverity.MEDIUM,
        description="Consistently low delivery percentage (<30%)",
        required_fields=["delivery_percentage"],
        threshold=30.0,
        score_impact=-3,
        condition_description="avg delivery_percentage < 30%",
    ),
    ValidationRule(
        rule_id="R10",
        name="High Contingent Liabilities",
        rule_type=RuleType.RISK_PENALTY,
        severity=RuleSeverity.MEDIUM,
        description="Contingent liabilities exceeding 50% of net worth",
        required_fields=["contingent_liabilities", "total_equity"],
        threshold=0.5,
        score_impact=-5,
        condition_description="contingent_liabilities > 50% of total_equity",
    ),
]

# ===== QUALITY BOOSTERS (Q1-Q10): Score additions =====
QUALITY_BOOSTER_RULES = [
    ValidationRule(
        rule_id="Q1",
        name="Consistent High ROE",
        rule_type=RuleType.QUALITY_BOOSTER,
        severity=RuleSeverity.POSITIVE,
        description="ROE above 20% for 5 consecutive years",
        required_fields=["roe"],
        threshold=20.0,
        score_impact=10,
        condition_description="roe > 20% for 5 years",
    ),
    ValidationRule(
        rule_id="Q2",
        name="Strong Revenue Growth",
        rule_type=RuleType.QUALITY_BOOSTER,
        severity=RuleSeverity.POSITIVE,
        description="Revenue growth above 15% for 3+ years",
        required_fields=["revenue_growth_yoy"],
        threshold=15.0,
        score_impact=8,
        condition_description="revenue_growth_yoy > 15% for 3+ years",
    ),
    ValidationRule(
        rule_id="Q3",
        name="Zero Debt",
        rule_type=RuleType.QUALITY_BOOSTER,
        severity=RuleSeverity.POSITIVE,
        description="Company has zero or negligible debt (D/E < 0.1)",
        required_fields=["debt_to_equity"],
        threshold=0.1,
        score_impact=8,
        condition_description="debt_to_equity < 0.1",
    ),
    ValidationRule(
        rule_id="Q4",
        name="Consistent Dividend Payer",
        rule_type=RuleType.QUALITY_BOOSTER,
        severity=RuleSeverity.POSITIVE,
        description="Paid dividends for 10+ consecutive years",
        required_fields=["dividends_paid"],
        threshold=10,
        score_impact=5,
        condition_description="10+ years of consecutive dividends",
    ),
    ValidationRule(
        rule_id="Q5",
        name="Increasing Promoter Holding",
        rule_type=RuleType.QUALITY_BOOSTER,
        severity=RuleSeverity.POSITIVE,
        description="Promoter holding increased in last 2+ quarters",
        required_fields=["promoter_holding_change"],
        threshold=2,
        score_impact=5,
        condition_description="promoter_holding increased 2+ quarters",
    ),
    ValidationRule(
        rule_id="Q6",
        name="Rising FII Interest",
        rule_type=RuleType.QUALITY_BOOSTER,
        severity=RuleSeverity.POSITIVE,
        description="FII holding increased by more than 2% in last year",
        required_fields=["fii_holding_change"],
        threshold=2.0,
        score_impact=5,
        condition_description="fii_holding_change > 2%",
    ),
    ValidationRule(
        rule_id="Q7",
        name="High Operating Margin",
        rule_type=RuleType.QUALITY_BOOSTER,
        severity=RuleSeverity.POSITIVE,
        description="Operating margin consistently above 25%",
        required_fields=["operating_margin"],
        threshold=25.0,
        score_impact=5,
        condition_description="operating_margin > 25%",
    ),
    ValidationRule(
        rule_id="Q8",
        name="Near 52-Week High",
        rule_type=RuleType.QUALITY_BOOSTER,
        severity=RuleSeverity.POSITIVE,
        description="Stock within 5% of 52-week high (momentum)",
        required_fields=["distance_from_52w_high"],
        threshold=-5.0,
        score_impact=3,
        condition_description="distance_from_52w_high > -5%",
    ),
    ValidationRule(
        rule_id="Q9",
        name="Strong Free Cash Flow Yield",
        rule_type=RuleType.QUALITY_BOOSTER,
        severity=RuleSeverity.POSITIVE,
        description="FCF yield above 5%",
        required_fields=["fcf_yield"],
        threshold=5.0,
        score_impact=5,
        condition_description="fcf_yield > 5%",
    ),
    ValidationRule(
        rule_id="Q10",
        name="Improving Working Capital",
        rule_type=RuleType.QUALITY_BOOSTER,
        severity=RuleSeverity.POSITIVE,
        description="Current ratio improving over last 3 years",
        required_fields=["current_ratio"],
        threshold=3,
        score_impact=3,
        condition_description="current_ratio improving for 3 years",
    ),
]

# Aggregate all rules
ALL_RULES = DEAL_BREAKER_RULES + RISK_PENALTY_RULES + QUALITY_BOOSTER_RULES
RULES_BY_ID = {r.rule_id: r for r in ALL_RULES}
RULES_BY_TYPE = {
    RuleType.DEAL_BREAKER: DEAL_BREAKER_RULES,
    RuleType.RISK_PENALTY: RISK_PENALTY_RULES,
    RuleType.QUALITY_BOOSTER: QUALITY_BOOSTER_RULES,
}
