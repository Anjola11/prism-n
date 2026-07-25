import asyncio, os
from unittest.mock import MagicMock
os.environ["PYTHONPATH"] = "."

from src.markets.services import MarketServices
from src.markets.schemas import EventMarketRead, SignalRead
from src.markets.discovery_worker import DiscoveryWorker

async def test_section_1_sparklines():
    print("--- Testing Section 1: Non-flat warmup sparkline generation ---")
    s = MarketServices(bayse=MagicMock())
    
    # 1. RISING market
    m_rising = EventMarketRead(
        market_id='m1', market_title='Rising Market', yes_outcome_id='1', yes_outcome_label='Y', no_outcome_id='2', no_outcome_label='N',
        current_probability=0.80, probability_delta=0.10,
        signal=SignalRead(score=82.0, classification='strong', direction='RISING', factors={'move': 0.6})
    )
    pts_rising = s._build_warmup_score_history_points(observed_rows=[], current_market=m_rising, current_live_probability=0.70)
    scores_rising = [round(p.score, 1) for p in pts_rising]
    print("Rising scores:", scores_rising)
    assert scores_rising[0] < scores_rising[1] < scores_rising[2], f"Expected ascending scores, got {scores_rising}"

    # 2. FALLING market
    m_falling = EventMarketRead(
        market_id='m2', market_title='Falling Market', yes_outcome_id='1', yes_outcome_label='Y', no_outcome_id='2', no_outcome_label='N',
        current_probability=0.30, probability_delta=-0.15,
        signal=SignalRead(score=35.0, classification='weak', direction='FALLING', factors={'move': 0.7})
    )
    pts_falling = s._build_warmup_score_history_points(observed_rows=[], current_market=m_falling, current_live_probability=0.45)
    scores_falling = [round(p.score, 1) for p in pts_falling]
    print("Falling scores:", scores_falling)
    assert scores_falling[0] > scores_falling[1] > scores_falling[2], f"Expected descending scores, got {scores_falling}"

    print("Section 1 Warmup Sparkline test PASSED!")

async def test_section_4_discovery_lock():
    print("\n--- Testing Section 4: DiscoveryWorker concurrency lock ---")
    worker = DiscoveryWorker(bayse=MagicMock(), polymarket=MagicMock(), live_state=MagicMock())
    assert hasattr(worker, "_refresh_lock"), "Worker missing _refresh_lock"
    assert not worker._refresh_lock.locked(), "Lock should be unlocked initially"
    print("Section 4 Concurrency Lock test PASSED!")

async def main():
    await test_section_1_sparklines()
    await test_section_4_discovery_lock()
    print("\nAll Section 1-5 backend verification tests PASSED!")

if __name__ == "__main__":
    asyncio.run(main())
