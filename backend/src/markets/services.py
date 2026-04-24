from datetime import datetime, timezone
from uuid import UUID

import httpx
import json
from fastapi import HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.markets.baselines import BaselineServices
from src.markets.live_state import LiveStateServices
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
    DISCOVERY_LISTINGS_CACHE_TTL = 30
    TRACKER_CACHE_TTL = 10
    EVENT_DETAIL_CACHE_TTL = 10

    def __init__(
        self,
        bayse: BayseServices,
        polymarket: PolymarketServices | None = None,
        polymarket_clob: PolymarketCLOBServices | None = None,
        polymarket_data: PolymarketDataServices | None = None,
        live_state: LiveStateServices | None = None,
        baseline_services: BaselineServices | None = None,
        scoring_services: ScoringServices | None = None,
    ):
        self.bayse = bayse
        self.polymarket = polymarket
        self.polymarket_clob = polymarket_clob
        self.polymarket_data = polymarket_data
        self.live_state = live_state
        self.baseline_services = baseline_services
        self.scoring_services = scoring_services

    def _discovery_listings_cache_id(self, *, currency: Currency) -> str:
        return f"discovery-listings:{currency.value}"

    def _tracker_cache_id(self, *, user_id: UUID, currency: Currency) -> str:
        return f"tracker:{user_id}:{currency.value}"

    def _event_detail_cache_id(self, *, event_id: str, currency: Currency) -> str:
        return f"event-detail:{event_id}:{currency.value}"

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
        live_market = None
        live_signal = None
        if self.live_state:
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
            probability_delta=probability_delta,
            event_liquidity=getattr(live_market, "event_liquidity", event_liquidity),
            signal=self._build_signal_read(signal_state=live_signal, market_state=live_market),
            last_updated=getattr(live_market, "last_updated_at", None),
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

    async def _get_live_event_metadata(
        self,
        *,
        source: MarketSource,
        event_id: str,
        currency: Currency,
    ) -> tuple[float | None, str | None]:
        if not self.live_state:
            return None, None

        live_event = await self.live_state.get_event_state(
            source=source,
            event_id=event_id,
            currency=currency,
        )
        if not live_event:
            return None, None
        return live_event.total_liquidity, live_event.last_synced_at

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
                top_bid_depth=self.polymarket_clob.level_total((yes_book or {}).get("bids", [None])[0]) if yes_book else 0.0,
                top_ask_depth=self.polymarket_clob.level_total((yes_book or {}).get("asks", [None])[0]) if yes_book else 0.0,
                top_5_bid_depth=sum(self.polymarket_clob.level_total(level) for level in (yes_book or {}).get("bids", [])[:5]),
                top_5_ask_depth=sum(self.polymarket_clob.level_total(level) for level in (yes_book or {}).get("asks", [])[:5]),
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

    def _clone_event_detail_with_tracking(
        self,
        *,
        cached_detail: EventDetailRead,
        tracking_enabled: bool,
    ) -> EventDetailRead:
        payload = cached_detail.model_dump()
        payload["tracking_enabled"] = tracking_enabled
        return EventDetailRead.model_validate(payload)

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
        grouped_markets = [
            await self._build_market_read(
                market=market,
                currency=currency,
                event_liquidity=total_liquidity,
            )
            for market in markets
        ]
        highest_scoring_market = self._build_highest_scoring_market(grouped_markets)

        return EventDetailRead(
            event_id=first_market.event_id,
            event_title=first_market.event_title,
            event_slug=first_market.event_slug,
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
        return DiscoveryEventRead(
            event_id=first_market.event_id,
            event_title=first_market.event_title,
            event_slug=first_market.event_slug,
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
            highest_scoring_market=self._build_highest_scoring_market(grouped_markets),
        )

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
        statement = select(TrackedEventMetric).where(
            TrackedEventMetric.event_id == event_id,
            TrackedEventMetric.source == source,
            TrackedEventMetric.currency == currency,
        )
        result = await session.exec(statement)
        existing = result.first()

        if existing:
            existing.total_liquidity = total_liquidity
            existing.updated_at = datetime.now(timezone.utc)
            session.add(existing)
            logger.info(
                "Updated tracked event metric for event %s source %s currency %s",
                event_id,
                source.value,
                currency.value,
            )
            return existing

        metric = TrackedEventMetric(
            event_id=event_id,
            source=source,
            currency=currency,
            total_liquidity=total_liquidity,
        )
        session.add(metric)
        logger.info(
            "Created tracked event metric for event %s source %s currency %s",
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
        statement = select(TrackedMarket).where(TrackedMarket.market_id == tracked_market.market_id)
        result = await session.exec(statement)
        existing = result.first()

        data = tracked_market.model_dump()
        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
            existing.updated_at = datetime.now(timezone.utc)
            session.add(existing)
            logger.info("Updated tracked market %s for event %s", existing.market_id, existing.event_id)
            return existing

        db_market = TrackedMarket(**data)
        session.add(db_market)
        logger.info("Created tracked market %s for event %s", db_market.market_id, db_market.event_id)
        return db_market

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

        persisted_markets: list[TrackedMarket] = []
        for market in normalized.markets:
            persisted_market = await self._upsert_tracked_market(session, market)
            persisted_markets.append(persisted_market)

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

        persisted_markets: list[TrackedMarket] = []
        for market in normalized.markets:
            persisted_market = await self._upsert_tracked_market(session, market)
            persisted_market.is_system_tracked = True
            persisted_market.tracking_enabled = True
            persisted_market.updated_at = datetime.now(timezone.utc)
            session.add(persisted_market)
            persisted_markets.append(persisted_market)

        await self._upsert_event_metric(
            session,
            event_id=normalized.event_id,
            source=normalized.source,
            currency=normalized.currency,
            total_liquidity=normalized.total_liquidity,
        )
        await session.commit()

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
            return cached_response

        statement = select(UserTrackedEvent).where(
            UserTrackedEvent.user_id == user_id,
            UserTrackedEvent.tracking_enabled == True,
        )
        result = await session.exec(statement)
        tracked_events = result.all()

        response: list[TrackedEventRead] = []
        for tracked_event in tracked_events:
            markets_statement = select(TrackedMarket).where(
                TrackedMarket.event_id == tracked_event.event_id,
                TrackedMarket.tracking_enabled == True,
            )
            markets_result = await session.exec(markets_statement)
            markets = markets_result.all()
            if not markets:
                logger.warning("No tracked markets found for event %s", tracked_event.event_id)
                continue

            first_market = markets[0]
            effective_currency = Currency.DOLLAR if first_market.source == MarketSource.POLYMARKET else currency
            metric = await self._get_event_metric(
                session,
                event_id=first_market.event_id,
                source=first_market.source,
                currency=effective_currency,
            )
            live_total_liquidity, live_last_updated = await self._get_live_event_metadata(
                source=first_market.source,
                event_id=first_market.event_id,
                currency=effective_currency,
            )
            grouped_markets = [
                await self._build_market_read(
                    market=market,
                    currency=effective_currency,
                    event_liquidity=live_total_liquidity if live_total_liquidity is not None else (metric.total_liquidity if metric else None),
                )
                for market in markets
            ]
            response.append(
                TrackedEventRead(
                    event_id=first_market.event_id,
                    event_title=first_market.event_title,
                    event_slug=first_market.event_slug,
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
                    tracking_enabled=tracked_event.tracking_enabled,
                    data_mode="tracked_live",
                    last_updated=live_last_updated,
                    ai_insight="Insight unavailable",
                    highest_scoring_market=self._build_highest_scoring_market(grouped_markets),
                )
            )

        logger.info("Listed %s tracked events for user %s", len(response), user_id)
        await self._set_cached_tracker_response(user_id=user_id, currency=currency, response=response)
        return response

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
                return [TrackedEventRead.model_validate(item) for item in cached]

        statement = select(TrackedMarket).where(
            TrackedMarket.is_system_tracked == True,
            TrackedMarket.tracking_enabled == True,
        )
        result = await session.exec(statement)
        markets = result.all()

        grouped: dict[str, list[TrackedMarket]] = {}
        for market in markets:
            grouped.setdefault(market.event_id, []).append(market)

        response: list[TrackedEventRead] = []
        for event_markets in grouped.values():
            first_market = event_markets[0]
            effective_currency = Currency.DOLLAR if first_market.source == MarketSource.POLYMARKET else currency
            metric = await self._get_event_metric(
                session,
                event_id=first_market.event_id,
                source=first_market.source,
                currency=effective_currency,
            )
            live_total_liquidity, live_last_updated = await self._get_live_event_metadata(
                source=first_market.source,
                event_id=first_market.event_id,
                currency=effective_currency,
            )
            grouped_markets = [
                await self._build_market_read(
                    market=market,
                    currency=effective_currency,
                    event_liquidity=live_total_liquidity if live_total_liquidity is not None else (metric.total_liquidity if metric else None),
                )
                for market in event_markets
            ]
            response.append(
                TrackedEventRead(
                    event_id=first_market.event_id,
                    event_title=first_market.event_title,
                    event_slug=first_market.event_slug,
                    source=first_market.source,
                    currency=metric.currency if metric else effective_currency,
                    event_type=first_market.event_type,
                    category=first_market.category,
                    status=first_market.status,
                    engine=first_market.engine,
                    total_liquidity=live_total_liquidity if live_total_liquidity is not None else (metric.total_liquidity if metric else None),
                    event_total_orders=first_market.event_total_orders,
                    closing_date=first_market.closing_date,
                    tracked_markets_count=len(event_markets),
                    tracking_enabled=True,
                    data_mode="tracked_live",
                    last_updated=live_last_updated,
                    ai_insight="Insight unavailable",
                    highest_scoring_market=self._build_highest_scoring_market(grouped_markets),
                )
            )

        response.sort(key=lambda item: item.event_title)

        # Cache the response
        if self.live_state:
            await self.live_state.set_read_model(
                namespace="tracker-feed",
                identifier=cache_id,
                payload=[item.model_dump(mode="json") for item in response],
                ttl_seconds=30,
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
        if cached_detail is not None and cached_detail.source == source:
            tracking_enabled = await self._get_user_tracking_status(
                session=session,
                user_id=user_id,
                event_id=event_id,
            )
            logger.info("Serving event detail for %s in %s from Redis cache", event_id, currency.value)
            return self._clone_event_detail_with_tracking(
                cached_detail=cached_detail,
                tracking_enabled=tracking_enabled,
            )

        statement = select(TrackedMarket).where(
            TrackedMarket.event_id == event_id,
            TrackedMarket.tracking_enabled == True,
            TrackedMarket.source == source,
        )
        result = await session.exec(statement)
        markets = result.all()

        if not markets:
            logger.info("Event %s not in DB yet, fetching from source %s", event_id, source.value)
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
            grouped_markets = [
                await self._build_market_read(
                    market=market,
                    currency=currency,
                    event_liquidity=normalized.total_liquidity,
                )
                for market in normalized.markets
            ]
            response = EventDetailRead(
                event_id=normalized.event_id,
                event_title=normalized.event_title,
                event_slug=normalized.event_slug,
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
            return response

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
        return response

    async def get_discovery_feed_for_user(
        self,
        *,
        session: AsyncSession,
        user_id: UUID,
        source: MarketSource | None = None,
        currency: Currency = Currency.DOLLAR,
    ) -> list[DiscoveryEventRead]:
        logger.info("Fetching discovery feed for user %s in %s", user_id, currency.value)

        # Read the pre-built feed from Redis (written by DiscoveryWorker)
        cached = await self.live_state.get_read_model(
            namespace="discovery-feed",
            identifier=currency.value,
        ) if self.live_state else None

        if cached is None or not isinstance(cached, list):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Discovery feed is warming up, please try again shortly",
            )

        # One fast DB query for user's tracked event IDs
        tracked_ids = await self._get_user_tracked_event_ids(session, user_id)

        # Overlay per-user tracking status and build response
        discovery: list[DiscoveryEventRead] = []
        for item in cached:
            if source and item.get("source") != source.value:
                continue
            item["tracking_enabled"] = item.get("event_id") in tracked_ids
            try:
                discovery.append(DiscoveryEventRead.model_validate(item))
            except Exception:
                logger.warning("Discovery worker card validation failed for %s", item.get("event_id"))
                continue

        logger.info("Discovery feed contains %s events for user %s", len(discovery), user_id)
        return discovery

    async def get_discovery_feed_for_system(
        self,
        *,
        session: AsyncSession,
        source: MarketSource | None = None,
        currency: Currency = Currency.DOLLAR,
    ) -> list[DiscoveryEventRead]:
        logger.info("Fetching system discovery feed in %s", currency.value)

        # Read the pre-built feed from Redis (written by DiscoveryWorker)
        cached = await self.live_state.get_read_model(
            namespace="discovery-feed",
            identifier=currency.value,
        ) if self.live_state else None

        if cached is None or not isinstance(cached, list):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Discovery feed is warming up, please try again shortly",
            )

        # One fast DB query for system-tracked event IDs
        system_result = await session.exec(
            select(TrackedMarket.event_id).where(
                TrackedMarket.is_system_tracked == True,
                TrackedMarket.tracking_enabled == True,
            )
        )
        system_tracked_ids = set(system_result.all())

        # Overlay system tracking status and build response
        discovery: list[DiscoveryEventRead] = []
        for item in cached:
            if source and item.get("source") != source.value:
                continue
            item["tracking_enabled"] = item.get("event_id") in system_tracked_ids
            try:
                discovery.append(DiscoveryEventRead.model_validate(item))
            except Exception:
                logger.warning("System discovery card validation failed for %s", item.get("event_id"))
                continue

        logger.info("System discovery feed contains %s events", len(discovery))
        return discovery
