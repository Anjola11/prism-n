import time
import asyncio
from src.utils.logger import logger


class CircuitBreakerOpenException(Exception):
    pass


class CircuitBreaker:
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF-OPEN

    async def call(self, func, *args, **kwargs):
        now = time.time()
        if self.state == "OPEN":
            if now - self.last_failure_time > self.recovery_timeout:
                logger.info("Circuit breaker '%s' entering HALF-OPEN state", self.name)
                self.state = "HALF-OPEN"
            else:
                raise CircuitBreakerOpenException(f"Circuit breaker '{self.name}' is OPEN")

        try:
            result = await func(*args, **kwargs)
            if self.state == "HALF-OPEN":
                logger.info("Circuit breaker '%s' recovered to CLOSED state", self.name)
                self.state = "CLOSED"
                self.failure_count = 0
            return result
        except Exception as exc:
            self.failure_count += 1
            self.last_failure_time = now
            if self.failure_count >= self.failure_threshold:
                if self.state != "OPEN":
                    logger.warning(
                        "Circuit breaker '%s' tripped to OPEN after %s consecutive failures: %s",
                        self.name,
                        self.failure_count,
                        exc,
                    )
                self.state = "OPEN"
            raise exc
