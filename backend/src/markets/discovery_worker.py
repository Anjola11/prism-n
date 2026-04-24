"""
Background worker that periodically fetches Bayse listings and writes
a fully-assembled discovery read-model to Redis.

This ensures that user-facing discovery routes NEVER block on Bayse REST.
They read from Redis only (<50ms) instead of waiting 1-3s+ for Bayse.
"""

import asyncio
import json
from datetime import datetime, timezone

import httpx
from sqlmodel import select

from src.db.main import async_session_maker
from src.markets.live_state import LiveStateServices
from src.markets.models import (
    Currency,
    MarketEngine,
    MarketSource,
    TrackedEventMetric,
    TrackedMarket,
    UserTrackedEvent,
)
from src.markets.schemas import (
    DiscoveryEventRead,
    HighestScoringMarketRead,
    SignalRead,
)
from src.utils.bayse import BayseServices
from src.utils.logger import logger
from src.utils.polymarket import PolymarketServices


class DiscoveryWorker:
    """Refreshes the discovery feed read-model in Redis on a timer."""

    REDIS_NAMESPACE = "discovery-feed"
    REDIS_TTL = 90  # safety expiry; worker refreshes every interval_seconds

    def __init__(
        self,
        *,
        bayse: BayseServices,
        polymarket: PolymarketServices,
        live_state: LiveStateServices,
        interval_seconds: int = 30,
        initial_delay_seconds: int = 3,
        currencies: list[Currency] | None = None,
    ):
        self.bayse = bayse
        self.polymarket = polymarket
        self.live_state = live_state
        self.interval_seconds = interval_seconds
        self.initial_delay_seconds = initial_delay_seconds
        self.currencies = currencies or [Currency.NAIRA]

        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run(), name="discovery-worker")
        logger.info("Discovery worker started")

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Discovery worker stopped")

    async def _run(self) -> None:
        if self.initial_delay_seconds > 0:
            await asyncio.sleep(self.initial_delay_seconds)

        while not self._stop_event.is_set():
            for currency in self.currencies:
                try:
                    await self._refresh_currency(currency)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.warning(
                        "Discovery worker refresh failed for %s",
                        currency.value,
                        exc_info=True,
                    )

            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.interval_seconds,
                )
                break  # stop_event was set
            except asyncio.TimeoutError:
                pass  # normal: interval elapsed, loop again

    async def _refresh_currency(self, currency: Currency) -> None:
        """Fetch Bayse listings, enrich with tracked state, write to Redis."""

        # 1. Fetch from upstreams (this is the slow part — but we're in background)
        try:
            listings_payload = await self.bayse.get_all_listings(currency=currency)
            bayse_events = listings_payload.get("events", [])
        except (httpx.TimeoutException, httpx.RequestError):
            logger.warning(
                "Discovery worker: Bayse timeout for %s, skipping cycle",
                currency.value,
            )
            bayse_events = []

        try:
            polymarket_events = await self.polymarket.get_events(limit=24, active=True, closed=False, archived=False)
        except (httpx.TimeoutException, httpx.RequestError):
            logger.warning("Discovery worker: Polymarket timeout, skipping poly cycle", exc_info=True)
            polymarket_events = []

        if not bayse_events and not polymarket_events:
            logger.info("Discovery worker: no events from Bayse or Polymarket for %s", currency.value)
            return

        # 2. Load tracking context from DB
        async with async_session_maker() as session:
            # System-tracked event IDs
            system_result = await session.exec(
                select(TrackedMarket.event_id).where(
                    TrackedMarket.is_system_tracked == True,
                    TrackedMarket.tracking_enabled == True,
                )
            )
            system_tracked_ids: set[str] = set(system_result.all())

            # All tracked markets for events in this listing
            event_ids = [e.get("id") for e in bayse_events if e.get("id")] + [str(e.get("id")) for e in polymarket_events if e.get("id")]
            tracked_result = await session.exec(
                select(TrackedMarket).where(
                    TrackedMarket.event_id.in_(event_ids),
                    TrackedMarket.tracking_enabled == True,
                )
            )
            all_tracked_markets = tracked_result.all()
            tracked_map: dict[str, list[TrackedMarket]] = {}
            for tm in all_tracked_markets:
                tracked_map.setdefault(tm.event_id, []).append(tm)

            # Tracked event metrics
            metric_result = await session.exec(
                select(TrackedEventMetric).where(
                    TrackedEventMetric.event_id.in_(event_ids),
                )
            )
            metrics: dict[tuple[str, str], TrackedEventMetric] = {}
            for m in metric_result.all():
                metrics[(m.event_id, m.currency.value)] = m

        # 3. Build discovery cards
        discovery_items: list[dict] = []
        bayse_cards: list[dict] = []
        for event_payload in bayse_events:
            event_id = event_payload.get("id")
            if not event_id:
                continue

            try:
                card = await self._build_card(
                    event_payload=event_payload,
                    currency=currency,
                    tracked_markets=tracked_map.get(event_id),
                    metric=metrics.get((event_id, currency.value)),
                    is_system_tracked=event_id in system_tracked_ids,
                )
                bayse_cards.append(card)
            except Exception:
                logger.warning(
                    "Discovery worker: failed to build card for event %s",
                    event_id,
                    exc_info=True,
                )

        polymarket_cards: list[dict] = []
        for event_payload in polymarket_events:
            event_id = str(event_payload.get("id") or "")
            if not event_id:
                continue

            try:
                card = await self._build_polymarket_card(
                    event_payload=event_payload,
                    tracked_markets=tracked_map.get(event_id),
                    metric=metrics.get((event_id, Currency.DOLLAR.value)),
                    is_system_tracked=event_id in system_tracked_ids,
                )
                polymarket_cards.append(card)
            except Exception:
                logger.warning(
                    "Discovery worker: failed to build polymarket card for event %s",
                    event_id,
                    exc_info=True,
                )

        bayse_cards.sort(
            key=lambda item: (
                item.get("data_mode") != "tracked_live",
                not item.get("tracking_enabled", False),
                (item.get("event_title") or "").lower(),
            )
        )
        polymarket_cards.sort(
            key=lambda item: (
                item.get("data_mode") != "tracked_live",
                not item.get("tracking_enabled", False),
                -(item.get("total_liquidity") or 0.0),
                -(item.get("event_total_orders") or 0),
            )
        )

        # 4. Mix: first 3 Bayse cards, then Polymarket ranked by liquidity/activity, then leftover Bayse
        discovery_items = bayse_cards[:3] + polymarket_cards + bayse_cards[3:]

        # 5. Write to Redis
        await self.live_state.set_read_model(
            namespace=self.REDIS_NAMESPACE,
            identifier=currency.value,
            payload=discovery_items,
            ttl_seconds=self.REDIS_TTL,
        )
        logger.info(
            "Discovery worker: refreshed %d events for %s",
            len(discovery_items),
            currency.value,
        )

    async def _build_card(
        self,
        *,
        event_payload: dict,
        currency: Currency,
        tracked_markets: list[TrackedMarket] | None,
        metric: TrackedEventMetric | None,
        is_system_tracked: bool,
    ) -> dict:
        """Build a single discovery card dict.

        If the event is tracked, enrich with Redis live state and signals.
        Otherwise, build a lightweight card from the listing payload.
        """

        event_id = event_payload["id"]

        # Parse event-level fields from Bayse payload
        event_title = event_payload.get("title", "")
        event_slug = event_payload.get("slug")
        event_type_raw = event_payload.get("type", "SINGLE_MARKET")
        engine_raw = event_payload.get("engine", "AMM")
        category = event_payload.get("category")
        status = event_payload.get("status")
        total_liquidity = event_payload.get("liquidity")
        event_total_orders = event_payload.get("totalOrders")
        closing_date_raw = event_payload.get("closingDate")

        # Normalize
        event_type_map = {"COMBINED_MARKETS": "combined", "SINGLE_MARKET": "single"}
        event_type = event_type_map.get(event_type_raw, "single")
        engine = engine_raw.upper() if engine_raw else "AMM"
        if category:
            category = " ".join(category.strip().split()).upper()

        closing_date = None
        if closing_date_raw:
            try:
                closing_date = datetime.fromisoformat(
                    closing_date_raw.replace("Z", "+00:00")
                ).isoformat()
            except (ValueError, TypeError):
                pass

        bayse_markets = event_payload.get("markets", [])

        # --- Tracked path: enrich from Redis live state ---
        if tracked_markets:
            first = tracked_markets[0]

            # Get live event metadata from Redis
            live_event = await self.live_state.get_event_state(
                source=MarketSource.BAYSE,
                event_id=event_id,
                currency=currency,
            )
            live_liquidity = live_event.total_liquidity if live_event else None
            live_last_updated = live_event.last_synced_at if live_event else None

            effective_liquidity = (
                live_liquidity
                if live_liquidity is not None
                else (metric.total_liquidity if metric else total_liquidity)
            )

            # Build highest scoring market from live signals
            best_score = -1.0
            best_market: dict | None = None

            for tm in tracked_markets:
                signal_state = await self.live_state.get_signal_state(
                    source=tm.source,
                    market_id=tm.market_id,
                    currency=currency,
                )
                market_state = await self.live_state.get_market_state(
                    source=tm.source,
                    market_id=tm.market_id,
                    currency=currency,
                )

                score = signal_state.score if signal_state else 0.0
                prob = (
                    market_state.current_probability
                    if market_state and market_state.current_probability is not None
                    else (tm.current_probability or 0.0)
                )
                prev_prob = (
                    market_state.previous_probability
                    if market_state
                    else None
                )
                delta = (prob - prev_prob) if prev_prob is not None else 0.0

                direction_map = {"UP": "RISING", "DOWN": "FALLING", "FLAT": "STABLE", None: "STABLE"}

                candidate = {
                    "market_id": tm.market_id,
                    "market_title": tm.market_title,
                    "current_probability": prob,
                    "probability_delta": delta,
                    "signal": {
                        "score": score,
                        "classification": signal_state.classification if signal_state else "unscored",
                        "direction": direction_map.get(
                            market_state.last_direction if market_state else None, "STABLE"
                        ),
                        "formula": signal_state.formula if signal_state else None,
                        "factors": signal_state.factors if signal_state else None,
                        "notes": signal_state.notes if signal_state else [],
                        "detected_at": signal_state.scored_at if signal_state else None,
                    },
                }

                if score > best_score or (score == best_score and prob > (best_market or {}).get("current_probability", -1)):
                    best_score = score
                    best_market = candidate

            return {
                "event_id": event_id,
                "event_title": first.event_title,
                "event_slug": first.event_slug,
                "event_icon_url": first.market_image_128_url or first.market_image_url,
                "source": first.source.value,
                "currency": currency.value,
                "event_type": first.event_type.value,
                "category": first.category,
                "status": first.status,
                "engine": first.engine.value,
                "total_liquidity": effective_liquidity,
                "event_total_orders": first.event_total_orders,
                "closing_date": closing_date,
                "tracked_markets_count": len(tracked_markets),
                "tracking_enabled": False,  # user-specific; overlaid at read time
                "data_mode": "tracked_live",
                "last_updated": live_last_updated,
                "ai_insight": "Insight unavailable",
                "highest_scoring_market": best_market,
            }

        # --- Untracked path: lightweight card from listing ---
        markets_list = event_payload.get("markets", [])
        first_market = markets_list[0] if markets_list else None

        highest = None
        if first_market:
            highest = {
                "market_id": first_market.get("id", ""),
                "market_title": first_market.get("title", ""),
                "current_probability": first_market.get("outcome1Price"),
                "probability_delta": 0.0,
                "signal": {
                    "score": 0.0,
                    "classification": "unscored",
                    "direction": "STABLE",
                    "formula": None,
                    "factors": None,
                    "notes": [],
                    "detected_at": None,
                },
            }

        return {
            "event_id": event_id,
            "event_title": event_title,
            "event_slug": event_slug,
            "event_icon_url": (first_market or {}).get("image128Url") or (first_market or {}).get("imageUrl"),
            "source": "bayse",
            "currency": currency.value,
            "event_type": event_type,
            "category": category,
            "status": status,
            "engine": engine,
            "total_liquidity": total_liquidity,
            "event_total_orders": event_total_orders,
            "closing_date": closing_date,
            "tracked_markets_count": len(markets_list),
            "tracking_enabled": False,
            "data_mode": "lite_snapshot",
            "last_updated": None,
            "ai_insight": "Insight unavailable",
            "highest_scoring_market": highest,
        }

    async def _build_polymarket_card(
        self,
        *,
        event_payload: dict,
        tracked_markets: list[TrackedMarket] | None,
        metric: TrackedEventMetric | None,
        is_system_tracked: bool,
    ) -> dict:
        event_id = str(event_payload["id"])
        markets_list = event_payload.get("markets", [])
        event_type = "combined" if len(markets_list) > 1 else "single"
        total_liquidity = event_payload.get("liquidity")
        if total_liquidity is None:
            total_liquidity = event_payload.get("liquidityClob")
        event_total_orders = int(float(event_payload.get("volume") or 0))

        if tracked_markets:
            first = tracked_markets[0]
            live_event = await self.live_state.get_event_state(
                source=MarketSource.POLYMARKET,
                event_id=event_id,
                currency=Currency.DOLLAR,
            )
            live_liquidity = live_event.total_liquidity if live_event else None
            live_last_updated = live_event.last_synced_at if live_event else event_payload.get("updatedAt")
            effective_liquidity = (
                live_liquidity
                if live_liquidity is not None
                else (metric.total_liquidity if metric else total_liquidity)
            )

            best_score = -1.0
            best_market = None
            for tm in tracked_markets:
                signal_state = await self.live_state.get_signal_state(
                    source=tm.source,
                    market_id=tm.market_id,
                    currency=Currency.DOLLAR,
                )
                market_state = await self.live_state.get_market_state(
                    source=tm.source,
                    market_id=tm.market_id,
                    currency=Currency.DOLLAR,
                )
                score = signal_state.score if signal_state else 0.0
                prob = (
                    market_state.current_probability
                    if market_state and market_state.current_probability is not None
                    else (tm.current_probability or 0.0)
                )
                prev_prob = market_state.previous_probability if market_state else None
                delta = (prob - prev_prob) if prev_prob is not None else 0.0
                best_market_candidate = {
                    "market_id": tm.market_id,
                    "market_title": tm.market_title,
                    "current_probability": prob,
                    "probability_delta": delta,
                    "signal": {
                        "score": score,
                        "classification": signal_state.classification if signal_state else "unscored",
                        "direction": "STABLE",
                        "formula": signal_state.formula if signal_state else None,
                        "factors": signal_state.factors if signal_state else None,
                        "notes": signal_state.notes if signal_state else [],
                        "detected_at": signal_state.scored_at if signal_state else None,
                    },
                }
                if score > best_score:
                    best_score = score
                    best_market = best_market_candidate

            return {
                "event_id": event_id,
                "event_title": first.event_title,
                "event_slug": first.event_slug,
                "event_icon_url": first.market_image_128_url or first.market_image_url,
                "source": first.source.value,
                "currency": Currency.DOLLAR.value,
                "event_type": first.event_type.value,
                "category": first.category,
                "status": first.status,
                "engine": first.engine.value,
                "total_liquidity": effective_liquidity,
                "event_total_orders": first.event_total_orders,
                "closing_date": first.closing_date.isoformat() if first.closing_date else None,
                "tracked_markets_count": len(tracked_markets),
                "tracking_enabled": is_system_tracked,
                "data_mode": "tracked_live",
                "last_updated": live_last_updated,
                "ai_insight": "Insight unavailable",
                "highest_scoring_market": best_market,
            }

        first_market = markets_list[0] if markets_list else None
        highest = None
        if first_market:
            outcomes = first_market.get("outcomes") or '["Yes","No"]'
            prices = first_market.get("outcomePrices") or "[null,null]"
            try:
                parsed_prices = json.loads(prices) if isinstance(prices, str) else prices
            except Exception:
                parsed_prices = [None, None]
            highest = {
                "market_id": str(first_market.get("id") or ""),
                "market_title": first_market.get("question") or first_market.get("slug") or event_payload.get("title", ""),
                "current_probability": float(parsed_prices[0]) if parsed_prices and parsed_prices[0] is not None else None,
                "probability_delta": 0.0,
                "signal": {
                    "score": 0.0,
                    "classification": "unscored",
                    "direction": "STABLE",
                    "formula": None,
                    "factors": None,
                    "notes": [],
                    "detected_at": None,
                },
            }

        return {
            "event_id": event_id,
            "event_title": event_payload.get("title", ""),
            "event_slug": event_payload.get("slug"),
            "event_icon_url": (first_market or {}).get("icon") or (first_market or {}).get("image") or event_payload.get("icon") or event_payload.get("image"),
            "source": MarketSource.POLYMARKET.value,
            "currency": Currency.DOLLAR.value,
            "event_type": event_type,
            "category": event_payload.get("category"),
            "status": "closed" if event_payload.get("closed") else ("open" if event_payload.get("active") else "inactive"),
            "engine": MarketEngine.CLOB.value,
            "total_liquidity": float(total_liquidity) if total_liquidity is not None else None,
            "event_total_orders": event_total_orders,
            "closing_date": event_payload.get("endDate") or event_payload.get("closedTime"),
            "tracked_markets_count": len(markets_list),
            "tracking_enabled": is_system_tracked,
            "data_mode": "lite_snapshot",
            "last_updated": event_payload.get("updatedAt"),
            "ai_insight": "Insight unavailable",
            "highest_scoring_market": highest,
        }
