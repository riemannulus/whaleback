"""Heston stochastic volatility model simulation.

Two coupled SDEs with Euler-Maruyama discretisation:
  dS = μ·S·dt + √V·S·dW₁
  dV = κ(θ − V)dt + ξ√V·dW₂
  corr(W₁, W₂) = ρ
"""

import logging

import numpy as np

from . import ModelResult
from .gbm import _compute_horizon_stats

logger = logging.getLogger(__name__)

TRADING_DAYS_PER_YEAR = 252


def simulate_heston(
    log_returns: np.ndarray,
    base_price: int,
    num_simulations: int,
    horizons: tuple[int, ...],
    rng: np.random.Generator,
    kappa: float = 2.0,
    theta: float = 0.04,
    xi: float = 0.3,
    rho: float = -0.7,
    drift_adj_annual: float = 0.0,
    theta_mult: float = 1.0,
    v0_mult: float = 1.0,
    rho_adj: float = 0.0,
) -> ModelResult | None:
    """Run Heston stochastic volatility simulation.

    Args:
        log_returns: Daily log returns for drift estimation.
        base_price: Starting price.
        num_simulations: Number of paths.
        horizons: Forward horizons in trading days.
        rng: Random generator.
        kappa: Mean reversion speed.
        theta: Long-run variance level.
        xi: Vol-of-vol.
        rho: Correlation between price and variance Brownian motions.
        drift_adj_annual: Additive annual drift adjustment (sentiment).
        theta_mult: Multiplicative scaling for long-run variance (sentiment).
        v0_mult: Multiplicative scaling for initial variance (sentiment).
        rho_adj: Additive adjustment for price-variance correlation (sentiment).
    """
    if len(log_returns) < 30:
        logger.debug("Heston: insufficient data")
        return None

    # Validate parameters
    rho = max(-1.0, min(1.0, rho))  # clamp to valid correlation range
    rho = max(-0.99, min(0.99, rho + rho_adj))

    if 2 * kappa * theta <= xi**2:
        logger.warning(
            "Heston: Feller condition violated (2κθ=%.4f ≤ ξ²=%.4f). "
            "Variance may hit zero; full truncation will handle it.",
            2 * kappa * theta, xi**2,
        )

    # Apply theta multiplier after Feller condition check
    theta *= theta_mult

    # Annualise drift and variance so all parameters are on the same scale
    daily_mu = float(np.mean(log_returns))
    daily_sigma = float(np.std(log_returns, ddof=1))
    dt = 1.0 / TRADING_DAYS_PER_YEAR

    # Recover arithmetic drift from sample log returns (undo implicit Ito correction).
    # Then use it with the stochastic variance V_t for the correct single Ito correction.
    # E[log_ret] = (μ_arith − ½σ²_hist)·dt  →  μ_arith = (daily_mu + ½σ²_hist) × 252
    mu_arith_annual = (daily_mu + 0.5 * daily_sigma**2) * TRADING_DAYS_PER_YEAR
    mu_arith_annual += drift_adj_annual

    # Initial variance: annualise daily variance to match theta scale
    recent_var = float(np.var(log_returns[-20:], ddof=1)) if len(log_returns) >= 20 else float(np.var(log_returns, ddof=1))
    v0 = max(recent_var * TRADING_DAYS_PER_YEAR, 1e-8)
    v0 *= v0_mult

    max_horizon = max(horizons)

    # Pre-generate all random numbers
    z1 = rng.standard_normal((num_simulations, max_horizon))
    z_indep = rng.standard_normal((num_simulations, max_horizon))
    z2 = rho * z1 + np.sqrt(1 - rho**2) * z_indep  # correlated

    # Euler-Maruyama simulation
    log_s = np.zeros((num_simulations, max_horizon + 1))
    v = np.zeros((num_simulations, max_horizon + 1))
    v[:, 0] = v0

    for t in range(max_horizon):
        v_pos = np.maximum(v[:, t], 0)  # full truncation
        sqrt_v = np.sqrt(v_pos)

        # Price process (log space) — arithmetic drift with stochastic Ito correction
        log_s[:, t + 1] = log_s[:, t] + (mu_arith_annual - 0.5 * v_pos) * dt + sqrt_v * np.sqrt(dt) * z1[:, t]

        # Variance process
        v[:, t + 1] = v[:, t] + kappa * (theta - v_pos) * dt + xi * sqrt_v * np.sqrt(dt) * z2[:, t]

    terminal_prices: dict[int, np.ndarray] = {}
    horizons_result = {}

    for h in horizons:
        terminal = base_price * np.exp(log_s[:, h])

        # Cap extreme values
        terminal = np.clip(terminal, base_price * 0.001, base_price * 100)

        terminal_prices[h] = terminal
        horizons_result[h] = _compute_horizon_stats(terminal, base_price, h)

    return ModelResult(
        model="heston",
        terminal_prices=terminal_prices,
        horizons=horizons_result,
    )
