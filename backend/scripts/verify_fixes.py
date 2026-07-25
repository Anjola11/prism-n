import sys
import asyncio
from unittest.mock import AsyncMock, MagicMock
import json
import time
import os
from dotenv import load_dotenv
load_dotenv()
db_url = os.environ.get("DATABASE_URL", "")
if db_url and db_url.startswith("postgresql://"):
    os.environ["DATABASE_URL"] = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

from src.markets.models import TrackedMarket, Currency, MarketEngine, MarketSource, TrackedEventMetric, EventType
from src.markets.live_state import LiveStateServices, MarketLiveState
from src.markets.services import MarketServices
from src.markets.schemas import EventMarketRead
from src.config import Config

class MockRedis:
    def __init__(self):
        self.store = {}
        self.ttls = {}
        self.set_calls = []

    async def set(self, key, value, ex=None, px=None, nx=False, xx=False):
        self.store[key] = value
        if ex:
            self.ttls[key] = ex
        self.set_calls.append({"key": key, "value": value, "ex": ex})
        return True

    async def get(self, key):
        return self.store.get(key)

    async def delete(self, key):
        if key in self.store:
            del self.store[key]
        if key in self.ttls:
            del self.ttls[key]
        return 1

async def test_finding_5_warmup_seed():
    print("--- Testing Finding 5: Seeding previous_probability on warmup ---")
    mock_redis = MockRedis()
    live_state = LiveStateServices(redis=mock_redis)

    # Mock TrackedMarket
    tm_yes = TrackedMarket(
        event_id="evt_123",
        market_id="mkt_yes",
        market_title="Will NVDA hit $200?",
        current_probability=0.75,
        inverse_probability=0.25,
        engine=MarketEngine.CLOB,
        source=MarketSource.POLYMARKET,
        tracking_enabled=True,
        yes_outcome_id="yes_token_123",
        no_outcome_id="no_token_123",
    )
    
    # Warm market state
    warmed_state = await live_state.warm_market_state_from_tracking(
        tracked_market=tm_yes,
        currency=Currency.DOLLAR,
        total_liquidity=5000.0,
    )
    
    print(f"Warmed MarketLiveState probability values:")
    print(f" - current_probability: {warmed_state.current_probability}")
    print(f" - previous_probability: {warmed_state.previous_probability}")
    assert warmed_state.previous_probability == 0.75, "previous_probability should be seeded to 0.75!"

    # Simulate subsequent update with price tick 0.80
    updated_state = await live_state.update_market_state(
        source=MarketSource.POLYMARKET,
        market_id="mkt_yes",
        currency=Currency.DOLLAR,
        current_probability=0.80,
    )
    print(f"After live update (price tick 0.80):")
    print(f" - current_probability: {updated_state.current_probability}")
    print(f" - previous_probability: {updated_state.previous_probability}")
    assert updated_state.previous_probability == 0.75, "previous_probability should carry the warmed price 0.75!"

    # Test market read delta calculation
    services = MarketServices(bayse=None, live_state=live_state)
    market_read = await services._build_market_read(
        market=tm_yes,
        currency=Currency.DOLLAR,
    )
    print(f"Market Read Delta calculation:")
    print(f" - current_probability: {market_read.current_probability}")
    print(f" - probability_delta: {market_read.probability_delta}")
    assert abs(market_read.probability_delta - 0.05) < 1e-6, "probability_delta should be exactly 0.05 (0.80 - 0.75)!"
    print("Finding 5 Warmup Seed test passed successfully.")

async def test_finding_1_ttls():
    print("\n--- Testing Finding 1: TTLs on live-state keys ---")
    mock_redis = MockRedis()
    live_state = LiveStateServices(redis=mock_redis)

    tm = TrackedMarket(
        event_id="evt_123",
        market_id="mkt_yes",
        market_title="Will NVDA hit $200?",
        current_probability=0.75,
        inverse_probability=0.25,
        engine=MarketEngine.CLOB,
        source=MarketSource.POLYMARKET,
        tracking_enabled=True,
        yes_outcome_id="yes_token_123",
        no_outcome_id="no_token_123",
    )

    await live_state.warm_market_state_from_tracking(
        tracked_market=tm,
        currency=Currency.DOLLAR,
    )

    print("Set calls tracked in Redis:")
    for call in mock_redis.set_calls:
        print(f" - Key: {call['key']} | ex: {call['ex']}")
        assert call['ex'] == 259200, f"TTL for key {call['key']} should be 259200 (72h)!"
    print("Finding 1 TTLs test passed successfully.")

