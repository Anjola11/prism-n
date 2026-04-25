from redis.asyncio import Redis
from src.config import Config

from src.utils.logger import logger

# Initialize
redis_client = Redis.from_url(
    Config.REDIS_URL,
    decode_responses=True,
    max_connections=Config.REDIS_MAX_CONNECTIONS,
    health_check_interval=30,
    socket_connect_timeout=10,
    socket_timeout=10,
)

async def check_redis_connection():
    try:
        await redis_client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.error(f"Redis connection failed:", exc_info=True)
