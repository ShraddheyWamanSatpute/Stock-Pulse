from typing import Dict, List, Tuple, Any, Optional
import random
from datetime import datetime


# =============================================================================
# TIER 1: HARD DEAL-BREAKERS (D1-D10)
# If ANY condition is TRUE, stock is immediately rejected. Score capped at 35.
# =============================================================================
DEAL_BREAKERS = [
    # D1: Interest Coverage Ratio < 2.0x - Cannot service debt - bankruptcy risk
    {
        "code": "D1",
        "rule": "interest_coverage_low", 
        "field": "interest_coverage", 
        "threshold": 2.0, 
        "operator": "lt", 
        "description": "D1: Interest Coverage < 2.0x - Cannot service debt",
        "severity": "CRITICAL"
    },
    # D2: SEBI Investigation = true - Financial statements untrustworthy
    {
        "code": "D2",
        "rule": "sebi_investigation", 
        "field": "sebi_investigation", 
        "threshold": True, 
        "operator": "eq", 
        "description": "D2: Active SEBI Investigation - Regulatory risk",
        "severity": "CRITICAL"
    },
    # D3: Revenue declining 3+ consecutive years - Business structurally failing
    {
        "code": "D3",
        "rule": "revenue_declining_3yr", 
        "field": "revenue_declining_years", 
        "threshold": 3, 
        "operator": "gte", 
        "description": "D3: Revenue Declining 3+ Years - Business failing",
        "severity": "CRITICAL"
    },
    # D4: Negative Operating Cash Flow for 2+ years - Cash burn spiral
    {
        "code": "D4",
        "rule": "negative_ocf_2yr", 
        "field": "negative_ocf_years", 
        "threshold": 2, 
        "operator": "gte", 
        "description": "D4: Negative OCF 2+ Years - Cash burn issue",
        "severity": "CRITICAL"
    },
    # D5: Negative Free Cash Flow for 3+ years - No turnaround plan
    {
        "code": "D5",
        "rule": "negative_fcf_3yr", 
        "field": "negative_fcf_years", 
        "threshold": 3, 
        "operator": "gte", 
        "description": "D5: Negative FCF 3+ Years - Unsustainable business",
        "severity": "CRITICAL"
    },
    # D6: Stock halted/suspended/delisting announced - Untradeable
    {
        "code": "D6",
        "rule": "stock_not_active", 
        "field": "stock_status", 
        "threshold": "ACTIVE", 
        "operator": "neq", 
        "description": "D6: Stock Not Active - Halted/Suspended/Delisting",
        "severity": "CRITICAL"
    },
    # D7: Promoter pledging > 80% - Forced selling imminent
    {
        "code": "D7",
        "rule": "promoter_pledging_extreme", 
        "field": "promoter_pledging", 
        "threshold": 80, 
        "operator": "gt",
        "description": "D7: Promoter Pledging > 80% - High promoter stress",
        "severity": "CRITICAL"
    },
    # D8: Debt-to-Equity > 5.0 (non-financial) - Insolvency risk
    {
        "code": "D8",
        "rule": "debt_to_equity_extreme", 
        "field": "debt_to_equity", 
        "threshold": 5.0, 
        "operator": "gt",
        "description": "D8: Debt-to-Equity > 5.0 - Excessive leverage",
        "severity": "CRITICAL"
    },
    # D9: Credit rating = D (Default) or withdrawn - Default imminent
    {
        "code": "D9",
        "rule": "credit_rating_default", 
        "field": "credit_rating", 
        "threshold": ["D", "DEFAULT", "WITHDRAWN", "NR"], 
        "operator": "in", 
        "description": "D9: Credit Rating D/Withdrawn - Default risk",
        "severity": "CRITICAL"
    },
    # D10: Average daily volume < 50,000 (short-term only) - Liquidity trap
    {
        "code": "D10",
        "rule": "volume_too_low", 
        "field": "volume_avg_20", 
        "threshold": 50000, 
        "operator": "lt",
        "description": "D10: Avg Volume < 50,000 - Illiquid stock",
        "severity": "CRITICAL",
        "short_term_only": True
    },
]

