"""News sentiment analysis API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from whaleback.db import async_repositories as repo
from whaleback.web.cache import CacheService
from whaleback.web.dependencies import get_db_session, get_cache
from whaleback.web.schemas import (
    ApiResponse,
    Meta,
    PaginatedResponse,
    PaginatedMeta,
    NewsSnapshot,
    NewsTopItem,
)

router = APIRouter(prefix="/analysis/news-sentiment", tags=["news-sentiment"])


@router.get("/top", response_model=PaginatedResponse[NewsTopItem])
async def get_news_top(
    market: str | None = Query(None),
    min_score: float | None = Query(None),
    signal: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache),
):
    """Get top stocks by news sentiment score."""
    cache_key = f"news:top:{market}:{min_score}:{signal}:{page}:{size}"
    cached = await cache.get(cache_key)
    if cached:
        return PaginatedResponse(
            data=cached["data"],
            meta=PaginatedMeta(**cached["meta"], cached=True),
        )

    rows, total = await repo.get_news_top(
        session, market=market, min_score=min_score, signal=signal, page=page, size=size
    )

    result = {"data": rows, "meta": {"total": total, "page": page, "size": size}}
    await cache.set(cache_key, result, ttl=300)

    return PaginatedResponse(
        data=rows,
        meta=PaginatedMeta(total=total, page=page, size=size),
    )


@router.get("/{ticker}", response_model=ApiResponse[NewsSnapshot])
async def get_news_sentiment(
    ticker: str,
    session: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache),
):
    """Get news sentiment analysis for a stock."""
    cache_key = f"news:{ticker}"
    cached = await cache.get(cache_key)
    if cached:
        return ApiResponse(data=cached, meta=Meta(cached=True))

    data = await repo.get_news_snapshot(session, ticker)
    if not data:
        raise HTTPException(status_code=404, detail=f"No news sentiment data for {ticker}")

    stock = await repo.get_stock_detail(session, ticker)
    if stock:
        data["name"] = stock.get("name")

    result = NewsSnapshot(**data)
    await cache.set(cache_key, result.model_dump(), ttl=300)
    return ApiResponse(data=result)
