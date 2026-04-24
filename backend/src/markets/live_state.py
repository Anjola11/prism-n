import json
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from src.db.redis import redis_client
from src.markets.models import Currency, MarketEngine, MarketSource, TrackedMarket
from src.markets.scoring import MarketScoreResult, MarketScoringInput
from src.utils.logger import logger


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class EventLiveState(BaseModel):
    source: MarketSource
    event_id: str
    currency: Currency
    event_title: str
    event_slug: str | None = None
    engine: MarketEngine
    total_liquidity: float | None = None
    event_total_orders: int | None = None
    tracked_markets_count: int = 0
    last_synced_at: str = Field(default_factory=utc_now_iso)


class MarketLiveState(BaseModel):
    source: MarketSource
    event_id: str
    market_id: str
    currency: Currency
    engine: MarketEngine
    market_title: str
    current_probability: float | None = None
    previous_probability: float | None = None
    inverse_probability: float | None = None

    event_liquidity: float | None = None
    market_total_orders: int | None = None
    event_total_orders: int | None = None
    price_updates_in_window: int = 0
    persistence_ticks: int = 0

    top_bid_depth: float | None = None
    top_ask_depth: float | None = None
    top_5_bid_depth: float | None = None
    top_5_ask_depth: float | None = None
    spread_bps: float | None = None
    buy_notional: float = 0.0
    sell_notional: float = 0.0

    orderbook_supported: bool | None = None
    ticker_supported: bool | None = None
    last_direction: str | None = None
    has_recent_reversal: bool = False
    nearing_close: bool = False
    last_updated_at: str = Field(default_factory=utc_now_iso)


class SignalLiveState(BaseModel):
    source: MarketSource
    event_id: str
    market_id: str
    currency: Currency
    score: float
    classification: str
    formula: str
    factors: dict
    notes: list[str] = Field(default_factory=list)
    scored_at: str = Field(default_factory=utc_now_iso)


class SubscriptionLiveState(BaseModel):
    source: MarketSource
    event_id: str
    market_id: str | None = None
    channel: str
    active: bool = True
    last_subscribed_at: str = Field(default_factory=utc_now_iso)


class AssetMappingLiveState(BaseModel):
    source: MarketSource
    asset_id: str
    event_id: str
    market_id: str
    currency: Currency
    outcome_side: str
    last_bound_at: str = Field(default_factory=utc_now_iso)


class BayseSubscriptionPlan(BaseModel):
    version: str = Field(default_factory=utc_now_iso)
    event_ids: list[str] = Field(default_factory=list)
    currencies_by_event: dict[str, list[str]] = Field(default_factory=dict)
    orderbook_market_ids_by_currency: dict[str, list[str]] = Field(default_factory=dict)


class PolymarketAssetBindingState(BaseModel):
    asset_id: str
    event_id: str
    market_id: str
    currency: str
    outcome_side: str


class PolymarketSubscriptionPlan(BaseModel):
    version: str = Field(default_factory=utc_now_iso)
    bindings: list[PolymarketAssetBindingState] = Field(default_factory=list)


