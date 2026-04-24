from collections import deque
from collections.abc import Iterable
import asyncio
from typing import Any

import httpx

from src.utils.logger import logger


DATA_BASE_URL = "https://data-api.polymarket.com"


class SlidingWindowLimiter:
    def __init__(self, *, limit: int, window_seconds: float):
        self.limit = limit
        self.window_seconds = window_seconds
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        while True:
            async with self._lock:
                now = asyncio.get_running_loop().time()
                while self._timestamps and now - self._timestamps[0] >= self.window_seconds:
                    self._timestamps.popleft()
                if len(self._timestamps) < self.limit:
                    self._timestamps.append(now)
                    return
                wait_for = self.window_seconds - (now - self._timestamps[0])
            await asyncio.sleep(max(wait_for, 0.01))


class PolymarketDataServices:
    MAX_RETRIES = 2

    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url=DATA_BASE_URL,
            headers={"Accept": "application/json"},
            timeout=httpx.Timeout(12.0, connect=5.0),
        )
        self._general_limiter = SlidingWindowLimiter(limit=80, window_seconds=10.0)

    async def close(self) -> None:
        await self.client.aclose()

    async def _get(self, path: str, *, params: dict | None = None):
        for attempt in range(1, self.MAX_RETRIES + 1):
            await self._general_limiter.acquire()
            try:
                logger.info("Polymarket Data GET %s params=%s", path, params)
                response = await self.client.get(path, params=params)
                response.raise_for_status()
                logger.info("Polymarket Data GET success %s status=%s", path, response.status_code)
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(
                    "Polymarket Data HTTP error status=%s url=%s body=%s",
                    e.response.status_code,
                    e.request.url,
                    e.response.text,
                )
                raise
            except httpx.TimeoutException as e:
                logger.warning(
                    "Polymarket Data timeout attempt=%s/%s url=%s",
                    attempt,
                    self.MAX_RETRIES,
                    e.request.url,
                )
                if attempt >= self.MAX_RETRIES:
                    logger.error("Polymarket Data timeout exhausted for url=%s", e.request.url, exc_info=True)
                    raise
            except httpx.RequestError as e:
                logger.error("Polymarket Data request error url=%s error=%s", e.request.url, e)
                raise

    async def get_live_volume(self, event_id: str) -> float | None:
        payload = await self._get("/live-volume", params={"id": event_id})
        if isinstance(payload, list) and payload:
            first = payload[0] or {}
            total = first.get("total")
            if total is not None:
                return float(total)
        if isinstance(payload, dict):
            total = payload.get("total")
            if total is not None:
                return float(total)
        return None

    async def get_open_interest(self, condition_ids: Iterable[str]) -> dict[str, float]:
        normalized = [condition_id for condition_id in dict.fromkeys(condition_ids) if condition_id]
        if not normalized:
            return {}
        payload = await self._get("/oi", params={"market": ",".join(normalized)})
        if not isinstance(payload, list):
            return {}
        result: dict[str, float] = {}
        for row in payload:
            market = row.get("market")
            value = row.get("value")
            if market is None or value is None:
                continue
            result[str(market)] = float(value)
        return result
