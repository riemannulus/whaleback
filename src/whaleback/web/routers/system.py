"""System endpoints: health check, pipeline status."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from whaleback.db.async_repositories import get_collection_status
from whaleback.web.dependencies import get_db_session, get_cache
from whaleback.web.cache import CacheService
from whaleback.web.schemas import HealthResponse, PipelineStatus, ApiResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health(cache: CacheService = Depends(get_cache)):
    """API health check."""
    return HealthResponse(
        status="ok",
        version="0.2.0",
        cache_type="redis" if cache.is_redis else "memory",
    )


@router.get("/health/pipeline", response_model=ApiResponse[PipelineStatus])
async def pipeline_status(
    session: AsyncSession = Depends(get_db_session),
):
    """Get latest pipeline collection status."""
    collections = await get_collection_status(session)
    return ApiResponse(data=PipelineStatus(collections=collections))
