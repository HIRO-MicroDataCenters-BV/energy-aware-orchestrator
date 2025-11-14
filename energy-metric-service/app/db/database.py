"""
Database connection and session management.
"""

import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Import greenlet explicitly to ensure it's available
try:
    import greenlet
except ImportError:
    raise ImportError("greenlet is required for async SQLAlchemy operations. Install with: pip install greenlet")

ASYNC_DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/orchestration_db"
)

# For sync operations (if needed), use psycopg2 driver
SYNC_DATABASE_URL = ASYNC_DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True
)
AsyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Only create sync engine if absolutely necessary (not used in our async endpoints)
# engine = create_engine(SYNC_DATABASE_URL, echo=True)
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

async def get_async_db():
    """
    Dependency that provides an asynchronous database session.
    """
    async with AsyncSessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()
