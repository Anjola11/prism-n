from datetime import datetime, timezone
from uuid import UUID

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
from src.utils.bayse import BayseServices
from src.utils.logger import logger


class MarketServices:
    def __init__(
        self,
        bayse: BayseServices,
        live_state: LiveStateServices | None = None,
        baseline_services: BaselineServices | None = None,
    ):
        self.bayse = bayse
        self.live_state = live_state
        self.baseline_services = baseline_services

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

    def normalize_event_to_tracked_markets(
        self,
        event_payload: dict,
        *,
        currency: Currency,
        source: MarketSource = MarketSource.BAYSE,
    ) -> NormalizeEventResult:
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
            last_updated=last_updated,
            ai_insight="Insight unavailable",
            highest_scoring_market=highest_scoring_market,
            markets=grouped_markets,
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
        currency: Currency = Currency.DOLLAR,
    ) -> TrackEventResponse:
        logger.info("Tracking request started for user %s and event %s in %s", user_id, event_id, currency.value)
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

        logger.info("Tracking request completed for user %s and event %s", user_id, normalized.event_id)

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
        currency: Currency = Currency.DOLLAR,
    ) -> TrackEventResponse:
        logger.info("System tracking request started for event %s in %s", event_id, currency.value)
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

        logger.info("System tracking request completed for event %s", normalized.event_id)
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
        currency: Currency = Currency.DOLLAR,
    ) -> TrackEventResponse:
        logger.info("Untrack request started for user %s and event %s", user_id, event_id)
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

        markets_statement = select(TrackedMarket).where(TrackedMarket.event_id == event_id)
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
            currency=currency,
        )
        logger.info("Untrack request completed for user %s and event %s", user_id, event_id)
        return TrackEventResponse(
            event_id=first_market.event_id,
            event_title=first_market.event_title,
            event_slug=first_market.event_slug,
            source=first_market.source,
            currency=metric.currency if metric else currency,
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
            metric = await self._get_event_metric(
                session,
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
            response.append(
                TrackedEventRead(
                    event_id=first_market.event_id,
                    event_title=first_market.event_title,
                    event_slug=first_market.event_slug,
                    source=first_market.source,
                    currency=metric.currency if metric else currency,
                    event_type=first_market.event_type,
                    engine=first_market.engine,
                    tracked_markets_count=len(markets),
                    tracking_enabled=tracked_event.tracking_enabled,
                    last_updated=live_last_updated,
                    ai_insight="Insight unavailable",
                    highest_scoring_market=self._build_highest_scoring_market(grouped_markets),
                )
            )

        logger.info("Listed %s tracked events for user %s", len(response), user_id)
        return response

    async def list_system_tracked_events(
        self,
        *,
        session: AsyncSession,
        currency: Currency = Currency.DOLLAR,
    ) -> list[TrackedEventRead]:
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
            metric = await self._get_event_metric(
                session,
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
                for market in event_markets
            ]
            response.append(
                TrackedEventRead(
                    event_id=first_market.event_id,
                    event_title=first_market.event_title,
                    event_slug=first_market.event_slug,
                    source=first_market.source,
                    currency=metric.currency if metric else currency,
                    event_type=first_market.event_type,
                    engine=first_market.engine,
                    tracked_markets_count=len(event_markets),
                    tracking_enabled=True,
                    last_updated=live_last_updated,
                    ai_insight="Insight unavailable",
                    highest_scoring_market=self._build_highest_scoring_market(grouped_markets),
                )
            )

        response.sort(key=lambda item: item.event_title)
        return response

    async def untrack_event_for_system(
        self,
        *,
        session: AsyncSession,
        event_id: str,
        currency: Currency = Currency.DOLLAR,
    ) -> TrackEventResponse:
        statement = select(TrackedMarket).where(TrackedMarket.event_id == event_id)
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
            currency=currency,
        )
        return TrackEventResponse(
            event_id=first_market.event_id,
            event_title=first_market.event_title,
            event_slug=first_market.event_slug,
            source=first_market.source,
            currency=metric.currency if metric else currency,
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
        currency: Currency = Currency.DOLLAR,
    ) -> EventDetailRead:
        logger.info("Fetching event detail for user %s and event %s in %s", user_id, event_id, currency.value)
        statement = select(TrackedMarket).where(
            TrackedMarket.event_id == event_id,
            TrackedMarket.tracking_enabled == True,
            TrackedMarket.source == MarketSource.BAYSE,
        )
        result = await session.exec(statement)
        markets = result.all()

        if not markets:
            logger.info("Event %s not in DB yet, fetching from Bayse", event_id)
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
            return EventDetailRead(
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
                last_updated=None,
                ai_insight="Insight unavailable",
                highest_scoring_market=self._build_highest_scoring_market(grouped_markets),
                markets=grouped_markets,
            )

        tracking_enabled = await self._get_user_tracking_status(
            session=session,
            user_id=user_id,
            event_id=event_id,
        )
        metric = await self._get_event_metric(
            session,
            event_id=markets[0].event_id,
            source=markets[0].source,
            currency=currency,
        )
        live_total_liquidity, live_last_updated = await self._get_live_event_metadata(
            source=markets[0].source,
            event_id=markets[0].event_id,
            currency=currency,
        )
        return await self._group_tracked_markets(
            markets,
            currency=currency,
            total_liquidity=live_total_liquidity if live_total_liquidity is not None else (metric.total_liquidity if metric else None),
            last_updated=live_last_updated,
            tracking_enabled=tracking_enabled,
        )

    async def get_discovery_feed_for_user(
        self,
        *,
        session: AsyncSession,
        user_id: UUID,
        currency: Currency = Currency.DOLLAR,
    ) -> list[DiscoveryEventRead]:
        logger.info("Fetching discovery feed for user %s in %s", user_id, currency.value)
        listings_payload = await self.bayse.get_all_listings(currency=currency)
        events = listings_payload.get("events", [])

        tracked_statement = select(UserTrackedEvent).where(
            UserTrackedEvent.user_id == user_id,
            UserTrackedEvent.tracking_enabled == True,
        )
        tracked_result = await session.exec(tracked_statement)
        tracked_event_ids = {tracked_event.event_id for tracked_event in tracked_result.all()}

        discovery: list[DiscoveryEventRead] = []
        for event_payload in events:
            normalized = self.normalize_event_to_tracked_markets(event_payload, currency=currency)
            first_market = normalized.markets[0] if normalized.markets else None
            grouped_markets = [
                await self._build_market_read(
                    market=market,
                    currency=currency,
                    event_liquidity=normalized.total_liquidity,
                )
                for market in normalized.markets
            ]
            live_total_liquidity, live_last_updated = await self._get_live_event_metadata(
                source=normalized.source,
                event_id=normalized.event_id,
                currency=currency,
            )
            discovery.append(
                DiscoveryEventRead(
                    event_id=normalized.event_id,
                    event_title=normalized.event_title,
                    event_slug=normalized.event_slug,
                    source=normalized.source,
                    currency=normalized.currency,
                    event_type=normalized.event_type,
                    category=first_market.category if first_market else None,
                    status=first_market.status if first_market else None,
                    engine=normalized.engine,
                    total_liquidity=live_total_liquidity if live_total_liquidity is not None else normalized.total_liquidity,
                    event_total_orders=first_market.event_total_orders if first_market else None,
                    closing_date=first_market.closing_date if first_market else None,
                    tracked_markets_count=len(normalized.markets),
                    tracking_enabled=normalized.event_id in tracked_event_ids,
                    last_updated=live_last_updated,
                    ai_insight="Insight unavailable",
                    highest_scoring_market=self._build_highest_scoring_market(grouped_markets),
                )
            )

        logger.info("Discovery feed contains %s events for user %s", len(discovery), user_id)
        return discovery

    async def get_discovery_feed_for_system(
        self,
        *,
        session: AsyncSession,
        currency: Currency = Currency.DOLLAR,
    ) -> list[DiscoveryEventRead]:
        logger.info("Fetching system discovery feed in %s", currency.value)
        listings_payload = await self.bayse.get_all_listings(currency=currency)
        events = listings_payload.get("events", [])

        system_tracked_result = await session.exec(
            select(TrackedMarket.event_id).where(
                TrackedMarket.is_system_tracked == True,
                TrackedMarket.tracking_enabled == True,
            )
        )
        system_tracked_event_ids = set(system_tracked_result.all())

        discovery: list[DiscoveryEventRead] = []
        for event_payload in events:
            normalized = self.normalize_event_to_tracked_markets(event_payload, currency=currency)
            first_market = normalized.markets[0] if normalized.markets else None
            grouped_markets = [
                await self._build_market_read(
                    market=market,
                    currency=currency,
                    event_liquidity=normalized.total_liquidity,
                )
                for market in normalized.markets
            ]
            live_total_liquidity, live_last_updated = await self._get_live_event_metadata(
                source=normalized.source,
                event_id=normalized.event_id,
                currency=currency,
            )
            discovery.append(
                DiscoveryEventRead(
                    event_id=normalized.event_id,
                    event_title=normalized.event_title,
                    event_slug=normalized.event_slug,
                    source=normalized.source,
                    currency=normalized.currency,
                    event_type=normalized.event_type,
                    category=first_market.category if first_market else None,
                    status=first_market.status if first_market else None,
                    engine=normalized.engine,
                    total_liquidity=live_total_liquidity if live_total_liquidity is not None else normalized.total_liquidity,
                    event_total_orders=first_market.event_total_orders if first_market else None,
                    closing_date=first_market.closing_date if first_market else None,
                    tracked_markets_count=len(normalized.markets),
                    tracking_enabled=normalized.event_id in system_tracked_event_ids,
                    last_updated=live_last_updated,
                    ai_insight="Insight unavailable",
                    highest_scoring_market=self._build_highest_scoring_market(grouped_markets),
                )
            )

        logger.info("System discovery feed contains %s events", len(discovery))
        return discovery
