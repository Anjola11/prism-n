import asyncio
from collections import defaultdict
from datetime import datetime, timezone
from uuid import UUID
from uuid import uuid4

import httpx
import json
from sqlalchemy import false, func, or_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from fastapi import HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.markets.baselines import BaselineServices
from src.markets.ai_insights import AIInsightServices
from src.markets.live_state import (
    BayseSubscriptionPlan,
    LiveStateServices,
    PolymarketAssetBindingState,
    PolymarketSubscriptionPlan,
)
from src.markets.models import (
    Currency,
    EventType,
    MarketEngine,
    MarketSource,
    TrackedEventMetric,
    TrackedMarket,
    UserTrackedEvent,
)
from src.markets.scoring import ScoringServices
from src.markets.schemas import (
    DiscoveryEventRead,
    EventDetailRead,
    EventMarketRead,
    HighestScoringMarketRead,
    NormalizeEventResult,
    SignalRead,
    TrackEventResponse,
    TrackedEventRead,
    TrackedMarketCreate,
)
from src.utils.bayse import BayseServices, HistoryWindow, Outcome
from src.utils.logger import logger
from src.utils.polymarket_clob import PolymarketCLOBServices
from src.utils.polymarket_data import PolymarketDataServices
from src.utils.polymarket import PolymarketServices