# TIER 2: RISK PENALTIES
RISK_PENALTIES = [
    {"rule": "de_moderate", "field": "debt_to_equity", "min": 2.0, "max": 5.0, "lt_penalty": -15, "st_penalty": -10,
     "description": "D/E between 2.0 - 5.0"},
    {"rule": "interest_coverage_moderate", "field": "interest_coverage", "min": 2.0, "max": 3.0, "lt_penalty": -10, "st_penalty": -5,
     "description": "Interest coverage 2.0x - 3.0x"},
    {"rule": "roe_weak", "field": "roe", "threshold": 10, "operator": "lt", "lt_penalty": -12, "st_penalty": -5,
     "description": "ROE < 10% for extended period"},
    {"rule": "promoter_pledging_moderate", "field": "promoter_pledging", "min": 30, "max": 80, "lt_penalty": -10, "st_penalty": -15,
     "description": "Promoter pledging 30-80%"},
    {"rule": "pe_expensive", "field": "pe_ratio", "threshold": 50, "operator": "gt", "lt_penalty": -10, "st_penalty": -5,
     "description": "P/E > 2x typical industry average"},
]

# TIER 3: QUALITY BOOSTERS (Capped at +30 total)
QUALITY_BOOSTERS = [
    {"rule": "roe_excellent", "field": "roe", "threshold": 20, "operator": "gt", "lt_boost": 15, "st_boost": 5,
     "description": "ROE > 20% consistently"},
    {"rule": "growth_strong", "field": "revenue_growth_yoy", "threshold": 15, "operator": "gt", "lt_boost": 12, "st_boost": 5,
     "description": "Revenue CAGR > 15%"},
    {"rule": "zero_debt", "field": "debt_to_equity", "threshold": 0.1, "operator": "lt", "lt_boost": 10, "st_boost": 5,
     "description": "Zero debt or net cash positive"},
    {"rule": "high_margin", "field": "operating_margin", "threshold": 25, "operator": "gt", "lt_boost": 10, "st_boost": 5,
     "description": "Operating margin > 25%"},
    {"rule": "promoter_increased", "field": "promoter_holding", "threshold": 50, "operator": "gt", "lt_boost": 8, "st_boost": 10,
     "description": "High promoter holding"},
    {"rule": "fii_interest", "field": "fii_holding", "threshold": 20, "operator": "gt", "lt_boost": 5, "st_boost": 8,
     "description": "Strong FII interest"},
]

# Scoring weights
LONG_TERM_WEIGHTS = {
    "fundamentals": 0.35,
    "valuation": 0.25,
    "technicals": 0.10,
    "quality": 0.20,
    "risk": 0.10,
}

SHORT_TERM_WEIGHTS = {
    "fundamentals": 0.20,
    "valuation": 0.15,
    "technicals": 0.35,
    "quality": 0.10,
    "risk": 0.20,
}


def score_metric(value: float, thresholds: List[Tuple[float, int]]) -> int:
    """Score a metric based on thresholds. Returns 0-100."""
    for threshold, score in thresholds:
        if value >= threshold:
            return score
    return 0


def calculate_fundamental_score(data: Dict) -> float:
    """Calculate fundamental analysis score (0-100)"""
    scores = []
    
    # Revenue Growth
    scores.append(score_metric(data.get("revenue_growth_yoy", 0), [
        (15, 100), (10, 80), (5, 60), (0, 40), (-float('inf'), 0)
    ]))
    
    # ROE
    scores.append(score_metric(data.get("roe", 0), [
        (25, 100), (20, 85), (15, 70), (10, 50), (0, 20)
    ]))
    
    # Operating Margin
    scores.append(score_metric(data.get("operating_margin", 0), [
        (20, 100), (15, 80), (10, 60), (5, 40), (0, 20)
    ]))
    
    # Debt-to-Equity (inverse scoring)
    de = data.get("debt_to_equity", 1)
    de_score = 100 if de < 0.5 else 80 if de < 1 else 60 if de < 1.5 else 40 if de < 2 else 10
    scores.append(de_score)
    
    # Free Cash Flow Margin
    revenue = data.get("revenue_ttm", 1)
    fcf = data.get("free_cash_flow", 0)
    fcf_margin = (fcf / revenue) * 100 if revenue > 0 else 0
    scores.append(score_metric(fcf_margin, [
        (15, 100), (10, 80), (5, 60), (0, 40), (-float('inf'), 10)
    ]))
    
    # Interest Coverage
    scores.append(score_metric(data.get("interest_coverage", 0), [
        (10, 100), (5, 80), (3, 60), (2, 30), (0, 0)
    ]))
    
    return sum(scores) / len(scores) if scores else 50


