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
    app.state.live_state = LiveStateServices()
    app.state.baseline_services = BaselineServices(
        bayse=app.state.bayse,
        polymarket_clob=app.state.polymarket_clob,
    )
    app.state.scoring_services = ScoringServices()
    app.state.signal_snapshot_services = SignalSnapshotServices()
    app.state.ai_insight_services = AIInsightServices()

    logger.info("Stateless Web Process ready (Reads from Redis & Postgres)")

    yield

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

origins = [str(o).strip() for o in Config.ALLOWED_ORIGINS if o]
has_wildcard = "*" in origins or not origins

if has_wildcard:
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"https?://.*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.add_middleware(
    GZipMiddleware,
    minimum_size=1024
)

import time
import json
from src.db.main import async_session_maker
from sqlmodel import select

@app.middleware("http")
async def json_logging_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - start_time) * 1000, 2)
    logger.info(
        json.dumps({
            "event": "http_request",
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "latency_ms": duration_ms,
        })
    )
    return response


@app.get("/")
def root_health_check():
    return "server working"


@app.get("/healthz")
def health_check():
    return {
        "success": True,
        "message": "Server healthy",
        "data": {
            "status": "ok",
            "process": "web",
        },
    }


@app.get("/readiness")
async def readiness_check():
    redis_ok = False
    db_ok = False

    try:
        if redis_client:
            await redis_client.ping()
            redis_ok = True
    except Exception as e:
        logger.warning("Readiness probe Redis ping failed: %s", e)

    try:
        async with async_session_maker() as session:
            await session.exec(select(1))
            db_ok = True
    except Exception as e:
        logger.warning("Readiness probe DB ping failed: %s", e)

    if redis_ok and db_ok:
        return {
            "success": True,
            "message": "Service ready",
            "data": {"redis": "ok", "db": "ok"},
        }
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "success": False,
            "message": "Service unready",
            "data": {"redis": "ok" if redis_ok else "error", "db": "ok" if db_ok else "error"},
        },
    )



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


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled server exception on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "An internal server error occurred",
            "data": None,
        },
    )


app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(admin_router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(markets_router, prefix="/api/v1", tags=["Markets"])

