from enum import Enum

import httpx

from src.utils.logger import logger


class PolymarketOrder(str, Enum):
    VOLUME_24H = "volume24hr"
    LIQUIDITY = "liquidity"
    UPDATED_AT = "updatedAt"


GAMMA_BASE_URL = "https://gamma-api.polymarket.com"


class PolymarketServices:
    MAX_RETRIES = 2

    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url=GAMMA_BASE_URL,
            headers={"Accept": "application/json"},
            timeout=httpx.Timeout(15.0, connect=5.0),
        )

    async def close(self):
        await self.client.aclose()

    async def base_call(self, path: str, params: dict | None = None):
        logger.info("Polymarket GET %s params=%s", path, params)
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                response = await self.client.get(url=path, params=params)
                response.raise_for_status()
                logger.info("Polymarket GET success %s status=%s", path, response.status_code)
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(
                    "Polymarket HTTP error status=%s url=%s body=%s",
                    e.response.status_code,
                    e.request.url,
                    e.response.text,
                )
                raise
            except httpx.TimeoutException as e:
                logger.warning(
                    "Polymarket timeout attempt=%s/%s url=%s",
                    attempt,
                    self.MAX_RETRIES,
                    e.request.url,
                )
                if attempt >= self.MAX_RETRIES:
                    logger.error("Polymarket timeout exhausted for url=%s", e.request.url, exc_info=True)
                    raise
            except httpx.RequestError as e:
                logger.error("Polymarket request error url=%s error=%s", e.request.url, e)
                raise

    async def get_events(
        self,
        *,
        limit: int = 24,
        active: bool = True,
        closed: bool = False,
        archived: bool = False,
        order: str = "volume24hr",
        ascending: bool = False,
    ):
        return await self.base_call(
            "/events",
            params={
                "limit": limit,
                "active": active,
                "closed": closed,
                "archived": archived,
                "order": order,
                "ascending": ascending,
            },
        )

    async def get_event_by_id(self, event_id: str):
        return await self.base_call(f"/events/{event_id}")
