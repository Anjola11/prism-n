from typing import AsyncGenerator
from src.config import Config
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

def get_async_db_url(raw_url: str) -> str:
    if not raw_url:
        return "sqlite+aiosqlite:///:memory:"
    url = raw_url.strip()
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url

db_url = get_async_db_url(Config.DATABASE_URL)

# Primary Engine for HTTP API requests
engine = create_async_engine(
    url=db_url,
    echo=False,
    pool_size=10,
    max_overflow=10,
    pool_timeout=10.0,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
    },
)

async_session_maker = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Dedicated Background Engine for workers & websockets (isolates HTTP pool)
bg_engine = create_async_engine(
    url=db_url,
    echo=False,
    poolclass=NullPool,
    pool_pre_ping=True,
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
    },
)

bg_session_maker = sessionmaker(
    bind=bg_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

async def init_db():
    async with engine.begin() as conn:
        from src.auth.models import User, SignupOtp, ForgotPasswordOtp
        from src.admin.models import AdminActionLog
        from src.markets.models import (
            MarketBaseline,
            MarketSignalSnapshot,
            TrackedEventMetric,
            TrackedMarket,
            UserTrackedEvent,
        )
        
        await conn.run_sync(SQLModel.metadata.create_all)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
