import asyncio
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from src.db.main import engine
from src.markets.models import MarketSignalSnapshot, TrackedMarket

async def main():
    async with AsyncSession(engine) as session:
        # Find the market for "MPC Decision"
        market = await session.exec(
            select(TrackedMarket).where(TrackedMarket.event_title.like("%MPC Decision%")).limit(1)
        )
        market = market.first()
        if not market:
            print("Market not found")
            return
            
        print(f"Event ID: {market.event_id}, Market ID: {market.market_id}")
        
        # Count snapshots for this market
        count = await session.exec(
            select(MarketSignalSnapshot).where(MarketSignalSnapshot.market_id == market.market_id)
        )
        snapshots = count.all()
        print(f"Total snapshots for this market: {len(snapshots)}")
        
        if snapshots:
            print(f"Oldest: {snapshots[0].created_at}")
            print(f"Newest: {snapshots[-1].created_at}")

if __name__ == "__main__":
    asyncio.run(main())
