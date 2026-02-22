"""Sentiment analysis core module.

3-dimensional sentiment decomposition: Direction × Intensity × Confidence.
Pure computation — no database dependency. Only numpy + dataclasses.
"""

import logging
import math
from dataclasses import dataclass
from datetime import datetime

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SOURCE_WEIGHTS: dict[str, float] = {
    "financial": 1.5,
    "general": 1.0,
    "portal": 0.7,
}

TYPE_WEIGHTS: dict[str, float] = {
    "disclosure": 2.0,
    "analyst": 1.8,
    "earnings": 1.5,
    "general": 1.0,
}

BASE_ENSEMBLE_WEIGHTS: dict[str, float] = {
    "gbm": 0.25,
    "garch": 0.30,
    "heston": 0.20,
    "merton": 0.25,
}

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class SentimentScore:
    """3-dimensional sentiment decomposition."""

    direction: float       # D ∈ [-1, +1] — weighted average sentiment
    intensity: float       # I ∈ [0, 1] — reaction strength (article count)
    confidence: float      # C ∈ [0, 1] — agreement between articles
    effective_score: float  # S_eff = D × I × C ∈ [-1, +1]
    sentiment_score: float  # normalized 0-100 for composite axis
    signal: str            # strong_buy/buy/neutral/sell/strong_sell
    article_count: int
    status: str            # active/stale/insufficient/no_data


@dataclass
class SentimentAdjustments:
    """Parameters to pass to simulation models."""

    drift_adj_daily: float       # additive drift adjustment
    vol_multiplier: float        # multiplicative volatility scaling
    var_multiplier: float        # for GARCH variance scaling (vol_multiplier²)
    theta_mult: float            # Heston theta scaling
    v0_mult: float               # Heston v0 scaling
    rho_adj: float               # Heston rho adjustment
    lam_mult: float              # Merton jump intensity multiplier
    mu_j_adj: float              # Merton jump mean adjustment
    sig_j_mult: float            # Merton jump vol multiplier
    ensemble_weight_overrides: dict[str, float] | None  # dynamic ensemble weights


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def classify_sentiment_signal(effective_score: float) -> str:
    """Classify effective sentiment score into a signal label.

    Args:
        effective_score: S_eff ∈ [-1, +1]

    Returns:
        One of: strong_buy, buy, neutral, sell, strong_sell
    """
    if effective_score >= 0.4:
        return "strong_buy"
    elif effective_score >= 0.15:
        return "buy"
    elif effective_score >= -0.15:
        return "neutral"
    elif effective_score >= -0.4:
        return "sell"
    else:
        return "strong_sell"


def _neutral_score(article_count: int = 0, status: str = "no_data") -> SentimentScore:
    """Return a fully neutral SentimentScore."""
    return SentimentScore(
        direction=0.0,
        intensity=0.0,
        confidence=0.0,
        effective_score=0.0,
        sentiment_score=50.0,
        signal="neutral",
        article_count=article_count,
        status=status,
    )


def _neutral_adjustments() -> SentimentAdjustments:
    """Return neutral (identity) SentimentAdjustments."""
    return SentimentAdjustments(
        drift_adj_daily=0.0,
        vol_multiplier=1.0,
        var_multiplier=1.0,
        theta_mult=1.0,
        v0_mult=1.0,
        rho_adj=0.0,
        lam_mult=1.0,
        mu_j_adj=0.0,
        sig_j_mult=1.0,
        ensemble_weight_overrides=None,
    )


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def compute_sentiment_score(
    articles: list[dict],
    half_life: float = 3.0,
    min_articles: int = 2,
) -> SentimentScore:
    """Compute 3-dimensional sentiment score from a list of article dicts.

    Each article dict must have:
        - sentiment_raw (float, -1 to +1)
        - published_at (datetime)
        - importance_weight (float)
        - source_type (str)
        - article_type (str)

    Args:
        articles: List of article dicts.
        half_life: Half-life for time decay in trading days (default 3.0).
        min_articles: Minimum articles required for "active" status (default 2).

    Returns:
        SentimentScore with direction, intensity, confidence, effective_score,
        sentiment_score, signal, article_count, and status fields.
    """
    n = len(articles)

    if n == 0:
        return _neutral_score(article_count=0, status="no_data")

    if n < min_articles:
        # Still compute but mark as insufficient
        status = "insufficient"
    else:
        status = "active"

    # Decay rate
    lam = math.log(2.0) / half_life

    # Find newest article timestamp to compute relative ages
    newest_dt: datetime = max(a["published_at"] for a in articles)

    # Build arrays
    raw_sentiments: list[float] = []
    weights: list[float] = []

    trading_days_per_real_day = 1.0  # assume published_at is in trading days (calendar ok)

    for article in articles:
        s_i = float(article["sentiment_raw"])
        dt: datetime = article["published_at"]
        importance = float(article.get("importance_weight", 1.0))
        src_type = article.get("source_type", "general")
        art_type = article.get("article_type", "general")

        # Age in trading days (using total_seconds for sub-day precision)
        delta_seconds = (newest_dt - dt).total_seconds()
        t_days = delta_seconds / (3600.0 * 24.0) * trading_days_per_real_day
        t_days = max(t_days, 0.0)

        # Time decay weight
        w_t = math.exp(-lam * t_days)

        # Source and type weights
        src_w = SOURCE_WEIGHTS.get(src_type, 1.0)
        type_w = TYPE_WEIGHTS.get(art_type, 1.0)

        v_i = src_w * type_w * importance

        combined_weight = w_t * v_i
        weights.append(combined_weight)
        raw_sentiments.append(s_i)

    weights_arr = np.array(weights, dtype=float)
    sentiments_arr = np.array(raw_sentiments, dtype=float)

    total_weight = float(np.sum(weights_arr))

    if total_weight == 0.0:
        return _neutral_score(article_count=n, status=status)

    # S_composite: weighted average
    s_composite = float(np.dot(sentiments_arr, weights_arr) / total_weight)

    # Direction D = S_composite clamped to [-1, +1]
    D = float(np.clip(s_composite, -1.0, 1.0))

    # Intensity I = |D| × √(min(n, 20) / 20)
    I = abs(D) * math.sqrt(min(n, 20) / 20.0)
    I = float(np.clip(I, 0.0, 1.0))

    # Confidence C = (1 - σ_s) × min(n, 5) / 5
    if n > 1:
        sigma_s = float(np.std(sentiments_arr, ddof=0))
    else:
        sigma_s = 0.0
    C = (1.0 - sigma_s) * (min(n, 5) / 5.0)
    C = float(np.clip(C, 0.0, 1.0))

    # Effective score S_eff = D × I × C
    S_eff = D * I * C
    S_eff = float(np.clip(S_eff, -1.0, 1.0))

    # Normalized score 0-100
    sentiment_score = (S_eff + 1.0) / 2.0 * 100.0

    signal = classify_sentiment_signal(S_eff)

    return SentimentScore(
        direction=D,
        intensity=I,
        confidence=C,
        effective_score=S_eff,
        sentiment_score=sentiment_score,
        signal=signal,
        article_count=n,
        status=status,
    )


