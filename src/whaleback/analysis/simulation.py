"""Monte Carlo simulation orchestrator.

Delegates to individual stochastic models (GBM, GARCH, Heston, Merton)
and combines results via weighted-pooling ensemble.
"""

import hashlib
import logging
from typing import Any

import numpy as np

from whaleback.analysis.sim_models import SimModel
from whaleback.analysis.sim_models.gbm import simulate_gbm
from whaleback.analysis.sim_models.garch import simulate_garch
from whaleback.analysis.sim_models.heston import simulate_heston
from whaleback.analysis.sim_models.merton import simulate_merton
from whaleback.analysis.sim_models.ensemble import combine_ensemble

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_NUM_SIMULATIONS = 10000
DEFAULT_HORIZONS = (21, 63, 126, 252)  # 1M, 3M, 6M, 12M trading days
DEFAULT_CONFIDENCE_LEVELS = (0.05, 0.25, 0.50, 0.75, 0.95)
DEFAULT_TARGET_MULTIPLIERS = (1.1, 1.2, 1.5)
MIN_HISTORY_DAYS = 60
MAX_ANNUALIZED_SIGMA = 1.50
TRADING_DAYS_PER_YEAR = 252

HORIZON_LABELS = {
    21: "1개월",
    63: "3개월",
    126: "6개월",
    252: "1년",
}

# Simulation score weights
SCORE_WEIGHTS = {
    "mean_return_6m": 0.40,
    "upside_prob_3m": 0.35,
    "neg_var_5pct_3m": 0.25,
}

# Default ensemble weights
DEFAULT_WEIGHTS = {
    SimModel.GBM.value: 0.25,
    SimModel.GARCH.value: 0.30,
    SimModel.HESTON.value: 0.20,
    SimModel.MERTON.value: 0.25,
}

