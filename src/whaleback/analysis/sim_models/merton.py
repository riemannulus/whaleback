"""Merton jump-diffusion model simulation.

GBM + Poisson jump process:
  dS/S = (μ − λk)dt + σdW + JdN
  N ~ Poisson(λ·dt), J ~ LogNormal(μ_j, σ_j)
"""

import logging

import numpy as np

from . import ModelResult
from .gbm import _compute_horizon_stats

logger = logging.getLogger(__name__)

TRADING_DAYS_PER_YEAR = 252


def simulate_merton(
    log_returns: np.ndarray,
    base_price: int,
    num_simulations: int,
    horizons: tuple[int, ...],
    rng: np.random.Generator,
    lam: float = 0.1,
    mu_j: float = -0.02,
    sigma_j: float = 0.05,
    max_sigma: float = 1.50,
) -> ModelResult | None:
    """Run Merton jump-diffusion simulation.

    Args:
        log_returns: Daily log returns.
        base_price: Starting price.
        num_simulations: Number of paths.
        horizons: Forward horizons in trading days.
        rng: Random generator.
        lam: Annual jump intensity (expected jumps per year).
        mu_j: Mean jump size (log scale).
        sigma_j: Jump size volatility.
        max_sigma: Cap on annualised volatility.
    """
    if len(log_returns) < 30:
        logger.debug("Merton: insufficient data")
        return None

    daily_mu = float(np.mean(log_returns))
    daily_sigma_orig = float(np.std(log_returns, ddof=1))

    sigma = daily_sigma_orig * np.sqrt(TRADING_DAYS_PER_YEAR)
    if sigma > max_sigma:
        sigma = max_sigma
    daily_sigma = sigma / np.sqrt(TRADING_DAYS_PER_YEAR)

    if daily_sigma == 0.0:
        return None

    # Recover arithmetic drift from sample log returns (undo implicit Ito correction).
    # E[log_ret] = (μ_arith − ½σ²_hist)·dt  →  μ_arith_daily = daily_mu + ½σ²_hist
    mu_arith_daily = daily_mu + 0.5 * daily_sigma_orig**2

    # Daily jump intensity
    lam_daily = lam / TRADING_DAYS_PER_YEAR

    # Drift compensation for jump component
    # k = E[J - 1] = exp(mu_j + sigma_j^2/2) - 1
    k = np.exp(mu_j + 0.5 * sigma_j**2) - 1
    drift_comp = mu_arith_daily - lam_daily * k

    max_horizon = max(horizons)

    # Pre-generate diffusion component
    z = rng.standard_normal((num_simulations, max_horizon))

    # Pre-generate jump component
    n_jumps = rng.poisson(lam_daily, (num_simulations, max_horizon))
    jump_sizes = np.zeros((num_simulations, max_horizon))

    # For each cell with jumps > 0, sample jump magnitudes
    mask = n_jumps > 0
    total_jumps = int(n_jumps[mask].sum())
    if total_jumps > 0:
        # Sample all jump sizes at once, then assign
        all_jumps = rng.normal(mu_j, sigma_j, total_jumps)

        idx = 0
        rows, cols = np.where(mask)
        for r, c in zip(rows, cols):
            nj = n_jumps[r, c]
            jump_sizes[r, c] = np.sum(all_jumps[idx:idx + nj])
            idx += nj

    # Daily log returns: drift + diffusion + jumps
    daily_log_ret = (drift_comp - 0.5 * daily_sigma**2) + daily_sigma * z + jump_sizes

    # Cumulative
    cumulative = np.cumsum(daily_log_ret, axis=1)

    terminal_prices: dict[int, np.ndarray] = {}
    horizons_result = {}

    for h in horizons:
        terminal = base_price * np.exp(cumulative[:, h - 1])

        # Cap extreme values
        terminal = np.clip(terminal, base_price * 0.001, base_price * 100)

        terminal_prices[h] = terminal
        horizons_result[h] = _compute_horizon_stats(terminal, base_price, h)

    return ModelResult(
        model="merton",
        terminal_prices=terminal_prices,
        horizons=horizons_result,
    )
