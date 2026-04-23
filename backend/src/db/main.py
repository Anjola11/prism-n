from src.config import Config
from sqlalchemy.ext.asyncio import create_async_engine 
from sqlmodel import SQLModel
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

engine = create_async_engine(
    url=Config.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=300,
)

async def init_db():
    async with engine.begin() as conn:

        #import models here
        from src.auth.models import User, SignupOtp, ForgotPasswordOtp
        from src.markets.models import MarketBaseline, TrackedEventMetric, TrackedMarket, UserTrackedEvent
        
        await conn.run_sync(SQLModel.metadata.create_all)

async_session_maker = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_session():
    async with async_session_maker() as session:
        yield session