def calculate_valuation_score(data: Dict, sector: str) -> float:
    """Calculate valuation score (0-100)"""
    scores = []
    
    # Sector average P/E benchmarks
    sector_pe_avg = {
        "IT": 30, "Financial": 18, "FMCG": 55, "Energy": 12,
        "Pharma": 30, "Auto": 22, "Materials": 14, "Infrastructure": 22,
        "Consumer": 45, "Telecom": 25, "Utilities": 15, "Technology": 60,
        "Conglomerate": 25,
    }
    
    avg_pe = sector_pe_avg.get(sector, 20)
    pe = data.get("pe_ratio", avg_pe)
    pe_vs_sector = (pe - avg_pe) / avg_pe * 100
    
    # P/E vs Sector
    pe_score = 100 if pe_vs_sector < -30 else 80 if pe_vs_sector < -10 else 60 if abs(pe_vs_sector) < 10 else 40 if pe_vs_sector < 30 else 20
    scores.append(pe_score)
    
    # PEG Ratio
    peg = data.get("peg_ratio", 1.5)
    scores.append(score_metric(-peg, [  # Inverse - lower is better
        (-0.5, 100), (-1, 85), (-1.5, 65), (-2, 45), (-float('inf'), 20)
    ]))
    
    # EV/EBITDA
    ev_ebitda = data.get("ev_ebitda", 12)
    scores.append(score_metric(-ev_ebitda, [
        (-8, 100), (-12, 75), (-15, 50), (-20, 30), (-float('inf'), 10)
    ]))
    
    # Dividend Yield
    div_yield = data.get("dividend_yield", 0)
    scores.append(score_metric(div_yield, [
        (4, 100), (2, 80), (1, 60), (0.5, 40), (0, 30)
    ]))
    
    return sum(scores) / len(scores) if scores else 50


def calculate_technical_score(data: Dict, current_price: float) -> float:
    """Calculate technical analysis score (0-100)"""
    scores = []
    
    # Price vs 200-day MA
    sma_200 = data.get("sma_200", current_price)
    price_vs_200 = ((current_price - sma_200) / sma_200) * 100 if sma_200 > 0 else 0
    scores.append(100 if price_vs_200 > 10 else 80 if price_vs_200 > 0 else 40 if price_vs_200 > -10 else 20)
    
    # Price vs 50-day MA
    sma_50 = data.get("sma_50", current_price)
    price_vs_50 = ((current_price - sma_50) / sma_50) * 100 if sma_50 > 0 else 0
    scores.append(100 if price_vs_50 > 5 else 80 if price_vs_50 > 0 else 40 if price_vs_50 > -5 else 20)
    
    # RSI
    rsi = data.get("rsi_14", 50)
    if 30 <= rsi <= 40:
        scores.append(90)  # Recovering from oversold
    elif 40 <= rsi <= 60:
        scores.append(70)  # Neutral
    elif 60 <= rsi <= 70:
        scores.append(50)  # Getting overbought
    else:
        scores.append(30)  # Extreme
    
    # MACD
    macd = data.get("macd", 0)
    macd_signal = data.get("macd_signal", 0)
    if macd > macd_signal and macd > 0:
        scores.append(100)  # Bullish crossover
    elif macd > macd_signal:
        scores.append(70)  # Above signal
    elif macd < macd_signal:
        scores.append(40)  # Below signal
    else:
        scores.append(20)  # Bearish
    
    # 52-week position
    high_52 = data.get("high_52_week", current_price)
    low_52 = data.get("low_52_week", current_price)
    range_52 = high_52 - low_52 if high_52 > low_52 else 1
    position = ((current_price - low_52) / range_52) * 100
    scores.append(100 if position > 80 else 75 if position > 50 else 50 if position > 30 else 25)
    
    return sum(scores) / len(scores) if scores else 50