# All available models
ALL_MODELS = (SimModel.GBM, SimModel.GARCH, SimModel.HESTON, SimModel.MERTON)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run_monte_carlo(
    prices: list[float],
    num_simulations: int = DEFAULT_NUM_SIMULATIONS,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
    target_multipliers: tuple[float, ...] = DEFAULT_TARGET_MULTIPLIERS,
    ticker: str | None = None,
    # NEW — all optional for backward compatibility
    models: tuple[SimModel, ...] | None = None,
    weights: dict[str, float] | None = None,
    garch_params: dict[str, Any] | None = None,
    heston_params: dict[str, Any] | None = None,
    merton_params: dict[str, Any] | None = None,
    max_sigma: float = MAX_ANNUALIZED_SIGMA,
) -> dict[str, Any] | None:
    """Run multi-model Monte Carlo simulation on a price series.

    Runs selected models (default: all four), combines via weighted pooling,
    and returns ensemble statistics with per-model breakdown.

    Args:
        prices: Closing prices in chronological order (oldest first).
        num_simulations: Number of simulated paths per model per horizon.
        horizons: Forward horizons in trading days.
        target_multipliers: Price multipliers for target-probability analysis.
        ticker: Optional ticker for reproducible seeding.
        models: Which models to run (default: all four).
        weights: Model weights for ensemble (default: config weights).
        garch_params: Override GARCH parameters {p, q}.
        heston_params: Override Heston parameters {kappa, theta, xi, rho}.
        merton_params: Override Merton parameters {lam, mu_j, sigma_j}.
        max_sigma: Cap on annualised volatility.

    Returns:
        Result dict with ensemble statistics + model_breakdown, or None.
    """
    # --- Input validation (unchanged) -----------------------------------
    if not prices or len(prices) < MIN_HISTORY_DAYS:
        logger.debug(
            "Insufficient price history: %d days (need %d)",
            len(prices) if prices else 0,
            MIN_HISTORY_DAYS,
        )
        return None

    clean_prices = np.array(
        [p for p in prices if p is not None and np.isfinite(p) and p > 0]
    )
    if len(clean_prices) < MIN_HISTORY_DAYS:
        logger.debug("After cleaning, insufficient prices: %d", len(clean_prices))
        return None

    # --- Compute daily log returns --------------------------------------
    log_returns = np.diff(np.log(clean_prices))

    if len(log_returns) == 0 or np.all(log_returns == 0):
        logger.debug("No valid returns (zero variance)")
        return None

    # --- Derive annualised stats for metadata ---------------------------
    daily_mu = float(np.mean(log_returns))
    daily_sigma = float(np.std(log_returns, ddof=1))
    mu = daily_mu * TRADING_DAYS_PER_YEAR
    sigma = daily_sigma * np.sqrt(TRADING_DAYS_PER_YEAR)

    if sigma > max_sigma:
        sigma = max_sigma
    if sigma == 0.0:
        logger.debug("Zero volatility detected, skipping simulation")
        return None

    base_price = int(clean_prices[-1])

    # --- Stable seed (hashlib-based, not session-dependent hash()) ------
    if ticker:
        seed = int(hashlib.sha256(ticker.encode()).hexdigest(), 16) % (2**32)
    else:
        seed = None
    rng = np.random.default_rng(seed=seed)

    # --- Resolve models and weights -------------------------------------
    if models is None:
        models = ALL_MODELS
    if weights is None:
        weights = dict(DEFAULT_WEIGHTS)

    garch_p = garch_params or {}
    heston_p = heston_params or {}
    merton_p = merton_params or {}

    # --- Run each model (independent child RNGs for isolation) ----------
    model_results = {}

    for model in models:
        # Model-keyed seed: deterministic per (ticker, model) regardless of
        # which other models are in the set — true isolation.
        if ticker:
            model_seed = int(
                hashlib.sha256(f"{ticker}:{model.value}".encode()).hexdigest(), 16
            ) % (2**63)
        else:
            model_seed = rng.integers(2**63)
        child_rng = np.random.default_rng(model_seed)
        try:
            if model == SimModel.GBM:
                result = simulate_gbm(
                    log_returns, base_price, num_simulations,
                    horizons, child_rng, max_sigma=max_sigma,
                )
            elif model == SimModel.GARCH:
                result = simulate_garch(
                    log_returns, base_price, num_simulations,
                    horizons, child_rng,
                    p=garch_p.get("p", 1),
                    q=garch_p.get("q", 1),
                    max_sigma=max_sigma,
                )
            elif model == SimModel.HESTON:
                result = simulate_heston(
                    log_returns, base_price, num_simulations,
                    horizons, child_rng,
                    kappa=heston_p.get("kappa", 2.0),
                    theta=heston_p.get("theta", 0.04),
                    xi=heston_p.get("xi", 0.3),
                    rho=heston_p.get("rho", -0.7),
                )
            elif model == SimModel.MERTON:
                result = simulate_merton(
                    log_returns, base_price, num_simulations,
                    horizons, child_rng,
                    lam=merton_p.get("lam", 0.1),
                    mu_j=merton_p.get("mu_j", -0.02),
                    sigma_j=merton_p.get("sigma_j", 0.05),
                    max_sigma=max_sigma,
                )
            else:
                continue

            if result is not None:
                model_results[model.value] = result

        except Exception as e:
            logger.warning("Model %s failed: %s", model.value, e)
            continue

    if not model_results:
        logger.debug("All models failed, returning None")
        return None

    # --- Single model fast path -----------------------------------------
    if len(model_results) == 1:
        only_model = next(iter(model_results.values()))
        horizons_result = only_model["horizons"]

        # Target probabilities
        target_probs = _compute_target_probs(
            {h: only_model["terminal_prices"][h] for h in horizons if h in only_model["terminal_prices"]},
            base_price, target_multipliers,
        )

        score_result = compute_simulation_score(horizons_result)

        return {
            "simulation_score": score_result["score"],
            "simulation_grade": score_result["grade"],
            "base_price": base_price,
            "mu": float(round(mu, 6)),
            "sigma": float(round(sigma, 6)),
            "num_simulations": num_simulations,
            "input_days_used": len(clean_prices),
            "horizons": _stringify_keys(horizons_result),
            "target_probs": target_probs,
            "model_breakdown": None,
        }

    # --- Ensemble combination -------------------------------------------
    ensemble = combine_ensemble(
        model_results=model_results,
        weights=weights,
        horizons=horizons,
        base_price=base_price,
        target_multipliers=target_multipliers,
        total_samples=num_simulations,
    )

    if not ensemble or "horizons" not in ensemble:
        logger.debug("Ensemble combination failed")
        return None

    ensemble_horizons = ensemble["horizons"]
    score_result = compute_simulation_score(ensemble_horizons)

    # Stringify target_probs horizon keys from ensemble
    raw_target_probs = ensemble.get("target_probs", {})
    str_target_probs = {
        mult: {str(h): v for h, v in hprobs.items()}
        for mult, hprobs in raw_target_probs.items()
    }

    return {
        "simulation_score": score_result["score"],
        "simulation_grade": score_result["grade"],
        "base_price": base_price,
        "mu": float(round(mu, 6)),
        "sigma": float(round(sigma, 6)),
        "num_simulations": num_simulations,
        "input_days_used": len(clean_prices),
        "horizons": _stringify_keys(ensemble_horizons),
        "target_probs": str_target_probs,
        "model_breakdown": ensemble.get("model_breakdown"),
    }


