"""FastAPI dependency injection providers."""

from typing import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from whaleback.config import Settings
from whaleback.db.engine import get_async_session_factory
from whaleback.web.cache import CacheService


def get_settings(request: Request) -> Settings:
    """Get application settings from app state."""
    return request.app.state.settings


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Provide async database session for request lifetime."""
    session_factory = get_async_session_factory()
    session = session_factory()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


def get_cache(request: Request) -> CacheService:
    """Get cache service from app state."""
    return request.app.state.cache
