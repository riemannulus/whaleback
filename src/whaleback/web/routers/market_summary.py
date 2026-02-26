"""시장 AI 요약 API 라우터"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from whaleback.db.async_repositories import get_market_summary, get_market_summary_list
from whaleback.web.dependencies import get_db_session, get_cache
from whaleback.web.cache import CacheService
from whaleback.web.schemas import ApiResponse, MarketSummaryResponse, Meta

router = APIRouter(prefix="/analysis/market-summary", tags=["market-summary"])


@router.get("", response_model=ApiResponse[MarketSummaryResponse | None])
async def get_latest_market_summary(
    session: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache),
):
    """최신 시장 AI 요약 조회"""
    cache_key = "market_summary:latest"
    cached = await cache.get(cache_key)
    if cached:
        return ApiResponse(data=cached, meta=Meta(cached=True))

    summary = await get_market_summary(session)
    if summary is None:
        return ApiResponse(data=None)

    response = MarketSummaryResponse.model_validate(summary)
    await cache.set(cache_key, response.model_dump(mode="json"), ttl=300)
    return ApiResponse(data=response)


@router.get("/history", response_model=ApiResponse[list[MarketSummaryResponse]])
async def get_market_summary_history(
    limit: int = Query(default=10, le=30),
    session: AsyncSession = Depends(get_db_session),
):
    """시장 AI 요약 이력 조회"""
    summaries = await get_market_summary_list(session, limit=limit)
    return ApiResponse(data=[MarketSummaryResponse.model_validate(s) for s in summaries])


@router.get("/{trade_date}", response_model=ApiResponse[MarketSummaryResponse | None])
async def get_market_summary_by_date(
    trade_date: date,
    session: AsyncSession = Depends(get_db_session),
):
    """특정 날짜 시장 AI 요약 조회"""
    summary = await get_market_summary(session, trade_date=trade_date)
    if summary is None:
        return ApiResponse(data=None)
    return ApiResponse(data=MarketSummaryResponse.model_validate(summary))