async def test_finding_3_dead_key_removal():
    print("\n--- Testing Finding 3: Remove dead prism:persistence:* write ---")
    mock_redis = MockRedis()
    live_state = LiveStateServices(redis=mock_redis)

    tm = TrackedMarket(
        event_id="evt_123",
        market_id="mkt_yes",
        market_title="Will NVDA hit $200?",
        current_probability=0.75,
        inverse_probability=0.25,
        engine=MarketEngine.CLOB,
        source=MarketSource.POLYMARKET,
        tracking_enabled=True,
        yes_outcome_id="yes_token_123",
        no_outcome_id="no_token_123",
    )

    await live_state.warm_market_state_from_tracking(
        tracked_market=tm,
        currency=Currency.DOLLAR,
    )
    
    mock_redis.set_calls.clear()

    await live_state.update_market_state(
        source=MarketSource.POLYMARKET,
        market_id="mkt_yes",
        currency=Currency.DOLLAR,
        current_probability=0.80,
    )

    persistence_keys = [c['key'] for c in mock_redis.set_calls if "persistence" in c['key']]
    print(f"Persistence keys written during update: {persistence_keys}")
    assert len(persistence_keys) == 0, "No prism:persistence:* keys should be written!"
    print("Finding 3 Dead Key Removal test passed successfully.")

async def test_finding_4_bayse_notional_reset():
    print("\n--- Testing Finding 4: Bounded buy_notional/sell_notional on Bayse ---")
    mock_redis = MockRedis()
    live_state = LiveStateServices(redis=mock_redis)
    from src.markets.websocket_manager import BayseWebSocketManager

    ws_manager = BayseWebSocketManager(bayse=MagicMock(), live_state=live_state)
    ws_manager._score_market = AsyncMock()
    
    # 1. Warm market state
    tm = TrackedMarket(
        event_id="evt_123",
        market_id="mkt_1",
        market_title="Test Market",
        current_probability=0.5,
        inverse_probability=0.5,
        engine=MarketEngine.CLOB,
        source=MarketSource.BAYSE,
        tracking_enabled=True,
    )
    await live_state.warm_market_state_from_tracking(tracked_market=tm, currency=Currency.DOLLAR)
    
    # 2. Simulate orderbook update frame
    msg = {
        "type": "orderbook_update",
        "room": "orderbook:evt_123:USD",
        "data": {
            "marketId": "mkt_1",
            "bids": [{"price": "0.48", "quantity": "100", "total": "48"}],
            "asks": [{"price": "0.52", "quantity": "50", "total": "26"}]
        }
    }
    await ws_manager._handle_orderbook_update(msg)
    
    # Check updated live state notional
    state = await live_state.get_market_state(source=MarketSource.BAYSE, market_id="mkt_1", currency=Currency.DOLLAR)
    print(f"After book update frame:")
    print(f" - buy_notional: {state.buy_notional}")
    print(f" - sell_notional: {state.sell_notional}")
    assert state.buy_notional == 48.0, "buy_notional should match bids depth total!"
    assert state.sell_notional == 26.0, "sell_notional should match asks depth total!"
    print("Finding 4 reset-on-frame test passed successfully.")

async def test_finding_2_throttled_sync():
    print("\n--- Testing Finding 2: Throttled reconnect batch sync ---")
    mock_redis = MockRedis()
    live_state = LiveStateServices(redis=mock_redis)
    from src.markets.polymarket_websocket_manager import PolymarketWebSocketManager, AssetBinding
    
    ws_manager = PolymarketWebSocketManager(clob=MagicMock(), data_api=MagicMock(), live_state=live_state)
    
    # Create 25 mock bindings to test chunking
    mock_bindings = {}
    for idx in range(25):
        mock_bindings[f"asset_{idx}"] = AssetBinding(
            asset_id=f"asset_{idx}",
            event_id="evt_123",
            market_id="mkt_123",
            currency=Currency.DOLLAR,
            outcome_side="YES"
        )
        
    ws_manager._load_tracked_asset_bindings = AsyncMock(return_value=(mock_bindings, "v1"))
    ws_manager._ws = AsyncMock()
    ws_manager._chunk = MagicMock(return_value=[])
    
    concurrent_calls = 0
    peak_concurrent_calls = 0
    asset_mapping_calls = []

    async def track_set_asset_mapping(state):
        nonlocal concurrent_calls, peak_concurrent_calls
        concurrent_calls += 1
        peak_concurrent_calls = max(peak_concurrent_calls, concurrent_calls)
        asset_mapping_calls.append(state)
        # Small delay to allow concurrent tasks to overlap and be tracked
        await asyncio.sleep(0.01)
        concurrent_calls -= 1

    live_state.set_asset_mapping = track_set_asset_mapping

    await ws_manager._sync_subscriptions()
    print(f"Total set_asset_mapping calls: {len(asset_mapping_calls)}")
    print(f"Peak concurrent set_asset_mapping calls: {peak_concurrent_calls}")
    assert len(asset_mapping_calls) == 25
    assert peak_concurrent_calls <= 10, f"Peak concurrency exceeded: {peak_concurrent_calls}"
    print("Finding 2 Throttled sync checks out successfully.")

