"""Quant analysis endpoints: valuation, F-Score, grade, rankings."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from whaleback.db.async_repositories import get_quant_snapshot, get_quant_rankings, get_stock_detail
from whaleback.web.dependencies import get_db_session, get_cache
from whaleback.web.cache import CacheService
from whaleback.web.schemas import (
    QuantValuation,
    FScoreResponse,
    QuantRankingItem,
    PaginatedResponse,
    PaginatedMeta,
    ApiResponse,
    Meta,
)

router = APIRouter(prefix="/analysis/quant", tags=["quant"])


@router.get("/valuation/{ticker}", response_model=ApiResponse[QuantValuation])
async def quant_valuation(
    ticker: str,
    session: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache),
):
    """Get RIM valuation, intrinsic value, and safety margin for a stock."""
    cache_key = f"quant:valuation:{ticker}"
    cached = await cache.get(cache_key)
    if cached:
        return ApiResponse(data=cached, meta=Meta(cached=True))

    snapshot = await get_quant_snapshot(session, ticker)
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"No quant analysis for {ticker}")

    stock = await get_stock_detail(session, ticker)
    current_price = None
    name = None
    if stock:
        name = stock.get("name")
        if stock.get("latest_price"):
            current_price = stock["latest_price"].get("close")

    result = {
        "ticker": ticker,
        "name": name,
        "as_of_date": snapshot.get("trade_date", ""),
        "current_price": current_price,
        "rim_value": snapshot.get("rim_value"),
        "safety_margin_pct": snapshot.get("safety_margin"),
        "is_undervalued": (snapshot.get("safety_margin") or 0) > 0
        if snapshot.get("safety_margin") is not None
        else None,
        "grade": snapshot.get("investment_grade"),
        "grade_label": _grade_label(snapshot.get("investment_grade")),
    }

    await cache.set(cache_key, result, ttl=300)
    return ApiResponse(data=result)


@router.get("/fscore/{ticker}", response_model=ApiResponse[FScoreResponse])
async def quant_fscore(
    ticker: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Get detailed F-Score breakdown for a stock."""
    snapshot = await get_quant_snapshot(session, ticker)
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"No F-Score data for {ticker}")

    criteria = snapshot.get("fscore_detail") or []

    return ApiResponse(
        data={
            "ticker": ticker,
            "total_score": snapshot.get("fscore", 0),
            "max_score": 9,
            "criteria": criteria,
            "data_completeness": snapshot.get("data_completeness", 0),
        }
    )


@router.get("/grade/{ticker}")
async def quant_grade(
    ticker: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Get investment grade for a stock."""
    snapshot = await get_quant_snapshot(session, ticker)
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"No grade data for {ticker}")

    grade = snapshot.get("investment_grade", "F")
    return ApiResponse(
        data={
            "ticker": ticker,
            "grade": grade,
            "label": _grade_label(grade),
            "fscore": snapshot.get("fscore"),
            "safety_margin": snapshot.get("safety_margin"),
            "data_completeness": snapshot.get("data_completeness"),
        }
    )


@router.get("/rankings", response_model=PaginatedResponse[QuantRankingItem])
async def quant_rankings(
    market: str | None = Query(None),
    min_fscore: int | None = Query(None, ge=0, le=9),
    grade: str | None = Query(None),
    sort_by: str = Query("safety_margin", description="Sort field"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache),
):
    """Get ranked stocks by quant analysis scores."""
    cache_key = f"quant:rankings:{market}:{min_fscore}:{grade}:{sort_by}:{page}:{size}"
    cached = await cache.get(cache_key)
    if cached:
        return PaginatedResponse(
            data=cached["data"],
            meta=PaginatedMeta(**cached["meta"], cached=True),
        )

    rows, total = await get_quant_rankings(
        session,
        market=market,
        min_fscore=min_fscore,
        grade=grade,
        sort_by=sort_by,
        page=page,
        size=size,
    )

    result = {
        "data": rows,
        "meta": {"total": total, "page": page, "size": size},
    }
    await cache.set(cache_key, result, ttl=300)

    return PaginatedResponse(
        data=rows,
        meta=PaginatedMeta(total=total, page=page, size=size),
    )


def _grade_label(grade: str | None) -> str:
    labels = {
        "A+": "강력 매수",
        "A": "매수",
        "B+": "매수 검토",
        "B": "보유",
        "C+": "관망",
        "C": "주의",
        "D": "위험",
        "F": "데이터 부족",
    }
    return labels.get(grade or "", "알 수 없음")
