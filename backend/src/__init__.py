from fastapi import FastAPI, Request, HTTPException, status
from contextlib import asynccontextmanager
from src.db.main import init_db
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from src.utils.logger import logger
from src.auth.routes import auth_router
from src.admin.routes import admin_router
from src.markets.routes import markets_router

from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from src.db.redis import redis_client, check_redis_connection
from src.utils.logger import logger
from src.config import Config
from src.utils.bayse import BayseServices
from src.utils.polymarket_clob import PolymarketCLOBServices
from src.utils.polymarket_data import PolymarketDataServices
from src.utils.polymarket import PolymarketServices
from src.markets.baselines import BaselineServices
from src.markets.baseline_scheduler import BaselineRefreshScheduler
from src.markets.live_state import LiveStateServices
from src.markets.scoring import ScoringServices
from src.markets.signal_snapshots import SignalSnapshotServices
from src.markets.polymarket_websocket_manager import PolymarketWebSocketManager
from src.markets.websocket_manager import BayseWebSocketManager
from src.markets.discovery_worker import DiscoveryWorker
from src.markets.ai_insights import AIInsightServices

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Postgres
    await init_db()
    
    # Check Redis Connection
    await check_redis_connection()

    app.state.bayse = BayseServices()
    app.state.polymarket = PolymarketServices()
    app.state.polymarket_clob = PolymarketCLOBServices()
    app.state.polymarket_data = PolymarketDataServices()
    logger.info("BayseServices started (HTTP Connection Pool ready)")
    app.state.live_state = LiveStateServices()
    app.state.baseline_services = BaselineServices(
        bayse=app.state.bayse,
        polymarket_clob=app.state.polymarket_clob,
    )
    app.state.scoring_services = ScoringServices()
    app.state.signal_snapshot_services = SignalSnapshotServices()
    app.state.ai_insight_services = AIInsightServices()
    app.state.bayse_ws_manager = BayseWebSocketManager(
        bayse=app.state.bayse,
        live_state=app.state.live_state,
        baseline_services=app.state.baseline_services,
        scoring_services=app.state.scoring_services,
        signal_snapshot_services=app.state.signal_snapshot_services,
    )
    await app.state.bayse_ws_manager.start()
    logger.info("Bayse websocket manager started")
    app.state.polymarket_ws_manager = PolymarketWebSocketManager(
        clob=app.state.polymarket_clob,
        data_api=app.state.polymarket_data,
        live_state=app.state.live_state,
        baseline_services=app.state.baseline_services,
        scoring_services=app.state.scoring_services,
        signal_snapshot_services=app.state.signal_snapshot_services,
    )
    await app.state.polymarket_ws_manager.start()
    logger.info("Polymarket websocket manager started")
    app.state.baseline_scheduler = BaselineRefreshScheduler(
        baseline_services=app.state.baseline_services,
        on_refresh=_reset_all_baseline_caches(
            app.state.bayse_ws_manager,
            app.state.polymarket_ws_manager,
        ),
    )
    await app.state.baseline_scheduler.start()
    logger.info("Baseline refresh scheduler started")

    app.state.discovery_worker = DiscoveryWorker(
        bayse=app.state.bayse,
        polymarket=app.state.polymarket,
        live_state=app.state.live_state,
    )
    await app.state.discovery_worker.start()
    logger.info("Discovery worker started")

    yield
    
    if hasattr(app.state, "discovery_worker"):
        try:
            await app.state.discovery_worker.stop()
        except Exception as e:
            logger.error(f"Error stopping discovery worker: {e}")

    if hasattr(app.state, "baseline_scheduler"):
        try:
            await app.state.baseline_scheduler.stop()
        except Exception as e:
            logger.error(f"Error stopping baseline scheduler: {e}")

    if hasattr(app.state, "bayse_ws_manager"):
        try:
            await app.state.bayse_ws_manager.stop()
        except Exception as e:
            logger.error(f"Error stopping Bayse websocket manager: {e}")

    if hasattr(app.state, "polymarket_ws_manager"):
        try:
            await app.state.polymarket_ws_manager.stop()
        except Exception as e:
            logger.error(f"Error stopping Polymarket websocket manager: {e}")

    if hasattr(app.state, "bayse"):
        try:
            await app.state.bayse.close()
        except Exception as e:
            logger.error(f"Error closing BayseServices: {e}")

    if hasattr(app.state, "polymarket"):
        try:
            await app.state.polymarket.close()
        except Exception as e:
            logger.error(f"Error closing PolymarketServices: {e}")

    if hasattr(app.state, "polymarket_clob"):
        try:
            await app.state.polymarket_clob.close()
        except Exception as e:
            logger.error(f"Error closing PolymarketCLOBServices: {e}")

    if hasattr(app.state, "polymarket_data"):
        try:
            await app.state.polymarket_data.close()
        except Exception as e:
            logger.error(f"Error closing PolymarketDataServices: {e}")

    # Clean up Redis connections on shutdown
    logger.info("Closing Redis Connection")
    if redis_client:
        await redis_client.close()
    logger.info("Server Closed")



logger.info("server starting")


def _reset_all_baseline_caches(*managers):
    def _reset():
        for manager in managers:
            try:
                manager.reset_baseline_cache()
            except Exception:
                logger.warning("Failed resetting websocket baseline cache", exc_info=True)
    return _reset


app = FastAPI(
    title="API for Prism Auth",
    description="Documentation of Prism Authentication API",
    lifespan=lifespan
)

origins = Config.ALLOWED_ORIGINS if Config.ALLOWED_ORIGINS else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins = origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    GZipMiddleware,
    minimum_size=1024
)

@app.get("/")
def root_health_check():
    return "server working"


@app.get("/healthz")
def health_check():
    bayse_ws_manager = getattr(app.state, "bayse_ws_manager", None)
    polymarket_ws_manager = getattr(app.state, "polymarket_ws_manager", None)
    baseline_scheduler = getattr(app.state, "baseline_scheduler", None)
    discovery_worker = getattr(app.state, "discovery_worker", None)
    return {
        "success": True,
        "message": "Server healthy",
        "data": {
            "status": "ok",
            "bayse_websocket_running": bool(
                bayse_ws_manager and bayse_ws_manager._task and not bayse_ws_manager._task.done()
            ),
            "polymarket_websocket_running": bool(
                polymarket_ws_manager and polymarket_ws_manager._task and not polymarket_ws_manager._task.done()
            ),
            "baseline_scheduler_running": bool(
                baseline_scheduler and baseline_scheduler._task and not baseline_scheduler._task.done()
            ),
            "discovery_worker_running": bool(
                discovery_worker and discovery_worker._task and not discovery_worker._task.done()
            ),
        },
    }


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc:HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content = {
            "success": False,
            "message": exc.detail,
            "data": None
        }
    )

def format_validation_errors(errors):
    formatted = []
    for err in errors:
        loc = err["loc"]
        field = ".".join(str(l) for l in loc[1:]) if len(loc) > 1 else str(loc[0])
        formatted.append({
            "field": field,
            "message": err["msg"]
        })
    return formatted

@app.exception_handler(RequestValidationError)
async def custom_validation_exception_handler(request:Request, exc: RequestValidationError):
    logger.error(f"validation error", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "success": False,
            "message": "Validation error",
            "errors": format_validation_errors(exc.errors()),
            "data": None
        }
    )


app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(admin_router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(markets_router, prefix="/api/v1", tags=["Markets"])
