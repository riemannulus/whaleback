"""Whaleback Composite Score (WCS) - Multi-factor scoring and signal synthesis.

Combines five independent analysis axes into a single actionable score:
  - Value (가치): F-Score + RIM safety margin
  - Flow (수급): Whale score (institutional accumulation) + sector flow bonus
  - Momentum (모멘텀): RS percentile + sector rotation
  - Forecast (전망): Monte Carlo simulation score
  - Sentiment (감성): News sentiment analysis

The WCS provides:
  1. Composite score (0-100) with configurable weights
  2. Confluence detection (signal agreement across axes)
  3. Divergence warnings (conflicting signals)
  4. Investor profile-based screening
"""

import logging
import math
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_WEIGHTS: dict[str, float] = {
    "w_value": 0.25,
    "w_flow": 0.25,
    "w_momentum": 0.20,
    "w_forecast": 0.20,
    "w_sentiment": 0.10,
}

BUY_SIGNALS = {"strong_buy", "buy"}
SELL_SIGNALS = {"strong_sell", "sell"}

INVESTOR_PROFILES: dict[str, dict[str, Any]] = {
    "value": {
        "w_value": 0.35,
        "w_flow": 0.20,
        "w_momentum": 0.15,
        "w_forecast": 0.20,
        "w_sentiment": 0.10,
        "label": "가치 투자",
        "description": "저평가 우량주 발굴",
        "min_filters": {"fscore": 6, "safety_margin": 10},
    },
    "growth": {
        "w_value": 0.20,
        "w_flow": 0.25,
        "w_momentum": 0.25,
        "w_forecast": 0.20,
        "w_sentiment": 0.10,
        "label": "성장 투자",
        "description": "기관 수급과 성장성 중시",
        "min_filters": {"fscore": 5, "whale_score": 50},
    },
    "momentum": {
        "w_value": 0.15,
        "w_flow": 0.25,
        "w_momentum": 0.25,
        "w_forecast": 0.25,
        "w_sentiment": 0.10,
        "label": "모멘텀 투자",
        "description": "상대강도와 추세 추종",
        "min_filters": {"rs_percentile": 70},
    },
    "balanced": {
        "w_value": 0.25,
        "w_flow": 0.25,
        "w_momentum": 0.20,
        "w_forecast": 0.20,
        "w_sentiment": 0.10,
        "label": "균형 투자",
        "description": "가치·수급·모멘텀·전망·감성 균형",
        "min_filters": {},
    },
}


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------


def normalize_fscore(fscore: int, max_score: int = 9) -> float:
    """Normalize F-Score (0-9) to 0-100 with non-linear exponent.

    Formula: (fscore / max_score) ** 1.3 * 100

    The 1.3 exponent rewards high F-Scores while compressing the middle range.
    Examples: 5/9 → 44.4 (linear 55.6), 7/9 → 72.1 (linear 77.8),
              8/9 → 85.0 (linear 88.9), 9/9 → 100.0
    """
    if max_score <= 0:
        return 0.0
    ratio = max(fscore, 0) / max_score
    return round(ratio ** 1.3 * 100, 2)


def normalize_safety_margin(margin_pct: float | None) -> float:
    """Normalize RIM safety margin to 0-100 via sigmoid function.

    Formula: 100 / (1 + exp(-margin_pct / 25))

    The sigmoid maps the unbounded margin percentage to a smooth 0-100 range:
      -30% → 23.1,  0% → 50.0,  +30% → 76.8,  +50% → 88.1

    Returns 50.0 (neutral) when margin is unavailable.
    """
    if margin_pct is None:
        return 50.0
    # Clamp to prevent math.exp overflow for extreme values
    clamped = max(-500, min(margin_pct, 500))
    return round(100 / (1 + math.exp(-clamped / 25)), 2)


def _quadrant_bonus(quadrant: str | None) -> float:
    """Sector rotation quadrant adjustment for momentum score.

    Quadrants (RRG-style):
      leading   → +15  (strong momentum + improving RS)
      improving → +10  (RS starting to pick up)
      weakening →  -5  (momentum fading)
      lagging   → -15  (weak momentum + falling RS)
    """
    bonuses = {
        "leading": 15,
        "improving": 10,
        "weakening": -5,
        "lagging": -15,
    }
    return bonuses.get(quadrant, 0) if quadrant else 0


# ---------------------------------------------------------------------------
# Signal classification (shared helper)
# ---------------------------------------------------------------------------