def check_deal_breakers(stock_data: Dict, is_short_term: bool = False) -> List[Dict]:
    """
    Check for deal-breaker conditions (D1-D10).
    Returns list of all deal-breakers with their triggered status.
    """
    triggered = []
    fund = stock_data.get("fundamentals", {})
    tech = stock_data.get("technicals", {})
    share = stock_data.get("shareholding", {})
    corp_actions = stock_data.get("corporate_actions", {})
    
    # Combine all data sources for easy field lookup
    all_data = {
        **fund, 
        **tech, 
        **share,
        **corp_actions,
        # Set defaults for fields that might not exist
        "stock_status": stock_data.get("stock_status", "ACTIVE"),
        "sebi_investigation": stock_data.get("sebi_investigation", False),
        "credit_rating": stock_data.get("credit_rating", ""),
        # Calculate derived fields for D3, D4, D5
        "revenue_declining_years": _calculate_declining_revenue_years(fund),
        "negative_ocf_years": _calculate_negative_ocf_years(fund),
        "negative_fcf_years": _calculate_negative_fcf_years(fund),
    }
    
    for db in DEAL_BREAKERS:
        # Skip short-term-only checks when evaluating long-term
        if db.get("short_term_only") and not is_short_term:
            triggered.append({
                "code": db.get("code", ""),
                "rule": db["rule"],
                "triggered": False,
                "value": all_data.get(db["field"], 0),
                "threshold": db["threshold"],
                "description": db["description"],
                "severity": db.get("severity", "CRITICAL"),
                "skipped": True,
                "skip_reason": "Long-term analysis - liquidity not critical"
            })
            continue
            
        value = all_data.get(db["field"], None)
        is_triggered = False
        
        # Handle different operator types
        operator = db["operator"]
        threshold = db["threshold"]
        
        if value is None:
            # Missing data - cannot evaluate, mark as not triggered but flag
            is_triggered = False
        elif operator == "lt":
            is_triggered = value < threshold
        elif operator == "gt":
            is_triggered = value > threshold
        elif operator == "gte":
            is_triggered = value >= threshold
        elif operator == "lte":
            is_triggered = value <= threshold
        elif operator == "eq":
            is_triggered = value == threshold
        elif operator == "neq":
            is_triggered = value != threshold
        elif operator == "in":
            # For checking if value is in a list (e.g., credit ratings)
            if isinstance(threshold, list):
                value_upper = str(value).upper() if value else ""
                is_triggered = value_upper in [str(t).upper() for t in threshold]
            else:
                is_triggered = value == threshold
        
        triggered.append({
            "code": db.get("code", ""),
            "rule": db["rule"],
            "triggered": is_triggered,
            "value": value if value is not None else "N/A",
            "threshold": threshold,
            "description": db["description"],
            "severity": db.get("severity", "CRITICAL"),
            "skipped": False
        })
    
    return triggered


def _calculate_declining_revenue_years(fund: Dict) -> int:
    """Calculate consecutive years of revenue decline for D3"""
    revenue_history = fund.get("revenue_history", [])
    if not revenue_history or len(revenue_history) < 2:
        # Check if current YoY growth is negative
        current_growth = fund.get("revenue_growth_yoy", 0)
        if current_growth < 0:
            return 1
        return 0
    
    declining_years = 0
    for i in range(1, len(revenue_history)):
        if revenue_history[i] < revenue_history[i-1]:
            declining_years += 1
        else:
            declining_years = 0  # Reset if growth resumes
    
    return declining_years


def _calculate_negative_ocf_years(fund: Dict) -> int:
    """Calculate consecutive years of negative Operating Cash Flow for D4"""
    ocf_history = fund.get("operating_cash_flow_history", [])
    if not ocf_history:
        # Check current OCF
        current_ocf = fund.get("operating_cash_flow", 0)
        return 1 if current_ocf < 0 else 0
    
    negative_years = 0
    for ocf in reversed(ocf_history):  # Most recent first
        if ocf < 0:
            negative_years += 1
        else:
            break
    
    return negative_years


def _calculate_negative_fcf_years(fund: Dict) -> int:
    """Calculate consecutive years of negative Free Cash Flow for D5"""
    fcf_history = fund.get("free_cash_flow_history", [])
    if not fcf_history:
        # Check current FCF
        current_fcf = fund.get("free_cash_flow", 0)
        return 1 if current_fcf < 0 else 0
    
    negative_years = 0
    for fcf in reversed(fcf_history):  # Most recent first
        if fcf < 0:
            negative_years += 1
        else:
            break
    
    return negative_years


def apply_risk_penalties(stock_data: Dict, is_long_term: bool) -> float:
    """Calculate risk penalty adjustments"""
    penalty = 0
    fund = stock_data.get("fundamentals", {})
    val = stock_data.get("valuation", {})
    share = stock_data.get("shareholding", {})
    
    all_data = {**fund, **val, **share}
    
    for rp in RISK_PENALTIES:
        value = all_data.get(rp["field"], 0)
        
        if "min" in rp and "max" in rp:
            if rp["min"] <= value <= rp["max"]:
                penalty += rp["lt_penalty"] if is_long_term else rp["st_penalty"]
        elif rp.get("operator") == "lt" and value < rp["threshold"]:
            penalty += rp["lt_penalty"] if is_long_term else rp["st_penalty"]
        elif rp.get("operator") == "gt" and value > rp["threshold"]:
            penalty += rp["lt_penalty"] if is_long_term else rp["st_penalty"]
    
    return penalty


