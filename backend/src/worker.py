import asyncio
import signal
import sys
from src.db.main import init_db
from src.db.redis import redis_client, check_redis_connection
from src.utils.logger import logger
from src.utils.bayse import BayseServices
from src.utils.polymarket import PolymarketServices
from src.utils.polymarket_clob import PolymarketCLOBServices
from src.utils.polymarket_data import PolymarketDataServices
from src.markets.baselines import BaselineServices
from src.markets.baseline_scheduler import BaselineRefreshScheduler
from src.markets.live_state import LiveStateServices
from src.markets.scoring import ScoringServices
from src.markets.signal_snapshots import SignalSnapshotServices
from src.markets.polymarket_websocket_manager import PolymarketWebSocketManager
from src.markets.websocket_manager import BayseWebSocketManager
from src.markets.discovery_worker import DiscoveryWorker
from src.markets.ai_insights import AIInsightServices


def _reset_all_baseline_caches(*managers):
    def _reset():
        for manager in managers:
            try:
                manager.reset_baseline_cache()
            except Exception:
                logger.warning("Failed resetting websocket baseline cache in worker", exc_info=True)
    return _reset


async def run_worker():
    logger.info("Starting Prism Background Ingestion Worker Process...")

    # Initialize Postgres
    await init_db()

    # Check Redis Connection
    await check_redis_connection()

    bayse = BayseServices()
    polymarket = PolymarketServices()
    polymarket_clob = PolymarketCLOBServices()
    polymarket_data = PolymarketDataServices()

    live_state = LiveStateServices()
    baseline_services = BaselineServices(
        bayse=bayse,
        polymarket_clob=polymarket_clob,
    )
    scoring_services = ScoringServices()
    signal_snapshot_services = SignalSnapshotServices()
    ai_insight_services = AIInsightServices()

    bayse_ws_manager = BayseWebSocketManager(
        bayse=bayse,
        live_state=live_state,
        baseline_services=baseline_services,
        scoring_services=scoring_services,
        signal_snapshot_services=signal_snapshot_services,
    )
    await bayse_ws_manager.start()
    logger.info("Worker: Bayse WebSocket manager started")

    polymarket_ws_manager = PolymarketWebSocketManager(
        clob=polymarket_clob,
        data_api=polymarket_data,
        live_state=live_state,
        baseline_services=baseline_services,
        scoring_services=scoring_services,
        signal_snapshot_services=signal_snapshot_services,
    )
    await polymarket_ws_manager.start()
    logger.info("Worker: Polymarket WebSocket manager started")

    baseline_scheduler = BaselineRefreshScheduler(
        baseline_services=baseline_services,
        on_refresh=_reset_all_baseline_caches(
            bayse_ws_manager,
            polymarket_ws_manager,
        ),
    )
    await baseline_scheduler.start()
    logger.info("Worker: Baseline refresh scheduler started")

    discovery_worker = DiscoveryWorker(
        bayse=bayse,
        polymarket=polymarket,
        live_state=live_state,
    )
    await discovery_worker.start()
    logger.info("Worker: Discovery worker started")

    stop_event = asyncio.Event()

    def _on_signal(*_):
        logger.info("Worker shutdown signal received")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for s in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(s, _on_signal)
        except NotImplementedError:
            # Signal handling on Windows
            pass

    logger.info("Worker is running and ingesting live market data...")
    try:
        await stop_event.wait()
    except asyncio.CancelledError:
        pass
    finally:
        logger.info("Shutting down worker components...")
        try:
            await discovery_worker.stop()
        except Exception as e:
            logger.error(f"Error stopping discovery worker: {e}")

        try:
            await baseline_scheduler.stop()
        except Exception as e:
            logger.error(f"Error stopping baseline scheduler: {e}")

        try:
            await bayse_ws_manager.stop()
        except Exception as e:
            logger.error(f"Error stopping Bayse websocket manager: {e}")

        try:
            await polymarket_ws_manager.stop()
        except Exception as e:
            logger.error(f"Error stopping Polymarket websocket manager: {e}")

        try:
            await bayse.close()
            await polymarket.close()
            await polymarket_clob.close()
            await polymarket_data.close()
        except Exception as e:
            logger.error(f"Error closing API services: {e}")

        if redis_client:
            await redis_client.close()
        logger.info("Worker stopped cleanly.")


if __name__ == "__main__":
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
        sys.exit(0)
