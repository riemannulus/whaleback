"""Composite (WCS) analysis endpoints: composite score, detail, rankings."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from whaleback.db.async_repositories import (
    get_composite_snapshot,
    get_composite_rankings,
    get_flow_snapshot,
    get_technical_snapshot,
    get_risk_snapshot,
    get_stock_detail,
)
from whaleback.web.dependencies import get_db_session, get_cache
from whaleback.web.cache import CacheService
from whaleback.web.schemas import (
    CompositeScore,
    CompositeDetail,
    CompositeRankingItem,
    PaginatedResponse,
    PaginatedMeta,
    ApiResponse,
    Meta,
)

router = APIRouter(prefix="/analysis/composite", tags=["composite"])


@router.get("/score/{ticker}", response_model=ApiResponse[CompositeScore])
async def composite_score(
    ticker: str,
    session: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache),
):
    """Get WCS composite score for a stock."""
    cache_key = f"composite:score:{ticker}"
    cached = await cache.get(cache_key)
    if cached:
        return ApiResponse(data=cached, meta=Meta(cached=True))

    snapshot = await get_composite_snapshot(session, ticker)
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"No composite analysis for {ticker}")

    stock = await get_stock_detail(session, ticker)
    if stock:
        snapshot["name"] = stock.get("name")

    await cache.set(cache_key, snapshot, ttl=300)
    return ApiResponse(data=snapshot)


@router.get("/detail/{ticker}", response_model=ApiResponse[CompositeDetail])
async def composite_detail(
    ticker: str,
    session: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache),
):
    """Get full composite analysis detail including flow, technical, risk."""
    cache_key = f"composite:detail:{ticker}"
    cached = await cache.get(cache_key)
    if cached:
        return ApiResponse(data=cached, meta=Meta(cached=True))

    composite = await get_composite_snapshot(session, ticker)
    if not composite:
        raise HTTPException(status_code=404, detail=f"No composite analysis for {ticker}")

    stock = await get_stock_detail(session, ticker)
    if stock:
        composite["name"] = stock.get("name")

    flow = await get_flow_snapshot(session, ticker)
    technical = await get_technical_snapshot(session, ticker)
    risk = await get_risk_snapshot(session, ticker)

    result = {
        "composite": composite,
        "flow": flow,
        "technical": technical,
        "risk": risk,
    }

    await cache.set(cache_key, result, ttl=300)
    return ApiResponse(data=result)


@router.get("/rankings", response_model=PaginatedResponse[CompositeRankingItem])
async def composite_rankings(
    market: str | None = Query(None),
    min_score: float | None = Query(None, ge=0, le=100),
    min_confluence: int | None = Query(None, ge=1, le=5),
    score_tier: str | None = Query(None),
    sort_by: str = Query("composite_score", description="Sort field"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache),
):
    """Get ranked stocks by WCS composite score."""
    cache_key = f"composite:rankings:{market}:{min_score}:{min_confluence}:{score_tier}:{sort_by}:{page}:{size}"
    cached = await cache.get(cache_key)
    if cached:
        return PaginatedResponse(
            data=cached["data"],
            meta=PaginatedMeta(**cached["meta"], cached=True),
        )

    rows, total = await get_composite_rankings(
        session,
        market=market,
        min_score=min_score,
        min_confluence=min_confluence,
        score_tier=score_tier,
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
