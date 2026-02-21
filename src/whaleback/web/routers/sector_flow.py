"""Sector whale flow analysis endpoints."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from whaleback.db.async_repositories import (
    get_sector_flow_overview,
    get_sector_flow_heatmap,
)
from whaleback.web.dependencies import get_db_session, get_cache
from whaleback.web.cache import CacheService
from whaleback.web.schemas import (
    ApiResponse,
    Meta,
    SectorFlowOverviewItem,
    SectorFlowHeatmapData,
)

router = APIRouter(prefix="/analysis/sector-flow", tags=["sector-flow"])


@router.get("/overview", response_model=ApiResponse[list[SectorFlowOverviewItem]])
async def sector_flow_overview(
    as_of_date: date | None = Query(None),
    session: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache),
):
    """Get sector-level whale flow overview grouped by sector."""
    cache_key = f"sector_flow:overview:{as_of_date}"
    cached = await cache.get(cache_key)
    if cached:
        return ApiResponse(data=cached, meta=Meta(cached=True))

    rows = await get_sector_flow_overview(session, as_of_date)
    await cache.set(cache_key, rows, ttl=300)
    return ApiResponse(data=rows)


@router.get("/heatmap", response_model=ApiResponse[SectorFlowHeatmapData])
async def sector_flow_heatmap(
    as_of_date: date | None = Query(None),
    metric: str = Query("intensity", pattern="^(intensity|consistency|net_purchase)$"),
    session: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache),
):
    """Get heatmap data for sector flow visualization.

    metric: intensity | consistency | net_purchase
    """
    cache_key = f"sector_flow:heatmap:{as_of_date}:{metric}"
    cached = await cache.get(cache_key)
    if cached:
        return ApiResponse(data=cached, meta=Meta(cached=True))

    data = await get_sector_flow_heatmap(session, as_of_date, metric)
    await cache.set(cache_key, data, ttl=300)
    return ApiResponse(data=data)


@router.get("/sector/{sector_name}", response_model=ApiResponse[SectorFlowOverviewItem | None])
async def sector_flow_detail(
    sector_name: str,
    as_of_date: date | None = Query(None),
    session: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache),
):
    """Get per-sector whale flow detail."""
    cache_key = f"sector_flow:detail:{sector_name}:{as_of_date}"
    cached = await cache.get(cache_key)
    if cached:
        return ApiResponse(data=cached, meta=Meta(cached=True))

    rows = await get_sector_flow_overview(session, as_of_date)
    match = next((r for r in rows if r.get("sector") == sector_name), None)
    await cache.set(cache_key, match, ttl=300)
    return ApiResponse(data=match)
