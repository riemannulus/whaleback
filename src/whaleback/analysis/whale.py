"""Whale (institutional investor) tracking analysis module.

Pure computation functions for detecting institutional accumulation patterns.
No database dependency - operates on raw data passed as arguments.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Investor types tracked for whale analysis
WHALE_INVESTOR_TYPES = ["institution_net", "foreign_net", "pension_net", "private_equity_net", "other_corp_net"]


def compute_whale_score(
    investor_data: list[dict[str, Any]],
    avg_daily_trading_value: float | None = None,
    lookback_days: int = 20,
) -> dict[str, Any]:
    """Compute composite whale score based on institutional buying patterns.

    For each investor type (institution, foreign, pension, private_equity, other_corp):
      consistency = buy_days / total_days
      intensity = abs(net_value) / avg_daily_trading_value (capped at 1.0)
      sub_score = consistency * 60 + min(intensity * 40, 40)

    whale_score = max(sub_scores) * 0.5 + avg(sub_scores) * 0.5

    Args:
        investor_data: List of daily investor trading records (newest first or any order).
            Each record: {trade_date, institution_net, foreign_net, pension_net, private_equity_net, other_corp_net, ...}
        avg_daily_trading_value: Average daily trading value for volume normalization.
        lookback_days: Number of trading days to analyze.

    Returns:
        {whale_score, components: {type: {net_total, buy_days, sell_days, consistency, intensity, score}}, signal}
    """
    if not investor_data:
        return _empty_whale_result()

    # Limit to lookback period
    data = sorted(investor_data, key=lambda x: x.get("trade_date", ""))[-lookback_days:]
    total_days = len(data)

    if total_days == 0:
        return _empty_whale_result()

    components = {}
    sub_scores = []

    for investor_type in WHALE_INVESTOR_TYPES:
        net_values = []
        for record in data:
            val = record.get(investor_type)
            if val is not None:
                net_values.append(val)

        if not net_values:
            components[investor_type] = _empty_component()
            sub_scores.append(0.0)
            continue

        net_total = sum(net_values)
        buy_days = sum(1 for v in net_values if v > 0)
        sell_days = sum(1 for v in net_values if v < 0)
        active_days = len(net_values)

        # Consistency: ratio of buy days to total active days
        consistency = buy_days / active_days if active_days > 0 else 0.0

        # Intensity: net buying pressure relative to market trading volume
        if avg_daily_trading_value and avg_daily_trading_value > 0:
            avg_net = abs(net_total) / active_days if active_days > 0 else 0
            intensity = min(avg_net / avg_daily_trading_value, 1.0)
        else:
            # Fallback: use consistency-only scoring
            intensity = consistency * 0.5

        # Sub-score: weighted combination
        sub_score = consistency * 60 + min(intensity * 40, 40)

        components[investor_type] = {
            "net_total": net_total,
            "buy_days": buy_days,
            "sell_days": sell_days,
            "neutral_days": active_days - buy_days - sell_days,
            "consistency": round(consistency, 4),
            "intensity": round(intensity, 4),
            "score": round(sub_score, 2),
        }
        sub_scores.append(sub_score)

    # Composite score: max * 0.5 + avg * 0.5 (only over types with data)
    active_scores = [
        sub_scores[i]
        for i, t in enumerate(WHALE_INVESTOR_TYPES)
        if components[t]["buy_days"] + components[t]["sell_days"] > 0
    ]
    if active_scores:
        max_score = max(active_scores)
        avg_score = sum(active_scores) / len(active_scores)
        whale_score = max_score * 0.5 + avg_score * 0.5
    else:
        whale_score = 0.0

    # Determine signal
    signal = _classify_signal(whale_score, components)

    return {
        "whale_score": round(whale_score, 2),
        "components": components,
        "signal": signal,
        "signal_label": _signal_label(signal),
        "lookback_days": total_days,
    }


def _classify_signal(whale_score: float, components: dict) -> str:
    """Classify the overall whale signal."""
    # Check if net is negative across all investors
    total_net = sum(c.get("net_total", 0) for c in components.values() if isinstance(c, dict))

    if whale_score >= 70:
        return "strong_accumulation"
    elif whale_score >= 50:
        return "mild_accumulation"
    elif whale_score >= 30:
        return "neutral"
    else:
        if total_net < 0:
            return "distribution"
        return "neutral"


def _signal_label(signal: str) -> str:
    """Korean label for whale signal."""
    labels = {
        "strong_accumulation": "강한 매집",
        "mild_accumulation": "완만한 매집",
        "neutral": "중립",
        "distribution": "매도 우위",
    }
    return labels.get(signal, "알 수 없음")


def _empty_whale_result() -> dict[str, Any]:
    return {
        "whale_score": 0.0,
        "components": {t: _empty_component() for t in WHALE_INVESTOR_TYPES},
        "signal": "neutral",
        "signal_label": "중립",
        "lookback_days": 0,
    }


def _empty_component() -> dict[str, Any]:
    return {
        "net_total": 0,
        "buy_days": 0,
        "sell_days": 0,
        "neutral_days": 0,
        "consistency": 0.0,
        "intensity": 0.0,
        "score": 0.0,
    }
