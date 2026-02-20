"""FastAPI application factory for Whaleback API."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from whaleback.config import Settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize and cleanup resources."""
    settings = app.state.settings
    logger.info("Starting Whaleback API...")

    # Initialize async DB engine
    from whaleback.db.engine import create_async_db_engine

    app.state.async_engine = create_async_db_engine(settings)

    # Initialize cache
    from whaleback.web.cache import CacheService

    app.state.cache = await CacheService.create(settings.redis_url, settings.cache_ttl)

    logger.info("Whaleback API ready")
    yield

    # Cleanup
    if app.state.cache:
        await app.state.cache.close()
    if app.state.async_engine:
        await app.state.async_engine.dispose()
    logger.info("Whaleback API shutdown complete")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    if settings is None:
        settings = Settings()

    app = FastAPI(
        title="Whaleback API",
        description="Korean stock market analysis API - KOSPI/KOSDAQ quant analysis, whale tracking, sector trends",
        version="0.2.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.state.settings = settings

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["Content-Type", "Accept"],
    )

    # Register routers (will be added in Wave 5)
    _register_routers(app)

    return app


def _register_routers(app: FastAPI):
    """Register all API routers."""
    from whaleback.web.routers.stocks import router as stocks_router
    from whaleback.web.routers.quant import router as quant_router
    from whaleback.web.routers.whale import router as whale_router
    from whaleback.web.routers.trend import router as trend_router
    from whaleback.web.routers.system import router as system_router

    app.include_router(stocks_router, prefix="/api/v1")
    app.include_router(quant_router, prefix="/api/v1")
    app.include_router(whale_router, prefix="/api/v1")
    app.include_router(trend_router, prefix="/api/v1")
    app.include_router(system_router, prefix="/api/v1")
