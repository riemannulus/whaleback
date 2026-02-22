"""Ensemble combiner for multiple simulation models.

Weighted pooling: sample proportionally from each model's terminal prices,
then recompute statistics on the pooled distribution.
"""

import logging
from typing import Any

import numpy as np

from . import ModelResult, SimModel
from .gbm import _compute_horizon_stats, HORIZON_LABELS

logger = logging.getLogger(__name__)


def combine_ensemble(
    model_results: dict[str, ModelResult],
    weights: dict[str, float],
    horizons: tuple[int, ...],
    base_price: int,
    target_multipliers: tuple[float, ...],
    total_samples: int = 10000,
) -> dict[str, Any]:
    """Combine model results via weighted pooling.

    For each horizon, sample terminal prices from each model proportional
    to its weight, pool them, and recompute distributional statistics.

    Args:
        model_results: {model_name: ModelResult} for successful models.
        weights: {model_name: weight} (will be renormalised to sum=1).
        horizons: Tuple of horizon days.
        base_price: Starting price.
        target_multipliers: Price target multipliers.
        total_samples: Total pooled sample size.

    Returns:
        Dict with ensemble horizons, target_probs, and model_breakdown.
    """
    if not model_results:
        return {}

    # Renormalise weights for available models only
    available = {k: weights.get(k, 0.0) for k in model_results}
    total_weight = sum(available.values())
    if total_weight <= 0:
        # Equal weight fallback
        n = len(available)
        available = {k: 1.0 / n for k in available}
        total_weight = 1.0
    else:
        available = {k: v / total_weight for k, v in available.items()}

    # Compute per-model sample counts
    sample_counts: dict[str, int] = {}
    allocated = 0
    models_list = list(available.keys())
    for i, model_name in enumerate(models_list):
        if i == len(models_list) - 1:
            # Last model gets remainder to ensure exact total
            sample_counts[model_name] = max(0, total_samples - allocated)
        else:
            n = int(round(available[model_name] * total_samples))
            sample_counts[model_name] = n
            allocated += n

    # Pool terminal prices per horizon
    ensemble_horizons: dict[int, dict[str, Any]] = {}
    ensemble_terminal: dict[int, np.ndarray] = {}

    rng = np.random.default_rng(42)  # deterministic pooling

    for h in horizons:
        pooled_parts: list[np.ndarray] = []

        for model_name, result in model_results.items():
            tp = result["terminal_prices"].get(h)
            if tp is None or len(tp) == 0:
                continue

            n_sample = sample_counts.get(model_name, 0)
            if n_sample <= 0:
                continue

            # Sample with replacement from this model's terminal prices
            indices = rng.choice(len(tp), size=n_sample, replace=True)
            pooled_parts.append(tp[indices])

        if not pooled_parts:
            continue

        pooled = np.concatenate(pooled_parts)
        ensemble_terminal[h] = pooled
        ensemble_horizons[h] = _compute_horizon_stats(pooled, base_price, h)

    # Target probabilities from pooled distribution
    target_probs: dict[str, dict[int, float]] = {}
    for mult in target_multipliers:
        target_price = base_price * mult
        key = str(mult)
        target_probs[key] = {}
        for h in horizons:
            tp = ensemble_terminal.get(h)
            if tp is not None:
                target_probs[key][h] = round(float(np.mean(tp > target_price)), 4)

    # Model breakdown for transparency
    from whaleback.analysis.simulation import compute_simulation_score

    model_scores: list[dict[str, Any]] = []
    for model_name, result in model_results.items():
        score_result = compute_simulation_score(result["horizons"])
        model_scores.append({
            "model": model_name,
            "score": score_result.get("score"),
            "weight": round(available.get(model_name, 0.0), 4),
        })

    model_breakdown = {
        "model_scores": model_scores,
        "model_weights": {k: round(v, 4) for k, v in available.items()},
        "ensemble_method": "weighted_pooling",
    }

    return {
        "horizons": ensemble_horizons,
        "target_probs": target_probs,
        "terminal_prices": ensemble_terminal,
        "model_breakdown": model_breakdown,
    }