def _stringify_keys(d: dict) -> dict[str, Any]:
    """Convert int dict keys to strings for JSONB compatibility."""
    return {str(k): v for k, v in d.items()}


def _compute_target_probs(
    terminal_prices: dict[int, np.ndarray],
    base_price: int,
    target_multipliers: tuple[float, ...],
) -> dict[str, dict[str, float]]:
    """Compute target-price probabilities from terminal price arrays."""
    target_probs: dict[str, dict[str, float]] = {}
    for mult in target_multipliers:
        target_price = base_price * mult
        key = str(mult)
        target_probs[key] = {}
        for h, terminal in terminal_prices.items():
            target_probs[key][str(h)] = round(float(np.mean(terminal > target_price)), 4)
    return target_probs


# ---------------------------------------------------------------------------
# Scoring (unchanged from original)
# ---------------------------------------------------------------------------


def compute_simulation_score(
    horizons_result: dict[int, dict[str, Any]],
) -> dict[str, float | str | None]:
    """Derive a 0-100 simulation score from horizon statistics.

    Weights:
        - 40 %  mean return at 6 months (126d)
        - 35 %  upside probability at 3 months (63d)
        - 25 %  negative VaR (5 %) at 3 months (63d)

    Returns:
        {"score": float | None, "grade": str | None}
    """
    # Support both int keys (pre-DB) and string keys (post-JSONB)
    h126 = horizons_result.get(126) or horizons_result.get("126")
    h63 = horizons_result.get(63) or horizons_result.get("63")

    if h126 is None or h63 is None:
        return {"score": None, "grade": None}

    median_return_6m = h126.get("expected_return_pct")
    upside_prob_3m = h63.get("upside_prob")
    var_5pct_3m = h63.get("var_5pct_pct")

    if any(v is None for v in (median_return_6m, upside_prob_3m, var_5pct_3m)):
        return {"score": None, "grade": None}

    # Normalize components to 0-100
    norm_return = _normalize_return(median_return_6m, center=0, scale=20)
    norm_upside = upside_prob_3m * 100
    norm_var = _normalize_var(var_5pct_3m, center=-15, scale=10)

    w = SCORE_WEIGHTS
    score = (
        w["mean_return_6m"] * norm_return
        + w["upside_prob_3m"] * norm_upside
        + w["neg_var_5pct_3m"] * norm_var
    )

    score = round(float(np.clip(score, 0, 100)), 2)

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

    Responsive range (10-90 score): approx -40% to +40%.
    Returns beyond ±40% saturate, reducing discrimination for extreme-vol stocks.
    Calibrated for typical Korean equity 6-month return distributions.
    """
    return float(100.0 / (1.0 + np.exp(-(value - center) / scale)))


def _normalize_var(value: float, center: float = -15, scale: float = 10) -> float:
    """Sigmoid normalisation for VaR values (lower VaR loss = higher score).

    Center at -15% means a 15% loss over 3 months scores 50 (neutral).
    Responsive range (10-90 score): approx -35% to +5% VaR.
    Calibrated for Korean equities (30% annualised downside vol → neutral).
    """
    return float(100.0 / (1.0 + np.exp(-(value - center) / scale)))
