"""Whale tracking endpoints: score, accumulation, top picks."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from whaleback.db.async_repositories import (
    get_whale_snapshot,
    get_whale_top,
    get_investor_history,
    get_stock_detail,
)
from whaleback.web.dependencies import get_db_session, get_cache
from whaleback.web.cache import CacheService
from whaleback.web.schemas import (
    WhaleScore,
    WhaleTopItem,
    WhaleAccumulationDay,
    PaginatedResponse,
    PaginatedMeta,
    ApiResponse,
    Meta,
)

router = APIRouter(prefix="/analysis/whale", tags=["whale"])


@router.get("/score/{ticker}", response_model=ApiResponse[WhaleScore])
async def whale_score(
    ticker: str,
    session: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache),
):
    """Get composite whale score for a stock."""
    cache_key = f"whale:score:{ticker}"
    cached = await cache.get(cache_key)
    if cached:
        return ApiResponse(data=cached, meta=Meta(cached=True))

    snapshot = await get_whale_snapshot(session, ticker)
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"No whale data for {ticker}")

    stock = await get_stock_detail(session, ticker)
    name = stock.get("name") if stock else None

    signal_labels = {
        "strong_accumulation": "강한 매집",
        "mild_accumulation": "완만한 매집",
        "neutral": "중립",
        "distribution": "매도 우위",
    }

    result = {
        "ticker": ticker,
        "name": name,
        "as_of_date": snapshot.get("trade_date", ""),
        "lookback_days": 20,
        "whale_score": snapshot.get("whale_score", 0),
        "signal": snapshot.get("signal", "neutral"),
        "signal_label": signal_labels.get(snapshot.get("signal", ""), "알 수 없음"),
        "components": {
            "institution_net": {
                "net_total": snapshot.get("institution_net_20d", 0),
                "consistency": snapshot.get("institution_consistency", 0),
            },
            "foreign_net": {
                "net_total": snapshot.get("foreign_net_20d", 0),
                "consistency": snapshot.get("foreign_consistency", 0),
            },
            "pension_net": {
                "net_total": snapshot.get("pension_net_20d", 0),
                "consistency": snapshot.get("pension_consistency", 0),
            },
        },
    }

    await cache.set(cache_key, result, ttl=300)
    return ApiResponse(data=result)


@router.get("/accumulation/{ticker}", response_model=ApiResponse[list[WhaleAccumulationDay]])
async def whale_accumulation(
    ticker: str,
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    session: AsyncSession = Depends(get_db_session),
):
    """Get daily accumulation timeline for a stock."""
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=40)

    data = await get_investor_history(session, ticker, start_date, end_date)
    return ApiResponse(data=data)


@router.get("/top", response_model=PaginatedResponse[WhaleTopItem])
async def whale_top(
    market: str | None = Query(None),
    min_score: float | None = Query(None, ge=0, le=100),
    signal: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache),
):
    """Get top whale-accumulated stocks ranked by whale score."""
    cache_key = f"whale:top:{market}:{min_score}:{signal}:{page}:{size}"
    cached = await cache.get(cache_key)
    if cached:
        return PaginatedResponse(
            data=cached["data"],
            meta=PaginatedMeta(**cached["meta"], cached=True),
        )

    rows, total = await get_whale_top(
        session, market=market, min_score=min_score, signal=signal, page=page, size=size
    )

    result = {"data": rows, "meta": {"total": total, "page": page, "size": size}}
    await cache.set(cache_key, result, ttl=300)

    return PaginatedResponse(
        data=rows,
        meta=PaginatedMeta(total=total, page=page, size=size),
    )