async def test_finding_7_parallel_reads():
    print("\n--- Testing Finding 7: Parallelized Discovery reads ---")
    mock_redis = MockRedis()
    live_state = LiveStateServices(redis=mock_redis)
    from src.markets.discovery_worker import DiscoveryWorker

    worker = DiscoveryWorker(bayse=MagicMock(), polymarket=MagicMock(), live_state=live_state)
    
    # Track calls to get_signal_state and get_market_state
    get_calls = []
    
    original_get_signal = live_state.get_signal_state
    original_get_market = live_state.get_market_state
    
    async def track_get_signal(*args, **kwargs):
        get_calls.append("get_signal_state")
        return None
    async def track_get_market(*args, **kwargs):
        get_calls.append("get_market_state")
        return None
        
    live_state.get_signal_state = track_get_signal
    live_state.get_market_state = track_get_market

    tm1 = TrackedMarket(event_id="evt_1", market_id="mkt_1", current_probability=0.5, inverse_probability=0.5, engine=MarketEngine.CLOB, source=MarketSource.BAYSE, tracking_enabled=True, event_type=EventType.SINGLE)
    tm2 = TrackedMarket(event_id="evt_1", market_id="mkt_2", current_probability=0.6, inverse_probability=0.4, engine=MarketEngine.CLOB, source=MarketSource.BAYSE, tracking_enabled=True, event_type=EventType.SINGLE)
    
    metric = TrackedEventMetric(event_id="evt_1", source=MarketSource.BAYSE, currency=Currency.DOLLAR, total_liquidity=1000.0)
    
    res = await worker._build_card(
        event_payload={"id": "evt_1", "markets": []},
        currency=Currency.DOLLAR,
        tracked_markets=[tm1, tm2],
        metric=metric,
        is_system_tracked=False,
    )
    
    print(f"Discovery card getter calls: {get_calls}")
    assert len(get_calls) == 4
    assert get_calls.count("get_signal_state") == 2
    assert get_calls.count("get_market_state") == 2
    print("Finding 7 Parallelized reads checks out successfully.")

def test_finding_8_semaphore_values():
    print("\n--- Testing Finding 8: Option B Semaphore Configurations ---")
    print(f"REDIS_OPERATION_CONCURRENCY configured in Config: {Config.REDIS_OPERATION_CONCURRENCY}")
    assert Config.REDIS_OPERATION_CONCURRENCY == 6
    
    print(f"LIVE_STATE_MARKET_READ_CONCURRENCY in MarketServices: {MarketServices.LIVE_STATE_MARKET_READ_CONCURRENCY}")
    assert MarketServices.LIVE_STATE_MARKET_READ_CONCURRENCY == 4
    
    print(f"TRACKER_EVENT_BUILD_CONCURRENCY in MarketServices: {MarketServices.TRACKER_EVENT_BUILD_CONCURRENCY}")
    assert MarketServices.TRACKER_EVENT_BUILD_CONCURRENCY == 2
    
    print("Finding 8 Semaphore settings verified successfully.")

