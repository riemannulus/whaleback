"""Risk and volatility analysis module.

Pure computation functions for risk metrics including volatility, beta, and drawdown.
No database dependency - operates on price series passed as arguments.
"""

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


def compute_volatility(
    prices: list[float],
    periods: tuple[int, ...] = (20, 60, 252),
) -> dict[str, Any]:
    """Compute annualized volatility for multiple periods.

    Calculates daily return volatility and annualizes using sqrt(252) convention.
    Provides risk classification based on 60-day volatility.

    Args:
        prices: List of closing prices (chronological order, oldest first)
        periods: Tuple of lookback periods in trading days (default: 20d, 60d, 1y)

    Returns:
        {
            volatility_20d: float | None,
            volatility_60d: float | None,
            volatility_1y: float | None,
            risk_level: str,
            risk_label: str (Korean)
        }
    """
    if not prices or len(prices) < 2:
        return {
            "volatility_20d": None,
            "volatility_60d": None,
            "volatility_1y": None,
            "risk_level": "unknown",
            "risk_label": "알 수 없음",
        }

    # Compute daily returns
    returns = []
    for i in range(1, len(prices)):
        if prices[i - 1] > 0:
            daily_return = (prices[i] - prices[i - 1]) / prices[i - 1]
            returns.append(daily_return)

    if not returns:
        return {
            "volatility_20d": None,
            "volatility_60d": None,
            "volatility_1y": None,
            "risk_level": "unknown",
            "risk_label": "알 수 없음",
        }

    result = {}

    # Compute volatility for each period
    period_keys = {20: "volatility_20d", 60: "volatility_60d", 252: "volatility_1y"}

    for period in periods:
        key = period_keys.get(period, f"volatility_{period}d")

        if len(returns) >= period:
            period_returns = returns[-period:]
            vol_std = float(np.std(period_returns, ddof=1))
            # Annualize: std * sqrt(252) * 100 for percentage
            annualized_vol = round(vol_std * np.sqrt(252) * 100, 4)
            result[key] = annualized_vol
        else:
            result[key] = None

    # Risk classification based on 60-day volatility
    vol_60d = result.get("volatility_60d")

    if vol_60d is None:
        risk_level = "unknown"
        risk_label = "알 수 없음"
    elif vol_60d < 20:
        risk_level = "low"
        risk_label = "저변동"
    elif vol_60d < 40:
        risk_level = "medium"
        risk_label = "보통"
    elif vol_60d < 60:
        risk_level = "high"
        risk_label = "고변동"
    else:
        risk_level = "very_high"
        risk_label = "초고변동"

    result["risk_level"] = risk_level
    result["risk_label"] = risk_label

    return result


