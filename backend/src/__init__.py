from fastapi import FastAPI, Request, HTTPException, status
from contextlib import asynccontextmanager
from src.db.main import init_db
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from src.utils.logger import logger
from src.auth.routes import auth_router

from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from src.db.redis import redis_client, check_redis_connection
from src.utils.logger import logger
from src.config import Config

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize Postgres
    await init_db()
    
    # 2. Check Redis Connection
    await check_redis_connection()

    yield
    
    # 3. Clean up Redis connections on shutdown
    logger.info("Closing Redis Connection")
    if redis_client:
        await redis_client.close()
    logger.info("Server Closed")



logger.info("server starting")
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
def health_check():
    return "server working"


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
