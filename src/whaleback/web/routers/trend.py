"""Trend analysis endpoints: sector ranking, relative strength, sector rotation."""

import logging
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from whaleback.db.async_repositories import (
    get_price_history,
    get_sector_ranking,
    get_stock_detail,
    get_trend_snapshot,
)
from whaleback.db.models import AnalysisTrendSnapshot, Stock
from whaleback.web.cache import CacheService
from whaleback.web.dependencies import get_cache, get_db_session
from whaleback.web.schemas import (
    ApiResponse,
    Meta,
    PaginatedMeta,
    PaginatedResponse,
    RelativeStrength,
    SectorRankingItem,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis/trend", tags=["trend"])


@router.get("/sector-ranking", response_model=ApiResponse[list[SectorRankingItem]])
async def sector_ranking(
    market: str | None = Query(None),
    session: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache),
):
    """Get sector performance ranking."""
    cache_key = f"trend:sectors:{market}"
    cached = await cache.get(cache_key)
    if cached:
        return ApiResponse(data=cached, meta=Meta(cached=True))

    data = await get_sector_ranking(session, market=market)

    # Add momentum rank
    for i, item in enumerate(data):
        item["momentum_rank"] = i + 1

    await cache.set(cache_key, data, ttl=300)
    return ApiResponse(data=data)


@router.get("/relative-strength/{ticker}", response_model=ApiResponse[RelativeStrength])
async def relative_strength(
    ticker: str,
    benchmark: str = Query("KOSPI", description="KOSPI or KOSDAQ"),
    days: int = Query(120, ge=20, le=365),
    session: AsyncSession = Depends(get_db_session),
):
    """Get relative strength of a stock vs market index."""
    from whaleback.analysis.trend import compute_relative_strength
    from whaleback.db.models import MarketIndex

    end_date = date.today()
    start_date = end_date - timedelta(days=days * 2)

    # Stock prices
    price_data = await get_price_history(session, ticker, start_date, end_date)
    if not price_data:
        raise HTTPException(status_code=404, detail=f"No price data for {ticker}")

    # Index prices
    index_code = "1001" if benchmark == "KOSPI" else "2001"
    try:
        result = await session.execute(
            select(MarketIndex)
            .where(
                and_(
                    MarketIndex.index_code == index_code,
                    MarketIndex.trade_date.between(start_date, end_date),
                )
            )
            .order_by(MarketIndex.trade_date)
        )
        index_rows = result.scalars().all()
    except Exception:
        await session.rollback()
        logger.warning("MarketIndex table not found, using empty index data")
        index_rows = []
    index_by_date = {r.trade_date.isoformat(): float(r.close) for r in index_rows}

    # Align dates
    stock_prices = []
    index_prices = []
    dates = []
    for p in price_data:
        d = p["trade_date"]
        if d in index_by_date:
            stock_prices.append(p["close"])
            index_prices.append(index_by_date[d])
            dates.append(d)

    rs_result = compute_relative_strength(stock_prices, index_prices, dates)

    # Get trend snapshot for percentile
    trend_snap = await get_trend_snapshot(session, ticker)

    stock = await get_stock_detail(session, ticker)
    name = stock.get("name") if stock else None

    return ApiResponse(
        data={
            "ticker": ticker,
            "name": name,
            "benchmark": benchmark,
            "current_rs": rs_result.get("current_rs"),
            "rs_percentile": trend_snap.get("rs_percentile") if trend_snap else None,
            "rs_change_pct": rs_result.get("rs_change_pct"),
            "series": rs_result.get("series", []),
        }
    )


@router.get("/sector-rotation")
async def sector_rotation(
    market: str | None = Query(None),
    session: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache),
):
    """Get sector rotation quadrant data."""
    from whaleback.analysis.trend import compute_sector_rotation

    data = await get_sector_ranking(session, market=market)

    sectors_for_rotation = [
        {
            "sector": s.get("sector"),
            "avg_rs_20d": s.get("avg_rs_20d"),
            "avg_rs_change": (s.get("avg_rs_20d") or 1.0) - 1.0,
            "stock_count": s.get("stock_count"),
        }
        for s in data
    ]

    rotation = compute_sector_rotation(sectors_for_rotation)
    return ApiResponse(data=rotation)


@router.get("/sector/{sector_name}", response_model=PaginatedResponse[dict])
async def sector_stocks(
    sector_name: str,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
):
    """Get stocks in a specific sector with trend data."""
    from sqlalchemy import func
    from whaleback.db.async_repositories import get_latest_analysis_date

    try:
        as_of_date = await get_latest_analysis_date(session)

        query = (
            select(AnalysisTrendSnapshot, Stock.name, Stock.market)
            .join(Stock, AnalysisTrendSnapshot.ticker == Stock.ticker)
            .where(
                and_(
                    AnalysisTrendSnapshot.sector == sector_name,
                    AnalysisTrendSnapshot.trade_date == as_of_date,
                )
            )
            .order_by(AnalysisTrendSnapshot.rs_percentile.desc().nullslast())
            .offset((page - 1) * size)
            .limit(size)
        )

        count_query = (
            select(func.count())
            .select_from(AnalysisTrendSnapshot)
            .where(
                and_(
                    AnalysisTrendSnapshot.sector == sector_name,
                    AnalysisTrendSnapshot.trade_date == as_of_date,
                )
            )
        )

        total = (await session.execute(count_query)).scalar() or 0
        result = await session.execute(query)

        rows = []
        for row in result.all():
            snap = row[0]
            rows.append(
                {
                    "ticker": snap.ticker,
                    "name": row[1],
                    "market": row[2],
                    "rs_vs_kospi_20d": float(snap.rs_vs_kospi_20d) if snap.rs_vs_kospi_20d else None,
                    "rs_percentile": snap.rs_percentile,
                    "sector": snap.sector,
                }
            )
    except Exception:
        await session.rollback()
        logger.warning(f"Failed to get sector stocks for {sector_name}, table may not exist")
        rows = []
        total = 0

    return PaginatedResponse(
        data=rows,
        meta=PaginatedMeta(total=total, page=page, size=size),
    )