def compute_beta(
    stock_prices: list[float],
    index_prices: list[float],
    periods: tuple[int, ...] = (60, 252),
) -> dict[str, Any]:
    """Compute beta (market sensitivity) for multiple periods.

    Beta = Cov(stock_returns, market_returns) / Var(market_returns)
    Measures systematic risk relative to market benchmark.

    Args:
        stock_prices: List of stock closing prices (chronological, oldest first)
        index_prices: List of index closing values (same order and length)
        periods: Tuple of lookback periods in trading days (default: 60d, 252d)

    Returns:
        {
            beta_60d: float | None,
            beta_252d: float | None,
            interpretation: str,
            interpretation_label: str (Korean)
        }
    """
    if not stock_prices or not index_prices:
        return {
            "beta_60d": None,
            "beta_252d": None,
            "interpretation": "unknown",
            "interpretation_label": "알 수 없음",
        }

    if len(stock_prices) != len(index_prices):
        # Trim to matching length
        min_len = min(len(stock_prices), len(index_prices))
        stock_prices = stock_prices[-min_len:]
        index_prices = index_prices[-min_len:]

    if len(stock_prices) < 2:
        return {
            "beta_60d": None,
            "beta_252d": None,
            "interpretation": "unknown",
            "interpretation_label": "알 수 없음",
        }

    # Compute returns for both series
    stock_returns = []
    index_returns = []

    for i in range(1, len(stock_prices)):
        if stock_prices[i - 1] > 0 and index_prices[i - 1] > 0:
            stock_ret = (stock_prices[i] - stock_prices[i - 1]) / stock_prices[i - 1]
            index_ret = (index_prices[i] - index_prices[i - 1]) / index_prices[i - 1]
            stock_returns.append(stock_ret)
            index_returns.append(index_ret)

    if not stock_returns or not index_returns:
        return {
            "beta_60d": None,
            "beta_252d": None,
            "interpretation": "unknown",
            "interpretation_label": "알 수 없음",
        }

    result = {}
    period_keys = {60: "beta_60d", 252: "beta_252d"}

    # Compute beta for each period
    for period in periods:
        key = period_keys.get(period, f"beta_{period}d")

        if len(stock_returns) >= period:
            stock_ret_period = stock_returns[-period:]
            market_ret_period = index_returns[-period:]

            market_var = float(np.var(market_ret_period, ddof=1))

            if market_var > 0:
                cov_matrix = np.cov(stock_ret_period, market_ret_period)
                beta = round(float(cov_matrix[0, 1] / market_var), 4)
                result[key] = beta
            else:
                result[key] = None
        else:
            result[key] = None

    # Interpretation based on 60-day beta
    beta_60d = result.get("beta_60d")

    if beta_60d is None:
        interpretation = "unknown"
        interpretation_label = "알 수 없음"
    elif beta_60d < 0.8:
        interpretation = "defensive"
        interpretation_label = "방어적"
    elif beta_60d < 1.2:
        interpretation = "neutral"
        interpretation_label = "중립"
    elif beta_60d < 1.5:
        interpretation = "aggressive"
        interpretation_label = "공격적"
    else:
        interpretation = "highly_aggressive"
        interpretation_label = "초공격적"

    result["interpretation"] = interpretation
    result["interpretation_label"] = interpretation_label

    return result


def compute_max_drawdown(
    prices: list[float],
    periods: tuple[int, ...] = (60, 252),
) -> dict[str, Any]:
    """Compute maximum drawdown (peak-to-trough decline) for multiple periods.

    MDD = max((price - running_peak) / running_peak) over period
    Measures worst peak-to-trough loss an investor would have experienced.

    Args:
        prices: List of closing prices (chronological order, oldest first)
        periods: Tuple of lookback periods in trading days (default: 60d, 252d)

    Returns:
        {
            mdd_60d: float | None,
            mdd_1y: float | None,
            current_drawdown: float | None,
            recovery_label: str (Korean)
        }
    """
    if not prices or len(prices) < 2:
        return {
            "mdd_60d": None,
            "mdd_1y": None,
            "current_drawdown": None,
            "recovery_label": "알 수 없음",
        }

    result = {}
    period_keys = {60: "mdd_60d", 252: "mdd_1y"}

    # Compute MDD for each period
    for period in periods:
        key = period_keys.get(period, f"mdd_{period}d")

        if len(prices) >= period:
            subset = prices[-period:]

            # Track running peak and compute drawdowns
            running_max = []
            for i in range(len(subset)):
                running_max.append(max(subset[: i + 1]))

            drawdowns = []
            for i in range(len(subset)):
                if running_max[i] > 0:
                    dd = (subset[i] - running_max[i]) / running_max[i]
                    drawdowns.append(dd)

            if drawdowns:
                mdd = round(float(min(drawdowns)), 4)
                result[key] = mdd
            else:
                result[key] = None
        else:
            result[key] = None

    # Current drawdown from all-time high
    current_price = prices[-1]
    all_time_high = max(prices)

    if all_time_high > 0:
        current_dd = round((current_price - all_time_high) / all_time_high, 4)
        result["current_drawdown"] = current_dd

        # Recovery label
        if current_dd > -0.05:
            recovery_label = "회복"
        elif current_dd > -0.15:
            recovery_label = "조정 중"
        else:
            recovery_label = "하락 지속"
    else:
        result["current_drawdown"] = None
        recovery_label = "알 수 없음"

    result["recovery_label"] = recovery_label

    return result
