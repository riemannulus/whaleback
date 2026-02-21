"""Technical analysis indicators module.

Pure computation functions for technical indicators (Disparity, Bollinger Bands, MACD).
No database dependency - operates on price series passed as arguments.
"""

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


def _ema(data: list[float], period: int) -> list[float]:
    """Calculate exponential moving average.

    Args:
        data: List of values (chronological order, oldest first)
        period: EMA period

    Returns:
        List of EMA values (same length as input, early values are None until enough data)
    """
    if len(data) < period:
        return [None] * len(data)

    multiplier = 2.0 / (period + 1)
    ema_values = [None] * len(data)

    # Start with SMA for first period
    sma = np.mean(data[:period])
    ema_values[period - 1] = sma

    # Apply EMA formula for remaining values
    for i in range(period, len(data)):
        ema_values[i] = (data[i] - ema_values[i - 1]) * multiplier + ema_values[i - 1]

    return ema_values


def compute_disparity(
    prices: list[float],
    periods: tuple[int, ...] = (20, 60, 120),
) -> dict[str, Any]:
    """Compute disparity index (price vs moving average deviation).

    Disparity = (current_price / SMA) * 100
    Signal based on 20-day disparity thresholds.

    Args:
        prices: List of closing prices (chronological order, oldest first)
        periods: Tuple of periods for disparity calculation (default: 20, 60, 120 days)

    Returns:
        {
            disparity_20d: float | None,
            disparity_60d: float | None,
            disparity_120d: float | None,
            signal: str,
            signal_label: str
        }
    """
    if not prices:
        return {
            "disparity_20d": None,
            "disparity_60d": None,
            "disparity_120d": None,
            "signal": "neutral",
            "signal_label": "중립",
        }

    current_price = prices[-1]
    result = {}

    # Compute disparity for each period
    for period in periods:
        key = f"disparity_{period}d"
        if len(prices) >= period:
            sma = np.mean(prices[-period:])
            disparity = (current_price / sma) * 100 if sma > 0 else None
            result[key] = round(disparity, 2) if disparity else None
        else:
            result[key] = None

    # Determine signal based on 20-day disparity
    disparity_20 = result.get("disparity_20d")
    if disparity_20 is None:
        signal = "neutral"
        signal_label = "중립"
    elif disparity_20 < 92:
        signal = "strong_oversold"
        signal_label = "강한 과매도"
    elif disparity_20 < 96:
        signal = "oversold"
        signal_label = "과매도"
    elif disparity_20 > 108:
        signal = "strong_overbought"
        signal_label = "강한 과매수"
    elif disparity_20 > 104:
        signal = "overbought"
        signal_label = "과매수"
    else:
        signal = "neutral"
        signal_label = "중립"

    result["signal"] = signal
    result["signal_label"] = signal_label

    return result


def compute_bollinger(
    prices: list[float],
    period: int = 20,
    num_std: float = 2.0,
) -> dict[str, Any]:
    """Compute Bollinger Bands indicator.

    Args:
        prices: List of closing prices (chronological order, oldest first)
        period: Moving average period (default: 20)
        num_std: Number of standard deviations for bands (default: 2.0)

    Returns:
        {
            upper: float | None,
            center: float | None,
            lower: float | None,
            bandwidth: float | None,
            percent_b: float | None,
            signal: str,
            signal_label: str
        }
    """
    if not prices or len(prices) < period:
        return {
            "upper": None,
            "center": None,
            "lower": None,
            "bandwidth": None,
            "percent_b": None,
            "signal": "neutral",
            "signal_label": "중립",
        }

    recent_prices = prices[-period:]
    center = float(np.mean(recent_prices))
    std = float(np.std(recent_prices, ddof=1))

    upper = center + num_std * std
    lower = center - num_std * std

    bandwidth = (upper - lower) / center * 100 if center > 0 else 0
    current_price = prices[-1]

    if upper != lower:
        percent_b = (current_price - lower) / (upper - lower)
    else:
        percent_b = 0.5

    # Determine signal
    if percent_b > 1.0:
        signal = "upper_break"
        signal_label = "상단 돌파"
    elif percent_b < 0.0:
        signal = "lower_support"
        signal_label = "하단 지지"
    elif bandwidth < 10:
        signal = "squeeze"
        signal_label = "밴드 수축"
    else:
        signal = "neutral"
        signal_label = "중립"

    return {
        "upper": round(upper, 2),
        "center": round(center, 2),
        "lower": round(lower, 2),
        "bandwidth": round(bandwidth, 2),
        "percent_b": round(percent_b, 4),
        "signal": signal,
        "signal_label": signal_label,
    }


def compute_macd(
    prices: list[float],
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> dict[str, Any]:
    """Compute MACD (Moving Average Convergence Divergence) indicator.

    MACD Line = EMA(fast) - EMA(slow)
    Signal Line = EMA(MACD, signal_period)
    Histogram = MACD - Signal

    Args:
        prices: List of closing prices (chronological order, oldest first)
        fast: Fast EMA period (default: 12)
        slow: Slow EMA period (default: 26)
        signal_period: Signal line EMA period (default: 9)

    Returns:
        {
            macd: float | None,
            signal_line: float | None,
            histogram: float | None,
            crossover: str,
            signal_label: str
        }
    """
    min_required = slow + signal_period
    if not prices or len(prices) < min_required:
        return {
            "macd": None,
            "signal_line": None,
            "histogram": None,
            "crossover": "none",
            "signal_label": "없음",
        }

    # Calculate fast and slow EMAs
    fast_ema = _ema(prices, fast)
    slow_ema = _ema(prices, slow)

    # Calculate MACD line
    macd_line = []
    for f, s in zip(fast_ema, slow_ema):
        if f is not None and s is not None:
            macd_line.append(f - s)
        else:
            macd_line.append(None)

    # Calculate signal line (EMA of MACD)
    # Filter out None values for signal line calculation
    valid_macd_start = next(
        (i for i, v in enumerate(macd_line) if v is not None),
        len(macd_line),
    )
    if valid_macd_start + signal_period > len(macd_line):
        return {
            "macd": None,
            "signal_line": None,
            "histogram": None,
            "crossover": "none",
            "signal_label": "없음",
        }

    valid_macd = [v for v in macd_line[valid_macd_start:] if v is not None]
    signal_ema = _ema(valid_macd, signal_period)

    # Get current values
    current_macd = macd_line[-1]
    current_signal = signal_ema[-1] if signal_ema and signal_ema[-1] is not None else None

    if current_macd is None or current_signal is None:
        return {
            "macd": None,
            "signal_line": None,
            "histogram": None,
            "crossover": "none",
            "signal_label": "없음",
        }

    current_histogram = current_macd - current_signal

    # Detect crossover (need previous histogram)
    if len(signal_ema) >= 2 and signal_ema[-2] is not None:
        prev_macd_idx = len(macd_line) - 2
        if macd_line[prev_macd_idx] is not None:
            prev_histogram = macd_line[prev_macd_idx] - signal_ema[-2]

            if current_histogram > 0 and prev_histogram <= 0:
                crossover = "golden_cross"
                signal_label = "골든크로스"
            elif current_histogram < 0 and prev_histogram >= 0:
                crossover = "dead_cross"
                signal_label = "데드크로스"
            else:
                crossover = "none"
                signal_label = "없음"
        else:
            crossover = "none"
            signal_label = "없음"
    else:
        crossover = "none"
        signal_label = "없음"

    return {
        "macd": round(current_macd, 4),
        "signal_line": round(current_signal, 4),
        "histogram": round(current_histogram, 4),
        "crossover": crossover,
        "signal_label": signal_label,
    }
