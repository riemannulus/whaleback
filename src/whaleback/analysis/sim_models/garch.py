"""GARCH(1,1) time-varying volatility simulation.

Three-stage fallback: GARCH fit → EWMA(λ=0.94) → constant σ.
"""

import logging
import warnings

import numpy as np

from . import ModelResult
from .gbm import _compute_horizon_stats

logger = logging.getLogger(__name__)

TRADING_DAYS_PER_YEAR = 252
MAX_DAILY_MU = 1.0 / TRADING_DAYS_PER_YEAR  # Cap annual drift at ±100%


def simulate_garch(
    log_returns: np.ndarray,
    base_price: int,
    num_simulations: int,
    horizons: tuple[int, ...],
    rng: np.random.Generator,
    p: int = 1,
    q: int = 1,
    max_sigma: float = 1.50,
    drift_adj_daily: float = 0.0,
    var_multiplier: float = 1.0,
) -> ModelResult | None:
    """Run GARCH(1,1) simulation with time-varying volatility paths.

    Fallback chain: GARCH → EWMA → constant σ.
    """
    if len(log_returns) < 30:
        logger.debug("GARCH: insufficient data (%d returns)", len(log_returns))
        return None

    daily_mu = float(np.mean(log_returns))
    daily_sigma_hist = float(np.std(log_returns, ddof=1))

    # Recover arithmetic drift from sample log returns (undo implicit Ito correction).
    # E[log_ret] = (μ_arith − ½σ²_hist)·dt  →  μ_arith_daily = daily_mu + ½σ²_hist
    mu_arith_daily = daily_mu + 0.5 * daily_sigma_hist**2
    mu_arith_daily = float(np.clip(mu_arith_daily, -MAX_DAILY_MU, MAX_DAILY_MU))
    mu_arith_daily += drift_adj_daily

    max_daily_sigma = max_sigma / np.sqrt(TRADING_DAYS_PER_YEAR)
    max_horizon = max(horizons)

    # Stage 1: Try GARCH fit
    forecast_variance = _fit_garch(log_returns, p, q, max_horizon)

    if forecast_variance is None:
        # Stage 2: Mean-reverting exponential smoothing fallback
        forecast_variance = _mean_reverting_variance(log_returns, max_horizon, lam=0.94)
        logger.debug("GARCH: fell back to EWMA")

    if forecast_variance is None:
        # Stage 3: constant sigma fallback
        daily_sigma = float(np.std(log_returns, ddof=1))
        if daily_sigma == 0.0:
            return None
        forecast_variance = np.full(max_horizon, daily_sigma**2)
        logger.debug("GARCH: fell back to constant sigma")

    # Apply variance multiplier before capping
    forecast_variance = forecast_variance * var_multiplier

    # Cap variance
    max_var = max_daily_sigma**2
    forecast_variance = np.clip(forecast_variance, 1e-10, max_var)

    terminal_prices: dict[int, np.ndarray] = {}
    horizons_result = {}

    for h in horizons:
        # NOTE: All paths share the same GARCH-forecasted volatility trajectory.
        # In a full GARCH simulation, each path would evolve its own variance.
        # This produces lighter tails than a path-dependent approach but is
        # acceptable for screening/scoring purposes.
        sigma_path = np.sqrt(forecast_variance[:h])  # (h,)

        # Broadcast: (num_simulations, h)
        z = rng.standard_normal((num_simulations, h))
        # Use arithmetic drift with time-varying Ito correction from GARCH volatility
        daily_log_ret = (mu_arith_daily - 0.5 * sigma_path**2) + sigma_path * z

        cumulative = np.cumsum(daily_log_ret, axis=1)
        terminal = base_price * np.exp(cumulative[:, -1])

        # Cap extreme values
        terminal = np.clip(terminal, base_price * 0.001, base_price * 100)

        terminal_prices[h] = terminal
        horizons_result[h] = _compute_horizon_stats(terminal, base_price, h)

    return ModelResult(
        model="garch",
        terminal_prices=terminal_prices,
        horizons=horizons_result,
    )


def _fit_garch(
    log_returns: np.ndarray, p: int, q: int, max_horizon: int
) -> np.ndarray | None:
    """Fit GARCH(p,q) and return forecasted variance path."""
    try:
        from arch import arch_model

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            scaled_returns = log_returns * 100  # arch expects percentage returns
            model = arch_model(scaled_returns, vol="Garch", p=p, q=q, mean="Constant", dist="normal")
            result = model.fit(disp="off", show_warning=False)

            forecasts = result.forecast(horizon=max_horizon, method="simulation", simulations=1000)
            variance_forecast = forecasts.variance.iloc[-1].values / 10000  # back to decimal

            if np.any(np.isnan(variance_forecast)) or np.any(variance_forecast <= 0):
                logger.debug("GARCH: invalid forecast values")
                return None

            return variance_forecast

    except Exception as e:
        logger.debug("GARCH fit failed: %s", e)
        return None


def _mean_reverting_variance(
    log_returns: np.ndarray, max_horizon: int, lam: float = 0.94
) -> np.ndarray | None:
    """Compute mean-reverting exponential smoothing variance forecast.

    Unlike standard RiskMetrics EWMA (flat forecast), this produces a variance
    path that decays toward the long-run variance: h[t] = λ·h[t-1] + (1-λ)·σ²_lr.
    More suitable for multi-step forecasting than flat EWMA.
    """
    try:
        daily_var = float(np.var(log_returns[-20:], ddof=1)) if len(log_returns) >= 20 else float(np.var(log_returns, ddof=1))

        if daily_var <= 0:
            return None

        # EWMA: variance mean-reverts slowly
        variance_path = np.empty(max_horizon)
        variance_path[0] = daily_var
        long_run_var = float(np.var(log_returns, ddof=1))

        for t in range(1, max_horizon):
            variance_path[t] = lam * variance_path[t - 1] + (1 - lam) * long_run_var

        return variance_path

    except Exception as e:
        logger.debug("EWMA fallback failed: %s", e)
        return None
