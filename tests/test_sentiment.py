"""Tests for whaleback.analysis.sentiment module."""

import math
from datetime import datetime, timedelta

import pytest

from whaleback.analysis.sentiment import (
    SentimentAdjustments,
    SentimentScore,
    classify_sentiment_signal,
    compute_sentiment_adjustments,
    compute_sentiment_score,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NOW = datetime(2024, 1, 15, 12, 0, 0)


def make_article(
    sentiment_raw: float,
    days_ago: float = 0.0,
    importance_weight: float = 1.0,
    source_type: str = "general",
    article_type: str = "general",
) -> dict:
    return {
        "sentiment_raw": sentiment_raw,
        "published_at": NOW - timedelta(days=days_ago),
        "importance_weight": importance_weight,
        "source_type": source_type,
        "article_type": article_type,
    }


# ---------------------------------------------------------------------------
# 1. No articles → neutral score, status="no_data"
# ---------------------------------------------------------------------------


def test_no_articles_returns_neutral():
    score = compute_sentiment_score([])
    assert score.direction == 0.0
    assert score.intensity == 0.0
    assert score.confidence == 0.0
    assert score.effective_score == 0.0
    assert score.sentiment_score == 50.0
    assert score.signal == "neutral"
    assert score.status == "no_data"
    assert score.article_count == 0


# ---------------------------------------------------------------------------
# 2. Single article positive → status="insufficient"
# ---------------------------------------------------------------------------


def test_single_article_is_insufficient():
    articles = [make_article(0.8)]
    score = compute_sentiment_score(articles, min_articles=2)
    assert score.status == "insufficient"
    assert score.article_count == 1


# ---------------------------------------------------------------------------
# 3. Multiple positive articles → positive direction, signal buy/strong_buy
# ---------------------------------------------------------------------------


def test_multiple_positive_articles_positive_direction():
    articles = [make_article(0.7, days_ago=i * 0.5) for i in range(5)]
    score = compute_sentiment_score(articles)
    assert score.direction > 0.0
    assert score.status == "active"
    assert score.signal in ("buy", "strong_buy")
    assert score.effective_score > 0.0
    assert score.sentiment_score > 50.0


# ---------------------------------------------------------------------------
# 4. Multiple negative articles → negative direction, signal sell/strong_sell
# ---------------------------------------------------------------------------


def test_multiple_negative_articles_negative_direction():
    articles = [make_article(-0.7, days_ago=i * 0.5) for i in range(5)]
    score = compute_sentiment_score(articles)
    assert score.direction < 0.0
    assert score.signal in ("sell", "strong_sell")
    assert score.effective_score < 0.0
    assert score.sentiment_score < 50.0


# ---------------------------------------------------------------------------
# 5. Mixed articles → neutral direction
# ---------------------------------------------------------------------------


def test_mixed_articles_neutral_direction():
    # Balanced positive and negative
    articles = [make_article(0.8), make_article(-0.8), make_article(0.1), make_article(-0.1)]
    score = compute_sentiment_score(articles)
    assert -0.2 < score.direction < 0.2
    assert score.signal == "neutral"


# ---------------------------------------------------------------------------
# 6. Adjustments with neutral sentiment → all multipliers near 1.0
# ---------------------------------------------------------------------------


def test_adjustments_neutral_sentiment_near_identity():
    # Create a score that approximates neutral
    articles = [make_article(0.0) for _ in range(3)]
    score = compute_sentiment_score(articles)
    adj = compute_sentiment_adjustments(score)
    assert abs(adj.drift_adj_daily) < 1e-9
    assert abs(adj.vol_multiplier - 1.0) < 0.05
    assert abs(adj.lam_mult - 1.0) < 0.05
    assert adj.mu_j_adj == 0.0
    assert abs(adj.sig_j_mult - 1.0) < 0.05


# ---------------------------------------------------------------------------
# 7. Adjustments with strong negative → vol up, drift down, more jumps
# ---------------------------------------------------------------------------


def test_adjustments_strong_negative():
    # Construct score manually for deterministic test
    score = SentimentScore(
        direction=-0.9,
        intensity=0.9,
        confidence=0.9,
        effective_score=-0.729,
        sentiment_score=((-0.729 + 1) / 2 * 100),
        signal="strong_sell",
        article_count=10,
        status="active",
    )
    adj = compute_sentiment_adjustments(score)
    assert adj.drift_adj_daily < 0.0
    assert adj.vol_multiplier > 1.0
    assert adj.lam_mult > 1.0
    assert adj.mu_j_adj < 0.0
    assert adj.sig_j_mult > 1.0
    assert adj.rho_adj < 0.0


# ---------------------------------------------------------------------------
# 8. Adjustments with strong positive → vol slightly down, drift up
# ---------------------------------------------------------------------------


def test_adjustments_strong_positive():
    score = SentimentScore(
        direction=0.9,
        intensity=0.9,
        confidence=0.9,
        effective_score=0.729,
        sentiment_score=((0.729 + 1) / 2 * 100),
        signal="strong_buy",
        article_count=10,
        status="active",
    )
    adj = compute_sentiment_adjustments(score)
    assert adj.drift_adj_daily > 0.0
    assert adj.vol_multiplier < 1.0
    assert adj.lam_mult == pytest.approx(1.0, abs=0.01)  # no negative sentiment
    assert adj.mu_j_adj == pytest.approx(0.0, abs=1e-9)
    assert adj.rho_adj == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# 9. Volatility multiplier caps [0.70, 1.50]
# ---------------------------------------------------------------------------


def test_vol_multiplier_caps():
    # Extreme negative → should not exceed 1.50
    score_neg = SentimentScore(
        direction=-1.0, intensity=1.0, confidence=1.0,
        effective_score=-1.0, sentiment_score=0.0,
        signal="strong_sell", article_count=20, status="active",
    )
    adj_neg = compute_sentiment_adjustments(score_neg)
    assert adj_neg.vol_multiplier <= 1.50

    # Extreme positive → should not go below 0.70
    score_pos = SentimentScore(
        direction=1.0, intensity=1.0, confidence=1.0,
        effective_score=1.0, sentiment_score=100.0,
        signal="strong_buy", article_count=20, status="active",
    )
    adj_pos = compute_sentiment_adjustments(score_pos)
    assert adj_pos.vol_multiplier >= 0.70


# ---------------------------------------------------------------------------
# 10. Drift adjustment cap ±(0.10/252)
# ---------------------------------------------------------------------------


def test_drift_cap():
    max_drift = 0.10 / 252.0

    score_pos = SentimentScore(
        direction=1.0, intensity=1.0, confidence=1.0,
        effective_score=1.0, sentiment_score=100.0,
        signal="strong_buy", article_count=20, status="active",
    )
    adj_pos = compute_sentiment_adjustments(score_pos)
    assert adj_pos.drift_adj_daily <= max_drift + 1e-12

    score_neg = SentimentScore(
        direction=-1.0, intensity=1.0, confidence=1.0,
        effective_score=-1.0, sentiment_score=0.0,
        signal="strong_sell", article_count=20, status="active",
    )
    adj_neg = compute_sentiment_adjustments(score_neg)
    assert adj_neg.drift_adj_daily >= -max_drift - 1e-12


# ---------------------------------------------------------------------------
# 11. Ensemble weights sum to 1.0 for any input
# ---------------------------------------------------------------------------


def test_ensemble_weights_sum_to_one():
    for eff_score in [-1.0, -0.5, 0.0, 0.5, 1.0]:
        score = SentimentScore(
            direction=eff_score,
            intensity=abs(eff_score),
            confidence=0.8,
            effective_score=eff_score * abs(eff_score) * 0.8,
            sentiment_score=50.0,
            signal="neutral",
            article_count=5,
            status="active",
        )
        adj = compute_sentiment_adjustments(score)
        assert adj.ensemble_weight_overrides is not None
        total = sum(adj.ensemble_weight_overrides.values())
        assert total == pytest.approx(1.0, abs=1e-9), (
            f"Ensemble weights don't sum to 1.0 for S={eff_score}: {total}"
        )


# ---------------------------------------------------------------------------
# 12. Edge case: all same sentiment → high confidence
# ---------------------------------------------------------------------------


def test_all_same_sentiment_high_confidence():
    # All articles have the exact same sentiment → std = 0 → max confidence
    articles = [make_article(0.6, days_ago=i * 0.3) for i in range(5)]
    score = compute_sentiment_score(articles)
    # With std=0, confidence formula = (1 - 0) × min(5,5)/5 = 1.0
    assert score.confidence == pytest.approx(1.0, abs=1e-9)


# ---------------------------------------------------------------------------
# Additional: classify_sentiment_signal boundaries
# ---------------------------------------------------------------------------


def test_classify_signal_boundaries():
    assert classify_sentiment_signal(0.4) == "strong_buy"
    assert classify_sentiment_signal(0.39) == "buy"
    assert classify_sentiment_signal(0.15) == "buy"
    assert classify_sentiment_signal(0.14) == "neutral"
    assert classify_sentiment_signal(0.0) == "neutral"
    assert classify_sentiment_signal(-0.14) == "neutral"
    assert classify_sentiment_signal(-0.15) == "neutral"
    assert classify_sentiment_signal(-0.16) == "sell"
    assert classify_sentiment_signal(-0.4) == "sell"
    assert classify_sentiment_signal(-0.41) == "strong_sell"


# ---------------------------------------------------------------------------
# Additional: no_data / insufficient → neutral adjustments
# ---------------------------------------------------------------------------


def test_no_data_score_returns_neutral_adjustments():
    score = compute_sentiment_score([])
    adj = compute_sentiment_adjustments(score)
    assert adj.drift_adj_daily == 0.0
    assert adj.vol_multiplier == 1.0
    assert adj.var_multiplier == 1.0
    assert adj.ensemble_weight_overrides is None


def test_insufficient_score_returns_neutral_adjustments():
    articles = [make_article(0.9)]
    score = compute_sentiment_score(articles, min_articles=2)
    adj = compute_sentiment_adjustments(score)
    assert adj.drift_adj_daily == 0.0
    assert adj.vol_multiplier == 1.0
    assert adj.ensemble_weight_overrides is None


# ---------------------------------------------------------------------------
# Additional: var_multiplier = vol_multiplier²
# ---------------------------------------------------------------------------


def test_var_multiplier_equals_vol_squared():
    articles = [make_article(-0.5, days_ago=i * 0.5) for i in range(5)]
    score = compute_sentiment_score(articles)
    adj = compute_sentiment_adjustments(score)
    assert adj.var_multiplier == pytest.approx(adj.vol_multiplier ** 2, rel=1e-9)
    assert adj.theta_mult == pytest.approx(adj.vol_multiplier ** 2, rel=1e-9)
    assert adj.v0_mult == pytest.approx(adj.vol_multiplier ** 2, rel=1e-9)
