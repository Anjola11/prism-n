import asyncio
from collections import deque
from collections.abc import Iterable
from datetime import datetime, timezone
from enum import Enum
from math import ceil
from typing import Any

import httpx

from src.utils.logger import logger


CLOB_BASE_URL = "https://clob.polymarket.com"


class ClobInterval(str, Enum):
    MAX = "max"
    ALL = "all"
    MINUTE_1 = "1m"
    HOUR_1 = "1h"
    HOUR_6 = "6h"
    DAY_1 = "1d"
    WEEK_1 = "1w"


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

                sleep_for = self.window_seconds - (now - self._timestamps[0])

            await asyncio.sleep(max(sleep_for, 0.01))


class PolymarketCLOBServices:
    MAX_RETRIES = 2
    BOOK_BATCH_SIZE = 25
    HISTORY_BATCH_SIZE = 20

    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url=CLOB_BASE_URL,
            headers={"Accept": "application/json"},
            timeout=httpx.Timeout(15.0, connect=5.0),
        )
        # Deliberately conservative relative to official limits so background sync stays well behaved.
        self._general_limiter = SlidingWindowLimiter(limit=300, window_seconds=10.0)
        self._books_limiter = SlidingWindowLimiter(limit=120, window_seconds=10.0)
        self._history_limiter = SlidingWindowLimiter(limit=120, window_seconds=10.0)

    async def close(self) -> None:
        await self.client.aclose()

    async def _get(
        self,
        path: str,
        *,
        params: dict | None = None,
        limiter: SlidingWindowLimiter | None = None,
    ):
        limiter = limiter or self._general_limiter
        for attempt in range(1, self.MAX_RETRIES + 1):
            await limiter.acquire()
            try:
                logger.info("Polymarket CLOB GET %s params=%s", path, params)
                response = await self.client.get(path, params=params)
                response.raise_for_status()
                logger.info("Polymarket CLOB GET success %s status=%s", path, response.status_code)
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(
                    "Polymarket CLOB HTTP error status=%s url=%s body=%s",
                    e.response.status_code,
                    e.request.url,
                    e.response.text,
                )
                raise
            except httpx.TimeoutException as e:
                logger.warning(
                    "Polymarket CLOB timeout attempt=%s/%s url=%s",
                    attempt,
                    self.MAX_RETRIES,
                    e.request.url,
                )
                if attempt >= self.MAX_RETRIES:
                    logger.error("Polymarket CLOB timeout exhausted for url=%s", e.request.url, exc_info=True)
                    raise
            except httpx.RequestError as e:
                logger.error("Polymarket CLOB request error url=%s error=%s", e.request.url, e)
                raise

    async def _post(
        self,
        path: str,
        *,
        json_payload: Any,
        limiter: SlidingWindowLimiter | None = None,
    ):
        limiter = limiter or self._general_limiter
        for attempt in range(1, self.MAX_RETRIES + 1):
            await limiter.acquire()
            try:
                logger.info("Polymarket CLOB POST %s payload_size=%s", path, self._payload_size(json_payload))
                response = await self.client.post(path, json=json_payload)
                response.raise_for_status()
                logger.info("Polymarket CLOB POST success %s status=%s", path, response.status_code)
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(
                    "Polymarket CLOB HTTP error status=%s url=%s body=%s",
                    e.response.status_code,
                    e.request.url,
                    e.response.text,
                )
                raise
            except httpx.TimeoutException as e:
                logger.warning(
                    "Polymarket CLOB timeout attempt=%s/%s url=%s",
                    attempt,
                    self.MAX_RETRIES,
                    e.request.url,
                )
                if attempt >= self.MAX_RETRIES:
                    logger.error("Polymarket CLOB timeout exhausted for url=%s", e.request.url, exc_info=True)
                    raise
            except httpx.RequestError as e:
                logger.error("Polymarket CLOB request error url=%s error=%s", e.request.url, e)
                raise

    async def get_book(self, token_id: str) -> dict:
        return await self._get("/book", params={"token_id": token_id}, limiter=self._books_limiter)

    async def get_books(self, token_ids: Iterable[str]) -> list[dict]:
        normalized = [token_id for token_id in dict.fromkeys(token_ids) if token_id]
        if not normalized:
            return []

        responses: list[dict] = []
        for start in range(0, len(normalized), self.BOOK_BATCH_SIZE):
            batch = normalized[start : start + self.BOOK_BATCH_SIZE]
            payload = [{"token_id": token_id} for token_id in batch]
            result = await self._post("/books", json_payload=payload, limiter=self._books_limiter)
            if isinstance(result, list):
                responses.extend(result)
        return responses

    async def get_prices_history(
        self,
        *,
        asset_id: str,
        interval: ClobInterval = ClobInterval.WEEK_1,
        fidelity: int = 5,
        start_ts: int | None = None,
        end_ts: int | None = None,
    ) -> dict:
        params: dict[str, Any] = {
            "market": asset_id,
            "interval": interval.value,
            "fidelity": fidelity,
        }
        if start_ts is not None:
            params["startTs"] = start_ts
        if end_ts is not None:
            params["endTs"] = end_ts
        return await self._get("/prices-history", params=params, limiter=self._history_limiter)

    async def get_batch_prices_history(
        self,
        *,
        asset_ids: Iterable[str],
        interval: ClobInterval = ClobInterval.WEEK_1,
        fidelity: int = 5,
        start_ts: int | None = None,
        end_ts: int | None = None,
    ) -> dict[str, dict]:
        normalized = [asset_id for asset_id in dict.fromkeys(asset_ids) if asset_id]
        if not normalized:
            return {}

        results: dict[str, dict] = {}
        for start in range(0, len(normalized), self.HISTORY_BATCH_SIZE):
            batch = normalized[start : start + self.HISTORY_BATCH_SIZE]
            payload: dict[str, Any] = {
                "markets": batch,
                "interval": interval.value,
                "fidelity": fidelity,
            }
            if start_ts is not None:
                payload["start_ts"] = start_ts
            if end_ts is not None:
                payload["end_ts"] = end_ts

            response = await self._post("/batch-prices-history", json_payload=payload, limiter=self._history_limiter)
            if isinstance(response, dict):
                results.update(response)
        return results

    async def get_market_by_token(self, token_id: str) -> dict:
        return await self._get(f"/markets-by-token/{token_id}")

    async def get_clob_market(self, condition_id: str) -> dict:
        return await self._get(f"/clob-markets/{condition_id}")

    def midpoint_from_book(self, book: dict | None) -> float | None:
        if not book:
            return None
        bids = book.get("bids") or []
        asks = book.get("asks") or []
        best_bid = self._price(bids[0]) if bids else None
        best_ask = self._price(asks[0]) if asks else None
        if best_bid is not None and best_ask is not None:
            return (best_bid + best_ask) / 2
        if best_bid is not None:
            return best_bid
        if best_ask is not None:
            return best_ask
        return self._to_float(book.get("last_trade_price"))

    def spread_bps_from_book(self, book: dict | None) -> float | None:
        if not book:
            return None
        bids = book.get("bids") or []
        asks = book.get("asks") or []
        best_bid = self._price(bids[0]) if bids else None
        best_ask = self._price(asks[0]) if asks else None
        if best_bid is None or best_ask is None:
            return None
        return max(best_ask - best_bid, 0.0) * 10_000

    def level_total(self, level: dict | None) -> float:
        if not level:
            return 0.0
        price = self._price(level) or 0.0
        size = self._size(level) or 0.0
        return price * size

    def timestamp_iso(self, raw_timestamp: str | int | None) -> str | None:
        if raw_timestamp is None:
            return None
        try:
            value = int(raw_timestamp)
        except (TypeError, ValueError):
            return None
        if value > 10_000_000_000:
            seconds = value / 1000
        else:
            seconds = value
        return datetime.fromtimestamp(seconds, tz=timezone.utc).isoformat()

    def _payload_size(self, payload: Any) -> int:
        if isinstance(payload, list):
            return len(payload)
        if isinstance(payload, dict):
            markets = payload.get("markets")
            if isinstance(markets, list):
                return len(markets)
            return ceil(len(payload))
        return 1

    def _price(self, level: dict | None) -> float | None:
        if not level:
            return None
        value = level.get("price")
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _size(self, level: dict | None) -> float | None:
        if not level:
            return None
        value = level.get("size")
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