class LiveStateServices:
    def __init__(self, redis=redis_client):
        self.redis = redis

    def event_key(self, *, source: MarketSource, event_id: str, currency: Currency) -> str:
        return f"prism:event:{source.value}:{currency.value}:{event_id}"

    def market_key(self, *, source: MarketSource, market_id: str, currency: Currency) -> str:
        return f"prism:market:{source.value}:{currency.value}:{market_id}"

    def signal_key(self, *, source: MarketSource, market_id: str, currency: Currency) -> str:
        return f"prism:signal:{source.value}:{currency.value}:{market_id}"

    def persistence_key(self, *, source: MarketSource, market_id: str, currency: Currency) -> str:
        return f"prism:persistence:{source.value}:{currency.value}:{market_id}"

    def subscription_key(
        self,
        *,
        source: MarketSource,
        channel: str,
        event_id: str,
        market_id: str | None = None,
    ) -> str:
        if market_id:
            return f"prism:subscription:{source.value}:{channel}:{event_id}:{market_id}"
        return f"prism:subscription:{source.value}:{channel}:{event_id}"

    def read_model_key(self, *, namespace: str, identifier: str) -> str:
        return f"prism:readmodel:{namespace}:{identifier}"

    def asset_mapping_key(self, *, source: MarketSource, asset_id: str) -> str:
        return f"prism:assetmap:{source.value}:{asset_id}"

    def coordination_key(self, *, namespace: str, identifier: str) -> str:
        return f"prism:coordination:{namespace}:{identifier}"

    async def set_read_model(self, *, namespace: str, identifier: str, payload, ttl_seconds: int | None = None) -> None:
        key = self.read_model_key(namespace=namespace, identifier=identifier)
        serialized = json.dumps(payload)
        if ttl_seconds:
            await self.redis.set(key, serialized, ex=ttl_seconds)
            return
        await self.redis.set(key, serialized)

    async def get_read_model(self, *, namespace: str, identifier: str):
        payload = await self.redis.get(self.read_model_key(namespace=namespace, identifier=identifier))
        if not payload:
            return None
        return json.loads(payload)

    async def delete_read_model(self, *, namespace: str, identifier: str) -> None:
        await self.redis.delete(self.read_model_key(namespace=namespace, identifier=identifier))

    async def set_subscription_plan(self, *, identifier: str, payload: BaseModel | dict) -> None:
        serialized = payload.model_dump(mode="json") if isinstance(payload, BaseModel) else payload
        await self.set_read_model(
            namespace="subscription-plan",
            identifier=identifier,
            payload=serialized,
        )

    async def get_subscription_plan(self, *, identifier: str):
        return await self.get_read_model(
            namespace="subscription-plan",
            identifier=identifier,
        )

    async def acquire_coordination_lock(self, *, namespace: str, identifier: str, ttl_seconds: int) -> bool:
        return bool(
            await self.redis.set(
                self.coordination_key(namespace=namespace, identifier=identifier),
                utc_now_iso(),
                ex=ttl_seconds,
                nx=True,
            )
        )

    async def set_asset_mapping(self, state: AssetMappingLiveState) -> None:
        await self.redis.set(
            self.asset_mapping_key(source=state.source, asset_id=state.asset_id),
            state.model_dump_json(),
        )

    async def get_asset_mapping(
        self,
        *,
        source: MarketSource,
        asset_id: str,
    ) -> AssetMappingLiveState | None:
        payload = await self.redis.get(self.asset_mapping_key(source=source, asset_id=asset_id))
        if not payload:
            return None
        return AssetMappingLiveState.model_validate_json(payload)

    async def set_event_state(self, state: EventLiveState) -> None:
        await self.redis.set(
            self.event_key(source=state.source, event_id=state.event_id, currency=state.currency),
            state.model_dump_json(),
        )

    async def get_event_state(
        self,
        *,
        source: MarketSource,
        event_id: str,
        currency: Currency,
    ) -> EventLiveState | None:
        payload = await self.redis.get(self.event_key(source=source, event_id=event_id, currency=currency))
        if not payload:
            return None
        return EventLiveState.model_validate_json(payload)

    async def update_event_state(
        self,
        *,
        source: MarketSource,
        event_id: str,
        currency: Currency,
        **updates,
    ) -> EventLiveState | None:
        current = await self.get_event_state(source=source, event_id=event_id, currency=currency)
        if current is None:
            return None

        data = current.model_dump()
        data.update(updates)
        data["last_synced_at"] = utc_now_iso()
        updated = EventLiveState(**data)
        await self.set_event_state(updated)
        return updated

    async def set_market_state(self, state: MarketLiveState) -> None:
        await self.redis.set(
            self.market_key(source=state.source, market_id=state.market_id, currency=state.currency),
            state.model_dump_json(),
        )

    async def get_market_state(
        self,
        *,
        source: MarketSource,
        market_id: str,
        currency: Currency,
    ) -> MarketLiveState | None:
        payload = await self.redis.get(self.market_key(source=source, market_id=market_id, currency=currency))
        if not payload:
            return None
        return MarketLiveState.model_validate_json(payload)

    async def update_market_state(
        self,
        *,
        source: MarketSource,
        market_id: str,
        currency: Currency,
        **updates,
    ) -> MarketLiveState | None:
        current = await self.get_market_state(source=source, market_id=market_id, currency=currency)
        if current is None:
            return None

        data = current.model_dump()
        incoming_probability = updates.get("current_probability")
        previous_probability = data.get("current_probability")

        if incoming_probability is not None:
            data["previous_probability"] = previous_probability
            direction = self._infer_direction(previous_probability, incoming_probability)
            if direction and data.get("last_direction") and data["last_direction"] != direction:
                data["has_recent_reversal"] = True
                data["persistence_ticks"] = 1
            elif direction:
                data["has_recent_reversal"] = False
                data["persistence_ticks"] = int(data.get("persistence_ticks") or 0) + 1
            if direction:
                data["last_direction"] = direction
            data["price_updates_in_window"] = int(data.get("price_updates_in_window") or 0) + 1

        data.update(updates)
        data["last_updated_at"] = utc_now_iso()
        updated = MarketLiveState(**data)
        await self.set_market_state(updated)
        await self.redis.set(
            self.persistence_key(source=source, market_id=market_id, currency=currency),
            json.dumps(
                {
                    "ticks": updated.persistence_ticks,
                    "last_direction": updated.last_direction,
                    "has_recent_reversal": updated.has_recent_reversal,
                    "updated_at": updated.last_updated_at,
                }
            ),
        )
        return updated

    async def increment_trade_flow(
        self,
        *,
        source: MarketSource,
        market_id: str,
        currency: Currency,
        side: str,
        notional: float,
    ) -> MarketLiveState | None:
        current = await self.get_market_state(source=source, market_id=market_id, currency=currency)
        if current is None:
            return None

        side_normalized = side.upper()
        updates: dict = {}
        if side_normalized == "BUY":
            updates["buy_notional"] = current.buy_notional + notional
        elif side_normalized == "SELL":
            updates["sell_notional"] = current.sell_notional + notional
        else:
            logger.warning("Unsupported trade side %s for market %s", side, market_id)
            return current

        return await self.update_market_state(
            source=source,
            market_id=market_id,
            currency=currency,
            **updates,
        )

    async def set_signal_state(self, state: SignalLiveState) -> None:
        await self.redis.set(
            self.signal_key(source=state.source, market_id=state.market_id, currency=state.currency),
            state.model_dump_json(),
        )

    async def get_signal_state(
        self,
        *,
        source: MarketSource,
        market_id: str,
        currency: Currency,
    ) -> SignalLiveState | None:
        payload = await self.redis.get(self.signal_key(source=source, market_id=market_id, currency=currency))
        if not payload:
            return None
        return SignalLiveState.model_validate_json(payload)

    async def set_subscription_state(self, state: SubscriptionLiveState) -> None:
        await self.redis.set(
            self.subscription_key(
                source=state.source,
                channel=state.channel,
                event_id=state.event_id,
                market_id=state.market_id,
            ),
            state.model_dump_json(),
        )

    async def get_subscription_state(
        self,
        *,
        source: MarketSource,
        channel: str,
        event_id: str,
        market_id: str | None = None,
    ) -> SubscriptionLiveState | None:
        payload = await self.redis.get(
            self.subscription_key(
                source=source,
                channel=channel,
                event_id=event_id,
                market_id=market_id,
            )
        )
        if not payload:
            return None
        return SubscriptionLiveState.model_validate_json(payload)

    async def warm_market_state_from_tracking(
        self,
        *,
        tracked_market: TrackedMarket,
        currency: Currency,
        total_liquidity: float | None = None,
    ) -> MarketLiveState:
        state = MarketLiveState(
            source=tracked_market.source,
            event_id=tracked_market.event_id,
            market_id=tracked_market.market_id,
            currency=currency,
            engine=tracked_market.engine,
            market_title=tracked_market.market_title,
            current_probability=tracked_market.current_probability,
            previous_probability=None,
            inverse_probability=tracked_market.inverse_probability,
            event_liquidity=total_liquidity,
            market_total_orders=tracked_market.market_total_orders,
            event_total_orders=tracked_market.event_total_orders,
        )
        await self.set_market_state(state)
        if tracked_market.source == MarketSource.POLYMARKET:
            await self.set_asset_mapping(
                AssetMappingLiveState(
                    source=tracked_market.source,
                    asset_id=tracked_market.yes_outcome_id,
                    event_id=tracked_market.event_id,
                    market_id=tracked_market.market_id,
                    currency=currency,
                    outcome_side="YES",
                )
            )
            await self.set_asset_mapping(
                AssetMappingLiveState(
                    source=tracked_market.source,
                    asset_id=tracked_market.no_outcome_id,
                    event_id=tracked_market.event_id,
                    market_id=tracked_market.market_id,
                    currency=currency,
                    outcome_side="NO",
                )
            )
        return state

    async def warm_event_state_from_tracking(
        self,
        *,
        tracked_market: TrackedMarket,
        currency: Currency,
        total_liquidity: float | None = None,
        tracked_markets_count: int = 1,
    ) -> EventLiveState:
        state = EventLiveState(
            source=tracked_market.source,
            event_id=tracked_market.event_id,
            currency=currency,
            event_title=tracked_market.event_title,
            event_slug=tracked_market.event_slug,
            engine=tracked_market.engine,
            total_liquidity=total_liquidity,
            event_total_orders=tracked_market.event_total_orders,
            tracked_markets_count=tracked_markets_count,
        )
        await self.set_event_state(state)
        return state

    def build_scoring_input(
        self,
        *,
        market_state: MarketLiveState,
        baseline_sigma: float | None = None,
    ) -> MarketScoringInput:
        return MarketScoringInput(
            source=market_state.source,
            engine=market_state.engine,
            event_id=market_state.event_id,
            market_id=market_state.market_id,
            current_probability=market_state.current_probability or 0.0,
            previous_probability=market_state.previous_probability,
            baseline_sigma=baseline_sigma,
            event_liquidity=market_state.event_liquidity,
            market_total_orders=market_state.market_total_orders,
            event_total_orders=market_state.event_total_orders,
            price_updates_in_window=market_state.price_updates_in_window,
            persistence_ticks=market_state.persistence_ticks,
            top_bid_depth=market_state.top_bid_depth,
            top_ask_depth=market_state.top_ask_depth,
            top_5_bid_depth=market_state.top_5_bid_depth,
            top_5_ask_depth=market_state.top_5_ask_depth,
            spread_bps=market_state.spread_bps,
            buy_notional=market_state.buy_notional,
            sell_notional=market_state.sell_notional,
            orderbook_supported=market_state.orderbook_supported,
            ticker_supported=market_state.ticker_supported,
            has_recent_reversal=market_state.has_recent_reversal,
            nearing_close=market_state.nearing_close,
        )

    def build_signal_state(
        self,
        *,
        market_state: MarketLiveState,
        score_result: MarketScoreResult,
    ) -> SignalLiveState:
        return SignalLiveState(
            source=market_state.source,
            event_id=market_state.event_id,
            market_id=market_state.market_id,
            currency=market_state.currency,
            score=score_result.score,
            classification=score_result.classification,
            formula=score_result.formula,
            factors=score_result.factors.model_dump(),
            notes=score_result.notes,
        )

    def _infer_direction(self, previous: float | None, current: float | None) -> str | None:
        if previous is None or current is None:
            return None
        if current > previous:
            return "UP"
        if current < previous:
            return "DOWN"
        return "FLAT"
