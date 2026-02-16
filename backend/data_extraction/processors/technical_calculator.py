"""
Technical indicator calculator.

Computes all 15 technical indicator fields (138-152) from price history data.
Uses pure Python/NumPy implementations - no external TA library required.
"""

import logging
import math
from typing import Any, Dict, List, Optional, Tuple

from ..models.extraction_models import StockDataRecord

logger = logging.getLogger(__name__)


class TechnicalCalculator:
    """
    Calculates all technical indicators from price history.

    Indicators computed:
        - SMA 20/50/200
        - EMA 12/26
        - RSI 14
        - MACD + Signal line
        - Bollinger Bands (upper/lower)
        - ATR 14
        - ADX 14
        - OBV
        - Support / Resistance levels
    """

    def calculate_all(self, record: StockDataRecord) -> List[str]:
        """
        Calculate all technical indicators and set them on the record.

        Returns list of successfully calculated field names.
        """
        history = record.price_history
        if not history or len(history) < 26:
            return []

        closes = _extract_series(history, "close")
        highs = _extract_series(history, "high")
        lows = _extract_series(history, "low")
        volumes = _extract_series(history, "volume")

        # Reverse so index 0 = oldest (required for indicator math)
        closes_asc = list(reversed(closes))
        highs_asc = list(reversed(highs))
        lows_asc = list(reversed(lows))
        volumes_asc = list(reversed(volumes))

        calculated = []

        # SMA
        for period, field_name in [(20, "sma_20"), (50, "sma_50"), (200, "sma_200")]:
            val = _sma(closes_asc, period)
            if val is not None:
                record.set_field(field_name, round(val, 2), "calculated")
                calculated.append(field_name)

        # EMA
        for period, field_name in [(12, "ema_12"), (26, "ema_26")]:
            val = _ema(closes_asc, period)
            if val is not None:
                record.set_field(field_name, round(val, 2), "calculated")
                calculated.append(field_name)

        # RSI 14
        rsi = _rsi(closes_asc, 14)
        if rsi is not None:
            record.set_field("rsi_14", round(rsi, 2), "calculated")
            calculated.append("rsi_14")

        # MACD
        macd_val, signal_val = _macd(closes_asc)
        if macd_val is not None:
            record.set_field("macd", round(macd_val, 4), "calculated")
            calculated.append("macd")
        if signal_val is not None:
            record.set_field("macd_signal", round(signal_val, 4), "calculated")
            calculated.append("macd_signal")

        # Bollinger Bands
        upper, lower = _bollinger_bands(closes_asc, 20, 2.0)
        if upper is not None:
            record.set_field("bollinger_upper", round(upper, 2), "calculated")
            calculated.append("bollinger_upper")
        if lower is not None:
            record.set_field("bollinger_lower", round(lower, 2), "calculated")
            calculated.append("bollinger_lower")

        # ATR 14
        atr = _atr(highs_asc, lows_asc, closes_asc, 14)
        if atr is not None:
            record.set_field("atr_14", round(atr, 2), "calculated")
            calculated.append("atr_14")

        # ADX 14
        adx = _adx(highs_asc, lows_asc, closes_asc, 14)
        if adx is not None:
            record.set_field("adx_14", round(adx, 2), "calculated")
            calculated.append("adx_14")

        # OBV
        obv = _obv(closes_asc, volumes_asc)
        if obv is not None:
            record.set_field("obv", int(obv), "calculated")
            calculated.append("obv")

        # Support & Resistance
        support, resistance = _support_resistance(highs_asc, lows_asc, closes_asc)
        if support is not None:
            record.set_field("support_level", round(support, 2), "calculated")
            calculated.append("support_level")
        if resistance is not None:
            record.set_field("resistance_level", round(resistance, 2), "calculated")
            calculated.append("resistance_level")

        return calculated


# ===== Indicator implementations =====

def _extract_series(history: List[Dict], key: str) -> List[float]:
    """Extract a numeric series from price history (newest first)."""
    result = []
    for d in history:
        val = d.get(key)
        try:
            result.append(float(val) if val is not None else 0.0)
        except (ValueError, TypeError):
            result.append(0.0)
    return result


def _sma(prices: List[float], period: int) -> Optional[float]:
    """Simple Moving Average — latest value."""
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period


def _ema(prices: List[float], period: int) -> Optional[float]:
    """Exponential Moving Average — latest value."""
    if len(prices) < period:
        return None
    multiplier = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema
    return ema


def _ema_series(prices: List[float], period: int) -> List[float]:
    """Full EMA series (oldest to newest)."""
    if len(prices) < period:
        return []
    multiplier = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    result = [ema]
    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema
        result.append(ema)
    return result


