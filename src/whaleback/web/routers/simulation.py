"""Simulation analysis API endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from whaleback.db import async_repositories as repo
from whaleback.web.cache import CacheService
from whaleback.web.dependencies import get_db_session, get_cache
from whaleback.web.schemas import (
    ApiResponse,
    Meta,
    PaginatedResponse,
    PaginatedMeta,
    SimulationResult,
    SimulationTopItem,
)

router = APIRouter(prefix="/analysis/simulation", tags=["simulation"])


@router.get("/top", response_model=PaginatedResponse[SimulationTopItem])
async def get_simulation_top(
    market: str | None = Query(None),
    min_score: float | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache),
):
    """Get top stocks by simulation score."""
    cache_key = f"simulation:top:{market}:{min_score}:{page}:{size}"
    cached = await cache.get(cache_key)
    if cached:
        return PaginatedResponse(
            data=cached["data"],
            meta=PaginatedMeta(**cached["meta"], cached=True),
        )

    rows, total = await repo.get_simulation_top(
        session, market=market, min_score=min_score, page=page, size=size
    )

    result = {"data": rows, "meta": {"total": total, "page": page, "size": size}}
    await cache.set(cache_key, result, ttl=300)

    return PaginatedResponse(
        data=rows,
        meta=PaginatedMeta(total=total, page=page, size=size),
    )


@router.get("/{ticker}", response_model=ApiResponse[SimulationResult])
async def get_simulation(
    ticker: str,
    session: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache),
):
    """Get Monte Carlo simulation results for a stock."""
    cache_key = f"simulation:{ticker}"
    cached = await cache.get(cache_key)
    if cached:
        return ApiResponse(data=cached, meta=Meta(cached=True))

    data = await repo.get_simulation_snapshot(session, ticker)
    if not data:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"No simulation data for {ticker}")

    stock = await repo.get_stock_detail(session, ticker)
    if stock:
        data["name"] = stock.get("name")
    data["as_of_date"] = data.pop("trade_date", "")

    result = SimulationResult(**data)
    await cache.set(cache_key, result.model_dump(), ttl=300)
    return ApiResponse(data=result)
