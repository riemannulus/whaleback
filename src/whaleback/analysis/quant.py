"""Quant analysis module: RIM valuation, Modified F-Score, Investment Grade.

All functions are pure computations with no database dependency.
Input: fundamental data as dicts/floats
Output: computed metrics as dicts/tuples
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def compute_rim(
    bps: float | None,
    roe: float | None,
    risk_free_rate: float = 0.035,
    equity_risk_premium: float = 0.065,
    growth_rate: float = 0.0,
) -> dict[str, Any]:
    """Compute Residual Income Model (RIM) intrinsic value.

    Formula: intrinsic_value = BPS + (ROE% - r) * BPS / (r - g)
    where r = risk_free_rate + equity_risk_premium (required return)
          g = perpetuity growth rate

    Returns dict with: rim_value, safety_margin_pct, is_undervalued, inputs
    """
    required_return = risk_free_rate + equity_risk_premium

    # Validation
    if bps is None or roe is None:
        return {
            "rim_value": None,
            "safety_margin_pct": None,
            "computable": False,
            "reason": "missing_data",
        }

    if bps <= 0:
        return {
            "rim_value": None,
            "safety_margin_pct": None,
            "computable": False,
            "reason": "negative_bps",
        }

    # ROE from DB is in percentage (e.g., 13.21 means 13.21%)
    roe_decimal = roe / 100.0

    # Check for degenerate case: required_return == growth_rate
    denominator = required_return - growth_rate
    if abs(denominator) < 1e-10:
        # Fallback: no-growth perpetuity
        if roe_decimal > required_return:
            # Infinite value theoretically, cap at BPS * 10
            rim_value = bps * 10
        else:
            rim_value = bps
    else:
        # Standard RIM formula
        residual_income = (roe_decimal - required_return) * bps
        rim_value = bps + residual_income / denominator

    # Ensure non-negative
    rim_value = max(rim_value, 0)

    return {
        "rim_value": round(rim_value, 2),
        "computable": True,
        "inputs": {
            "bps": bps,
            "roe_pct": roe,
            "required_return": required_return,
            "growth_rate": growth_rate,
        },
    }


def compute_safety_margin(rim_value: float | None, current_price: int | None) -> dict[str, Any]:
    """Compute safety margin between intrinsic value and market price.

    safety_margin_pct = (rim_value - current_price) / rim_value * 100
    Positive = undervalued, Negative = overvalued
    """
    if rim_value is None or current_price is None or rim_value <= 0 or current_price <= 0:
        return {"safety_margin_pct": None, "is_undervalued": None}

    margin = (rim_value - current_price) / rim_value * 100.0
    return {
        "safety_margin_pct": round(margin, 2),
        "is_undervalued": margin > 0,
    }


def compute_fscore(
    current: dict[str, Any] | None,
    previous: dict[str, Any] | None,
    sector_medians: dict[str, float] | None = None,
    volume_current: int | None = None,
    volume_previous: int | None = None,
) -> dict[str, Any]:
    """Compute Modified Piotroski F-Score (0-9) using available fundamental data.

    Adapted for Korean market data available via pykrx:
    1. EPS > 0 (profitability)
    2. ROE > 0 (return on equity)
    3. ROE increasing YoY
    4. EPS increasing YoY
    5. BPS increasing YoY (book value growth - retained earnings proxy)
    6. PBR < sector median (relative valuation)
    7. DIV > 0 (shareholder returns)
    8. PER < sector median AND PER > 0 (earnings valuation)
    9. Volume increasing (liquidity improvement)

    Args:
        current: Current period fundamentals {bps, per, pbr, eps, div, dps, roe}
        previous: Previous period fundamentals (same keys)
        sector_medians: {median_pbr, median_per} for the stock's sector
        volume_current: Current period average volume
        volume_previous: Previous period average volume

    Returns:
        {total_score, max_score, criteria: [...], data_completeness}
    """
    criteria = []
    computable_count = 0
    total_signals = 9

    if current is None:
        return {
            "total_score": 0,
            "max_score": total_signals,
            "criteria": [],
            "data_completeness": 0.0,
        }

    # Signal 1: EPS > 0 (Profitability)
    eps = current.get("eps")
    if eps is not None:
        computable_count += 1
        score = 1 if eps > 0 else 0
        criteria.append(
            {
                "name": "positive_eps",
                "score": score,
                "value": eps,
                "label": "당기순이익 > 0",
            }
        )
    else:
        criteria.append(
            {
                "name": "positive_eps",
                "score": 0,
                "value": None,
                "label": "당기순이익 > 0",
                "note": "데이터 없음",
            }
        )

    # Signal 2: ROE > 0
    roe = current.get("roe")
    if roe is not None:
        computable_count += 1
        score = 1 if roe > 0 else 0
        criteria.append(
            {
                "name": "positive_roe",
                "score": score,
                "value": roe,
                "label": "자기자본이익률 > 0",
            }
        )
    else:
        criteria.append(
            {
                "name": "positive_roe",
                "score": 0,
                "value": None,
                "label": "자기자본이익률 > 0",
                "note": "데이터 없음",
            }
        )

    # Signal 3: ROE increasing YoY
    roe_prev = previous.get("roe") if previous else None
    if roe is not None and roe_prev is not None:
        computable_count += 1
        score = 1 if roe > roe_prev else 0
        criteria.append(
            {
                "name": "roe_increasing",
                "score": score,
                "value": round(roe - roe_prev, 4),
                "label": "ROE 증가",
            }
        )
    else:
        criteria.append(
            {
                "name": "roe_increasing",
                "score": 0,
                "value": None,
                "label": "ROE 증가",
                "note": "전기 데이터 없음",
            }
        )

    # Signal 4: EPS increasing YoY
    eps_prev = previous.get("eps") if previous else None
    if eps is not None and eps_prev is not None:
        computable_count += 1
        score = 1 if eps > eps_prev else 0
        criteria.append(
            {
                "name": "eps_increasing",
                "score": score,
                "value": round(eps - eps_prev, 2),
                "label": "EPS 증가",
            }
        )
    else:
        criteria.append(
            {
                "name": "eps_increasing",
                "score": 0,
                "value": None,
                "label": "EPS 증가",
                "note": "전기 데이터 없음",
            }
        )

    # Signal 5: BPS increasing YoY (retained earnings proxy)
    bps = current.get("bps")
    bps_prev = previous.get("bps") if previous else None
    if bps is not None and bps_prev is not None:
        computable_count += 1
        score = 1 if bps > bps_prev else 0
        criteria.append(
            {
                "name": "bps_increasing",
                "score": score,
                "value": round(bps - bps_prev, 2),
                "label": "BPS 증가 (자본축적)",
            }
        )
    else:
        criteria.append(
            {
                "name": "bps_increasing",
                "score": 0,
                "value": None,
                "label": "BPS 증가 (자본축적)",
                "note": "전기 데이터 없음",
            }
        )

    # Signal 6: PBR < sector median (relative valuation)
    pbr = current.get("pbr")
    median_pbr = sector_medians.get("median_pbr") if sector_medians else None
    if pbr is not None and median_pbr is not None and pbr > 0:
        computable_count += 1
        score = 1 if pbr < median_pbr else 0
        criteria.append(
            {
                "name": "pbr_below_sector",
                "score": score,
                "value": pbr,
                "label": f"PBR < 섹터 중앙값 ({median_pbr:.2f})",
            }
        )
    else:
        criteria.append(
            {
                "name": "pbr_below_sector",
                "score": 0,
                "value": pbr,
                "label": "PBR < 섹터 중앙값",
                "note": "섹터 데이터 없음",
            }
        )

    # Signal 7: DIV > 0 (shareholder returns)
    div_val = current.get("div")
    if div_val is not None:
        computable_count += 1
        score = 1 if div_val > 0 else 0
        criteria.append(
            {
                "name": "positive_dividend",
                "score": score,
                "value": div_val,
                "label": "배당수익률 > 0",
            }
        )
    else:
        criteria.append(
            {
                "name": "positive_dividend",
                "score": 0,
                "value": None,
                "label": "배당수익률 > 0",
                "note": "데이터 없음",
            }
        )

    # Signal 8: PER < sector median AND PER > 0
    per = current.get("per")
    median_per = sector_medians.get("median_per") if sector_medians else None
    if per is not None and median_per is not None and per > 0 and median_per > 0:
        computable_count += 1
        score = 1 if per < median_per else 0
        criteria.append(
            {
                "name": "per_below_sector",
                "score": score,
                "value": per,
                "label": f"PER < 섹터 중앙값 ({median_per:.2f})",
            }
        )
    else:
        criteria.append(
            {
                "name": "per_below_sector",
                "score": 0,
                "value": per,
                "label": "PER < 섹터 중앙값",
                "note": "섹터/PER 데이터 없음",
            }
        )

    # Signal 9: Volume increasing
    if volume_current is not None and volume_previous is not None and volume_previous > 0:
        computable_count += 1
        score = 1 if volume_current > volume_previous else 0
        criteria.append(
            {
                "name": "volume_increasing",
                "score": score,
                "value": volume_current - volume_previous,
                "label": "거래량 증가",
            }
        )
    else:
        criteria.append(
            {
                "name": "volume_increasing",
                "score": 0,
                "value": None,
                "label": "거래량 증가",
                "note": "거래량 데이터 없음",
            }
        )

    total_score = sum(c["score"] for c in criteria)
    data_completeness = round(computable_count / total_signals, 2)

    return {
        "total_score": total_score,
        "max_score": total_signals,
        "criteria": criteria,
        "data_completeness": data_completeness,
    }


def compute_investment_grade(
    fscore: int,
    safety_margin_pct: float | None,
    data_completeness: float,
) -> dict[str, Any]:
    """Compute investment grade based on F-Score and safety margin.

    Grades:
        A+ : F-Score >= 8, safety_margin >= 30%
        A  : F-Score >= 7, safety_margin >= 20%
        B+ : F-Score >= 6, safety_margin >= 10%
        B  : F-Score >= 5, safety_margin >= 0%
        C+ : F-Score >= 4
        C  : F-Score >= 3
        D  : F-Score < 3
        F  : data_completeness < 0.5
    """
    if data_completeness < 0.5:
        return {"grade": "F", "label": "데이터 부족", "description": "분석 가능 데이터 50% 미만"}

    margin = safety_margin_pct if safety_margin_pct is not None else -999

    if fscore >= 8 and margin >= 30:
        return {"grade": "A+", "label": "강력 매수", "description": "재무 우수 + 고안전마진"}
    elif fscore >= 7 and margin >= 20:
        return {"grade": "A", "label": "매수", "description": "재무 양호 + 적정 안전마진"}
    elif fscore >= 6 and margin >= 10:
        return {"grade": "B+", "label": "매수 검토", "description": "양호한 재무 + 소폭 저평가"}
    elif fscore >= 5 and margin >= 0:
        return {"grade": "B", "label": "보유", "description": "적정 재무 + 적정 가치"}
    elif fscore >= 4:
        return {"grade": "C+", "label": "관망", "description": "보통 재무 상태"}
    elif fscore >= 3:
        return {"grade": "C", "label": "주의", "description": "재무 취약 신호"}
    else:
        return {"grade": "D", "label": "위험", "description": "재무 건전성 심각 우려"}