def _rsi(prices: List[float], period: int = 14) -> Optional[float]:
    """Relative Strength Index — latest value."""
    if len(prices) < period + 1:
        return None

    gains = []
    losses = []
    for i in range(1, len(prices)):
        change = prices[i] - prices[i - 1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))

    if len(gains) < period:
        return None

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _macd(prices: List[float], fast: int = 12, slow: int = 26,
          signal: int = 9) -> Tuple[Optional[float], Optional[float]]:
    """MACD line and signal line — latest values."""
    if len(prices) < slow + signal:
        return None, None

    ema_fast = _ema_series(prices, fast)
    ema_slow = _ema_series(prices, slow)

    # Align series (ema_slow starts later)
    offset = slow - fast
    macd_line = []
    for i in range(len(ema_slow)):
        macd_line.append(ema_fast[i + offset] - ema_slow[i])

    if len(macd_line) < signal:
        return macd_line[-1] if macd_line else None, None

    signal_line = _ema_series(macd_line, signal)
    return macd_line[-1], signal_line[-1] if signal_line else None


def _bollinger_bands(prices: List[float], period: int = 20,
                     std_dev: float = 2.0) -> Tuple[Optional[float], Optional[float]]:
    """Bollinger upper and lower bands — latest values."""
    if len(prices) < period:
        return None, None

    window = prices[-period:]
    sma = sum(window) / period
    variance = sum((p - sma) ** 2 for p in window) / period
    sd = math.sqrt(variance)

    return sma + std_dev * sd, sma - std_dev * sd


def _atr(highs: List[float], lows: List[float], closes: List[float],
         period: int = 14) -> Optional[float]:
    """Average True Range — latest value."""
    if len(closes) < period + 1:
        return None

    true_ranges = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        true_ranges.append(tr)

    if len(true_ranges) < period:
        return None

    atr = sum(true_ranges[:period]) / period
    for tr in true_ranges[period:]:
        atr = (atr * (period - 1) + tr) / period
    return atr


def _adx(highs: List[float], lows: List[float], closes: List[float],
         period: int = 14) -> Optional[float]:
    """Average Directional Index — latest value."""
    n = len(closes)
    if n < 2 * period + 1:
        return None

    plus_dm = []
    minus_dm = []
    tr_list = []

    for i in range(1, n):
        up_move = highs[i] - highs[i - 1]
        down_move = lows[i - 1] - lows[i]

        plus_dm.append(max(up_move, 0) if up_move > down_move else 0)
        minus_dm.append(max(down_move, 0) if down_move > up_move else 0)

        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        tr_list.append(tr)

    # Smooth with Wilder's method
    atr_s = sum(tr_list[:period]) / period
    plus_di_s = sum(plus_dm[:period]) / period
    minus_di_s = sum(minus_dm[:period]) / period

    dx_values = []
    for i in range(period, len(tr_list)):
        atr_s = (atr_s * (period - 1) + tr_list[i]) / period
        plus_di_s = (plus_di_s * (period - 1) + plus_dm[i]) / period
        minus_di_s = (minus_di_s * (period - 1) + minus_dm[i]) / period

        if atr_s > 0:
            plus_di = (plus_di_s / atr_s) * 100
            minus_di = (minus_di_s / atr_s) * 100
        else:
            plus_di = 0
            minus_di = 0

        di_sum = plus_di + minus_di
        if di_sum > 0:
            dx = abs(plus_di - minus_di) / di_sum * 100
            dx_values.append(dx)

    if len(dx_values) < period:
        return None

    adx = sum(dx_values[:period]) / period
    for dx in dx_values[period:]:
        adx = (adx * (period - 1) + dx) / period
    return adx


def _obv(closes: List[float], volumes: List[float]) -> Optional[int]:
    """On-Balance Volume — latest value."""
    if len(closes) < 2 or len(volumes) < 2:
        return None

    obv = 0
    for i in range(1, len(closes)):
        if closes[i] > closes[i - 1]:
            obv += int(volumes[i])
        elif closes[i] < closes[i - 1]:
            obv -= int(volumes[i])
    return obv


def _support_resistance(highs: List[float], lows: List[float],
                        closes: List[float]) -> Tuple[Optional[float], Optional[float]]:
    """
    Estimate support and resistance using pivot points from recent data.

    Uses classic pivot point formula from last 20 trading days.
    """
    if len(closes) < 20:
        return None, None

    # Recent period highs/lows
    recent_highs = highs[-20:]
    recent_lows = lows[-20:]
    recent_close = closes[-1]

    pivot_high = max(recent_highs)
    pivot_low = min(recent_lows)
    pivot = (pivot_high + pivot_low + recent_close) / 3

    support = 2 * pivot - pivot_high
    resistance = 2 * pivot - pivot_low

    return support, resistance
