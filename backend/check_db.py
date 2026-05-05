import asyncio
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, func
from src.db.main import engine
from src.markets.models import MarketSignalSnapshot

async def main():
    async with AsyncSession(engine) as session:
        latest = await session.exec(select(func.max(MarketSignalSnapshot.created_at)))
        print(f"Latest snapshot timestamp: {latest.one()}")

if __name__ == "__main__":
    asyncio.run(main())
