"""Stock endpoints: list, detail, price history, investor history."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from whaleback.db.async_repositories import (
    get_stocks_paginated,
    get_stock_detail,
    get_price_history,
    get_investor_history,
)
from whaleback.web.dependencies import get_db_session, get_cache
from whaleback.web.cache import CacheService
from whaleback.web.schemas import (
    StockSummary,
    StockDetail,
    PriceData,
    InvestorData,
    PaginatedResponse,
    PaginatedMeta,
    ApiResponse,
    Meta,
)

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("", response_model=PaginatedResponse[StockSummary])
async def list_stocks(
    market: str | None = Query(None, description="KOSPI or KOSDAQ"),
    search: str | None = Query(None, description="Search by ticker or name"),
    is_active: bool | None = Query(True, description="Filter active stocks"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
):
    """List stocks with optional filters and pagination."""
    rows, total = await get_stocks_paginated(session, page, size, market, search, is_active)
    return PaginatedResponse(
        data=rows,
        meta=PaginatedMeta(total=total, page=page, size=size),
    )


@router.get("/{ticker}", response_model=ApiResponse[StockDetail])
async def stock_detail(
    ticker: str,
    session: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache),
):
    """Get detailed stock information with latest price and fundamentals."""
    cache_key = f"stock:detail:{ticker}"
    cached = await cache.get(cache_key)
    if cached:
        return ApiResponse(data=cached, meta=Meta(cached=True))

    data = await get_stock_detail(session, ticker)
    if not data:
        raise HTTPException(status_code=404, detail=f"Stock {ticker} not found")

    await cache.set(cache_key, data, ttl=300)
    return ApiResponse(data=data)


@router.get("/{ticker}/price", response_model=ApiResponse[list[PriceData]])
async def stock_price_history(
    ticker: str,
    start_date: date | None = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: date | None = Query(None, description="End date (YYYY-MM-DD)"),
    session: AsyncSession = Depends(get_db_session),
):
    """Get OHLCV price history for a stock."""
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=180)

    data = await get_price_history(session, ticker, start_date, end_date)
    return ApiResponse(data=data)


@router.get("/{ticker}/investors", response_model=ApiResponse[list[InvestorData]])
async def stock_investor_history(
    ticker: str,
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    session: AsyncSession = Depends(get_db_session),
):
    """Get investor trading history for a stock."""
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=60)

    data = await get_investor_history(session, ticker, start_date, end_date)
    return ApiResponse(data=data)
