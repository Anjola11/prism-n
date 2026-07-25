import sys
import asyncio
import time
import os
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

os.environ["PYTHONPATH"] = "."
from src.markets.services import MarketServices
from src.markets.models import Currency, MarketSource
from src.db.redis import redis_client

async def test_step1_discovery_cold_start():
    print("\n--- Testing Step 1: Discovery Feed Cold Start Live Fallback ---")
    mock_live_state = MagicMock()
    mock_live_state.get_read_model = AsyncMock(return_value=None)
    mock_live_state.set_read_model = AsyncMock()
    
    mock_bayse = MagicMock()
    mock_bayse.get_all_listings = AsyncMock(return_value={"events": []})
    
    mock_polymarket = MagicMock()
    mock_polymarket.get_events = AsyncMock(return_value=[])

    services = MarketServices(
        bayse=mock_bayse,
        polymarket=mock_polymarket,
        live_state=mock_live_state,
    )
    services._safe_get_read_model = AsyncMock(return_value=None)
    services._safe_set_read_model = AsyncMock()
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.all = MagicMock(return_value=[])
    mock_session.exec = AsyncMock(return_value=mock_result)

    start_time = time.perf_counter()
    feed, count = await services.get_discovery_feed_for_user(
        session=mock_session,
        user_id="00000000-0000-0000-0000-000000000000",
        currency=Currency.DOLLAR,
    )
    elapsed = (time.perf_counter() - start_time) * 1000
    print(f"Cold start fallback returned {len(feed)} items in {elapsed:.2f}ms without 503 error!")
    print("Step 1 Cold Start Test PASSED!")

async def test_step2_oldest_snapshot_scores():
    print("\n--- Testing Step 2: Oldest Snapshot Scores Query ---")
    services = MarketServices(bayse=MagicMock())
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.all = MagicMock(return_value=[("mkt_1", 85.5), ("mkt_2", 42.0)])
    mock_session.exec = AsyncMock(return_value=mock_result)
    
    scores = await services._get_oldest_snapshot_scores(
        session=mock_session,
        market_ids=["mkt_1", "mkt_2"],
        hours=48,
    )
    print(f"Returned oldest snapshot scores: {scores}")
    assert scores == {"mkt_1": 85.5, "mkt_2": 42.0}
    print("Step 2 Score-Delta Query Test PASSED!")

def test_step4_redis_timeouts():
    print("\n--- Testing Step 4: Redis Socket Timeouts ---")
    print(f"redis_client connection kwargs socket_connect_timeout={redis_client.connection_pool.connection_kwargs.get('socket_connect_timeout')}")
    print(f"redis_client connection kwargs socket_timeout={redis_client.connection_pool.connection_kwargs.get('socket_timeout')}")
    assert redis_client.connection_pool.connection_kwargs.get('socket_connect_timeout') == 1.5
    assert redis_client.connection_pool.connection_kwargs.get('socket_timeout') == 1.5
    print("Step 4 Redis Timeouts Test PASSED!")

async def run():
    await test_step1_discovery_cold_start()
    await test_step2_oldest_snapshot_scores()
    test_step4_redis_timeouts()
    print("\nAll Step 1, 2, and 4 backend tests PASSED!")

if __name__ == "__main__":
    asyncio.run(run())
