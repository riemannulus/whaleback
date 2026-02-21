"""Sector-level whale flow analysis.

Aggregates investor trading data by sector to detect sector-level
accumulation/distribution patterns across whale investor types.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

WHALE_TYPES = ["institution_net", "foreign_net", "pension_net", "private_equity_net", "other_corp_net"]

WHALE_TYPE_LABELS = {
    "institution_net": "기관",
    "foreign_net": "외국인",
    "pension_net": "연기금",
    "private_equity_net": "사모펀드",
    "other_corp_net": "기타법인",
}


def compute_sector_flows(
    sector_map: dict[str, str],
    investor_data: dict[str, list[dict[str, Any]]],
    trading_values: dict[str, float],
    lookback_days: int = 20,
) -> list[dict[str, Any]]:
    """Compute sector-level whale flow metrics.

    Groups tickers by sector, then for each (sector, investor_type) pair:
      - net_purchase: sum of net flows across tickers in sector
      - intensity: |net_purchase| / sector total trading value
      - consistency: days with sector-net-buy / total days
      - signal: strong_accumulation / mild_accumulation / neutral / distribution
      - trend_5d/trend_20d: recent vs full period momentum comparison

    Args:
        sector_map: {ticker: sector_name}
        investor_data: {ticker: [{trade_date, institution_net, foreign_net, ...}]}
        trading_values: {ticker: avg_daily_trading_value}
        lookback_days: Analysis window in trading days.

    Returns:
        List of dicts, one per (sector, investor_type) combination.
    """
    # Group tickers by sector
    sector_tickers: dict[str, list[str]] = {}
    for ticker, sector in sector_map.items():
        if sector and ticker in investor_data:
            sector_tickers.setdefault(sector, []).append(ticker)

    results = []

    for sector, tickers in sector_tickers.items():
        stock_count = len(tickers)
        if stock_count == 0:
            continue

        # Aggregate sector trading value
        sector_trading_value = sum(trading_values.get(t, 0) for t in tickers)

        for whale_type in WHALE_TYPES:
            # Aggregate daily net flows across all tickers in sector
            daily_sector_flows: dict[str, int] = {}  # date -> total net

            for ticker in tickers:
                rows = investor_data.get(ticker, [])
                recent = sorted(rows, key=lambda x: x.get("trade_date", ""))[-lookback_days:]
                for row in recent:
                    d = str(row.get("trade_date", ""))
                    val = row.get(whale_type)
                    if val is not None:
                        daily_sector_flows[d] = daily_sector_flows.get(d, 0) + val

            if not daily_sector_flows:
                results.append(_empty_sector_flow(sector, whale_type, stock_count))
                continue

            dates_sorted = sorted(daily_sector_flows.keys())
            flows = [daily_sector_flows[d] for d in dates_sorted]
            total_days = len(flows)

            net_purchase = sum(flows)
            buy_days = sum(1 for f in flows if f > 0)
            consistency = buy_days / total_days if total_days > 0 else 0.0

            # Intensity
            if sector_trading_value > 0 and total_days > 0:
                avg_daily_net = abs(net_purchase) / total_days
                intensity = min(avg_daily_net / sector_trading_value, 1.0)
            else:
                intensity = 0.0

            # Signal
            signal = _classify_flow_signal(consistency, intensity, net_purchase)

            # Trend: last 5 days vs full period
            trend_5d = sum(flows[-5:]) if len(flows) >= 5 else net_purchase
            trend_20d = net_purchase

            results.append({
                "sector": sector,
                "investor_type": whale_type,
                "net_purchase": net_purchase,
                "intensity": round(intensity, 4),
                "consistency": round(consistency, 2),
                "signal": signal,
                "trend_5d": trend_5d,
                "trend_20d": trend_20d,
                "stock_count": stock_count,
            })

    return results


def _classify_flow_signal(consistency: float, intensity: float, net_purchase: int) -> str:
    """Classify sector flow into signal categories."""
    if net_purchase > 0 and consistency >= 0.7 and intensity >= 0.3:
        return "strong_accumulation"
    elif net_purchase > 0 and consistency >= 0.5:
        return "mild_accumulation"
    elif net_purchase < 0 and consistency <= 0.3:
        return "distribution"
    return "neutral"


def _empty_sector_flow(sector: str, investor_type: str, stock_count: int) -> dict[str, Any]:
    return {
        "sector": sector,
        "investor_type": investor_type,
        "net_purchase": 0,
        "intensity": 0.0,
        "consistency": 0.0,
        "signal": "neutral",
        "trend_5d": 0,
        "trend_20d": 0,
        "stock_count": stock_count,
    }
