"""Geometric Brownian Motion (constant volatility) simulation."""

import logging

import numpy as np

from . import HorizonStats, ModelResult

logger = logging.getLogger(__name__)

TRADING_DAYS_PER_YEAR = 252
MAX_DAILY_MU = 1.0 / TRADING_DAYS_PER_YEAR  # Cap annual drift at ±100%

HORIZON_LABELS = {
    21: "1개월",
    63: "3개월",
    126: "6개월",
    252: "1년",
}


def simulate_gbm(
    log_returns: np.ndarray,
    base_price: int,
    num_simulations: int,
    horizons: tuple[int, ...],
    rng: np.random.Generator,
    max_sigma: float = 1.50,
    drift_adj_daily: float = 0.0,
    vol_multiplier: float = 1.0,
) -> ModelResult | None:
    """Run GBM simulation and return terminal prices + per-horizon stats.

    Args:
        log_returns: Array of daily log returns.
        base_price: Starting price for simulation.
        num_simulations: Number of Monte Carlo paths.
        horizons: Tuple of forward horizons in trading days.
        rng: NumPy random generator for reproducibility.
        max_sigma: Cap on annualised volatility.
        drift_adj_daily: Additive daily drift adjustment (sentiment).
        vol_multiplier: Multiplicative volatility scaling (sentiment).

    Returns:
        ModelResult with terminal prices and horizon statistics, or None.
    """
    daily_mu = float(np.mean(log_returns))
    daily_sigma = float(np.std(log_returns, ddof=1))

    sigma = daily_sigma * np.sqrt(TRADING_DAYS_PER_YEAR)

    if sigma > max_sigma:
        logger.debug("GBM: capping sigma from %.4f to %.4f", sigma, max_sigma)
        sigma = max_sigma

    if sigma == 0.0:
        logger.debug("GBM: zero volatility, skipping")
        return None

    daily_vol = sigma / np.sqrt(TRADING_DAYS_PER_YEAR)

    # Recover arithmetic drift from sample log returns (undo implicit Ito),
    # then re-apply Ito with (possibly capped) volatility for a consistent pair.
    # E[log_ret] = (μ_arith − ½σ²_hist)·dt  →  μ_arith_daily = daily_mu + ½σ²_hist
    mu_arith_daily = daily_mu + 0.5 * daily_sigma**2
    mu_arith_daily = float(np.clip(mu_arith_daily, -MAX_DAILY_MU, MAX_DAILY_MU))
    mu_arith_daily += drift_adj_daily
    mu_arith_daily = float(np.clip(mu_arith_daily, -MAX_DAILY_MU * 2, MAX_DAILY_MU * 2))
    daily_vol *= vol_multiplier
    max_daily_vol = max_sigma / np.sqrt(TRADING_DAYS_PER_YEAR)
    daily_vol = min(daily_vol, max_daily_vol)
    daily_drift = mu_arith_daily - 0.5 * daily_vol**2

    terminal_prices: dict[int, np.ndarray] = {}
    horizons_result: dict[int, HorizonStats] = {}

    for h in horizons:
        z = rng.standard_normal((num_simulations, h))
        daily_log_ret = daily_drift + daily_vol * z
        cumulative = np.cumsum(daily_log_ret, axis=1)
        terminal = base_price * np.exp(cumulative[:, -1])

        # Cap extreme values (consistent with other models)
        terminal = np.clip(terminal, base_price * 0.001, base_price * 100)

        terminal_prices[h] = terminal
        horizons_result[h] = _compute_horizon_stats(terminal, base_price, h)

    return ModelResult(
        model="gbm",
        terminal_prices=terminal_prices,
        horizons=horizons_result,
    )


def _compute_horizon_stats(
    terminal: np.ndarray, base_price: int, h: int
) -> HorizonStats:
    """Compute percentile stats from terminal price distribution."""
    label = HORIZON_LABELS.get(h, f"{h}일")
    return HorizonStats(
        label=label,
        p5=int(np.percentile(terminal, 5)),
        p25=int(np.percentile(terminal, 25)),
        p50=int(np.percentile(terminal, 50)),
        p75=int(np.percentile(terminal, 75)),
        p95=int(np.percentile(terminal, 95)),
        expected_return_pct=round(float((np.mean(terminal) / base_price - 1) * 100), 2),
        var_5pct_pct=round(float((np.percentile(terminal, 5) / base_price - 1) * 100), 2),
        upside_prob=round(float(np.mean(terminal > base_price)), 4),
    )
