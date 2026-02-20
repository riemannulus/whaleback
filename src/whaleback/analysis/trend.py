"""Trend and sector rotation analysis module.

Pure computation functions for relative strength and sector rotation.
No database dependency - operates on price series passed as arguments.
"""

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


def compute_relative_strength(
    stock_prices: list[float],
    index_prices: list[float],
    dates: list[str] | None = None,
) -> dict[str, Any]:
    """Compute relative strength of a stock vs benchmark index.

    RS ratio = (stock_price / stock_price_base) / (index_price / index_price_base)
    Both indexed to 100 at the start of the period.

    Args:
        stock_prices: List of closing prices (chronological order, oldest first)
        index_prices: List of index closing values (same order and length)
        dates: Optional list of date strings for the series

    Returns:
        {current_rs, rs_change_pct, series: [{date, stock_indexed, index_indexed, rs_ratio}]}
    """
    if not stock_prices or not index_prices:
        return {"current_rs": None, "rs_change_pct": None, "series": []}

    if len(stock_prices) != len(index_prices):
        # Trim to matching length
        min_len = min(len(stock_prices), len(index_prices))
        stock_prices = stock_prices[-min_len:]
        index_prices = index_prices[-min_len:]
        if dates:
            dates = dates[-min_len:]

    if len(stock_prices) < 2:
        return {"current_rs": None, "rs_change_pct": None, "series": []}

    # Base values (first period)
    stock_base = stock_prices[0]
    index_base = index_prices[0]

    if stock_base <= 0 or index_base <= 0:
        return {"current_rs": None, "rs_change_pct": None, "series": []}

    series = []
    for i, (sp, ip) in enumerate(zip(stock_prices, index_prices)):
        stock_indexed = (sp / stock_base) * 100.0
        index_indexed = (ip / index_base) * 100.0
        rs_ratio = stock_indexed / index_indexed if index_indexed > 0 else None

        entry = {
            "stock_indexed": round(stock_indexed, 2),
            "index_indexed": round(index_indexed, 2),
            "rs_ratio": round(rs_ratio, 4) if rs_ratio else None,
        }
        if dates and i < len(dates):
            entry["date"] = dates[i]
        series.append(entry)

    current_rs = series[-1]["rs_ratio"] if series else None
    first_rs = series[0]["rs_ratio"] if series else None

    rs_change_pct = None
    if current_rs and first_rs and first_rs > 0:
        rs_change_pct = round((current_rs - first_rs) / first_rs * 100, 2)

    return {
        "current_rs": current_rs,
        "rs_change_pct": rs_change_pct,
        "series": series,
    }


def compute_rs_percentile(
    ticker_rs: float | None,
    all_rs_values: list[float],
) -> int | None:
    """Compute the percentile rank of a stock's RS among all stocks.

    Returns 0-100 percentile (100 = strongest relative performer).
    """
    if ticker_rs is None or not all_rs_values:
        return None

    # Filter valid values
    valid = [v for v in all_rs_values if v is not None]
    if not valid:
        return None

    # Rank: count how many are below
    below = sum(1 for v in valid if v < ticker_rs)
    percentile = int(round(below / len(valid) * 100))
    return min(percentile, 100)


def compute_sector_rotation(
    sectors: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Classify sectors into rotation quadrants.

    Quadrants based on momentum (RS change) and level (RS ratio):
      - leading: high RS + improving momentum
      - weakening: high RS + declining momentum
      - lagging: low RS + declining momentum
      - improving: low RS + improving momentum

    Args:
        sectors: List of {sector, avg_rs_20d, avg_rs_change, stock_count}

    Returns:
        Same list with added 'quadrant' field
    """
    if not sectors:
        return []

    # Compute medians for quadrant boundaries
    rs_values = [s.get("avg_rs_20d") for s in sectors if s.get("avg_rs_20d") is not None]
    change_values = [s.get("avg_rs_change") for s in sectors if s.get("avg_rs_change") is not None]

    if not rs_values or not change_values:
        return [{**s, "quadrant": "neutral"} for s in sectors]

    rs_median = float(np.median(rs_values))
    change_median = float(np.median(change_values))

    results = []
    for sector in sectors:
        rs = sector.get("avg_rs_20d")
        change = sector.get("avg_rs_change")

        if rs is None or change is None:
            quadrant = "neutral"
        elif rs >= rs_median and change >= change_median:
            quadrant = "leading"
        elif rs >= rs_median and change < change_median:
            quadrant = "weakening"
        elif rs < rs_median and change < change_median:
            quadrant = "lagging"
        else:
            quadrant = "improving"

        results.append({**sector, "quadrant": quadrant})

    return results


def compute_sector_ranking(
    sector_data: dict[str, list[dict[str, Any]]],
    index_prices: list[float],
    period: int = 20,
) -> list[dict[str, Any]]:
    """Rank sectors by average relative strength performance.

    Args:
        sector_data: {sector_name: [{ticker, prices: [float], volume: int}]}
        index_prices: Benchmark index prices for the period
        period: Lookback period in trading days

    Returns:
        Sorted list of {sector, stock_count, avg_change_rate, avg_rs, momentum_rank, quadrant}
    """
    if not sector_data or not index_prices:
        return []

    rankings = []

    for sector_name, stocks in sector_data.items():
        if not stocks:
            continue

        rs_values = []
        change_rates = []

        for stock in stocks:
            prices = stock.get("prices", [])
            if len(prices) >= 2:
                # Price change rate
                change = (prices[-1] - prices[0]) / prices[0] * 100 if prices[0] > 0 else 0
                change_rates.append(change)

                # RS vs index
                rs_result = compute_relative_strength(prices, index_prices[-len(prices) :])
                if rs_result["current_rs"] is not None:
                    rs_values.append(rs_result["current_rs"])

        if not change_rates:
            continue

        avg_change = float(np.mean(change_rates))
        median_change = float(np.median(change_rates))
        avg_rs = float(np.mean(rs_values)) if rs_values else None

        # Find top performer
        top_stock = None
        if stocks:
            best = max(
                stocks,
                key=lambda s: (s.get("prices", [0])[-1] / s.get("prices", [1])[0] * 100 - 100)
                if len(s.get("prices", [])) >= 2 and s.get("prices", [1])[0] > 0
                else -999,
            )
            if best.get("prices") and len(best["prices"]) >= 2 and best["prices"][0] > 0:
                top_stock = {
                    "ticker": best.get("ticker"),
                    "name": best.get("name"),
                    "change_rate": round((best["prices"][-1] / best["prices"][0] - 1) * 100, 2),
                }

        rankings.append(
            {
                "sector": sector_name,
                "stock_count": len(stocks),
                "avg_change_rate": round(avg_change, 2),
                "median_change_rate": round(median_change, 2),
                "avg_rs": round(avg_rs, 4) if avg_rs else None,
                "top_performer": top_stock,
            }
        )

    # Sort by avg_change_rate descending
    rankings.sort(key=lambda x: x["avg_change_rate"], reverse=True)

    # Assign momentum rank
    for i, r in enumerate(rankings):
        r["momentum_rank"] = i + 1

    return rankings
