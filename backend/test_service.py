import asyncio
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from src.db.main import engine
from src.markets.models import MarketSignalSnapshot, TrackedMarket, Currency, MarketSource
from src.markets.services import MarketServices

async def main():
    async with AsyncSession(engine) as session:
        # Get first market
        market = await session.exec(select(TrackedMarket).limit(1))
        market = market.first()
        if not market:
            print("Market not found")
            return
            
        print(f"Event ID: {market.event_id}, Market ID: {market.market_id}")
        
        from src.markets.services import MarketServices
        from src.markets.live_state import LiveStateServices
        
        # Test the service
        services = MarketServices(bayse=None, live_state=LiveStateServices(None))
        
        try:
            res = await services.get_score_history_for_market(
                session=session,
                event_id=market.event_id,
                source=market.source,
                currency=market.currency if hasattr(market, 'currency') else Currency.DOLLAR,
                market_id=market.market_id,
                hours=48
            )
            print("Points returned:", len(res.points))
            if res.points:
                print("First point:", res.points[0])
                print("Last point:", res.points[-1])
        except Exception as e:
            print("Error calling service:", e)

if __name__ == "__main__":
    asyncio.run(main())
