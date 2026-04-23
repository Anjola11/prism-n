from enum import Enum
from uuid import UUID

import httpx

from src.markets.models import Currency
from src.utils.logger import logger

class HistoryWindow(str, Enum):
    HOURS_12 = "12H"
    HOURS_24 = "24H"
    WEEK_1 = "1W"
    MONTH_1 = "1M"
    YEAR_1 = "1Y"

class Outcome(str, Enum):
    YES = "YES"
    NO = "NO"

BASE_URL = "https://relay.bayse.markets/v1/pm/"


class BayseServices:

    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url=BASE_URL,
            headers={"Accept": "application/json"},
            timeout=httpx.Timeout(15.0, connect=5.0)
        )
    
    async def close(self):
        await self.client.aclose()

    def _serialize_value(self, value):
        if value is None:
            return None
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, UUID):
            return str(value)
        if isinstance(value, list):
            return [self._serialize_value(item) for item in value]
        return value

    def _clean_params(self, params: dict | None) -> dict | None:
        if not params:
            return None
        return {
            key: self._serialize_value(value)
            for key, value in params.items()
            if value is not None
        }

    async def base_call(self, path: str, params: dict | None = None):
        params = self._clean_params(params)
        logger.info("Bayse GET %s params=%s", path, params)

        try:
            response = await self.client.get(url=path, params=params)

            response.raise_for_status()

            logger.info("Bayse GET success %s status=%s", path, response.status_code)
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(
                "Bayse HTTP error status=%s url=%s body=%s",
                e.response.status_code,
                e.request.url,
                e.response.text,
            )
            raise

        except httpx.RequestError as e:
            logger.error("Bayse request error url=%s error=%s", e.request.url, e)
            raise 

        except Exception as e:
            logger.error("Unexpected Bayse client error: %s", e, exc_info=True)
            raise

    async def get_all_listings(
        self,
        trending: bool = True,
        currency: Currency = Currency.DOLLAR,
    ):
        path = "events"
        params = {
            "status": "open",
            "page": 1,
            "size": 20,
            "trending": trending,
            "currency": currency,
        }

        listings = await self.base_call(path, params)
        return listings

    async def get_event_by_id(
        self,
        event_id: str,
        currency: Currency = Currency.DOLLAR,
    ):
        path = f"events/{event_id}"
        params = {"currency": currency}

        event = await self.base_call(path, params)
        return event

    async def get_price_history(
        self,
        event_id: str,
        window: HistoryWindow = HistoryWindow.HOURS_24,
        outcome: Outcome | None = None,
    ):
        path = f"events/{event_id}/price-history"
        params = {"timePeriod": window, "outcome": outcome}

        price_history = await self.base_call(path, params)
        return price_history

    async def get_order_book(
        self,
        outcome_id: str,
        depth: int = 10,
        currency: Currency = Currency.NAIRA,
    ):
        path = "books"
        params = {"outcomeId": outcome_id, "depth": depth, "currency": currency}

        order_book = await self.base_call(path, params)

        return order_book

    async def get_ticker(
        self,
        market_id: str,
        outcome_id: str | None = None,
        outcome: Outcome | None = None,
    ):
        path = f"markets/{market_id}/ticker"
        params = {"outcomeId": outcome_id, "outcome": outcome}

        try:
            ticker = await self.base_call(path, params)
        except httpx.HTTPStatusError as exc:
            message = None
            try:
                payload = exc.response.json()
                if isinstance(payload, dict):
                    message = payload.get("message")
            except ValueError:
                payload = None

            if exc.response.status_code == 400 and message == "market does not have an active orderbook":
                return None
            raise

        return ticker

    async def get_trades(
        self,
        market_id: str,
        id: str | None = None,
        limit: int = 50,
    ):
        path = "trades"
        params = {"marketId": market_id, "id": id, "limit": limit}

        trades = await self.base_call(path, params)

        return trades

