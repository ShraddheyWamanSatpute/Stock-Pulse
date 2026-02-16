"""
Calculation engine for all derived/calculated fields.

Implements all 57 calculated field formulas organized by category:
- Derived price metrics (fields 28-38)
- Financial ratios (fields 82-92)
- Valuation metrics (fields 93-109)
- Cash flow derived (field 78)
- Income statement derived (fields 40-41, 45, 47, 49, 53, 56)
- Balance sheet derived (field 63)
- Shareholding changes (fields 115-116)
"""

import logging
import math
from typing import Any, Dict, List, Optional, Tuple

from ..models.extraction_models import StockDataRecord

logger = logging.getLogger(__name__)


class CalculationEngine:
    """
    Calculates all derived fields from raw extracted data.

    The engine respects calculation dependencies — fields that depend on
    other calculated fields are computed in the correct order.
    """

    # Calculation dependency order (fields computed first to last)
    CALCULATION_ORDER = [
        # Phase 1: Income statement derived
        "revenue_growth_yoy", "revenue_growth_qoq", "gross_margin",
        "net_profit_margin", "eps_growth_yoy", "ebit", "effective_tax_rate",
        # Phase 2: Balance sheet derived
        "net_debt",
        # Phase 3: Cash flow derived
        "free_cash_flow",
        # Phase 4: Financial ratios (depend on income + balance sheet)
        "roe", "roa", "roic", "debt_to_equity", "interest_coverage",
        "current_ratio", "quick_ratio", "asset_turnover",
        "inventory_turnover", "receivables_turnover", "dividend_payout_ratio",
        # Phase 5: Derived price metrics (depend on price history)
        "daily_return_pct", "return_5d_pct", "return_20d_pct", "return_60d_pct",
        "day_range_pct", "gap_percentage", "week_52_high", "week_52_low",
        "distance_from_52w_high", "avg_volume_20d", "volume_ratio",
        # Phase 6: Valuation (depends on price + fundamentals)
        "market_cap", "enterprise_value", "pe_ratio", "peg_ratio",
        "pb_ratio", "ps_ratio", "ev_to_ebitda", "ev_to_sales",
        "dividend_yield", "fcf_yield", "earnings_yield", "historical_pe_median",
        # Phase 7: Market cap classification
        "market_cap_category",
        # Phase 8: Shareholding changes
        "promoter_holding_change", "fii_holding_change",
    ]

    def calculate_all(self, record: StockDataRecord) -> List[str]:
        """
        Calculate all derived fields in dependency order.

        Returns list of successfully calculated field names.
        """
        calculated = []
        for field_name in self.CALCULATION_ORDER:
            method_name = f"_calc_{field_name}"
            method = getattr(self, method_name, None)
            if method:
                try:
                    value = method(record)
                    if value is not None:
                        record.set_field(field_name, value, "calculated")
                        calculated.append(field_name)
                except Exception as e:
                    logger.debug(f"Could not calculate {field_name}: {e}")
        return calculated

    # ===== INCOME STATEMENT DERIVED =====

    def _calc_revenue_growth_yoy(self, r: StockDataRecord) -> Optional[float]:
        """(Revenue_current - Revenue_prev_year) / Revenue_prev_year * 100"""
        results = r.quarterly_results
        if len(results) < 5:
            return None
        current = _safe_get(results[0], "revenue")
        prev_year = _safe_get(results[4], "revenue")
        if current is None or prev_year is None or prev_year == 0:
            return None
        return round((current - prev_year) / abs(prev_year) * 100, 2)

    def _calc_revenue_growth_qoq(self, r: StockDataRecord) -> Optional[float]:
        """(Revenue_current_q - Revenue_prev_q) / Revenue_prev_q * 100"""
        results = r.quarterly_results
        if len(results) < 2:
            return None
        current = _safe_get(results[0], "revenue")
        prev = _safe_get(results[1], "revenue")
        if current is None or prev is None or prev == 0:
            return None
        return round((current - prev) / abs(prev) * 100, 2)

    def _calc_gross_margin(self, r: StockDataRecord) -> Optional[float]:
        """Gross_Profit / Revenue * 100"""
        gp = r.get_field("gross_profit")
        rev = r.get_field("revenue")
        if gp is None or rev is None or rev == 0:
            return None
        return round(gp / rev * 100, 2)

    def _calc_net_profit_margin(self, r: StockDataRecord) -> Optional[float]:
        """Net_Profit / Revenue * 100"""
        np_ = r.get_field("net_profit")
        rev = r.get_field("revenue")
        if np_ is None or rev is None or rev == 0:
            return None
        return round(np_ / rev * 100, 2)

    def _calc_eps_growth_yoy(self, r: StockDataRecord) -> Optional[float]:
        """(EPS_current - EPS_prev_year) / |EPS_prev_year| * 100"""
        results = r.quarterly_results
        if len(results) < 5:
            return None
        current = _safe_get(results[0], "eps")
        prev_year = _safe_get(results[4], "eps")
        if current is None or prev_year is None or prev_year == 0:
            return None
        return round((current - prev_year) / abs(prev_year) * 100, 2)

    def _calc_ebit(self, r: StockDataRecord) -> Optional[float]:
        """EBITDA - Depreciation, or Operating_Profit"""
        ebitda = r.get_field("ebitda")
        dep = r.get_field("depreciation")
        if ebitda is not None and dep is not None:
            return round(ebitda - dep, 2)
        op = r.get_field("operating_profit")
        return op

    def _calc_effective_tax_rate(self, r: StockDataRecord) -> Optional[float]:
        """Tax_Expense / (Net_Profit + Tax_Expense) * 100"""
        tax = r.get_field("tax_expense")
        np_ = r.get_field("net_profit")
        if tax is None or np_ is None:
            return None
        pbt = np_ + tax
        if pbt == 0:
            return None
        return round(tax / pbt * 100, 2)

    # ===== BALANCE SHEET DERIVED =====

    def _calc_net_debt(self, r: StockDataRecord) -> Optional[float]:
        """Total_Debt - Cash_and_Equivalents"""
        debt = r.get_field("total_debt")
        cash = r.get_field("cash_and_equivalents")
        if debt is None:
            return None
        cash = cash or 0
        return round(debt - cash, 2)

    # ===== CASH FLOW DERIVED =====

    def _calc_free_cash_flow(self, r: StockDataRecord) -> Optional[float]:
        """Operating_Cash_Flow - Capital_Expenditure"""
        ocf = r.get_field("operating_cash_flow")
        capex = r.get_field("capital_expenditure")
        if ocf is None:
            return None
        capex = abs(capex) if capex is not None else 0
        return round(ocf - capex, 2)

    # ===== FINANCIAL RATIOS =====

    def _calc_roe(self, r: StockDataRecord) -> Optional[float]:
        """Net_Profit / Total_Equity * 100"""
        np_ = r.get_field("net_profit")
        eq = r.get_field("total_equity")
        if np_ is None or eq is None or eq == 0:
            return None
        return round(np_ / eq * 100, 2)

    def _calc_roa(self, r: StockDataRecord) -> Optional[float]:
        """Net_Profit / Total_Assets * 100"""
        np_ = r.get_field("net_profit")
        assets = r.get_field("total_assets")
        if np_ is None or assets is None or assets == 0:
            return None
        return round(np_ / assets * 100, 2)

    def _calc_roic(self, r: StockDataRecord) -> Optional[float]:
        """EBIT * (1 - tax_rate) / (Total_Equity + Total_Debt - Cash) * 100"""
        ebit = r.get_field("ebit")
        tax_rate = r.get_field("effective_tax_rate")
        eq = r.get_field("total_equity")
        debt = r.get_field("total_debt") or 0
        cash = r.get_field("cash_and_equivalents") or 0
        if ebit is None or eq is None:
            return None
        tax_pct = (tax_rate or 25.0) / 100.0
        invested_capital = eq + debt - cash
        if invested_capital <= 0:
            return None
        nopat = ebit * (1 - tax_pct)
        return round(nopat / invested_capital * 100, 2)

    def _calc_debt_to_equity(self, r: StockDataRecord) -> Optional[float]:
        """Total_Debt / Total_Equity"""
        debt = r.get_field("total_debt")
        eq = r.get_field("total_equity")
        if debt is None or eq is None or eq == 0:
            return None
        return round(debt / eq, 2)

    def _calc_interest_coverage(self, r: StockDataRecord) -> Optional[float]:
        """EBIT / Interest_Expense"""
        ebit = r.get_field("ebit") or r.get_field("operating_profit")
        interest = r.get_field("interest_expense")
        if ebit is None or interest is None or interest == 0:
            return None
        return round(ebit / interest, 2)

    def _calc_current_ratio(self, r: StockDataRecord) -> Optional[float]:
        """Current_Assets / Current_Liabilities"""
        ca = r.get_field("current_assets")
        cl = r.get_field("current_liabilities")
        if ca is None or cl is None or cl == 0:
            return None
        return round(ca / cl, 2)

    def _calc_quick_ratio(self, r: StockDataRecord) -> Optional[float]:
        """(Current_Assets - Inventory) / Current_Liabilities"""
        ca = r.get_field("current_assets")
        inv = r.get_field("inventory") or 0
        cl = r.get_field("current_liabilities")
        if ca is None or cl is None or cl == 0:
            return None
        return round((ca - inv) / cl, 2)

    def _calc_asset_turnover(self, r: StockDataRecord) -> Optional[float]:
        """Revenue / Total_Assets"""
        rev = r.get_field("revenue")
        assets = r.get_field("total_assets")
        if rev is None or assets is None or assets == 0:
            return None
        return round(rev / assets, 2)

    def _calc_inventory_turnover(self, r: StockDataRecord) -> Optional[float]:
        """Revenue / Inventory"""
        rev = r.get_field("revenue")
        inv = r.get_field("inventory")
        if rev is None or inv is None or inv == 0:
            return None
        return round(rev / inv, 2)

    def _calc_receivables_turnover(self, r: StockDataRecord) -> Optional[float]:
        """Revenue / Receivables"""
        rev = r.get_field("revenue")
        rec = r.get_field("receivables")
        if rev is None or rec is None or rec == 0:
            return None
        return round(rev / rec, 2)

    def _calc_dividend_payout_ratio(self, r: StockDataRecord) -> Optional[float]:
        """Dividends_Paid / Net_Profit * 100"""
        div = r.get_field("dividends_paid")
        np_ = r.get_field("net_profit")
        if div is None or np_ is None or np_ <= 0:
            return None
        return round(abs(div) / np_ * 100, 2)

    # ===== DERIVED PRICE METRICS =====

    def _calc_daily_return_pct(self, r: StockDataRecord) -> Optional[float]:
        """(Close - Prev_Close) / Prev_Close * 100"""
        close = r.get_field("close")
        prev = r.get_field("prev_close")
        if close is None or prev is None or prev == 0:
            return None
        return round((close - prev) / prev * 100, 2)

    def _calc_return_5d_pct(self, r: StockDataRecord) -> Optional[float]:
        """5-day return from price history"""
        return self._calc_period_return(r, 5)

    def _calc_return_20d_pct(self, r: StockDataRecord) -> Optional[float]:
        """20-day return from price history"""
        return self._calc_period_return(r, 20)

    def _calc_return_60d_pct(self, r: StockDataRecord) -> Optional[float]:
        """60-day return from price history"""
        return self._calc_period_return(r, 60)

    def _calc_period_return(self, r: StockDataRecord, days: int) -> Optional[float]:
        """Calculate N-day return from price history."""
        history = r.price_history
        if len(history) < days + 1:
            return None
        current_close = _safe_get(history[0], "close")
        past_close = _safe_get(history[days], "close")
        if current_close is None or past_close is None or past_close == 0:
            return None
        return round((current_close - past_close) / past_close * 100, 2)

    def _calc_day_range_pct(self, r: StockDataRecord) -> Optional[float]:
        """(High - Low) / Low * 100"""
        high = r.get_field("high")
        low = r.get_field("low")
        if high is None or low is None or low == 0:
            return None
        return round((high - low) / low * 100, 2)

    def _calc_gap_percentage(self, r: StockDataRecord) -> Optional[float]:
        """(Open - Prev_Close) / Prev_Close * 100"""
        open_p = r.get_field("open")
        prev = r.get_field("prev_close")
        if open_p is None or prev is None or prev == 0:
            return None
        return round((open_p - prev) / prev * 100, 2)

    def _calc_week_52_high(self, r: StockDataRecord) -> Optional[float]:
        """Maximum close price in last 252 trading days"""
        history = r.price_history
        if not history:
            return None
        prices = [_safe_get(d, "high") or _safe_get(d, "close") for d in history[:252]]
        prices = [p for p in prices if p is not None]
        return max(prices) if prices else None

    def _calc_week_52_low(self, r: StockDataRecord) -> Optional[float]:
        """Minimum close price in last 252 trading days"""
        history = r.price_history
        if not history:
            return None
        prices = [_safe_get(d, "low") or _safe_get(d, "close") for d in history[:252]]
        prices = [p for p in prices if p is not None]
        return min(prices) if prices else None

    def _calc_distance_from_52w_high(self, r: StockDataRecord) -> Optional[float]:
        """(Close - 52W_High) / 52W_High * 100"""
        close = r.get_field("close")
        high_52w = r.get_field("week_52_high")
        if close is None or high_52w is None or high_52w == 0:
            return None
        return round((close - high_52w) / high_52w * 100, 2)

    def _calc_avg_volume_20d(self, r: StockDataRecord) -> Optional[int]:
        """Average volume over last 20 trading days"""
        history = r.price_history
        if len(history) < 20:
            return None
        volumes = [_safe_get(d, "volume") for d in history[:20]]
        volumes = [v for v in volumes if v is not None and v > 0]
        if not volumes:
            return None
        return int(sum(volumes) / len(volumes))

    def _calc_volume_ratio(self, r: StockDataRecord) -> Optional[float]:
        """Today_Volume / Avg_Volume_20d"""
        volume = r.get_field("volume")
        avg_vol = r.get_field("avg_volume_20d")
        if volume is None or avg_vol is None or avg_vol == 0:
            return None
        return round(volume / avg_vol, 2)

    # ===== VALUATION METRICS =====

    def _calc_market_cap(self, r: StockDataRecord) -> Optional[float]:
        """Close * Shares_Outstanding / 10^7 (in Cr)"""
        close = r.get_field("close")
        shares = r.get_field("shares_outstanding")
        if close is None or shares is None:
            return None
        return round(close * shares / 1e7, 2)

    def _calc_enterprise_value(self, r: StockDataRecord) -> Optional[float]:
        """Market_Cap + Net_Debt"""
        mcap = r.get_field("market_cap")
        net_debt = r.get_field("net_debt")
        if mcap is None:
            return None
        nd = net_debt if net_debt is not None else 0
        return round(mcap + nd, 2)

    def _calc_pe_ratio(self, r: StockDataRecord) -> Optional[float]:
        """Close / EPS (TTM)"""
        close = r.get_field("close")
        eps = r.get_field("eps")
        if close is None or eps is None or eps <= 0:
            return None
        return round(close / eps, 2)

    def _calc_peg_ratio(self, r: StockDataRecord) -> Optional[float]:
        """PE_Ratio / EPS_Growth_YoY"""
        pe = r.get_field("pe_ratio")
        growth = r.get_field("eps_growth_yoy")
        if pe is None or growth is None or growth <= 0:
            return None
        return round(pe / growth, 2)

    def _calc_pb_ratio(self, r: StockDataRecord) -> Optional[float]:
        """Close / Book_Value_Per_Share"""
        close = r.get_field("close")
        bvps = r.get_field("book_value_per_share")
        if close is None or bvps is None or bvps <= 0:
            return None
        return round(close / bvps, 2)

    def _calc_ps_ratio(self, r: StockDataRecord) -> Optional[float]:
        """Market_Cap / Revenue"""
        mcap = r.get_field("market_cap")
        rev = r.get_field("revenue")
        if mcap is None or rev is None or rev <= 0:
            return None
        return round(mcap / rev, 2)

    def _calc_ev_to_ebitda(self, r: StockDataRecord) -> Optional[float]:
        """Enterprise_Value / EBITDA"""
        ev = r.get_field("enterprise_value")
        ebitda = r.get_field("ebitda")
        if ev is None or ebitda is None or ebitda <= 0:
            return None
        return round(ev / ebitda, 2)

    def _calc_ev_to_sales(self, r: StockDataRecord) -> Optional[float]:
        """Enterprise_Value / Revenue"""
        ev = r.get_field("enterprise_value")
        rev = r.get_field("revenue")
        if ev is None or rev is None or rev <= 0:
            return None
        return round(ev / rev, 2)

    def _calc_dividend_yield(self, r: StockDataRecord) -> Optional[float]:
        """(Dividend_Per_Share / Close) * 100"""
        dps = r.get_field("dividend_per_share")
        close = r.get_field("close")
        if dps is None or close is None or close <= 0:
            return None
        return round(dps / close * 100, 2)

    def _calc_fcf_yield(self, r: StockDataRecord) -> Optional[float]:
        """(Free_Cash_Flow / Market_Cap) * 100"""
        fcf = r.get_field("free_cash_flow")
        mcap = r.get_field("market_cap")
        if fcf is None or mcap is None or mcap <= 0:
            return None
        return round(fcf / mcap * 100, 2)

    def _calc_earnings_yield(self, r: StockDataRecord) -> Optional[float]:
        """(EPS / Close) * 100 — inverse of P/E"""
        eps = r.get_field("eps")
        close = r.get_field("close")
        if eps is None or close is None or close <= 0:
            return None
        return round(eps / close * 100, 2)

    def _calc_historical_pe_median(self, r: StockDataRecord) -> Optional[float]:
        """Median P/E over last 5 years of price history (approximate)."""
        history = r.price_history
        eps = r.get_field("eps")
        if not history or eps is None or eps <= 0:
            return None
        # Take yearly samples (every ~252 trading days)
        pe_values = []
        for i in range(0, min(len(history), 1260), 252):
            close = _safe_get(history[i], "close")
            if close is not None and close > 0:
                pe_values.append(close / eps)
        if not pe_values:
            return None
        pe_values.sort()
        mid = len(pe_values) // 2
        if len(pe_values) % 2 == 0:
            return round((pe_values[mid - 1] + pe_values[mid]) / 2, 2)
        return round(pe_values[mid], 2)

    def _calc_market_cap_category(self, r: StockDataRecord) -> Optional[str]:
        """Classify market cap: Large (>=20000 Cr), Mid (>=5000), Small"""
        mcap = r.get_field("market_cap")
        if mcap is None:
            return None
        if mcap >= 20000:
            return "Large Cap"
        elif mcap >= 5000:
            return "Mid Cap"
        else:
            return "Small Cap"

    # ===== SHAREHOLDING CHANGES =====

    def _calc_promoter_holding_change(self, r: StockDataRecord) -> Optional[float]:
        """Change in promoter holding over last year (4 quarters)."""
        history = r.shareholding_history
        if len(history) < 2:
            return None
        current = _safe_get(history[0], "promoter_holding")
        prev = _safe_get(history[-1], "promoter_holding")
        if current is None or prev is None:
            return None
        return round(current - prev, 2)

    def _calc_fii_holding_change(self, r: StockDataRecord) -> Optional[float]:
        """Change in FII holding over last year."""
        history = r.shareholding_history
        if len(history) < 2:
            return None
        current = _safe_get(history[0], "fii_holding")
        prev = _safe_get(history[-1], "fii_holding")
        if current is None or prev is None:
            return None
        return round(current - prev, 2)


def _safe_get(d: Dict[str, Any], key: str) -> Optional[float]:
    """Safely get a numeric value from a dict."""
    val = d.get(key)
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None