def _compute_ensemble_weights(S: float) -> dict[str, float]:
    """Compute dynamic ensemble weight overrides via softmax adjustment.

    Args:
        S: Effective sentiment score ∈ [-1, +1]

    Returns:
        Dict mapping model name to normalized weight (sums to 1.0).
    """
    phi = {
        "gbm": 1.0 * S,
        "garch": 0.8 * (-S),
        "heston": 0.6 * abs(S),
        "merton": 1.2 * max(0.0, -S),
    }

    unnormalized = {
        model: BASE_ENSEMBLE_WEIGHTS[model] * math.exp(phi[model])
        for model in BASE_ENSEMBLE_WEIGHTS
    }

    total = sum(unnormalized.values())
    if total == 0.0:
        return dict(BASE_ENSEMBLE_WEIGHTS)

    return {model: w / total for model, w in unnormalized.items()}


def compute_sentiment_adjustments(
    score: SentimentScore,
    alpha: float = 0.08,
    beta: float = 0.15,
    delta: float = 0.50,
    gamma_lam: float = 1.50,
    gamma_mu: float = 0.03,
) -> SentimentAdjustments:
    """Compute simulation model parameter adjustments from a SentimentScore.

    Args:
        score: SentimentScore from compute_sentiment_score().
        alpha: Annual drift sensitivity (default 0.08).
        beta: Volatility sensitivity (default 0.15).
        delta: Asymmetry factor for negative news vol impact (default 0.50).
        gamma_lam: Jump intensity sensitivity (default 1.50).
        gamma_mu: Jump mean sensitivity (default 0.03).

    Returns:
        SentimentAdjustments with all model parameter adjustments.
    """
    # Insufficient data → neutral adjustments
    if score.status in ("no_data", "insufficient"):
        return _neutral_adjustments()

    S = score.effective_score
    D = score.direction
    I = score.intensity
    C = score.confidence

    # --- Drift ---
    drift_cap = 0.10 / 252.0
    drift_adj_daily = float(np.clip((alpha / 252.0) * S, -drift_cap, drift_cap))

    # --- Volatility multiplier (asymmetric) ---
    if D >= 0.0:
        V = 1.0 - beta * D * I * C
    else:
        V = 1.0 + beta * abs(D) * (1.0 + delta) * I * C
    V = float(np.clip(V, 0.70, 1.50))

    # --- Variance-related multipliers ---
    var_multiplier = V ** 2
    theta_mult = V ** 2
    v0_mult = V ** 2

    # --- Heston rho adjustment ---
    rho_adj = -0.10 * max(0.0, -S)

    # --- Merton jump parameters ---
    lam_mult = float(np.clip(1.0 + gamma_lam * max(0.0, -S), 0.5, 3.0))
    mu_j_adj = -gamma_mu * max(0.0, -S)
    sig_j_mult = float(np.clip(1.0 + 0.5 * max(0.0, -S), 0.5, 2.0))

    # --- Ensemble weight overrides ---
    ensemble_weight_overrides = _compute_ensemble_weights(S)

    return SentimentAdjustments(
        drift_adj_daily=drift_adj_daily,
        vol_multiplier=V,
        var_multiplier=var_multiplier,
        theta_mult=theta_mult,
        v0_mult=v0_mult,
        rho_adj=rho_adj,
        lam_mult=lam_mult,
        mu_j_adj=mu_j_adj,
        sig_j_mult=sig_j_mult,
        ensemble_weight_overrides=ensemble_weight_overrides,
    )