async def test_finding_6_resolution_cleanup():
    print("\n--- Testing Finding 6: Market Resolution Cleanup ---")
    mock_redis = MockRedis()
    live_state = LiveStateServices(redis=mock_redis)
    from src.markets.polymarket_websocket_manager import PolymarketWebSocketManager
    import src.markets.polymarket_websocket_manager as pwm

    # Mock TrackedMarket in DB
    db_market = TrackedMarket(
        event_id="evt_123",
        market_id="mkt_res",
        market_title="Resolved Market",
        current_probability=0.5,
        inverse_probability=0.5,
        engine=MarketEngine.CLOB,
        source=MarketSource.POLYMARKET,
        tracking_enabled=True,
        yes_outcome_id="yes_token",
        no_outcome_id="no_token",
    )

    # Mock SQLModel select execution
    mock_result = MagicMock()
    mock_result.first = MagicMock(return_value=db_market)
    
    mock_session = AsyncMock()
    mock_session.exec = AsyncMock(return_value=mock_result)

    # Patch async_session_maker
    original_session_maker = pwm.async_session_maker
    mock_maker = MagicMock()
    mock_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_maker.return_value.__aexit__ = AsyncMock()
    pwm.async_session_maker = mock_maker

    ws_manager = PolymarketWebSocketManager(clob=MagicMock(), data_api=MagicMock(), live_state=live_state)
    ws_manager._sync_subscriptions = AsyncMock()

    # Pre-populate keys to confirm deletion
    yes_key = live_state.asset_mapping_key(source=MarketSource.POLYMARKET, asset_id="yes_token")
    no_key = live_state.asset_mapping_key(source=MarketSource.POLYMARKET, asset_id="no_token")
    mkt_key = live_state.market_key(source=MarketSource.POLYMARKET, market_id="mkt_res", currency=Currency.DOLLAR)
    sig_key = live_state.signal_key(source=MarketSource.POLYMARKET, market_id="mkt_res", currency=Currency.DOLLAR)

    await mock_redis.set(yes_key, "data")
    await mock_redis.set(no_key, "data")
    await mock_redis.set(mkt_key, "data")
    await mock_redis.set(sig_key, "data")

    # Simulate message
    msg = {
        "event_type": "market_resolved",
        "id": "mkt_res",
        "market": "0xcondition_id",
        "assets_ids": ["yes_token", "no_token"]
    }
    await ws_manager._handle_message(msg)

    # Verify key deletions
    assert yes_key not in mock_redis.store
    assert no_key not in mock_redis.store
    assert mkt_key not in mock_redis.store
    assert sig_key not in mock_redis.store
    print("Deleted all Redis keys successfully.")

    # Verify database update
    assert db_market.tracking_enabled is False
    print("Disabled database tracking successfully.")
    
    # Verify ws sync
    ws_manager._sync_subscriptions.assert_called_once()
    print("Subscription plan refresh triggered successfully.")

    # Restore session maker
    pwm.async_session_maker = original_session_maker

async def test_bayse_trade_recalculate():
    print("\n--- Testing Requirement 1: Bayse trade score update without notional modification ---")
    mock_redis = MockRedis()
    live_state = LiveStateServices(redis=mock_redis)
    from src.markets.websocket_manager import BayseWebSocketManager

    ws_manager = BayseWebSocketManager(bayse=MagicMock(), live_state=live_state)
    
    # 1. Warm market state
    tm = TrackedMarket(
        event_id="evt_123",
        market_id="mkt_1",
        market_title="Test Market",
        current_probability=0.5,
        inverse_probability=0.5,
        engine=MarketEngine.CLOB,
        source=MarketSource.BAYSE,
        tracking_enabled=True,
    )
    await live_state.warm_market_state_from_tracking(tracked_market=tm, currency=Currency.DOLLAR)

    # Pre-populate some notional values in orderbook
    await live_state.update_market_state(
        source=MarketSource.BAYSE,
        market_id="mkt_1",
        currency=Currency.DOLLAR,
        buy_notional=100.0,
        sell_notional=200.0,
    )

    # Mock _score_market to track calls
    ws_manager._score_market = AsyncMock()

    # 2. Simulate buy_order trade frame
    msg = {
        "type": "buy_order",
        "data": {
            "eventId": "evt_123",
            "marketId": "mkt_1",
            "order": {
                "currency": "USD",
                "amount": "500.0",
                "price": "0.55",
                "quantity": "909"
            }
        }
    }
    await ws_manager._handle_message(msg)

    # 3. Assertions
    ws_manager._score_market.assert_called_once_with(market_id="mkt_1", currency=Currency.DOLLAR)
    print("Called _score_market successfully.")

    # Confirm notionals are untouched
    state = await live_state.get_market_state(source=MarketSource.BAYSE, market_id="mkt_1", currency=Currency.DOLLAR)
    print(f"Notionals after trade message: buy_notional={state.buy_notional}, sell_notional={state.sell_notional}")
    assert state.buy_notional == 100.0
    assert state.sell_notional == 200.0
    print("Requirement 1 Bayse trade score test passed successfully.")

async def run_all():
    await test_finding_5_warmup_seed()
    await test_finding_1_ttls()
    await test_finding_3_dead_key_removal()
    await test_finding_4_bayse_notional_reset()
    await test_finding_2_throttled_sync()
    await test_finding_7_parallel_reads()
    await test_finding_6_resolution_cleanup()
    await test_bayse_trade_recalculate()
    test_finding_8_semaphore_values()
    print("\nAll verifications succeeded!")

if __name__ == "__main__":
    asyncio.run(run_all())
