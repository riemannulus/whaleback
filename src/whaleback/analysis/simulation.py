"""Monte Carlo simulation using Geometric Brownian Motion.

Pure computation functions for forward-looking price simulations.
No database dependency - operates on price series passed as arguments.
"""

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_NUM_SIMULATIONS = 10000
DEFAULT_HORIZONS = (21, 63, 126, 252)  # 1M, 3M, 6M, 12M trading days
DEFAULT_CONFIDENCE_LEVELS = (0.05, 0.25, 0.50, 0.75, 0.95)
DEFAULT_TARGET_MULTIPLIERS = (1.1, 1.2, 1.5)
MIN_HISTORY_DAYS = 60  # Minimum trading days required
MAX_ANNUALIZED_SIGMA = 1.50  # Cap extreme volatility at 150%
TRADING_DAYS_PER_YEAR = 252

HORIZON_LABELS = {
    21: "1개월",
    63: "3개월",
    126: "6개월",
    252: "1년",
}

# Simulation score weights
SCORE_WEIGHTS = {
    "median_return_6m": 0.40,
    "upside_prob_3m": 0.35,
    "neg_var_5pct_3m": 0.25,
}


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run_monte_carlo(
    prices: list[float],
    num_simulations: int = DEFAULT_NUM_SIMULATIONS,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
    target_multipliers: tuple[float, ...] = DEFAULT_TARGET_MULTIPLIERS,
    ticker: str | None = None,
) -> dict[str, Any] | None:
    """Run GBM-based Monte Carlo simulation on a price series.

    Generates ``num_simulations`` price paths for each horizon using
    Geometric Brownian Motion and computes distributional statistics.

    Args:
        prices: List of closing prices in chronological order (oldest first).
        num_simulations: Number of simulated paths per horizon.
        horizons: Tuple of forward horizons in trading days.
        target_multipliers: Price multipliers for target-probability analysis.
        ticker: Optional ticker string used as random seed for reproducibility.

    Returns:
        Result dict with simulation statistics, or ``None`` if insufficient data.
    """
    # --- Input validation ------------------------------------------------
    if not prices or len(prices) < MIN_HISTORY_DAYS:
        logger.debug(
            "Insufficient price history: %d days (need %d)",
            len(prices) if prices else 0,
            MIN_HISTORY_DAYS,
        )
        return None

    # Filter out NaN / zero / negative prices
    clean_prices = np.array([p for p in prices if p is not None and np.isfinite(p) and p > 0])
    if len(clean_prices) < MIN_HISTORY_DAYS:
        logger.debug("After cleaning, insufficient prices: %d", len(clean_prices))
        return None

    # --- Compute daily log returns ----------------------------------------
    log_returns = np.diff(np.log(clean_prices))

    if len(log_returns) == 0 or np.all(log_returns == 0):
        logger.debug("No valid returns (zero variance)")
        return None

    # --- Derive annualised drift (mu) and volatility (sigma) --------------
    daily_mu = float(np.mean(log_returns))
    daily_sigma = float(np.std(log_returns, ddof=1))

    mu = daily_mu * TRADING_DAYS_PER_YEAR
    sigma = daily_sigma * np.sqrt(TRADING_DAYS_PER_YEAR)

    # Cap extreme volatility
    if sigma > MAX_ANNUALIZED_SIGMA:
        logger.debug("Capping sigma from %.4f to %.4f", sigma, MAX_ANNUALIZED_SIGMA)
        sigma = MAX_ANNUALIZED_SIGMA

    # Handle sigma == 0 edge case (constant price)
    if sigma == 0.0:
        logger.debug("Zero volatility detected, skipping simulation")
        return None

    base_price = int(clean_prices[-1])

    # --- Seed RNG for reproducibility (optional) --------------------------
    rng = np.random.default_rng(
        seed=hash(ticker) % (2**32) if ticker else None
    )

    # --- Simulate per horizon ---------------------------------------------
    daily_drift = mu / TRADING_DAYS_PER_YEAR - (sigma ** 2) / (2 * TRADING_DAYS_PER_YEAR)
    daily_vol = sigma / np.sqrt(TRADING_DAYS_PER_YEAR)

    horizons_result: dict[int, dict[str, Any]] = {}
    # Cache terminal prices per horizon for target-prob calculation
    terminal_prices_cache: dict[int, np.ndarray] = {}

    for h in horizons:
        # Z matrix: (num_simulations, h)
        z = rng.standard_normal((num_simulations, h))

        # GBM daily log returns
        daily_log_returns = daily_drift + daily_vol * z  # (N, h)

        # Cumulative log returns
        cumulative = np.cumsum(daily_log_returns, axis=1)  # (N, h)

        # Price paths
        price_paths = base_price * np.exp(cumulative)  # (N, h)

        terminal = price_paths[:, -1]  # (N,)
        terminal_prices_cache[h] = terminal

        # Percentiles (as integer prices)
        p5 = int(np.percentile(terminal, 5))
        p25 = int(np.percentile(terminal, 25))
        p50 = int(np.percentile(terminal, 50))
        p75 = int(np.percentile(terminal, 75))
        p95 = int(np.percentile(terminal, 95))

        expected_return_pct = round(float((np.mean(terminal) / base_price - 1) * 100), 2)
        var_5pct_pct = round(float((np.percentile(terminal, 5) / base_price - 1) * 100), 2)
        upside_prob = round(float(np.mean(terminal > base_price)), 4)

        label = HORIZON_LABELS.get(h, f"{h}일")

        horizons_result[h] = {
            "label": label,
            "p5": p5,
            "p25": p25,
            "p50": p50,
            "p75": p75,
            "p95": p95,
            "expected_return_pct": expected_return_pct,
            "var_5pct_pct": var_5pct_pct,
            "upside_prob": upside_prob,
        }

    # --- Target-price probabilities ---------------------------------------
    target_probs: dict[str, dict[int, float]] = {}

    for mult in target_multipliers:
        target_price = base_price * mult
        key = str(mult)
        target_probs[key] = {}

        for h in horizons:
            terminal = terminal_prices_cache[h]
            prob = round(float(np.mean(terminal > target_price)), 4)
            target_probs[key][h] = prob

    # --- Simulation score -------------------------------------------------
    score_result = compute_simulation_score(horizons_result)

    return {
        "simulation_score": score_result["score"],
        "simulation_grade": score_result["grade"],
        "base_price": base_price,
        "mu": round(mu, 6),
        "sigma": round(sigma, 6),
        "num_simulations": num_simulations,
        "input_days_used": len(clean_prices),
        "horizons": horizons_result,
        "target_probs": target_probs,
    }


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def compute_simulation_score(
    horizons_result: dict[int, dict[str, Any]],
) -> dict[str, float | str | None]:
    """Derive a 0-100 simulation score from horizon statistics.

    Weights:
        - 40 %  median return at 6 months (126d)
        - 35 %  upside probability at 3 months (63d)
        - 25 %  negative VaR (5 %) at 3 months (63d)

    Returns:
        {"score": float | None, "grade": str | None}
    """
    h126 = horizons_result.get(126)
    h63 = horizons_result.get(63)

    if h126 is None or h63 is None:
        return {"score": None, "grade": None}

    median_return_6m = h126.get("expected_return_pct")
    upside_prob_3m = h63.get("upside_prob")
    var_5pct_3m = h63.get("var_5pct_pct")

    if any(v is None for v in (median_return_6m, upside_prob_3m, var_5pct_3m)):
        return {"score": None, "grade": None}

    # Normalize components to 0-100
    norm_return = _normalize_return(median_return_6m, center=0, scale=20)
    norm_upside = upside_prob_3m * 100  # already 0-1, scale to 0-100
    norm_var = _normalize_var(var_5pct_3m, center=-15, scale=10)

    w = SCORE_WEIGHTS
    score = (
        w["median_return_6m"] * norm_return
        + w["upside_prob_3m"] * norm_upside
        + w["neg_var_5pct_3m"] * norm_var
    )

    # Clamp
    score = round(float(np.clip(score, 0, 100)), 2)

    # Grade
    if score >= 70:
        grade = "positive"
    elif score >= 50:
        grade = "neutral_positive"
    elif score >= 30:
        grade = "neutral"
    else:
        grade = "negative"

    return {"score": score, "grade": grade}


# ---------------------------------------------------------------------------
# Normalisation helpers (sigmoid mapping to 0-100)
# ---------------------------------------------------------------------------


def _normalize_return(value: float, center: float = 0, scale: float = 20) -> float:
    """Sigmoid normalisation for expected-return values.

    Maps ``value`` to the range [0, 100] with the midpoint at ``center``.
    ``scale`` controls steepness; larger = more gradual.
    """
    return float(100.0 / (1.0 + np.exp(-(value - center) / scale)))


def _normalize_var(value: float, center: float = -15, scale: float = 10) -> float:
    """Sigmoid normalisation for VaR values (lower VaR loss = higher score).

    A VaR of 0 % (no loss) maps near 100; a severe -30 % maps near 0.
    The sign is inverted so that *less negative* VaR yields a *higher* score.
    """
    return float(100.0 / (1.0 + np.exp(-(value - center) / scale)))
