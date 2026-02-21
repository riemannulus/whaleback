"""Investor flow analysis module.

Pure computation functions for detecting retail contrarian signals,
smart/dumb money divergence, and flow momentum shifts.
No database dependency - operates on raw data passed as arguments.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def compute_retail_contrarian(
    investor_data: list[dict[str, Any]],
    avg_daily_trading_value: float | None = None,
    lookback_days: int = 20,
) -> dict[str, Any]:
    """Compute retail contrarian signal based on individual investor extremes.

    Uses Z-score to detect extreme retail buying/selling as contrarian indicators.
    High retail buying (Z > 2.0) suggests overbought → sell signal.
    High retail selling (Z < -2.0) suggests oversold → buy opportunity.

    Args:
        investor_data: List of daily investor trading records (any order).
            Each record: {trade_date, individual_net, ...}
        avg_daily_trading_value: Average daily trading value for normalization.
        lookback_days: Number of trading days to analyze for current signal.

    Returns:
        {retail_z, retail_intensity, retail_consistency, signal, signal_label}
    """
    if not investor_data:
        return _empty_retail_result()

    # Sort and limit to lookback period
    data = sorted(investor_data, key=lambda x: x.get("trade_date", ""))[-lookback_days:]

    if not data:
        return _empty_retail_result()

    # Compute current retail metrics
    net_values = [r.get("individual_net", 0) for r in data]
    net_total = sum(net_values)
    total_days = len(net_values)
    buy_days = sum(1 for v in net_values if v > 0)

    # Retail intensity (normalized by trading volume)
    if avg_daily_trading_value and avg_daily_trading_value > 0:
        retail_intensity = net_total / (avg_daily_trading_value * lookback_days)
    else:
        retail_intensity = 0.0

    # Retail consistency (buy day ratio)
    retail_consistency = buy_days / total_days if total_days > 0 else 0.0

    # Compute Z-score (requires at least 60 days for rolling windows)
    retail_z = _compute_retail_z_score(investor_data, avg_daily_trading_value, lookback_days)

    # Determine signal
    signal = _classify_retail_signal(retail_z)

    return {
        "retail_z": round(retail_z, 2),
        "retail_intensity": round(retail_intensity, 4),
        "retail_consistency": round(retail_consistency, 4),
        "signal": signal,
        "signal_label": _retail_signal_label(signal),
        "lookback_days": total_days,
    }


def compute_smart_dumb_divergence(
    investor_data: list[dict[str, Any]],
    avg_daily_trading_value: float | None = None,
    lookback_days: int = 20,
) -> dict[str, Any]:
    """Compute divergence between smart money and dumb money flows.

    Smart money = institution + foreign + pension
    Dumb money = individual retail investors
    Positive divergence = smart buying while dumb selling (accumulation signal)

    Args:
        investor_data: List of daily investor trading records (any order).
            Each record: {trade_date, institution_net, foreign_net, pension_net, individual_net, ...}
        avg_daily_trading_value: Average daily trading value for normalization.
        lookback_days: Number of trading days to analyze.

    Returns:
        {divergence_score, smart_ratio, dumb_ratio, signal, signal_label}
    """
    if not investor_data:
        return _empty_divergence_result()

    # Sort and limit to lookback period
    data = sorted(investor_data, key=lambda x: x.get("trade_date", ""))[-lookback_days:]

    if not data:
        return _empty_divergence_result()

    # Sum smart money flow
    smart_money_flow = 0.0
    for record in data:
        smart_money_flow += record.get("institution_net", 0)
        smart_money_flow += record.get("foreign_net", 0)
        smart_money_flow += record.get("pension_net", 0)

    # Sum dumb money flow
    dumb_money_flow = sum(r.get("individual_net", 0) for r in data)

    # Normalize by trading volume
    total_days = len(data)
    if avg_daily_trading_value and avg_daily_trading_value > 0:
        denominator = avg_daily_trading_value * lookback_days
        smart_ratio = smart_money_flow / denominator
        dumb_ratio = dumb_money_flow / denominator
    else:
        smart_ratio = 0.0
        dumb_ratio = 0.0

    # Divergence score (positive = smart buying, dumb selling)
    divergence_score = smart_ratio - dumb_ratio

    # Determine signal
    signal = _classify_divergence_signal(divergence_score)

    return {
        "divergence_score": round(divergence_score, 4),
        "smart_ratio": round(smart_ratio, 4),
        "dumb_ratio": round(dumb_ratio, 4),
        "signal": signal,
        "signal_label": _divergence_signal_label(signal),
        "lookback_days": total_days,
    }


def compute_flow_momentum_shift(
    investor_data: list[dict[str, Any]],
    lookback_short: int = 5,
    lookback_long: int = 60,
) -> dict[str, Any]:
    """Detect momentum shifts in institutional investor flows.

    Compares short-term flow (last 5 days) vs long-term trend (60 days).
    Reversal = short-term sign opposite to long-term sign.

    Args:
        investor_data: List of daily investor trading records (any order).
            Each record: {trade_date, institution_net, foreign_net, pension_net, ...}
        lookback_short: Short-term window (default 5 days).
        lookback_long: Long-term window (default 60 days).

    Returns:
        {shift_score, components: {type: {flow_short, flow_long, reversal_type, strength, score}},
         overall_signal, signal_label}
    """
    if not investor_data:
        return _empty_shift_result()

    # Sort by date
    data = sorted(investor_data, key=lambda x: x.get("trade_date", ""))

    if len(data) < lookback_short:
        return _empty_shift_result()

    investor_types = ["institution_net", "foreign_net", "pension_net"]
    components = {}
    sub_scores = []

    for investor_type in investor_types:
        # Extract short and long windows
        short_window = data[-lookback_short:]
        long_window = data[-lookback_long:] if len(data) >= lookback_long else data

        flow_short = sum(r.get(investor_type, 0) for r in short_window)
        flow_long = sum(r.get(investor_type, 0) for r in long_window)

        # Detect reversal
        reversal_type = "none"
        if flow_short > 0 and flow_long < 0:
            reversal_type = "bullish_reversal"
        elif flow_short < 0 and flow_long > 0:
            reversal_type = "bearish_reversal"

        # Compute strength (capped at 2.0)
        if reversal_type != "none" and flow_long != 0:
            # Normalize long flow to same timeframe as short
            normalized_long = abs(flow_long) / (len(long_window) / len(short_window))
            if normalized_long > 0:
                strength = min(abs(flow_short) / normalized_long, 2.0)
            else:
                strength = 0.0
        else:
            strength = 0.0

        # Sub-score
        if reversal_type != "none":
            sub_score = strength * 50.0
        else:
            sub_score = 0.0

        components[investor_type] = {
            "flow_short": flow_short,
            "flow_long": flow_long,
            "reversal_type": reversal_type,
            "strength": round(strength, 4),
            "score": round(sub_score, 2),
        }
        sub_scores.append(sub_score)

    # Composite shift score: max * 0.6 + avg * 0.4
    if sub_scores:
        max_score = max(sub_scores)
        avg_score = sum(sub_scores) / len(sub_scores)
        shift_score = max_score * 0.6 + avg_score * 0.4
    else:
        shift_score = 0.0

    # Determine overall signal
    signal = _classify_shift_signal(shift_score, components)

    return {
        "shift_score": round(shift_score, 2),
        "components": components,
        "overall_signal": signal,
        "signal_label": _shift_signal_label(signal),
        "lookback_short": len(data[-lookback_short:]),
        "lookback_long": len(data[-lookback_long:]) if len(data) >= lookback_long else len(data),
    }


# Helper functions

def _compute_retail_z_score(
    investor_data: list[dict[str, Any]],
    avg_daily_trading_value: float | None,
    lookback_days: int,
) -> float:
    """Compute Z-score for retail intensity using rolling windows.

    Requires at least 60 days of data. Computes intensity over sliding windows,
    then Z = (current_intensity - mean) / std.
    """
    # Need at least 60 days for meaningful statistics
    sorted_data = sorted(investor_data, key=lambda x: x.get("trade_date", ""))

    if len(sorted_data) < 60:
        return 0.0

    if not avg_daily_trading_value or avg_daily_trading_value <= 0:
        return 0.0

    # Compute rolling intensities
    intensities = []
    window_size = lookback_days

    for i in range(len(sorted_data) - window_size + 1):
        window = sorted_data[i:i + window_size]
        net_total = sum(r.get("individual_net", 0) for r in window)
        intensity = net_total / (avg_daily_trading_value * window_size)
        intensities.append(intensity)

    if not intensities or len(intensities) < 2:
        return 0.0

    # Compute Z-score for most recent intensity
    current_intensity = intensities[-1]
    mean_intensity = sum(intensities) / len(intensities)

    # Standard deviation
    variance = sum((x - mean_intensity) ** 2 for x in intensities) / len(intensities)
    std_intensity = variance ** 0.5

    if std_intensity > 0:
        z_score = (current_intensity - mean_intensity) / std_intensity
    else:
        z_score = 0.0

    return z_score


def _classify_retail_signal(retail_z: float) -> str:
    """Classify retail contrarian signal based on Z-score."""
    if retail_z > 2.0:
        return "extreme_buying"  # Contrarian sell warning
    elif retail_z < -2.0:
        return "extreme_selling"  # Contrarian buy opportunity
    else:
        return "neutral"


def _retail_signal_label(signal: str) -> str:
    """Korean label for retail contrarian signal."""
    labels = {
        "extreme_buying": "역발상 매도 경고",  # Retail overbought
        "extreme_selling": "역발상 매수 기회",  # Retail oversold
        "neutral": "중립",
    }
    return labels.get(signal, "알 수 없음")


def _classify_divergence_signal(divergence_score: float) -> str:
    """Classify smart/dumb money divergence signal."""
    if divergence_score > 0.5:
        return "smart_accumulation"  # Smart buying, dumb selling
    elif divergence_score < -0.5:
        return "smart_distribution"  # Smart selling, dumb buying
    else:
        return "mixed"


def _divergence_signal_label(signal: str) -> str:
    """Korean label for divergence signal."""
    labels = {
        "smart_accumulation": "스마트머니 매집",
        "smart_distribution": "스마트머니 매도",
        "mixed": "혼재",
    }
    return labels.get(signal, "알 수 없음")


def _classify_shift_signal(shift_score: float, components: dict) -> str:
    """Classify overall momentum shift signal."""
    # Check reversal types
    reversals = [c.get("reversal_type", "none") for c in components.values() if isinstance(c, dict)]

    bullish_count = sum(1 for r in reversals if r == "bullish_reversal")
    bearish_count = sum(1 for r in reversals if r == "bearish_reversal")

    if shift_score >= 40:
        if bullish_count > bearish_count:
            return "strong_bullish_shift"
        elif bearish_count > bullish_count:
            return "strong_bearish_shift"
        else:
            return "strong_shift"
    elif shift_score >= 20:
        if bullish_count > bearish_count:
            return "mild_bullish_shift"
        elif bearish_count > bullish_count:
            return "mild_bearish_shift"
        else:
            return "mild_shift"
    else:
        return "no_shift"


def _shift_signal_label(signal: str) -> str:
    """Korean label for momentum shift signal."""
    labels = {
        "strong_bullish_shift": "강한 상승 전환",
        "strong_bearish_shift": "강한 하락 전환",
        "strong_shift": "강한 수급 전환",
        "mild_bullish_shift": "완만한 상승 전환",
        "mild_bearish_shift": "완만한 하락 전환",
        "mild_shift": "완만한 수급 전환",
        "no_shift": "전환 없음",
    }
    return labels.get(signal, "알 수 없음")


def _empty_retail_result() -> dict[str, Any]:
    return {
        "retail_z": 0.0,
        "retail_intensity": 0.0,
        "retail_consistency": 0.0,
        "signal": "neutral",
        "signal_label": "중립",
        "lookback_days": 0,
    }


def _empty_divergence_result() -> dict[str, Any]:
    return {
        "divergence_score": 0.0,
        "smart_ratio": 0.0,
        "dumb_ratio": 0.0,
        "signal": "mixed",
        "signal_label": "혼재",
        "lookback_days": 0,
    }


def _empty_shift_result() -> dict[str, Any]:
    return {
        "shift_score": 0.0,
        "components": {
            "institution_net": _empty_shift_component(),
            "foreign_net": _empty_shift_component(),
            "pension_net": _empty_shift_component(),
        },
        "overall_signal": "no_shift",
        "signal_label": "전환 없음",
        "lookback_short": 0,
        "lookback_long": 0,
    }


def _empty_shift_component() -> dict[str, Any]:
    return {
        "flow_short": 0,
        "flow_long": 0,
        "reversal_type": "none",
        "strength": 0.0,
        "score": 0.0,
    }