class MarketServices:
    DISCOVERY_LISTINGS_CACHE_TTL = 60
    TRACKER_CACHE_TTL = 45
    EVENT_DETAIL_CACHE_TTL = 15
    AI_INSIGHT_CACHE_TTL = 1800
    AI_INSIGHT_LOCK_TTL = 45
    AI_INSIGHT_PLACEHOLDER = "AI insight is warming up."
    DISCOVERY_FEED_CACHE_TTL = 300
    DISCOVERY_FEED_BUILD_LOCK_TTL = 30
    LIVE_STATE_MARKET_READ_CONCURRENCY = 6
    TRACKER_EVENT_BUILD_CONCURRENCY = 3

    def __init__(
        self,
        bayse: BayseServices,
        polymarket: PolymarketServices | None = None,
        polymarket_clob: PolymarketCLOBServices | None = None,
        polymarket_data: PolymarketDataServices | None = None,
        live_state: LiveStateServices | None = None,
        baseline_services: BaselineServices | None = None,
        scoring_services: ScoringServices | None = None,
        ai_insight_services: AIInsightServices | None = None,
    ):
        self.bayse = bayse
        self.polymarket = polymarket
        self.polymarket_clob = polymarket_clob
        self.polymarket_data = polymarket_data
        self.live_state = live_state
        self.baseline_services = baseline_services
        self.scoring_services = scoring_services
        self.ai_insight_services = ai_insight_services
        self._market_read_semaphore = asyncio.Semaphore(self.LIVE_STATE_MARKET_READ_CONCURRENCY)
        self._tracker_event_build_semaphore = asyncio.Semaphore(self.TRACKER_EVENT_BUILD_CONCURRENCY)

    async def _run_limited(self, semaphore: asyncio.Semaphore, awaitable):
        async with semaphore:
            return await awaitable

    def _discovery_listings_cache_id(self, *, currency: Currency) -> str:
        return f"discovery-listings:{currency.value}"

    def _tracker_cache_id(self, *, user_id: UUID, currency: Currency) -> str:
        return f"tracker:{user_id}:{currency.value}"

    def _event_detail_cache_id(self, *, event_id: str, currency: Currency) -> str:
        return f"event-detail:{event_id}:{currency.value}"

    def _event_ai_insight_cache_id(self, *, event_id: str, currency: Currency) -> str:
        return f"event-ai-insight:v2:{event_id}:{currency.value}"

    def _is_missing_ai_insight(self, ai_insight: str | None) -> bool:
        if not ai_insight or not ai_insight.strip():
            return True
        normalized = ai_insight.strip().lower()
        return normalized in {
            "insight unavailable",
            "ai insight unavailable",
            self.AI_INSIGHT_PLACEHOLDER.lower(),
        }

    def _build_card_ai_insight(
        self,
        *,
        event_title: str,
        data_mode: str,
        highest_scoring_market: HighestScoringMarketRead | None,
    ) -> str:
        if not highest_scoring_market:
            if data_mode == "tracked_live":
                return (
                    f"Prism is monitoring '{event_title}' live, but the strongest outcome has not separated clearly yet. "
                    "Use the score and recent move together to see when the market starts showing real conviction."
                )
            return (
                f"'{event_title}' is still shown as an early snapshot. Open the event to see more detail, "
                "or track it so Prism can build a stronger live read."
            )

        leader = highest_scoring_market
        probability_text = (
            f"{round((leader.current_probability or 0.0) * 100)}%"
            if leader.current_probability is not None
            else "an early level"
        )
        delta_points = round(leader.probability_delta * 100, 2)
        if delta_points > 0:
            move_text = f"up {delta_points:.2f} points"
        elif delta_points < 0:
            move_text = f"down {abs(delta_points):.2f} points"
        else:
            move_text = "holding roughly steady"

        score = leader.signal.score
        if score >= 70:
            conviction_text = "a strong read with meaningful conviction"
        elif score >= 40:
            conviction_text = "some structure, but not a fully settled move yet"
        else:
            conviction_text = "a weak read that still needs confirmation"

        note = None
        if leader.signal.notes:
            for raw_note in leader.signal.notes:
                if isinstance(raw_note, str) and raw_note.strip():
                    note = raw_note.strip().rstrip(".")
                    break

        if data_mode == "tracked_live":
            return (
                f"Right now, Prism sees the clearest pressure in '{leader.market_title}', with the market leaning around {probability_text}. "
                f"The move is {move_text} and the current score suggests {conviction_text}"
                + (f" because {note.lower()}." if note else ".")
            )[:400]

        return (
            f"At first glance, '{leader.market_title}' is the outcome Prism would watch first, with the market sitting near {probability_text}. "
            f"This is still a lighter snapshot, so treat it as an early clue rather than a finished live call"
            + (f" - especially since {note.lower()}." if note else ".")
        )[:400]

    def _with_card_ai_insight(self, read_model):
        if not self._is_missing_ai_insight(getattr(read_model, "ai_insight", None)):
            return read_model
        return read_model.model_copy(
            update={
                "ai_insight": self._build_card_ai_insight(
                    event_title=getattr(read_model, "event_title", ""),
                    data_mode=getattr(read_model, "data_mode", "lite_snapshot"),
                    highest_scoring_market=getattr(read_model, "highest_scoring_market", None),
                )
            }
        )

    async def _refresh_subscription_plan_for_source(
        self,
        *,
        session: AsyncSession,
        source: MarketSource,
    ) -> None:
        if not self.live_state:
            return

        if source == MarketSource.POLYMARKET:
            tracked_event_ids = set(
                await session.exec(
                    select(UserTrackedEvent.event_id).where(UserTrackedEvent.tracking_enabled == True)
                )
            )
            tracked_event_filter = (
                TrackedMarket.event_id.in_(tracked_event_ids)
                if tracked_event_ids
                else false()
            )
            tracked_markets = (
                await session.exec(
                    select(TrackedMarket).where(
                        TrackedMarket.source == MarketSource.POLYMARKET,
                        TrackedMarket.tracking_enabled == True,
                        or_(
                            TrackedMarket.is_system_tracked == True,
                            tracked_event_filter,
                        ),
                    )
                )
            ).all()

            plan = PolymarketSubscriptionPlan(
                bindings=[
                    PolymarketAssetBindingState(
                        asset_id=market.yes_outcome_id,
                        event_id=market.event_id,
                        market_id=market.market_id,
                        currency=Currency.DOLLAR.value,
                        outcome_side="YES",
                    )
                    for market in tracked_markets
                ] + [
                    PolymarketAssetBindingState(
                        asset_id=market.no_outcome_id,
                        event_id=market.event_id,
                        market_id=market.market_id,
                        currency=Currency.DOLLAR.value,
                        outcome_side="NO",
                    )
                    for market in tracked_markets
                ]
            )
            await self.live_state.set_subscription_plan(
                identifier=MarketSource.POLYMARKET.value,
                payload=plan,
            )
            return

        tracked_event_ids = set(
            await session.exec(
                select(UserTrackedEvent.event_id).where(UserTrackedEvent.tracking_enabled == True)
            )
        )
        tracked_event_filter = (
            TrackedMarket.event_id.in_(tracked_event_ids)
            if tracked_event_ids
            else false()
        )
        tracked_markets = (
            await session.exec(
                select(TrackedMarket).where(
                    TrackedMarket.source == MarketSource.BAYSE,
                    TrackedMarket.tracking_enabled == True,
                    or_(
                        TrackedMarket.is_system_tracked == True,
                        tracked_event_filter,
                    ),
                )
            )
        ).all()

        event_ids = sorted({market.event_id for market in tracked_markets})
        currencies_by_event: dict[str, set[str]] = defaultdict(set)
        orderbook_market_ids_by_currency: dict[str, set[str]] = defaultdict(set)

        if event_ids:
            event_metrics = (
                await session.exec(
                    select(TrackedEventMetric).where(
                        TrackedEventMetric.source == MarketSource.BAYSE,
                        TrackedEventMetric.event_id.in_(event_ids),
                    )
                )
            ).all()
            for metric in event_metrics:
                currencies_by_event[metric.event_id].add(metric.currency.value)

        for event_id in event_ids:
            if not currencies_by_event[event_id]:
                currencies_by_event[event_id].add(Currency.DOLLAR.value)

        for market in tracked_markets:
            if market.engine != MarketEngine.CLOB:
                continue
            for currency_value in currencies_by_event.get(market.event_id, {Currency.DOLLAR.value}):
                orderbook_market_ids_by_currency[currency_value].add(market.market_id)

        plan = BayseSubscriptionPlan(
            event_ids=event_ids,
            currencies_by_event={
                event_id: sorted(currency_values)
                for event_id, currency_values in currencies_by_event.items()
            },
            orderbook_market_ids_by_currency={
                currency_value: sorted(market_ids)
                for currency_value, market_ids in orderbook_market_ids_by_currency.items()
            },
        )
        await self.live_state.set_subscription_plan(
            identifier=MarketSource.BAYSE.value,
            payload=plan,
        )

    async def _wait_for_discovery_cache_fill(self, *, currency: Currency) -> list[dict] | None:
        if not self.live_state:
            return None

        for _ in range(12):
            await asyncio.sleep(0.25)
            cached = await self.live_state.get_read_model(
                namespace="discovery-feed",
                identifier=currency.value,
            )
            if cached is not None and isinstance(cached, list):
                return cached
        return None

    def _parse_datetime(self, value: str | None) -> datetime | None:
        if not value:
            return None
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    def _normalize_category(self, category: str | None) -> str | None:
        if not category:
            return None
        return " ".join(category.strip().split()).upper()

    def _normalize_event_type(self, raw_event_type: str) -> EventType:
        mapping = {
            "COMBINED_MARKETS": EventType.COMBINED,
            "GROUPED_MARKETS": EventType.COMBINED,
            "SINGLE_MARKET": EventType.SINGLE,
        }
        try:
            return mapping[raw_event_type]
        except KeyError as exc:
            raise ValueError(f"Unsupported Bayse event type: {raw_event_type}") from exc

    def _normalize_engine(self, raw_engine: str) -> MarketEngine:
        try:
            return MarketEngine(raw_engine.upper())
        except ValueError as exc:
            raise ValueError(f"Unsupported Bayse market engine: {raw_engine}") from exc

    def _normalize_polymarket_status(self, event_payload: dict) -> str:
        if event_payload.get("closed"):
            return "closed"
        if event_payload.get("active"):
            return "open"
        return "inactive"

    def _parse_polymarket_outcomes(self, market_payload: dict) -> tuple[str, str, float | None, float | None, str | None, str | None]:
        outcomes_raw = market_payload.get("outcomes") or '["Yes","No"]'
        prices_raw = market_payload.get("outcomePrices") or "[null,null]"
        token_ids_raw = market_payload.get("clobTokenIds") or "[null,null]"

        try:
            outcomes = json.loads(outcomes_raw) if isinstance(outcomes_raw, str) else outcomes_raw
        except Exception:
            outcomes = ["Yes", "No"]
        try:
            prices = json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw
        except Exception:
            prices = [None, None]
        try:
            token_ids = json.loads(token_ids_raw) if isinstance(token_ids_raw, str) else token_ids_raw
        except Exception:
            token_ids = [None, None]

        yes_label = outcomes[0] if len(outcomes) > 0 else "Yes"
        no_label = outcomes[1] if len(outcomes) > 1 else "No"
        yes_price = float(prices[0]) if len(prices) > 0 and prices[0] is not None else None
        no_price = float(prices[1]) if len(prices) > 1 and prices[1] is not None else None
        yes_token = str(token_ids[0]) if len(token_ids) > 0 and token_ids[0] is not None else None
        no_token = str(token_ids[1]) if len(token_ids) > 1 and token_ids[1] is not None else None
        return yes_label, no_label, yes_price, no_price, yes_token, no_token

    def _build_signal_read(self, *, signal_state=None, market_state=None) -> SignalRead:
        direction_map = {
            "UP": "RISING",
            "DOWN": "FALLING",
            "FLAT": "STABLE",
            None: "STABLE",
        }
        if signal_state:
            return SignalRead(
                score=signal_state.score,
                classification=signal_state.classification,
                direction=direction_map.get(getattr(market_state, "last_direction", None), "STABLE"),
                formula=signal_state.formula,
                factors=signal_state.factors,
                notes=signal_state.notes,
                detected_at=signal_state.scored_at,
            )
        return SignalRead(
            direction=direction_map.get(getattr(market_state, "last_direction", None), "STABLE"),
            detected_at=getattr(market_state, "last_updated_at", None),
        )

    async def _build_market_read(
        self,
        *,
        market: TrackedMarketCreate | TrackedMarket,
        currency: Currency,
        event_liquidity: float | None = None,
    ) -> EventMarketRead:
        async with self._market_read_semaphore:
            live_market = None
            live_signal = None
            if self.live_state:
                try:
                    live_market = await self.live_state.get_market_state(
                        source=market.source,
                        market_id=market.market_id,
                        currency=currency,
                    )
                    live_signal = await self.live_state.get_signal_state(
                        source=market.source,
                        market_id=market.market_id,
                        currency=currency,
                    )
                except Exception:
                    logger.warning(
                        "Falling back to persisted market snapshot for %s in %s",
                        market.market_id,
                        currency.value,
                        exc_info=True,
                    )
                    live_market = None
                    live_signal = None

        current_probability = getattr(live_market, "current_probability", None)
        if current_probability is None:
            current_probability = market.current_probability

        inverse_probability = getattr(live_market, "inverse_probability", None)
        if inverse_probability is None:
            inverse_probability = market.inverse_probability

        market_total_orders = getattr(live_market, "market_total_orders", None)
        if market_total_orders is None:
            market_total_orders = market.market_total_orders

        previous_probability = getattr(live_market, "previous_probability", None)
        probability_delta = 0.0
        if current_probability is not None and previous_probability is not None:
            probability_delta = current_probability - previous_probability

        return EventMarketRead(
            market_id=market.market_id,
            market_title=market.market_title,
            market_image_url=market.market_image_url,
            market_image_128_url=market.market_image_128_url,
            rules=market.rules,
            yes_outcome_id=market.yes_outcome_id,
            yes_outcome_label=market.yes_outcome_label,
            no_outcome_id=market.no_outcome_id,
            no_outcome_label=market.no_outcome_label,
            current_probability=current_probability,
            inverse_probability=inverse_probability,
            market_total_orders=market_total_orders,
            buy_notional=getattr(live_market, "buy_notional", None),
            sell_notional=getattr(live_market, "sell_notional", None),
            probability_delta=probability_delta,
            event_liquidity=getattr(live_market, "event_liquidity", event_liquidity),
            signal=self._build_signal_read(signal_state=live_signal, market_state=live_market),
            last_updated=getattr(live_market, "last_updated_at", None),
        )

    async def _build_market_reads(
        self,
        *,
        markets: list[TrackedMarketCreate | TrackedMarket],
        currency: Currency,
        event_liquidity: float | None = None,
    ) -> list[EventMarketRead]:
        return await asyncio.gather(
            *[
                self._build_market_read(
                    market=market,
                    currency=currency,
                    event_liquidity=event_liquidity,
                )
                for market in markets
            ]
        )

    def _build_highest_scoring_market(
        self,
        markets: list[EventMarketRead],
    ) -> HighestScoringMarketRead | None:
        if not markets:
            return None

        highest = max(
            markets,
            key=lambda item: (
                item.signal.score,
                item.current_probability if item.current_probability is not None else -1.0,
            ),
        )
        return HighestScoringMarketRead(
            market_id=highest.market_id,
            market_title=highest.market_title,
            current_probability=highest.current_probability,
            probability_delta=highest.probability_delta,
            signal=highest.signal,
        )

    def _get_event_icon_url(
        self,
        *,
        markets: list[TrackedMarketCreate | TrackedMarket],
    ) -> str | None:
        for market in markets:
            if getattr(market, "market_image_128_url", None):
                return market.market_image_128_url
            if getattr(market, "market_image_url", None):
                return market.market_image_url
        return None

    def _get_payload_event_icon_url(
        self,
        *,
        markets: list[dict] | None = None,
        event_payload: dict | None = None,
    ) -> str | None:
        for market in markets or []:
            if market.get("image128Url"):
                return market["image128Url"]
            if market.get("imageUrl"):
                return market["imageUrl"]
            if market.get("icon"):
                return market["icon"]
            if market.get("image"):
                return market["image"]

        if event_payload:
            if event_payload.get("icon"):
                return event_payload["icon"]
            if event_payload.get("image"):
                return event_payload["image"]

        return None

    async def _get_live_event_metadata(
        self,
        *,
        source: MarketSource,
        event_id: str,
        currency: Currency,
    ) -> tuple[float | None, str | None]:
        if not self.live_state:
            return None, None

        try:
            live_event = await self.live_state.get_event_state(
                source=source,
                event_id=event_id,
                currency=currency,
            )
        except Exception:
            logger.warning(
                "Live event metadata unavailable for %s (%s); falling back to persisted values",
                event_id,
                currency.value,
                exc_info=True,
            )
            return None, None
        if not live_event:
            return None, None
        return live_event.total_liquidity, live_event.last_synced_at

    async def _get_live_event_metadata_bulk(
        self,
        *,
        keys: list[tuple[MarketSource, str, Currency]],
    ) -> dict[tuple[MarketSource, str, Currency], tuple[float | None, str | None]]:
        if not keys:
            return {}
        results = await asyncio.gather(
            *[
                self._get_live_event_metadata(
                    source=source,
                    event_id=event_id,
                    currency=currency,
                )
                for source, event_id, currency in keys
            ]
        )
        return {
            key: result
            for key, result in zip(keys, results, strict=False)
        }

    async def _get_event_metrics_bulk(
        self,
        *,
        session: AsyncSession,
        keys: list[tuple[str, MarketSource, Currency]],
    ) -> dict[tuple[str, MarketSource, Currency], TrackedEventMetric]:
        if not keys:
            return {}
        event_ids = sorted({event_id for event_id, _, _ in keys})
        sources = sorted({source for _, source, _ in keys}, key=lambda item: item.value)
        currencies = sorted({currency for _, _, currency in keys}, key=lambda item: item.value)
        rows = (
            await session.exec(
                select(TrackedEventMetric).where(
                    TrackedEventMetric.event_id.in_(event_ids),
                    TrackedEventMetric.source.in_(sources),
                    TrackedEventMetric.currency.in_(currencies),
                )
            )
        ).all()
        return {
            (row.event_id, row.source, row.currency): row
            for row in rows
        }

    async def _seed_initial_signal_states(
        self,
        *,
        session: AsyncSession,
        persisted_markets: list[TrackedMarket],
        currency: Currency,
    ) -> None:
        if not self.live_state or not self.scoring_services or not persisted_markets:
            return

        for tracked_market in persisted_markets:
            market_state = await self.live_state.get_market_state(
                source=tracked_market.source,
                market_id=tracked_market.market_id,
                currency=currency,
            )
            if not market_state:
                continue

            baseline_sigma = None
            if self.baseline_services:
                baseline = await self.baseline_services.get_market_baseline(
                    session=session,
                    market_id=tracked_market.market_id,
                    window=HistoryWindow.WEEK_1,
                    outcome=Outcome.YES,
                    source=tracked_market.source,
                )
                if baseline:
                    baseline_sigma = baseline.volatility_sigma

            scoring_input = self.live_state.build_scoring_input(
                market_state=market_state,
                baseline_sigma=baseline_sigma,
            )
            score_result = self.scoring_services.compute_signal_score(scoring_input)
            signal_state = self.live_state.build_signal_state(
                market_state=market_state,
                score_result=score_result,
            )
            await self.live_state.set_signal_state(signal_state)

        logger.info(
            "Seeded initial signal states for %s tracked markets in %s",
            len(persisted_markets),
            currency.value,
        )

    async def _warm_polymarket_tracked_markets_from_clob(
        self,
        *,
        session: AsyncSession,
        persisted_markets: list[TrackedMarket],
        event_id: str,
        total_liquidity: float | None,
    ) -> None:
        if not self.live_state or not self.polymarket_clob or not persisted_markets:
            return

        token_ids: list[str] = []
        for market in persisted_markets:
            if market.yes_outcome_id:
                token_ids.append(market.yes_outcome_id)
            if market.no_outcome_id:
                token_ids.append(market.no_outcome_id)

        books = await self.polymarket_clob.get_books(token_ids)
        book_map = {str(book.get("asset_id")): book for book in books if book.get("asset_id")}

        live_volume = None
        if self.polymarket_data:
            try:
                live_volume = await self.polymarket_data.get_live_volume(event_id)
            except Exception:
                logger.warning("Failed to fetch Polymarket live volume for event %s", event_id, exc_info=True)

        for market in persisted_markets:
            yes_book = book_map.get(market.yes_outcome_id)
            no_book = book_map.get(market.no_outcome_id)
            yes_bids = (yes_book or {}).get("bids") or []
            yes_asks = (yes_book or {}).get("asks") or []
            current_probability = self.polymarket_clob.midpoint_from_book(yes_book)
            inverse_probability = self.polymarket_clob.midpoint_from_book(no_book)
            if current_probability is None and inverse_probability is not None:
                current_probability = 1 - inverse_probability
            if inverse_probability is None and current_probability is not None:
                inverse_probability = 1 - current_probability

            await self.live_state.update_market_state(
                source=MarketSource.POLYMARKET,
                market_id=market.market_id,
                currency=Currency.DOLLAR,
                current_probability=current_probability,
                inverse_probability=inverse_probability,
                event_liquidity=total_liquidity,
                market_total_orders=market.market_total_orders,
                event_total_orders=int(live_volume) if live_volume is not None else market.event_total_orders,
                top_bid_depth=self.polymarket_clob.level_total(yes_bids[0]) if yes_bids else 0.0,
                top_ask_depth=self.polymarket_clob.level_total(yes_asks[0]) if yes_asks else 0.0,
                top_5_bid_depth=sum(self.polymarket_clob.level_total(level) for level in yes_bids[:5]),
                top_5_ask_depth=sum(self.polymarket_clob.level_total(level) for level in yes_asks[:5]),
                spread_bps=self.polymarket_clob.spread_bps_from_book(yes_book),
                orderbook_supported=True,
                ticker_supported=True,
            )

        await self.live_state.update_event_state(
            source=MarketSource.POLYMARKET,
            event_id=event_id,
            currency=Currency.DOLLAR,
            total_liquidity=total_liquidity,
            event_total_orders=int(live_volume) if live_volume is not None else None,
        )

    def _build_lightweight_highest_scoring_market(
        self,
        markets: list[TrackedMarketCreate],
    ) -> HighestScoringMarketRead | None:
        if not markets:
            return None

        candidate = max(
            markets,
            key=lambda item: (
                item.current_probability if item.current_probability is not None else -1.0,
                item.market_total_orders if item.market_total_orders is not None else -1,
            ),
        )

        return HighestScoringMarketRead(
            market_id=candidate.market_id,
            market_title=candidate.market_title,
            current_probability=candidate.current_probability,
            probability_delta=0.0,
            signal=SignalRead(),
        )

    async def _get_cached_discovery_listings(self, *, currency: Currency) -> list[dict] | None:
        if not self.live_state:
            return None
        payload = await self.live_state.get_read_model(
            namespace="discovery-listings",
            identifier=self._discovery_listings_cache_id(currency=currency),
        )
        if not payload or not isinstance(payload, list):
            return None
        return payload

    async def _set_cached_discovery_listings(self, *, currency: Currency, events: list[dict]) -> None:
        if not self.live_state:
            return
        await self.live_state.set_read_model(
            namespace="discovery-listings",
            identifier=self._discovery_listings_cache_id(currency=currency),
            payload=events,
            ttl_seconds=self.DISCOVERY_LISTINGS_CACHE_TTL,
        )

    async def _build_discovery_feed_fallback(
        self,
        *,
        session: AsyncSession,
        user_id: UUID | None = None,
        source: MarketSource | None,
        currency: Currency,
    ) -> list[DiscoveryEventRead]:
        tracked_ids = await self._get_user_tracked_event_ids(session, user_id) if user_id is not None else set()

        bayse_events: list[dict] = []
        polymarket_events: list[dict] = []

        fetch_tasks = []
        if source in (None, MarketSource.BAYSE):
            fetch_tasks.append(self.bayse.get_all_listings(currency=currency))
        else:
            fetch_tasks.append(None)
        if source in (None, MarketSource.POLYMARKET) and self.polymarket:
            fetch_tasks.append(
                self.polymarket.get_events(
                    limit=24,
                    active=True,
                    closed=False,
                    archived=False,
                )
            )
        else:
            fetch_tasks.append(None)

        coroutines = [task for task in fetch_tasks if task is not None]
        results = await asyncio.gather(*coroutines, return_exceptions=True) if coroutines else []

        result_index = 0
        if fetch_tasks[0] is not None:
            result = results[result_index]
            result_index += 1
            if isinstance(result, Exception):
                logger.warning("Discovery fallback: Bayse listings fetch failed", exc_info=True)
            else:
                bayse_events = result.get("events", [])

        if len(fetch_tasks) > 1 and fetch_tasks[1] is not None:
            result = results[result_index]
            if isinstance(result, Exception):
                logger.warning("Discovery fallback: Polymarket listings fetch failed", exc_info=True)
            else:
                polymarket_events = result

        fallback_cards: list[DiscoveryEventRead] = []

        for event_payload in bayse_events:
            event_id = event_payload.get("id")
            if not event_id:
                continue
            markets = event_payload.get("markets", [])
            first_market = markets[0] if markets else {}
            fallback_cards.append(
                DiscoveryEventRead(
                    event_id=event_id,
                    event_title=event_payload.get("title", ""),
                    event_slug=event_payload.get("slug"),
                    event_icon_url=self._get_payload_event_icon_url(markets=markets),
                    source=MarketSource.BAYSE,
                    currency=currency,
                    event_type=self._normalize_event_type(event_payload.get("type", "SINGLE_MARKET")),
                    category=self._normalize_category(event_payload.get("category")),
                    status=event_payload.get("status"),
                    engine=self._normalize_engine(event_payload.get("engine", "AMM")),
                    total_liquidity=event_payload.get("liquidity"),
                    event_total_orders=event_payload.get("totalOrders"),
                    closing_date=self._parse_datetime(event_payload.get("closingDate")),
                    tracked_markets_count=len(markets),
                    tracking_enabled=event_id in tracked_ids,
                    data_mode="lite_snapshot",
                    last_updated=None,
                    ai_insight="Insight unavailable",
                    highest_scoring_market=HighestScoringMarketRead(
                        market_id=str(first_market.get("id") or ""),
                        market_title=first_market.get("title", ""),
                        current_probability=first_market.get("outcome1Price"),
                        probability_delta=0.0,
                        signal=SignalRead(),
                    ) if first_market else None,
                )
            )

        for event_payload in polymarket_events:
            event_id = str(event_payload.get("id") or "")
            if not event_id:
                continue
            markets = event_payload.get("markets", [])
            first_market = markets[0] if markets else {}
            total_liquidity = event_payload.get("liquidity")
            if total_liquidity is None:
                total_liquidity = event_payload.get("liquidityClob")
            fallback_cards.append(
                DiscoveryEventRead(
                    event_id=event_id,
                    event_title=event_payload.get("title", ""),
                    event_slug=event_payload.get("slug"),
                    event_icon_url=self._get_payload_event_icon_url(
                        markets=markets,
                        event_payload=event_payload,
                    ),
                    source=MarketSource.POLYMARKET,
                    currency=Currency.DOLLAR,
                    event_type=EventType.COMBINED if len(markets) > 1 else EventType.SINGLE,
                    category=event_payload.get("category"),
                    status=self._normalize_polymarket_status(event_payload),
                    engine=MarketEngine.CLOB,
                    total_liquidity=float(total_liquidity) if total_liquidity is not None else None,
                    event_total_orders=int(float(event_payload.get("volume") or 0)),
                    closing_date=self._parse_datetime(event_payload.get("endDate") or event_payload.get("closedTime")),
                    tracked_markets_count=len(markets),
                    tracking_enabled=event_id in tracked_ids,
                    data_mode="lite_snapshot",
                    last_updated=(
                        self._parse_datetime(event_payload.get("updatedAt")).isoformat()
                        if self._parse_datetime(event_payload.get("updatedAt"))
                        else None
                    ),
                    ai_insight="Insight unavailable",
                    highest_scoring_market=HighestScoringMarketRead(
                        market_id=str(first_market.get("id") or ""),
                        market_title=first_market.get("question") or first_market.get("slug") or event_payload.get("title", ""),
                        current_probability=None,
                        probability_delta=0.0,
                        signal=SignalRead(),
                    ) if first_market else None,
                )
            )

        if source is None:
            bayse_cards = [card for card in fallback_cards if card.source == MarketSource.BAYSE]
            poly_cards = [card for card in fallback_cards if card.source == MarketSource.POLYMARKET]
            fallback_cards = bayse_cards[:3] + poly_cards + bayse_cards[3:]

        logger.info(
            "Built fallback discovery feed with %s events for user %s in %s",
            len(fallback_cards),
            user_id,
            currency.value,
        )
        return fallback_cards

    async def _get_cached_tracker_response(self, *, user_id: UUID, currency: Currency) -> list[TrackedEventRead] | None:
        if not self.live_state:
            return None
        payload = await self.live_state.get_read_model(
            namespace="tracker-feed",
            identifier=self._tracker_cache_id(user_id=user_id, currency=currency),
        )
        if not payload or not isinstance(payload, list):
            return None
        return [TrackedEventRead.model_validate(item) for item in payload]

    async def _set_cached_tracker_response(
        self,
        *,
        user_id: UUID,
        currency: Currency,
        response: list[TrackedEventRead],
    ) -> None:
        if not self.live_state:
            return
        await self.live_state.set_read_model(
            namespace="tracker-feed",
            identifier=self._tracker_cache_id(user_id=user_id, currency=currency),
            payload=[item.model_dump(mode="json") for item in response],
            ttl_seconds=self.TRACKER_CACHE_TTL,
        )

    async def _get_cached_event_detail(self, *, event_id: str, currency: Currency) -> EventDetailRead | None:
        if not self.live_state:
            return None
        payload = await self.live_state.get_read_model(
            namespace="event-detail",
            identifier=self._event_detail_cache_id(event_id=event_id, currency=currency),
        )
        if not payload or not isinstance(payload, dict):
            return None
        return EventDetailRead.model_validate(payload)

    async def _set_cached_event_detail(self, *, event_detail: EventDetailRead) -> None:
        if not self.live_state:
            return
        await self.live_state.set_read_model(
            namespace="event-detail",
            identifier=self._event_detail_cache_id(event_id=event_detail.event_id, currency=event_detail.currency),
            payload=event_detail.model_dump(mode="json"),
            ttl_seconds=self.EVENT_DETAIL_CACHE_TTL,
        )

    async def _get_cached_event_ai_insight(self, *, event_id: str, currency: Currency) -> str | None:
        if not self.live_state:
            return None
        payload = await self.live_state.get_read_model(
            namespace="event-ai-insight",
            identifier=self._event_ai_insight_cache_id(event_id=event_id, currency=currency),
        )
        if not payload or not isinstance(payload, dict):
            return None
        insight = payload.get("ai_insight")
        if not isinstance(insight, str) or not insight.strip():
            return None
        return insight

    async def _set_cached_event_ai_insight(self, *, event_id: str, currency: Currency, ai_insight: str) -> None:
        if not self.live_state:
            return
        await self.live_state.set_read_model(
            namespace="event-ai-insight",
            identifier=self._event_ai_insight_cache_id(event_id=event_id, currency=currency),
            payload={"ai_insight": ai_insight},
            ttl_seconds=self.AI_INSIGHT_CACHE_TTL,
        )

    async def _invalidate_user_read_models(
        self,
        *,
        user_id: UUID,
        event_id: str,
        currency: Currency,
    ) -> None:
        if not self.live_state:
            return
        await self.live_state.delete_read_model(
            namespace="tracker-feed",
            identifier=self._tracker_cache_id(user_id=user_id, currency=currency),
        )
        await self.live_state.delete_read_model(
            namespace="event-detail",
            identifier=self._event_detail_cache_id(event_id=event_id, currency=currency),
        )
        await self.live_state.delete_read_model(
            namespace="event-ai-insight",
            identifier=self._event_ai_insight_cache_id(event_id=event_id, currency=currency),
        )

    async def _invalidate_shared_read_models(
        self,
        *,
        event_id: str,
        currency: Currency,
    ) -> None:
        if not self.live_state:
            return
        await self.live_state.delete_read_model(
            namespace="discovery-listings",
            identifier=self._discovery_listings_cache_id(currency=currency),
        )
        await self.live_state.delete_read_model(
            namespace="event-detail",
            identifier=self._event_detail_cache_id(event_id=event_id, currency=currency),
        )
        await self.live_state.delete_read_model(
            namespace="event-ai-insight",
            identifier=self._event_ai_insight_cache_id(event_id=event_id, currency=currency),
        )

    def _clone_event_detail_with_tracking(
        self,
        *,
        cached_detail: EventDetailRead,
        tracking_enabled: bool,
    ) -> EventDetailRead:
        payload = cached_detail.model_dump()
        payload["tracking_enabled"] = tracking_enabled
        return EventDetailRead.model_validate(payload)

    async def _generate_and_cache_ai_insight(self, event_detail: EventDetailRead) -> None:
        if not self.ai_insight_services or not self.ai_insight_services.is_enabled:
            return
        ai_insight = await self.ai_insight_services.generate_event_insight(event_detail)
        if not ai_insight:
            logger.info("AI insight generation returned no content for event %s", event_detail.event_id)
            return
        await self._set_cached_event_ai_insight(
            event_id=event_detail.event_id,
            currency=event_detail.currency,
            ai_insight=ai_insight,
        )
        logger.info("Cached AI insight for event %s", event_detail.event_id)

    def _build_fallback_ai_insight(self, event_detail: EventDetailRead) -> str:
        leader = event_detail.highest_scoring_market
        summary = self._build_card_ai_insight(
            event_title=event_detail.event_title,
            data_mode=event_detail.data_mode,
            highest_scoring_market=leader,
        )
        if not leader:
            return summary
        return (
            f"{summary} In plain terms: this is the outcome currently attracting the most meaningful attention, "
            "but you should read it as direction and conviction building, not as a guarantee."
        )[:400]

    async def _attach_ai_insight(self, event_detail: EventDetailRead) -> EventDetailRead:
        if not self.ai_insight_services or not self.ai_insight_services.is_enabled:
            return event_detail.model_copy(update={"ai_insight": self._build_fallback_ai_insight(event_detail)})

        cached_ai_insight = await self._get_cached_event_ai_insight(
            event_id=event_detail.event_id,
            currency=event_detail.currency,
        )
        if cached_ai_insight:
            return event_detail.model_copy(update={"ai_insight": cached_ai_insight})

        if self.live_state:
            lock_acquired = await self.live_state.acquire_coordination_lock(
                namespace="event-ai-insight-generate",
                identifier=self._event_ai_insight_cache_id(
                    event_id=event_detail.event_id,
                    currency=event_detail.currency,
                ),
                ttl_seconds=self.AI_INSIGHT_LOCK_TTL,
            )
            if lock_acquired:
                asyncio.create_task(self._generate_and_cache_ai_insight(event_detail))

        return event_detail.model_copy(update={"ai_insight": self._build_fallback_ai_insight(event_detail)})

    def normalize_event_to_tracked_markets(
        self,
        event_payload: dict,
        *,
        currency: Currency,
        source: MarketSource = MarketSource.BAYSE,
    ) -> NormalizeEventResult:
        if source == MarketSource.POLYMARKET:
            return self.normalize_polymarket_event_to_tracked_markets(event_payload)

        event_type = self._normalize_event_type(event_payload["type"])
        engine = self._normalize_engine(event_payload["engine"])

        markets: list[TrackedMarketCreate] = []
        for market in event_payload.get("markets", []):
            markets.append(
                TrackedMarketCreate(
                    event_id=event_payload["id"],
                    market_id=market["id"],
                    event_slug=event_payload.get("slug"),
                    event_title=event_payload["title"],
                    source=source,
                    event_type=event_type,
                    category=self._normalize_category(event_payload.get("category")),
                    status=event_payload.get("status"),
                    engine=engine,
                    market_title=market["title"],
                    market_image_url=market.get("imageUrl"),
                    market_image_128_url=market.get("image128Url"),
                    rules=market.get("rules"),
                    yes_outcome_id=market["outcome1Id"],
                    yes_outcome_label=market.get("outcome1Label", "Yes"),
                    no_outcome_id=market["outcome2Id"],
                    no_outcome_label=market.get("outcome2Label", "No"),
                    current_probability=market.get("outcome1Price"),
                    inverse_probability=market.get("outcome2Price"),
                    market_total_orders=market.get("totalOrders"),
                    event_total_orders=event_payload.get("totalOrders"),
                    closing_date=self._parse_datetime(event_payload.get("closingDate")),
                    tracking_enabled=True,
                )
            )

        return NormalizeEventResult(
            event_id=event_payload["id"],
            event_title=event_payload["title"],
            event_slug=event_payload.get("slug"),
            source=source,
            currency=currency,
            total_liquidity=event_payload.get("liquidity"),
            event_type=event_type,
            engine=engine,
            markets=markets,
        )

    def normalize_polymarket_event_to_tracked_markets(
        self,
        event_payload: dict,
    ) -> NormalizeEventResult:
        markets_payload = event_payload.get("markets", [])
        event_type = EventType.COMBINED if len(markets_payload) > 1 else EventType.SINGLE
        markets: list[TrackedMarketCreate] = []

        event_total_orders = None
        event_volume = event_payload.get("volume")
        if event_volume is not None:
            event_total_orders = int(float(event_volume))

        for market in markets_payload:
            yes_label, no_label, yes_price, no_price, yes_token, no_token = self._parse_polymarket_outcomes(market)
            market_total_orders = None
            market_volume = market.get("volumeNum") or market.get("volume")
            if market_volume is not None:
                market_total_orders = int(float(market_volume))

            markets.append(
                TrackedMarketCreate(
                    event_id=str(event_payload["id"]),
                    market_id=str(market["id"]),
                    event_slug=event_payload.get("slug"),
                    event_title=event_payload["title"],
                    source=MarketSource.POLYMARKET,
                    event_type=event_type,
                    category=self._normalize_category(event_payload.get("category")),
                    status=self._normalize_polymarket_status(event_payload),
                    engine=MarketEngine.CLOB,
                    market_title=market.get("question") or market.get("slug") or event_payload["title"],
                    market_image_url=market.get("image") or event_payload.get("image"),
                    market_image_128_url=market.get("icon") or event_payload.get("icon"),
                    rules=market.get("description") or event_payload.get("description"),
                    yes_outcome_id=yes_token or f"{market['id']}:yes",
                    yes_outcome_label=yes_label,
                    no_outcome_id=no_token or f"{market['id']}:no",
                    no_outcome_label=no_label,
                    current_probability=yes_price,
                    inverse_probability=no_price,
                    market_total_orders=market_total_orders,
                    event_total_orders=event_total_orders,
                    closing_date=self._parse_datetime(
                        market.get("endDate") or event_payload.get("endDate") or event_payload.get("closedTime")
                    ),
                    tracking_enabled=True,
                )
            )

        total_liquidity = event_payload.get("liquidity")
        if total_liquidity is None:
            total_liquidity = event_payload.get("liquidityClob")

        return NormalizeEventResult(
            event_id=str(event_payload["id"]),
            event_title=event_payload["title"],
            event_slug=event_payload.get("slug"),
            source=MarketSource.POLYMARKET,
            currency=Currency.DOLLAR,
            total_liquidity=float(total_liquidity) if total_liquidity is not None else None,
            event_type=event_type,
            engine=MarketEngine.CLOB,
            markets=markets,
        )

    async def _group_tracked_markets(
        self,
        markets: list[TrackedMarket],
        *,
        currency: Currency,
        total_liquidity: float | None = None,
        last_updated: str | None = None,
        tracking_enabled: bool = False,
    ) -> EventDetailRead:
        if not markets:
            raise ValueError("Cannot group an empty tracked market list")

        first_market = markets[0]
        grouped_markets = await self._build_market_reads(
            markets=markets,
            currency=currency,
            event_liquidity=total_liquidity,
        )
        highest_scoring_market = self._build_highest_scoring_market(grouped_markets)

        return EventDetailRead(
            event_id=first_market.event_id,
            event_title=first_market.event_title,
            event_slug=first_market.event_slug,
            event_icon_url=self._get_event_icon_url(markets=markets),
            source=first_market.source,
            currency=currency,
            event_type=first_market.event_type,
            category=first_market.category,
            status=first_market.status,
            engine=first_market.engine,
            total_liquidity=total_liquidity,
            event_total_orders=first_market.event_total_orders,
            closing_date=first_market.closing_date,
            tracked_markets_count=len(markets),
            tracking_enabled=tracking_enabled,
            data_mode="tracked_live",
            last_updated=last_updated,
            ai_insight="Insight unavailable",
            highest_scoring_market=highest_scoring_market,
            markets=grouped_markets,
        )

    async def _build_tracked_event_summary(
        self,
        *,
        event_id: str,
        markets: list[TrackedMarket],
        tracked_event: UserTrackedEvent | None,
        effective_currency: Currency,
        metric: TrackedEventMetric | None,
        live_total_liquidity: float | None,
        live_last_updated: str | None,
    ) -> TrackedEventRead:
        first_market = markets[0]
        grouped_market_reads = await self._build_market_reads(
            markets=markets,
            currency=effective_currency,
            event_liquidity=live_total_liquidity if live_total_liquidity is not None else (metric.total_liquidity if metric else None),
        )
        highest_scoring_market = self._build_highest_scoring_market(grouped_market_reads)
        return self._with_card_ai_insight(TrackedEventRead(
            event_id=first_market.event_id,
            event_title=first_market.event_title,
            event_slug=first_market.event_slug,
            event_icon_url=self._get_event_icon_url(markets=markets),
            source=first_market.source,
            currency=metric.currency if metric else effective_currency,
            event_type=first_market.event_type,
            category=first_market.category,
            status=first_market.status,
            engine=first_market.engine,
            total_liquidity=live_total_liquidity if live_total_liquidity is not None else (metric.total_liquidity if metric else None),
            event_total_orders=first_market.event_total_orders,
            closing_date=first_market.closing_date,
            tracked_markets_count=len(markets),
            tracking_enabled=tracked_event.tracking_enabled if tracked_event else True,
            data_mode="tracked_live",
            last_updated=live_last_updated,
            ai_insight="Insight unavailable",
            highest_scoring_market=highest_scoring_market,
        ))

    async def _build_discovery_read_for_tracked_event(
        self,
        *,
        session: AsyncSession,
        markets: list[TrackedMarket],
        currency: Currency,
        tracking_enabled: bool,
    ) -> DiscoveryEventRead:
        first_market = markets[0]
        metric = await self._get_event_metric(
            session=session,
            event_id=first_market.event_id,
            source=first_market.source,
            currency=currency,
        )
        live_total_liquidity, live_last_updated = await self._get_live_event_metadata(
            source=first_market.source,
            event_id=first_market.event_id,
            currency=currency,
        )
        grouped_markets = [
            await self._build_market_read(
                market=market,
                currency=currency,
                event_liquidity=live_total_liquidity if live_total_liquidity is not None else (metric.total_liquidity if metric else None),
            )
            for market in markets
        ]
        highest_scoring_market = self._build_highest_scoring_market(grouped_markets)
        return self._with_card_ai_insight(DiscoveryEventRead(
            event_id=first_market.event_id,
            event_title=first_market.event_title,
            event_slug=first_market.event_slug,
            event_icon_url=self._get_event_icon_url(markets=markets),
            source=first_market.source,
            currency=metric.currency if metric else currency,
            event_type=first_market.event_type,
            category=first_market.category,
            status=first_market.status,
            engine=first_market.engine,
            total_liquidity=live_total_liquidity if live_total_liquidity is not None else (metric.total_liquidity if metric else None),
            event_total_orders=first_market.event_total_orders,
            closing_date=first_market.closing_date,
            tracked_markets_count=len(markets),
            tracking_enabled=tracking_enabled,
            data_mode="tracked_live",
            last_updated=live_last_updated,
            ai_insight="Insight unavailable",
            highest_scoring_market=highest_scoring_market,
        ))

    async def _get_user_tracking_status(
        self,
        *,
        session: AsyncSession,
        user_id: UUID,
        event_id: str,
    ) -> bool:
        statement = select(UserTrackedEvent).where(
            UserTrackedEvent.user_id == user_id,
            UserTrackedEvent.event_id == event_id,
            UserTrackedEvent.tracking_enabled == True,
        )
        result = await session.exec(statement)
        return result.first() is not None

    async def _get_user_tracked_event_ids(
        self,
        session: AsyncSession,
        user_id: UUID,
    ) -> set[str]:
        statement = select(UserTrackedEvent.event_id).where(
            UserTrackedEvent.user_id == user_id,
            UserTrackedEvent.tracking_enabled == True,
        )
        result = await session.exec(statement)
        return set(result.all())

    async def _upsert_event_metric(
        self,
        session: AsyncSession,
        *,
        event_id: str,
        source: MarketSource,
        currency: Currency,
        total_liquidity: float | None,
    ) -> TrackedEventMetric:
        now = datetime.now(timezone.utc)
        insert_stmt = pg_insert(TrackedEventMetric).values(
            event_id=event_id,
            source=source,
            currency=currency,
            total_liquidity=total_liquidity,
            created_at=now,
            updated_at=now,
        )
        upsert_stmt = insert_stmt.on_conflict_do_update(
            constraint="uq_tracked_event_metrics_event_source_currency",
            set_={
                "total_liquidity": insert_stmt.excluded.total_liquidity,
                "updated_at": now,
            },
        )
        await session.exec(upsert_stmt)
        result = await session.exec(
            select(TrackedEventMetric).where(
                TrackedEventMetric.event_id == event_id,
                TrackedEventMetric.source == source,
                TrackedEventMetric.currency == currency,
            )
        )
        metric = result.first()
        logger.info(
            "Upserted tracked event metric for event %s source %s currency %s",
            event_id,
            source.value,
            currency.value,
        )
        return metric

    async def _get_event_metric(
        self,
        session: AsyncSession,
        *,
        event_id: str,
        source: MarketSource,
        currency: Currency,
    ) -> TrackedEventMetric | None:
        statement = select(TrackedEventMetric).where(
            TrackedEventMetric.event_id == event_id,
            TrackedEventMetric.source == source,
            TrackedEventMetric.currency == currency,
        )
        result = await session.exec(statement)
        return result.first()

    async def _upsert_tracked_market(
        self,
        session: AsyncSession,
        tracked_market: TrackedMarketCreate,
    ) -> TrackedMarket:
        data = tracked_market.model_dump()
        now = datetime.now(timezone.utc)
        insert_stmt = pg_insert(TrackedMarket).values(
            **data,
            created_at=now,
            updated_at=now,
        )
        update_data = {
            key: insert_stmt.excluded[key]
            for key in data.keys()
            if key != "market_id"
        }
        update_data["updated_at"] = now
        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=[TrackedMarket.market_id],
            set_=update_data,
        )
        await session.exec(upsert_stmt)
        result = await session.exec(
            select(TrackedMarket).where(TrackedMarket.market_id == tracked_market.market_id)
        )
        db_market = result.first()
        logger.info(
            "Single-market upserted tracked market %s for event %s",
            db_market.market_id,
            db_market.event_id,
        )
        return db_market

    async def _upsert_tracked_markets(
        self,
        session: AsyncSession,
        tracked_markets: list[TrackedMarketCreate],
        *,
        overrides: dict | None = None,
    ) -> list[TrackedMarket]:
        if not tracked_markets:
            return []

        overrides = overrides or {}
        now = datetime.now(timezone.utc)
        rows = []
        market_ids: list[str] = []
        for tracked_market in tracked_markets:
            row = tracked_market.model_dump()
            row.update(overrides)
            row["id"] = uuid4()
            row["created_at"] = now
            row["updated_at"] = now
            rows.append(row)
            market_ids.append(tracked_market.market_id)

        insert_stmt = pg_insert(TrackedMarket).values(rows)
        excluded_fields = [
            field
            for field in rows[0].keys()
            if field not in {"id", "market_id", "created_at"}
        ]
        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=[TrackedMarket.market_id],
            set_={
                **{field: insert_stmt.excluded[field] for field in excluded_fields},
                "updated_at": now,
            },
        )
        await session.exec(upsert_stmt)

        persisted = (
            await session.exec(
                select(TrackedMarket).where(TrackedMarket.market_id.in_(market_ids))
            )
        ).all()
        persisted_by_market_id = {market.market_id: market for market in persisted}
        ordered = [persisted_by_market_id[market_id] for market_id in market_ids if market_id in persisted_by_market_id]
        event_id = ordered[0].event_id if ordered else "unknown"
        logger.info(
            "Bulk upserted %s tracked markets for event %s",
            len(ordered),
            event_id,
        )
        return ordered

    async def track_event_for_user(
        self,
        *,
        session: AsyncSession,
        user_id: UUID,
        event_id: str,
        source: MarketSource = MarketSource.BAYSE,
        currency: Currency = Currency.DOLLAR,
    ) -> TrackEventResponse:
        logger.info("Tracking request started for user %s and event %s in %s", user_id, event_id, currency.value)
        if source == MarketSource.POLYMARKET:
            if not self.polymarket:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Polymarket service unavailable",
                )
            event_payload = await self.polymarket.get_event_by_id(event_id=event_id)
            normalized = self.normalize_event_to_tracked_markets(
                event_payload,
                currency=Currency.DOLLAR,
                source=MarketSource.POLYMARKET,
            )
            currency = Currency.DOLLAR
        else:
            event_payload = await self.bayse.get_event_by_id(event_id=event_id, currency=currency)
            normalized = self.normalize_event_to_tracked_markets(event_payload, currency=currency)

        persisted_markets = await self._upsert_tracked_markets(
            session,
            normalized.markets,
        )

        await self._upsert_event_metric(
            session,
            event_id=normalized.event_id,
            source=normalized.source,
            currency=normalized.currency,
            total_liquidity=normalized.total_liquidity,
        )

        statement = select(UserTrackedEvent).where(
            UserTrackedEvent.user_id == user_id,
            UserTrackedEvent.event_id == normalized.event_id,
        )
        result = await session.exec(statement)
        user_tracking = result.first()

        if user_tracking:
            user_tracking.tracking_enabled = True
            user_tracking.updated_at = datetime.now(timezone.utc)
            session.add(user_tracking)
            logger.info("Re-enabled tracking for user %s and event %s", user_id, normalized.event_id)
        else:
            user_tracking = UserTrackedEvent(
                user_id=user_id,
                event_id=normalized.event_id,
                tracking_enabled=True,
            )
            session.add(user_tracking)
            logger.info("Created user-tracked event row for user %s and event %s", user_id, normalized.event_id)

        await session.commit()
        await self._refresh_subscription_plan_for_source(
            session=session,
            source=normalized.source,
        )

        if self.baseline_services:
            try:
                await self.baseline_services.refresh_event_baselines(
                    session=session,
                    event_id=normalized.event_id,
                    source=normalized.source,
                )
            except Exception:
                logger.warning("Baseline refresh failed for event %s", normalized.event_id, exc_info=True)

        if self.live_state and persisted_markets:
            first_market = persisted_markets[0]
            await self.live_state.warm_event_state_from_tracking(
                tracked_market=first_market,
                currency=currency,
                total_liquidity=normalized.total_liquidity,
                tracked_markets_count=len(persisted_markets),
            )
            for tracked_market in persisted_markets:
                await self.live_state.warm_market_state_from_tracking(
                    tracked_market=tracked_market,
                    currency=currency,
                    total_liquidity=normalized.total_liquidity,
                )
            if normalized.source == MarketSource.POLYMARKET:
                try:
                    await self._warm_polymarket_tracked_markets_from_clob(
                        session=session,
                        persisted_markets=persisted_markets,
                        event_id=normalized.event_id,
                        total_liquidity=normalized.total_liquidity,
                    )
                except Exception:
                    logger.warning("Polymarket CLOB warm failed for event %s", normalized.event_id, exc_info=True)
            await self._seed_initial_signal_states(
                session=session,
                persisted_markets=persisted_markets,
                currency=currency,
            )

        logger.info("Tracking request completed for user %s and event %s", user_id, normalized.event_id)
        await self._invalidate_user_read_models(user_id=user_id, event_id=normalized.event_id, currency=currency)
        await self._invalidate_shared_read_models(event_id=normalized.event_id, currency=currency)

        return TrackEventResponse(
            event_id=normalized.event_id,
            event_title=normalized.event_title,
            event_slug=normalized.event_slug,
            source=normalized.source,
            currency=normalized.currency,
            event_type=normalized.event_type,
            engine=normalized.engine,
            tracked_markets_count=len(normalized.markets),
            tracking_enabled=True,
        )

    async def track_event_for_system(
        self,
        *,
        session: AsyncSession,
        event_id: str,
        source: MarketSource = MarketSource.BAYSE,
        currency: Currency = Currency.DOLLAR,
    ) -> TrackEventResponse:
        logger.info("System tracking request started for event %s in %s", event_id, currency.value)
        if source == MarketSource.POLYMARKET:
            if not self.polymarket:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Polymarket service unavailable",
                )
            event_payload = await self.polymarket.get_event_by_id(event_id=event_id)
            normalized = self.normalize_event_to_tracked_markets(
                event_payload,
                currency=Currency.DOLLAR,
                source=MarketSource.POLYMARKET,
            )
            currency = Currency.DOLLAR
        else:
            event_payload = await self.bayse.get_event_by_id(event_id=event_id, currency=currency)
            normalized = self.normalize_event_to_tracked_markets(event_payload, currency=currency)

        persisted_markets = await self._upsert_tracked_markets(
            session,
            normalized.markets,
            overrides={
                "tracking_enabled": True,
                "is_system_tracked": True,
            },
        )

        await self._upsert_event_metric(
            session,
            event_id=normalized.event_id,
            source=normalized.source,
            currency=normalized.currency,
            total_liquidity=normalized.total_liquidity,
        )
        await session.commit()
        await self._refresh_subscription_plan_for_source(
            session=session,
            source=normalized.source,
        )

        if self.baseline_services:
            try:
                await self.baseline_services.refresh_event_baselines(
                    session=session,
                    event_id=normalized.event_id,
                    source=normalized.source,
                )
            except Exception:
                logger.warning(
                    "Baseline refresh failed for system-tracked event %s",
                    normalized.event_id,
                    exc_info=True,
                )

        if self.live_state and persisted_markets:
            first_market = persisted_markets[0]
            await self.live_state.warm_event_state_from_tracking(
                tracked_market=first_market,
                currency=currency,
                total_liquidity=normalized.total_liquidity,
                tracked_markets_count=len(persisted_markets),
            )
            for tracked_market in persisted_markets:
                await self.live_state.warm_market_state_from_tracking(
                    tracked_market=tracked_market,
                    currency=currency,
                    total_liquidity=normalized.total_liquidity,
                )
            if normalized.source == MarketSource.POLYMARKET:
                try:
                    await self._warm_polymarket_tracked_markets_from_clob(
                        session=session,
                        persisted_markets=persisted_markets,
                        event_id=normalized.event_id,
                        total_liquidity=normalized.total_liquidity,
                    )
                except Exception:
                    logger.warning(
                        "Polymarket CLOB warm failed for system-tracked event %s",
                        normalized.event_id,
                        exc_info=True,
                    )
            await self._seed_initial_signal_states(
                session=session,
                persisted_markets=persisted_markets,
                currency=currency,
            )

        logger.info("System tracking request completed for event %s", normalized.event_id)
        await self._invalidate_shared_read_models(event_id=normalized.event_id, currency=currency)
        return TrackEventResponse(
            event_id=normalized.event_id,
            event_title=normalized.event_title,
            event_slug=normalized.event_slug,
            source=normalized.source,
            currency=normalized.currency,
            event_type=normalized.event_type,
            engine=normalized.engine,
            tracked_markets_count=len(normalized.markets),
            tracking_enabled=True,
        )

    async def untrack_event_for_user(
        self,
        *,
        session: AsyncSession,
        user_id: UUID,
        event_id: str,
        source: MarketSource = MarketSource.BAYSE,
        currency: Currency = Currency.DOLLAR,
    ) -> TrackEventResponse:
        logger.info("Untrack request started for user %s and event %s", user_id, event_id)
        effective_currency = Currency.DOLLAR if source == MarketSource.POLYMARKET else currency
        statement = select(UserTrackedEvent).where(
            UserTrackedEvent.user_id == user_id,
            UserTrackedEvent.event_id == event_id,
        )
        result = await session.exec(statement)
        user_tracking = result.first()

        if not user_tracking:
            logger.warning("Tracked event not found for user %s and event %s", user_id, event_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tracked event not found for user",
            )

        user_tracking.tracking_enabled = False
        user_tracking.updated_at = datetime.now(timezone.utc)
        session.add(user_tracking)
        await session.commit()
        await self._refresh_subscription_plan_for_source(
            session=session,
            source=source,
        )

        markets_statement = select(TrackedMarket).where(
            TrackedMarket.event_id == event_id,
            TrackedMarket.source == source,
        )
        markets_result = await session.exec(markets_statement)
        markets = markets_result.all()

        if not markets:
            logger.warning("Tracked markets not found for event %s", event_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tracked markets not found for event",
            )

        first_market = markets[0]
        metric = await self._get_event_metric(
            session,
            event_id=first_market.event_id,
            source=first_market.source,
            currency=effective_currency,
        )
        logger.info("Untrack request completed for user %s and event %s", user_id, event_id)
        await self._invalidate_user_read_models(user_id=user_id, event_id=event_id, currency=effective_currency)
        await self._invalidate_shared_read_models(event_id=event_id, currency=effective_currency)
        return TrackEventResponse(
            event_id=first_market.event_id,
            event_title=first_market.event_title,
            event_slug=first_market.event_slug,
            source=first_market.source,
            currency=metric.currency if metric else effective_currency,
            event_type=first_market.event_type,
            engine=first_market.engine,
            tracked_markets_count=len(markets),
            tracking_enabled=False,
        )

    async def list_tracked_events_for_user(
        self,
        *,
        session: AsyncSession,
        user_id: UUID,
        currency: Currency = Currency.DOLLAR,
    ) -> list[TrackedEventRead]:
        logger.info("Listing tracked events for user %s in %s", user_id, currency.value)
        cached_response = await self._get_cached_tracker_response(user_id=user_id, currency=currency)
        if cached_response is not None:
            logger.info("Serving tracker feed from Redis cache for user %s in %s", user_id, currency.value)
            return [self._with_card_ai_insight(item) for item in cached_response]

        statement = select(UserTrackedEvent).where(
            UserTrackedEvent.user_id == user_id,
            UserTrackedEvent.tracking_enabled == True,
        )
        result = await session.exec(statement)
        tracked_events = result.all()
        tracked_event_map = {tracked_event.event_id: tracked_event for tracked_event in tracked_events}
        event_ids = list(tracked_event_map)
        if not event_ids:
            return []

        all_markets = (
            await session.exec(
                select(TrackedMarket).where(
                    TrackedMarket.event_id.in_(event_ids),
                    TrackedMarket.tracking_enabled == True,
                )
            )
        ).all()

        grouped_markets_by_event: dict[str, list[TrackedMarket]] = {}
        for market in all_markets:
            grouped_markets_by_event.setdefault(market.event_id, []).append(market)

        event_metric_keys: list[tuple[str, MarketSource, Currency]] = []
        live_metadata_keys: list[tuple[MarketSource, str, Currency]] = []
        effective_currency_by_event: dict[str, Currency] = {}
        for event_id, markets in grouped_markets_by_event.items():
            first_market = markets[0]
            effective_currency = Currency.DOLLAR if first_market.source == MarketSource.POLYMARKET else currency
            effective_currency_by_event[event_id] = effective_currency
            event_metric_keys.append((event_id, first_market.source, effective_currency))
            live_metadata_keys.append((first_market.source, event_id, effective_currency))

        metrics_map, live_metadata_map = await asyncio.gather(
            self._get_event_metrics_bulk(session=session, keys=event_metric_keys),
            self._get_live_event_metadata_bulk(keys=live_metadata_keys),
        )

        build_tasks = []
        for event_id in event_ids:
            markets = grouped_markets_by_event.get(event_id, [])
            if not markets:
                logger.warning("No tracked markets found for event %s", event_id)
                continue

            first_market = markets[0]
            effective_currency = effective_currency_by_event[event_id]
            metric = metrics_map.get((event_id, first_market.source, effective_currency))
            live_total_liquidity, live_last_updated = live_metadata_map.get(
                (first_market.source, event_id, effective_currency),
                (None, None),
            )
            build_tasks.append(
                self._run_limited(
                    self._tracker_event_build_semaphore,
                    self._build_tracked_event_summary(
                        event_id=event_id,
                        markets=markets,
                        tracked_event=tracked_event_map.get(event_id),
                        effective_currency=effective_currency,
                        metric=metric,
                        live_total_liquidity=live_total_liquidity,
                        live_last_updated=live_last_updated,
                    ),
                )
            )

        response = await asyncio.gather(*build_tasks) if build_tasks else []
        response = [self._with_card_ai_insight(item) for item in response]

        logger.info("Listed %s tracked events for user %s", len(response), user_id)
        await self._set_cached_tracker_response(user_id=user_id, currency=currency, response=response)
        return response

    async def list_tracked_events_page_for_user(
        self,
        *,
        session: AsyncSession,
        user_id: UUID,
        currency: Currency = Currency.DOLLAR,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[TrackedEventRead], int]:
        logger.info("Listing paginated tracked events for user %s in %s (page=%s, limit=%s)", user_id, currency.value, page, limit)

        cached_response = await self._get_cached_tracker_response(user_id=user_id, currency=currency)
        if cached_response is not None:
            start = (page - 1) * limit
            end = start + limit
            return cached_response[start:end], len(cached_response)
        full_response = await self.list_tracked_events_for_user(
            session=session,
            user_id=user_id,
            currency=currency,
        )
        start = (page - 1) * limit
        end = start + limit
        page_items = full_response[start:end]
        logger.info("Listed %s paginated tracked events for user %s (total=%s)", len(page_items), user_id, len(full_response))
        return page_items, len(full_response)

    async def list_system_tracked_events(
        self,
        *,
        session: AsyncSession,
        currency: Currency = Currency.DOLLAR,
    ) -> list[TrackedEventRead]:
        # Check cache first
        cache_id = f"system-{currency.value}"
        if self.live_state:
            cached = await self.live_state.get_read_model(
                namespace="tracker-feed",
                identifier=cache_id,
            )
            if cached and isinstance(cached, list):
                logger.info("Serving system tracker from cache for %s", currency.value)
                return [self._with_card_ai_insight(TrackedEventRead.model_validate(item)) for item in cached]

        statement = select(TrackedMarket).where(
            TrackedMarket.is_system_tracked == True,
            TrackedMarket.tracking_enabled == True,
        )
        result = await session.exec(statement)
        markets = result.all()

        grouped: dict[str, list[TrackedMarket]] = {}
        for market in markets:
            grouped.setdefault(market.event_id, []).append(market)

        event_metric_keys: list[tuple[str, MarketSource, Currency]] = []
        live_metadata_keys: list[tuple[MarketSource, str, Currency]] = []
        effective_currency_by_event: dict[str, Currency] = {}
        for event_id, event_markets in grouped.items():
            first_market = event_markets[0]
            effective_currency = Currency.DOLLAR if first_market.source == MarketSource.POLYMARKET else currency
            effective_currency_by_event[event_id] = effective_currency
            event_metric_keys.append((event_id, first_market.source, effective_currency))
            live_metadata_keys.append((first_market.source, event_id, effective_currency))

        metrics_map, live_metadata_map = await asyncio.gather(
            self._get_event_metrics_bulk(session=session, keys=event_metric_keys),
            self._get_live_event_metadata_bulk(keys=live_metadata_keys),
        )

        build_tasks = []
        for event_id, event_markets in grouped.items():
            first_market = event_markets[0]
            effective_currency = effective_currency_by_event[event_id]
            metric = metrics_map.get((event_id, first_market.source, effective_currency))
            live_total_liquidity, live_last_updated = live_metadata_map.get(
                (first_market.source, event_id, effective_currency),
                (None, None),
            )
            build_tasks.append(
                self._build_tracked_event_summary(
                    event_id=event_id,
                    markets=event_markets,
                    tracked_event=None,
                    effective_currency=effective_currency,
                    metric=metric,
                    live_total_liquidity=live_total_liquidity,
                    live_last_updated=live_last_updated,
                )
            )

        response = await asyncio.gather(*build_tasks) if build_tasks else []
        response = [self._with_card_ai_insight(item) for item in response]

        response.sort(key=lambda item: item.event_title)

        # Cache the response
        if self.live_state:
            await self.live_state.set_read_model(
                namespace="tracker-feed",
                identifier=cache_id,
                payload=[item.model_dump(mode="json") for item in response],
                ttl_seconds=self.TRACKER_CACHE_TTL,
            )

        return response

    async def untrack_event_for_system(
        self,
        *,
        session: AsyncSession,
        event_id: str,
        source: MarketSource = MarketSource.BAYSE,
        currency: Currency = Currency.DOLLAR,
    ) -> TrackEventResponse:
        effective_currency = Currency.DOLLAR if source == MarketSource.POLYMARKET else currency
        statement = select(TrackedMarket).where(
            TrackedMarket.event_id == event_id,
            TrackedMarket.source == source,
        )
        result = await session.exec(statement)
        markets = result.all()
        if not markets:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tracked markets not found for event",
            )

        for market in markets:
            market.is_system_tracked = False
            market.updated_at = datetime.now(timezone.utc)
            session.add(market)

        await session.commit()
        await self._refresh_subscription_plan_for_source(
            session=session,
            source=source,
        )
        first_market = markets[0]
        metric = await self._get_event_metric(
            session,
            event_id=first_market.event_id,
            source=first_market.source,
            currency=effective_currency,
        )
        await self._invalidate_shared_read_models(event_id=event_id, currency=effective_currency)
        return TrackEventResponse(
            event_id=first_market.event_id,
            event_title=first_market.event_title,
            event_slug=first_market.event_slug,
            source=first_market.source,
            currency=metric.currency if metric else effective_currency,
            event_type=first_market.event_type,
            engine=first_market.engine,
            tracked_markets_count=len(markets),
            tracking_enabled=False,
        )

    async def get_event_detail_for_user(
        self,
        *,
        session: AsyncSession,
        user_id: UUID,
        event_id: str,
        source: MarketSource = MarketSource.BAYSE,
        currency: Currency = Currency.DOLLAR,
    ) -> EventDetailRead:
        if source == MarketSource.POLYMARKET:
            currency = Currency.DOLLAR
        logger.info("Fetching event detail for user %s and event %s in %s", user_id, event_id, currency.value)
        cached_detail = await self._get_cached_event_detail(event_id=event_id, currency=currency)
        tracked_markets_for_event = (
            await session.exec(
                select(TrackedMarket).where(
                    TrackedMarket.event_id == event_id,
                    TrackedMarket.tracking_enabled == True,
                )
            )
        ).all()
        authoritative_source = tracked_markets_for_event[0].source if tracked_markets_for_event else source
        if authoritative_source == MarketSource.POLYMARKET:
            currency = Currency.DOLLAR

        if cached_detail is None or cached_detail.source != authoritative_source:
            authoritative_cached_detail = await self._get_cached_event_detail(event_id=event_id, currency=currency)
            if authoritative_cached_detail is not None and authoritative_cached_detail.source == authoritative_source:
                tracking_enabled = await self._get_user_tracking_status(
                    session=session,
                    user_id=user_id,
                    event_id=event_id,
                )
                logger.info("Serving authoritative event detail for %s in %s from Redis cache", event_id, currency.value)
                response = self._clone_event_detail_with_tracking(
                    cached_detail=authoritative_cached_detail,
                    tracking_enabled=tracking_enabled,
                )
                return await self._attach_ai_insight(response)

        if cached_detail is not None and cached_detail.source == authoritative_source:
            tracking_enabled = await self._get_user_tracking_status(
                session=session,
                user_id=user_id,
                event_id=event_id,
            )
            logger.info("Serving event detail for %s in %s from Redis cache", event_id, currency.value)
            response = self._clone_event_detail_with_tracking(
                cached_detail=cached_detail,
                tracking_enabled=tracking_enabled,
            )
            return await self._attach_ai_insight(response)

        markets = [
            market
            for market in tracked_markets_for_event
            if market.source == authoritative_source
        ]

        if not markets:
            logger.info("Event %s not in DB yet, fetching from source %s", event_id, authoritative_source.value)
            if authoritative_source == MarketSource.POLYMARKET:
                if not self.polymarket:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Polymarket service unavailable",
                    )
                event_payload = await self.polymarket.get_event_by_id(event_id=event_id)
                normalized = self.normalize_event_to_tracked_markets(
                    event_payload,
                    currency=Currency.DOLLAR,
                    source=MarketSource.POLYMARKET,
                )
                currency = Currency.DOLLAR
            else:
                event_payload = await self.bayse.get_event_by_id(event_id=event_id, currency=currency)
                normalized = self.normalize_event_to_tracked_markets(event_payload, currency=currency)
            grouped_markets = await self._build_market_reads(
                markets=normalized.markets,
                currency=currency,
                event_liquidity=normalized.total_liquidity,
            )
            response = EventDetailRead(
                event_id=normalized.event_id,
                event_title=normalized.event_title,
                event_slug=normalized.event_slug,
                event_icon_url=self._get_event_icon_url(markets=normalized.markets),
                source=normalized.source,
                currency=normalized.currency,
                event_type=normalized.event_type,
                category=normalized.markets[0].category if normalized.markets else None,
                status=normalized.markets[0].status if normalized.markets else None,
                engine=normalized.engine,
                total_liquidity=normalized.total_liquidity,
                event_total_orders=normalized.markets[0].event_total_orders if normalized.markets else None,
                closing_date=normalized.markets[0].closing_date if normalized.markets else None,
                tracked_markets_count=len(normalized.markets),
                tracking_enabled=False,
                data_mode="lite_snapshot",
                last_updated=None,
                ai_insight="Insight unavailable",
                highest_scoring_market=self._build_highest_scoring_market(grouped_markets),
                markets=grouped_markets,
            )
            await self._set_cached_event_detail(event_detail=response)
            return await self._attach_ai_insight(response)

        tracking_enabled = await self._get_user_tracking_status(
            session=session,
            user_id=user_id,
            event_id=event_id,
        )
        effective_currency = Currency.DOLLAR if markets[0].source == MarketSource.POLYMARKET else currency
        metric = await self._get_event_metric(
            session,
            event_id=markets[0].event_id,
            source=markets[0].source,
            currency=effective_currency,
        )
        live_total_liquidity, live_last_updated = await self._get_live_event_metadata(
            source=markets[0].source,
            event_id=markets[0].event_id,
            currency=effective_currency,
        )
        response = await self._group_tracked_markets(
            markets,
            currency=effective_currency,
            total_liquidity=live_total_liquidity if live_total_liquidity is not None else (metric.total_liquidity if metric else None),
            last_updated=live_last_updated,
            tracking_enabled=tracking_enabled,
        )
        await self._set_cached_event_detail(event_detail=response)
        return await self._attach_ai_insight(response)

    async def get_discovery_feed_for_user(
        self,
        *,
        session: AsyncSession,
        user_id: UUID,
        source: MarketSource | None = None,
        currency: Currency = Currency.DOLLAR,
        page: int = 1,
        limit: int | None = None,
    ) -> tuple[list[DiscoveryEventRead], int]:
        logger.info("Fetching discovery feed for user %s in %s", user_id, currency.value)

        # Read the pre-built feed from Redis (written by DiscoveryWorker)
        cached = await self.live_state.get_read_model(
            namespace="discovery-feed",
            identifier=currency.value,
        ) if self.live_state else None

        if cached is None or not isinstance(cached, list):
            logger.warning(
                "Discovery feed cache unavailable for %s; building fallback response",
                currency.value,
            )
            build_locally = True
            if self.live_state:
                lock_acquired = await self.live_state.acquire_coordination_lock(
                    namespace="discovery-feed-build",
                    identifier=currency.value,
                    ttl_seconds=self.DISCOVERY_FEED_BUILD_LOCK_TTL,
                )
                if not lock_acquired:
                    warmed_cache = await self._wait_for_discovery_cache_fill(currency=currency)
                    if warmed_cache is not None:
                        cached = warmed_cache
                        build_locally = False

            if build_locally:
                fallback_cards = await self._build_discovery_feed_fallback(
                    session=session,
                    user_id=user_id,
                    source=source,
                    currency=currency,
                )
                cached = [item.model_dump(mode="json") for item in fallback_cards]
                if self.live_state:
                    await self.live_state.set_read_model(
                        namespace="discovery-feed",
                        identifier=currency.value,
                        payload=cached,
                        ttl_seconds=self.DISCOVERY_FEED_CACHE_TTL,
                    )

        filtered_cached = [
            item
            for item in cached
            if not source or item.get("source") == source.value
        ]
        total_count = len(filtered_cached)

        if limit is not None:
            start = max(page - 1, 0) * limit
            end = start + limit
            paged_cached = filtered_cached[start:end]
        else:
            paged_cached = filtered_cached

        # One fast DB query for user's tracked event IDs
        tracked_ids = await self._get_user_tracked_event_ids(session, user_id)

        feed_event_ids = {
            str(item.get("event_id"))
            for item in paged_cached
            if item.get("event_id")
            and str(item.get("event_id")) in tracked_ids
            and item.get("data_mode") != "tracked_live"
        }
        upgraded_cards: dict[tuple[str, str], DiscoveryEventRead] = {}

        if feed_event_ids:
            tracked_markets = (
                await session.exec(
                    select(TrackedMarket).where(
                        TrackedMarket.event_id.in_(feed_event_ids),
                        TrackedMarket.tracking_enabled == True,
                    )
                )
            ).all()

            grouped_markets: dict[tuple[str, MarketSource], list[TrackedMarket]] = {}
            for market in tracked_markets:
                grouped_markets.setdefault((market.event_id, market.source), []).append(market)

            upgrade_tasks = []
            upgrade_keys: list[tuple[str, str]] = []
            for (event_id, market_source), event_markets in grouped_markets.items():
                effective_currency = Currency.DOLLAR if market_source == MarketSource.POLYMARKET else currency
                upgrade_keys.append((event_id, market_source.value))
                upgrade_tasks.append(
                    self._build_discovery_read_for_tracked_event(
                        session=session,
                        markets=event_markets,
                        currency=effective_currency,
                        tracking_enabled=True,
                    )
                )

            if upgrade_tasks:
                upgraded_results = await asyncio.gather(*upgrade_tasks, return_exceptions=True)
                for key, result in zip(upgrade_keys, upgraded_results, strict=False):
                    if isinstance(result, Exception):
                        logger.warning("Failed to upgrade tracked discovery card for %s", key[0], exc_info=True)
                        continue
                    upgraded_cards[key] = result

        # Overlay per-user tracking status and build response
        discovery: list[DiscoveryEventRead] = []
        for item in paged_cached:
            event_id = str(item.get("event_id") or "")
            source_value = str(item.get("source") or "")
            upgraded = upgraded_cards.get((event_id, source_value))
            if upgraded is not None:
                discovery.append(self._with_card_ai_insight(upgraded))
                continue

            item["tracking_enabled"] = event_id in tracked_ids
            try:
                discovery.append(self._with_card_ai_insight(DiscoveryEventRead.model_validate(item)))
            except Exception:
                logger.warning("Discovery worker card validation failed for %s", item.get("event_id"))
                continue

        logger.info("Discovery feed contains %s events for user %s", total_count, user_id)
        return discovery, total_count

    async def get_discovery_feed_for_system(
        self,
        *,
        session: AsyncSession,
        source: MarketSource | None = None,
        currency: Currency = Currency.DOLLAR,
        page: int = 1,
        limit: int | None = None,
    ) -> tuple[list[DiscoveryEventRead], int]:
        logger.info("Fetching system discovery feed in %s", currency.value)

        # Read the pre-built feed from Redis (written by DiscoveryWorker)
        cached = await self.live_state.get_read_model(
            namespace="discovery-feed",
            identifier=currency.value,
        ) if self.live_state else None

        if cached is None or not isinstance(cached, list):
            logger.warning(
                "Admin discovery feed cache unavailable for %s; building fallback response",
                currency.value,
            )
            build_locally = True
            if self.live_state:
                lock_acquired = await self.live_state.acquire_coordination_lock(
                    namespace="discovery-feed-build",
                    identifier=currency.value,
                    ttl_seconds=self.DISCOVERY_FEED_BUILD_LOCK_TTL,
                )
                if not lock_acquired:
                    warmed_cache = await self._wait_for_discovery_cache_fill(currency=currency)
                    if warmed_cache is not None:
                        cached = warmed_cache
                        build_locally = False

            if build_locally:
                fallback_cards = await self._build_discovery_feed_fallback(
                    session=session,
                    user_id=None,
                    source=source,
                    currency=currency,
                )
                cached = [item.model_dump(mode="json") for item in fallback_cards]
                if self.live_state:
                    await self.live_state.set_read_model(
                        namespace="discovery-feed",
                        identifier=currency.value,
                        payload=cached,
                        ttl_seconds=self.DISCOVERY_FEED_CACHE_TTL,
                    )

        # One fast DB query for system-tracked event IDs
        system_result = await session.exec(
            select(TrackedMarket.event_id).where(
                TrackedMarket.is_system_tracked == True,
                TrackedMarket.tracking_enabled == True,
            )
        )
        system_tracked_ids = set(system_result.all())

        filtered_cached = [
            item
            for item in cached
            if not source or item.get("source") == source.value
        ]
        total_count = len(filtered_cached)

        if limit is not None:
            start = max(page - 1, 0) * limit
            end = start + limit
            paged_cached = filtered_cached[start:end]
        else:
            paged_cached = filtered_cached

        # Overlay system tracking status and build response
        discovery: list[DiscoveryEventRead] = []
        for item in paged_cached:
            item["tracking_enabled"] = item.get("event_id") in system_tracked_ids
            try:
                discovery.append(self._with_card_ai_insight(DiscoveryEventRead.model_validate(item)))
            except Exception:
                logger.warning("System discovery card validation failed for %s", item.get("event_id"))
                continue

        logger.info("System discovery feed contains %s events", total_count)
        return discovery, total_count