def _classify_signal(score: float | None) -> str:
    """Classify a sub-score into a discrete signal level.

    Thresholds:
      >= 75 → strong_buy
      >= 60 → buy
      >= 40 → neutral
      >= 25 → sell
       < 25 → strong_sell
    """
    if score is None:
        return "unknown"
    if score >= 75:
        return "strong_buy"
    if score >= 60:
        return "buy"
    if score >= 40:
        return "neutral"
    if score >= 25:
        return "sell"
    return "strong_sell"


# ---------------------------------------------------------------------------
# Core composite score
# ---------------------------------------------------------------------------


def compute_composite_score(
    quant_data: dict[str, Any] | None,
    whale_data: dict[str, Any] | None,
    trend_data: dict[str, Any] | None,
    simulation_data: dict[str, Any] | None = None,
    sector_flow_bonus: float = 0.0,
    weights: dict[str, float] | None = None,
    sentiment_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute the Whaleback Composite Score (WCS).

    Combines five axes with configurable weights:
      value_score    = 0.55 * norm_fscore + 0.45 * norm_safety_margin
                       (penalized by data_completeness if < 1.0)
      flow_score     = whale_score (already 0-100) + sector_flow_bonus
      momentum_score = clamp(rs_percentile + quadrant_bonus, 0, 100)
      forecast_score = simulation_score (already 0-100)
      sentiment_score = normalized news sentiment score (0-100)

    When fewer than 5 axes are available, weights are redistributed
    proportionally among the available axes.

    Args:
        quant_data: {fscore, safety_margin, data_completeness} or None.
        whale_data: {whale_score, signal} or None.
        trend_data: {rs_percentile, sector_quadrant} or None.
        simulation_data: {simulation_score, ...} or None.
        sector_flow_bonus: Bonus points (0-15) from sector flow analysis.
        weights: {w_value, w_flow, w_momentum, w_forecast, w_sentiment} summing to 1.0, or None for defaults.
        sentiment_data: {sentiment_score, ...} or None.

    Returns:
        {composite_score, value_score, flow_score, momentum_score,
         forecast_score, sentiment_score, weights_used, confidence, axes_available}
    """
    w = dict(weights) if weights else dict(DEFAULT_WEIGHTS)

    # --- Sub-score: Value ---
    value_score: float | None = None
    has_value = False
    if quant_data is not None:
        fscore = quant_data.get("fscore")
        if fscore is not None:
            has_value = True
            margin = quant_data.get("safety_margin")
            completeness = min(quant_data.get("data_completeness", 1.0), 1.0)

            raw = 0.55 * normalize_fscore(fscore) + 0.45 * normalize_safety_margin(margin)
            value_score = round(raw * completeness, 2)

    # --- Sub-score: Flow ---
    flow_score: float | None = None
    has_flow = False
    if whale_data is not None:
        ws = whale_data.get("whale_score")
        if ws is not None:
            has_flow = True
            flow_score = round(float(ws), 2)

    # Apply sector flow bonus to flow score
    if has_flow and flow_score is not None and sector_flow_bonus != 0.0:
        flow_score = round(max(0.0, min(flow_score + sector_flow_bonus, 100.0)), 2)

    # --- Sub-score: Momentum ---
    momentum_score: float | None = None
    has_momentum = False
    if trend_data is not None:
        rs = trend_data.get("rs_percentile")
        if rs is not None:
            has_momentum = True
            quadrant = trend_data.get("sector_quadrant")
            raw_m = rs + _quadrant_bonus(quadrant)
            momentum_score = round(max(0.0, min(raw_m, 100.0)), 2)

    # --- Sub-score: Forecast ---
    forecast_score: float | None = None
    has_forecast = False
    if simulation_data is not None:
        sim_score = simulation_data.get("simulation_score")
        if sim_score is not None:
            has_forecast = True
            forecast_score = round(float(sim_score), 2)

    # --- Sub-score: Sentiment ---
    sentiment_score: float | None = None
    has_sentiment = False
    if sentiment_data is not None:
        sent_score = sentiment_data.get("sentiment_score")
        if sent_score is not None:
            has_sentiment = True
            sentiment_score = round(float(sent_score), 2)

    # --- Weight redistribution ---
    axes = {
        "w_value": (has_value, value_score),
        "w_flow": (has_flow, flow_score),
        "w_momentum": (has_momentum, momentum_score),
        "w_forecast": (has_forecast, forecast_score),
        "w_sentiment": (has_sentiment, sentiment_score),
    }
    axes_available = sum(1 for avail, _ in axes.values() if avail)

    if axes_available == 0:
        return {
            "composite_score": None,
            "value_score": None,
            "flow_score": None,
            "momentum_score": None,
            "forecast_score": None,
            "sentiment_score": None,
            "weights_used": {"w_value": 0.0, "w_flow": 0.0, "w_momentum": 0.0, "w_forecast": 0.0, "w_sentiment": 0.0},
            "confidence": 0.0,
            "axes_available": 0,
        }

    # Redistribute weights proportionally among available axes
    available_weight_sum = sum(w[k] for k, (avail, _) in axes.items() if avail)
    weights_used: dict[str, float] = {}
    for key, (avail, _) in axes.items():
        if avail and available_weight_sum > 0:
            weights_used[key] = round(w[key] / available_weight_sum, 4)
        else:
            weights_used[key] = 0.0

    # --- Composite ---
    composite = 0.0
    if has_value and value_score is not None:
        composite += weights_used["w_value"] * value_score
    if has_flow and flow_score is not None:
        composite += weights_used["w_flow"] * flow_score
    if has_momentum and momentum_score is not None:
        composite += weights_used["w_momentum"] * momentum_score
    if has_forecast and forecast_score is not None:
        composite += weights_used["w_forecast"] * forecast_score
    if has_sentiment and sentiment_score is not None:
        composite += weights_used["w_sentiment"] * sentiment_score

    return {
        "composite_score": round(composite, 2),
        "value_score": value_score,
        "flow_score": flow_score,
        "momentum_score": momentum_score,
        "forecast_score": forecast_score,
        "sentiment_score": sentiment_score,
        "weights_used": weights_used,
        "confidence": round(axes_available / 5, 2),
        "axes_available": axes_available,
    }


# ---------------------------------------------------------------------------
# Confluence & divergence detection
# ---------------------------------------------------------------------------


def detect_confluence(
    value_score: float | None,
    flow_score: float | None,
    momentum_score: float | None,
    forecast_score: float | None = None,
) -> dict[str, Any]:
    """Detect signal confluence and divergence across the four axes.

    Confluence tiers (1-5):
      5 - All known signals in the same *strong* direction
      4 - All known signals in the same direction (buy+ or sell+)
      3 - Two strong signals + rest neutral
      2 - Exactly one strong signal only
      1 - Conflicting or no strong signals

    Divergence types:
      value_momentum_divergence    - 가치-모멘텀 괴리 (바닥 가능성)
      momentum_value_divergence    - 모멘텀-가치 괴리 (과열 주의)
      flow_value_divergence        - 수급-가치 괴리 (테마주 가능성)
      forecast_value_divergence    - 전망-가치 괴리 (시뮬레이션 긍정적이나 가치 부족)
      forecast_momentum_divergence - 전망-모멘텀 괴리 (단기 강세이나 장기 불확실)

    Returns:
        {confluence_tier, confluence_pattern, value_signal, flow_signal,
         momentum_signal, forecast_signal, divergence_type, divergence_severity,
         divergence_label, action_label, action_description}
    """
    v_sig = _classify_signal(value_score)
    f_sig = _classify_signal(flow_score)
    m_sig = _classify_signal(momentum_score)
    fc_sig = _classify_signal(forecast_score)

    known_signals = [s for s in (v_sig, f_sig, m_sig, fc_sig) if s != "unknown"]
    num_known = len(known_signals)

    buy_count = sum(1 for s in known_signals if s in BUY_SIGNALS)
    sell_count = sum(1 for s in known_signals if s in SELL_SIGNALS)
    strong_buy_count = sum(1 for s in known_signals if s == "strong_buy")
    strong_sell_count = sum(1 for s in known_signals if s == "strong_sell")

    # --- Confluence tier ---
    if num_known >= 3 and strong_buy_count == num_known:
        tier = 5
        direction = "buy"
    elif num_known >= 3 and strong_sell_count == num_known:
        tier = 5
        direction = "sell"
    elif num_known >= 3 and buy_count == num_known:
        tier = 4
        direction = "buy"
    elif num_known >= 3 and sell_count == num_known:
        tier = 4
        direction = "sell"
    elif (strong_buy_count >= 2 and buy_count + strong_buy_count >= 2
          and (num_known - buy_count) <= 1):
        # 2 strong buy + rest neutral
        tier = 3
        direction = "buy"
    elif (strong_sell_count >= 2 and sell_count + strong_sell_count >= 2
          and (num_known - sell_count) <= 1):
        tier = 3
        direction = "sell"
    elif strong_buy_count == 1 and sell_count == 0 and strong_sell_count == 0:
        tier = 2
        direction = "buy"
    elif strong_sell_count == 1 and buy_count == 0 and strong_buy_count == 0:
        tier = 2
        direction = "sell"
    else:
        tier = 1
        direction = "neutral"

    # --- Confluence pattern description ---
    pattern = _describe_pattern(tier, direction, num_known)

    # --- Divergence detection ---
    div_type: str | None = None
    div_severity: str | None = None
    div_label: str | None = None

    if v_sig in BUY_SIGNALS and m_sig in SELL_SIGNALS:
        div_type = "value_momentum_divergence"
        div_severity = "medium"
        div_label = "가치-모멘텀 괴리 (바닥 가능성)"
    elif m_sig in BUY_SIGNALS and v_sig in SELL_SIGNALS:
        div_type = "momentum_value_divergence"
        div_severity = "high"
        div_label = "모멘텀-가치 괴리 (과열 주의)"
    elif f_sig in BUY_SIGNALS and v_sig in SELL_SIGNALS:
        div_type = "flow_value_divergence"
        div_severity = "medium"
        div_label = "수급-가치 괴리 (테마주 가능성)"
    elif fc_sig in BUY_SIGNALS and v_sig in SELL_SIGNALS:
        div_type = "forecast_value_divergence"
        div_severity = "low"
        div_label = "전망-가치 괴리 (시뮬레이션 긍정적이나 가치 부족)"
    elif fc_sig in SELL_SIGNALS and m_sig in BUY_SIGNALS:
        div_type = "forecast_momentum_divergence"
        div_severity = "medium"
        div_label = "전망-모멘텀 괴리 (단기 강세이나 장기 불확실)"

    # --- Action label ---
    action_label, action_desc = _action_for_tier(tier, direction)

    return {
        "confluence_tier": tier,
        "confluence_pattern": pattern,
        "value_signal": v_sig,
        "flow_signal": f_sig,
        "momentum_signal": m_sig,
        "forecast_signal": fc_sig,
        "divergence_type": div_type,
        "divergence_severity": div_severity,
        "divergence_label": div_label,
        "action_label": action_label,
        "action_description": action_desc,
    }


def _describe_pattern(tier: int, direction: str, num_known: int) -> str:
    """Human-readable confluence pattern."""
    if num_known == 0:
        return "no_data"
    if tier == 5:
        prefix = "quad" if num_known >= 4 else "triple"
        return f"{prefix}_strong_{direction}"
    if tier == 4:
        prefix = "quad" if num_known >= 4 else "triple"
        return f"{prefix}_{direction}"
    if tier == 3:
        return f"multi_strong_{direction}"
    if tier == 2:
        return f"single_strong_{direction}"
    return "mixed"


def _action_for_tier(tier: int, direction: str) -> tuple[str, str]:
    """Map confluence tier + direction to Korean action label and description."""
    if tier == 5:
        if direction == "buy":
            return "적극 매수", "가치·수급·모멘텀·전망 모두 강한 매수 신호입니다"
        return "적극 매도", "가치·수급·모멘텀·전망 모두 강한 매도 신호입니다"
    if tier == 4:
        if direction == "buy":
            return "매수 추천", "다수 축이 매수 방향을 가리킵니다"
        return "매도 추천", "다수 축이 매도 방향을 가리킵니다"
    if tier == 3:
        if direction == "buy":
            return "매수 검토", "두 가지 이상의 강한 매수 신호가 있습니다"
        return "매도 검토", "두 가지 이상의 강한 매도 신호가 있습니다"
    if tier == 2:
        return "관심 편입", "강한 신호가 하나 감지되었습니다"
    return "관망", "명확한 방향성이 없어 추가 관찰이 필요합니다"


# ---------------------------------------------------------------------------
# Score classification
# ---------------------------------------------------------------------------


def classify_composite_score(score: float | None) -> dict[str, str]:
    """Classify a WCS composite score into a qualitative tier.

    Tiers:
      80-100  excellent  최우량   emerald
      65-79   good       우량     green
      50-64   fair       양호     blue
      35-49   average    보통     yellow
      20-34   caution    주의     orange
       0-19   risk       위험     red
       None   unknown    분석불가 gray
    """
    if score is None:
        return {
            "tier": "unknown",
            "label": "분석 불가",
            "color": "gray",
            "description": "데이터 부족으로 종합 점수를 산출할 수 없습니다",
        }
    if score >= 80:
        return {
            "tier": "excellent",
            "label": "최우량",
            "color": "emerald",
            "description": "가치·수급·모멘텀·전망이 모두 우수합니다",
        }
    if score >= 65:
        return {
            "tier": "good",
            "label": "우량",
            "color": "green",
            "description": "대부분의 지표가 긍정적입니다",
        }
    if score >= 50:
        return {
            "tier": "fair",
            "label": "양호",
            "color": "blue",
            "description": "전반적으로 무난한 수준입니다",
        }
    if score >= 35:
        return {
            "tier": "average",
            "label": "보통",
            "color": "yellow",
            "description": "일부 지표에서 주의가 필요합니다",
        }
    if score >= 20:
        return {
            "tier": "caution",
            "label": "주의",
            "color": "orange",
            "description": "다수 지표가 부정적입니다",
        }
    return {
        "tier": "risk",
        "label": "위험",
        "color": "red",
        "description": "대부분의 지표가 위험 신호를 보이고 있습니다",
    }


# ---------------------------------------------------------------------------
# Investor profile scoring
# ---------------------------------------------------------------------------


def compute_profile_score(
    quant_data: dict[str, Any] | None,
    whale_data: dict[str, Any] | None,
    trend_data: dict[str, Any] | None,
    simulation_data: dict[str, Any] | None = None,
    sector_flow_bonus: float = 0.0,
    profile: str = "balanced",
) -> dict[str, Any]:
    """Compute composite score using an investor-profile's weight preset.

    Profiles apply custom weight distributions and minimum eligibility filters:
      value    - 가치 투자 (heavily weighted toward F-Score / safety margin)
      growth   - 성장 투자 (emphasizes institutional flow)
      momentum - 모멘텀 투자 (RS percentile dominant)
      balanced - 균형 투자 (default equal-ish weights)

    Args:
        quant_data: Same as compute_composite_score.
        whale_data: Same as compute_composite_score.
        trend_data: Same as compute_composite_score.
        simulation_data: {simulation_score, ...} or None.
        sector_flow_bonus: Bonus points (0-15) from sector flow analysis.
        profile: One of "value", "growth", "momentum", "balanced".

    Returns:
        {score, eligible, profile, profile_label, filters_met}
    """
    prof = INVESTOR_PROFILES.get(profile)
    if prof is None:
        logger.warning("Unknown investor profile '%s', falling back to balanced", profile)
        prof = INVESTOR_PROFILES["balanced"]

    profile_weights = {
        "w_value": prof["w_value"],
        "w_flow": prof["w_flow"],
        "w_momentum": prof["w_momentum"],
        "w_forecast": prof["w_forecast"],
        "w_sentiment": prof.get("w_sentiment", 0.10),
    }

    result = compute_composite_score(
        quant_data, whale_data, trend_data, simulation_data, sector_flow_bonus, profile_weights
    )

    # --- Eligibility check ---
    min_filters: dict[str, float] = prof.get("min_filters", {})
    filters_met: dict[str, bool] = {}
    eligible = True

    for filt, threshold in min_filters.items():
        actual = _extract_filter_value(filt, quant_data, whale_data, trend_data, simulation_data)
        if actual is None:
            filters_met[filt] = False
            eligible = False
        else:
            passed = actual >= threshold
            filters_met[filt] = passed
            if not passed:
                eligible = False

    return {
        "score": result.get("composite_score"),
        "eligible": eligible,
        "profile": profile,
        "profile_label": prof["label"],
        "filters_met": filters_met,
    }


def _extract_filter_value(
    filt: str,
    quant_data: dict[str, Any] | None,
    whale_data: dict[str, Any] | None,
    trend_data: dict[str, Any] | None,
    simulation_data: dict[str, Any] | None = None,
) -> float | None:
    """Extract a raw metric value for eligibility filtering."""
    if filt == "fscore" and quant_data is not None:
        return quant_data.get("fscore")
    if filt == "safety_margin" and quant_data is not None:
        return quant_data.get("safety_margin")
    if filt == "whale_score" and whale_data is not None:
        return whale_data.get("whale_score")
    if filt == "rs_percentile" and trend_data is not None:
        return trend_data.get("rs_percentile")
    if filt == "simulation_score" and simulation_data is not None:
        return simulation_data.get("simulation_score")
    return None