def apply_quality_boosters(stock_data: Dict, is_long_term: bool) -> float:
    """Calculate quality booster adjustments (capped at +30)"""
    boost = 0
    fund = stock_data.get("fundamentals", {})
    share = stock_data.get("shareholding", {})
    
    all_data = {**fund, **share}
    
    for qb in QUALITY_BOOSTERS:
        value = all_data.get(qb["field"], 0)
        
        if qb["operator"] == "gt" and value > qb["threshold"]:
            boost += qb["lt_boost"] if is_long_term else qb["st_boost"]
        elif qb["operator"] == "lt" and value < qb["threshold"]:
            boost += qb["lt_boost"] if is_long_term else qb["st_boost"]
    
    return min(boost, 30)  # Cap at +30


def calculate_ml_adjustment() -> float:
    """Simulate ML model adjustment (±10 points max)"""
    # In production, this would call actual ML models
    # For MVP, simulate with random adjustment weighted towards 0
    adjustment = random.gauss(0, 4)
    return max(-10, min(10, adjustment))


def generate_analysis(stock_data: Dict) -> Dict:
    """Generate complete stock analysis with full D1-D10 deal-breaker evaluation"""
    fund = stock_data.get("fundamentals", {})
    val = stock_data.get("valuation", {})
    tech = stock_data.get("technicals", {})
    current_price = stock_data.get("current_price", 0)
    sector = stock_data.get("sector", "")
    
    # Check deal-breakers for both long-term and short-term
    lt_deal_breakers = check_deal_breakers(stock_data, is_short_term=False)
    st_deal_breakers = check_deal_breakers(stock_data, is_short_term=True)
    
    # A deal-breaker is triggered if it affects the respective analysis type
    has_lt_deal_breaker = any(db["triggered"] for db in lt_deal_breakers if not db.get("skipped"))
    has_st_deal_breaker = any(db["triggered"] for db in st_deal_breakers)
    
    # Get list of triggered deal-breakers for reporting
    triggered_lt_dbs = [db for db in lt_deal_breakers if db["triggered"]]
    triggered_st_dbs = [db for db in st_deal_breakers if db["triggered"]]
    
    # Calculate base scores
    fundamental_score = calculate_fundamental_score(fund)
    valuation_score = calculate_valuation_score(val, sector)
    technical_score = calculate_technical_score(tech, current_price)
    quality_score = (fundamental_score + valuation_score) / 2  # Simplified
    
    # Long-term score
    lt_base = (
        fundamental_score * LONG_TERM_WEIGHTS["fundamentals"] +
        valuation_score * LONG_TERM_WEIGHTS["valuation"] +
        technical_score * LONG_TERM_WEIGHTS["technicals"] +
        quality_score * LONG_TERM_WEIGHTS["quality"]
    )
    lt_penalty = apply_risk_penalties(stock_data, True)
    lt_boost = apply_quality_boosters(stock_data, True)
    lt_ml = calculate_ml_adjustment()
    long_term_score = max(0, min(100, lt_base + lt_penalty + lt_boost + lt_ml))
    
    # Short-term score
    st_base = (
        fundamental_score * SHORT_TERM_WEIGHTS["fundamentals"] +
        valuation_score * SHORT_TERM_WEIGHTS["valuation"] +
        technical_score * SHORT_TERM_WEIGHTS["technicals"] +
        quality_score * SHORT_TERM_WEIGHTS["quality"]
    )
    st_penalty = apply_risk_penalties(stock_data, False)
    st_boost = apply_quality_boosters(stock_data, False)
    st_ml = calculate_ml_adjustment()
    short_term_score = max(0, min(100, st_base + st_penalty + st_boost + st_ml))
    
    # If deal-breaker triggered, cap scores at 35
    if has_lt_deal_breaker:
        long_term_score = min(long_term_score, 35)
    if has_st_deal_breaker:
        short_term_score = min(short_term_score, 35)
    
    # Determine verdict based on deal-breakers and scores
    has_any_deal_breaker = has_lt_deal_breaker or has_st_deal_breaker
    avg_score = (long_term_score + short_term_score) / 2
    
    if has_any_deal_breaker:
        verdict = "STRONG AVOID"
    elif avg_score >= 80:
        verdict = "STRONG BUY"
    elif avg_score >= 65:
        verdict = "BUY"
    elif avg_score >= 50:
        verdict = "HOLD"
    elif avg_score >= 35:
        verdict = "AVOID"
    else:
        verdict = "STRONG AVOID"
    
    # Confidence calculation
    data_completeness = 0.85 + random.uniform(-0.1, 0.1)
    confidence_score = data_completeness * 0.4 + 0.92 * 0.3 + 0.78 * 0.15 + 0.62 * 0.15
    confidence_level = "HIGH" if confidence_score >= 0.8 else "MEDIUM" if confidence_score >= 0.6 else "LOW"
    
    # Generate strengths and risks
    strengths = []
    risks = []
    
    if fund.get("roe", 0) > 20:
        strengths.append(f"Strong ROE of {fund['roe']:.1f}%")
    if fund.get("revenue_growth_yoy", 0) > 15:
        strengths.append(f"Healthy revenue growth of {fund['revenue_growth_yoy']:.1f}%")
    if fund.get("debt_to_equity", 1) < 0.5:
        strengths.append("Low debt levels provide financial flexibility")
    if fund.get("operating_margin", 0) > 20:
        strengths.append(f"High operating margin of {fund['operating_margin']:.1f}%")
    if tech.get("rsi_14", 50) < 40:
        strengths.append("Technically oversold - potential bounce")
    
    if fund.get("debt_to_equity", 0) > 1.5:
        risks.append(f"High leverage with D/E of {fund['debt_to_equity']:.2f}")
    if fund.get("interest_coverage", 10) < 5:
        risks.append(f"Interest coverage of {fund['interest_coverage']:.1f}x needs monitoring")
    if val.get("pe_ratio", 0) > 40:
        risks.append(f"High valuation with P/E of {val['pe_ratio']:.1f}")
    if stock_data.get("shareholding", {}).get("promoter_pledging", 0) > 20:
        risks.append(f"Promoter pledging at {stock_data['shareholding']['promoter_pledging']:.1f}%")
    if tech.get("rsi_14", 50) > 70:
        risks.append("Technically overbought - potential correction")
    
    # Bull/Bear/Base cases
    bull_case = {
        "target_price": round(current_price * 1.25, 2),
        "upside_percent": 25,
        "probability": round(random.uniform(20, 35), 1),
        "catalysts": ["Strong earnings beat", "Sector tailwinds", "Management execution"]
    }
    
    bear_case = {
        "target_price": round(current_price * 0.8, 2),
        "downside_percent": -20,
        "probability": round(random.uniform(15, 30), 1),
        "risks": ["Earnings miss", "Margin compression", "Market correction"]
    }
    
    base_case = {
        "target_price": round(current_price * 1.1, 2),
        "return_percent": 10,
        "probability": round(100 - bull_case["probability"] - bear_case["probability"], 1),
        "scenario": "Steady performance in line with guidance"
    }
    
    return {
        "short_term_score": round(short_term_score, 1),
        "long_term_score": round(long_term_score, 1),
        "verdict": verdict,
        "confidence_level": confidence_level,
        "confidence_score": round(confidence_score, 2),
        "score_breakdown": {
            "fundamental_score": round(fundamental_score, 1),
            "valuation_score": round(valuation_score, 1),
            "technical_score": round(technical_score, 1),
            "quality_score": round(quality_score, 1),
            "risk_score": round(100 + lt_penalty, 1),  # Higher is better
            "ml_adjustment": round(lt_ml, 1),
        },
        "deal_breakers": deal_breakers,
        "top_strengths": strengths[:3] if strengths else ["Diversified business model"],
        "top_risks": risks[:3] if risks else ["General market risk"],
        "bull_case": bull_case,
        "bear_case": bear_case,
        "base_case": base_case,
    }


def generate_ml_prediction(stock_data: Dict) -> Dict:
    """Generate mock ML predictions"""
    tech = stock_data.get("technicals", {})
    rsi = tech.get("rsi_14", 50)
    
    # Simulate price direction based on technicals
    if rsi < 35:
        direction = "UP"
        prob = random.uniform(0.55, 0.70)
    elif rsi > 65:
        direction = "DOWN"
        prob = random.uniform(0.55, 0.65)
    else:
        direction = "NEUTRAL"
        prob = random.uniform(0.45, 0.55)
    
    return {
        "price_direction_short": direction,
        "price_direction_probability": round(prob, 2),
        "volatility_forecast": round(random.uniform(15, 35), 2),
        "anomaly_score": round(random.uniform(0, 0.3), 2),
        "sentiment_score": round(random.uniform(-0.5, 0.5), 2),
    }
