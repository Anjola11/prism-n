import asyncio
import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import websockets
from sqlalchemy import false, or_
from sqlmodel import select
from websockets.asyncio.client import ClientConnection

from src.db.main import async_session_maker
from src.markets.baselines import BaselineServices
from src.markets.live_state import (
    BayseSubscriptionPlan,
    EventLiveState,
    LiveStateServices,
    MarketLiveState,
    SubscriptionLiveState,
)
from src.markets.models import (
    Currency,
    MarketEngine,
    MarketSource,
    TrackedEventMetric,
    TrackedMarket,
    UserTrackedEvent,
)
from src.markets.scoring import ScoringServices
from src.markets.signal_snapshots import SignalSnapshotServices
from src.utils.bayse import BayseServices
from src.utils.logger import logger


class BayseWebSocketManager:
    WS_URL = "wss://socket.bayse.markets/ws/v1/markets"
    ORDERBOOK_BATCH_SIZE = 10

    def __init__(
        self,
        *,
        bayse: BayseServices,
        live_state: LiveStateServices | None = None,
        baseline_services: BaselineServices | None = None,
        scoring_services: ScoringServices | None = None,
        signal_snapshot_services: SignalSnapshotServices | None = None,
        reconnect_base_seconds: float = 2.0,
        reconnect_cap_seconds: float = 30.0,
        subscription_sync_seconds: float = 30.0,
    ):
        self.bayse = bayse
        self.live_state = live_state or LiveStateServices()
        self.baseline_services = baseline_services or BaselineServices(bayse=bayse)
        self.scoring_services = scoring_services or ScoringServices()
        self.signal_snapshot_services = signal_snapshot_services or SignalSnapshotServices()
        self.reconnect_base_seconds = reconnect_base_seconds
        self.reconnect_cap_seconds = reconnect_cap_seconds
        self.subscription_sync_seconds = subscription_sync_seconds

        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._ws: ClientConnection | None = None
        self._subscription_sync_task: asyncio.Task | None = None
        self._active_subscriptions: set[tuple[str, str, str | None, str | None]] = set()
        self._baseline_cache: dict[tuple[str, str], float | None] = {}
        self._last_message_at: str | None = None
        self._last_connect_at: str | None = None
        self._reconnect_count: int = 0
        self._last_error: str | None = None
        self._last_subscription_plan_version: str | None = None

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self.run(), name="bayse-websocket-manager")
        logger.info("Bayse websocket manager task started")

    async def stop(self) -> None:
        self._stop_event.set()

        if self._subscription_sync_task:
            self._subscription_sync_task.cancel()
            try:
                await self._subscription_sync_task
            except asyncio.CancelledError:
                pass
            self._subscription_sync_task = None

        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                logger.warning("Failed to close Bayse websocket cleanly", exc_info=True)
            self._ws = None

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        await self._mark_active_subscriptions_inactive()
        logger.info("Bayse websocket manager stopped")

    async def run(self) -> None:
        attempt = 0
        while not self._stop_event.is_set():
            try:
                logger.info("Connecting to Bayse websocket at %s", self.WS_URL)
                async with websockets.connect(
                    self.WS_URL,
                    ping_interval=20,
                    ping_timeout=20,
                    close_timeout=10,
                    max_size=None,
                ) as ws:
                    self._ws = ws
                    attempt = 0
                    self._last_connect_at = datetime.now(timezone.utc).isoformat()
                    self._last_error = None
                    logger.info("Connected to Bayse websocket")
                    await self._handle_connection(ws)
            except asyncio.CancelledError:
                raise
            except Exception:
                attempt += 1
                self._reconnect_count += 1
                self._last_error = "Bayse websocket disconnected"
                wait_seconds = min(
                    self.reconnect_base_seconds * (2 ** max(attempt - 1, 0)),
                    self.reconnect_cap_seconds,
                )
                logger.warning(
                    "Bayse websocket disconnected; reconnecting in %.1fs (attempt %s)",
                    wait_seconds,
                    attempt,
                    exc_info=True,
                )
                await self._mark_active_subscriptions_inactive()
                await asyncio.sleep(wait_seconds)
            finally:
                self._ws = None

    async def _handle_connection(self, ws: ClientConnection) -> None:
        self._active_subscriptions.clear()
        await self._resync_tracked_events_from_rest()
        await self._sync_subscriptions()
        self._subscription_sync_task = asyncio.create_task(
            self._subscription_sync_loop(),
            name="bayse-websocket-subscription-sync",
        )

        try:
            async for raw_frame in ws:
                await self._handle_raw_frame(raw_frame)
        finally:
            if self._subscription_sync_task:
                self._subscription_sync_task.cancel()
                try:
                    await self._subscription_sync_task
                except asyncio.CancelledError:
                    pass
                self._subscription_sync_task = None
            await self._mark_active_subscriptions_inactive()

    async def _subscription_sync_loop(self) -> None:
        while not self._stop_event.is_set() and self._ws:
            await asyncio.sleep(self.subscription_sync_seconds)
            if self._stop_event.is_set() or not self._ws:
                return
            await self._sync_subscriptions()

    async def _sync_subscriptions(self) -> None:
        if not self._ws:
            return

        plan = await self._load_subscription_plan()
        if plan is None:
            return

        if plan.version == self._last_subscription_plan_version and self._active_subscriptions:
            return

        event_ids = set(plan.event_ids)
        if not event_ids:
            self._last_subscription_plan_version = plan.version
            return

        currency_map: dict[str, set[Currency]] = defaultdict(set)
        for event_id, currency_values in plan.currencies_by_event.items():
            for currency_value in currency_values:
                try:
                    currency_map[event_id].add(Currency(currency_value))
                except ValueError:
                    logger.warning("Skipping unsupported Bayse subscription currency %s", currency_value)

        for event_id in event_ids:
            await self._subscribe_prices(event_id)
            await self._subscribe_activity(event_id)

        for currency_value, market_ids in plan.orderbook_market_ids_by_currency.items():
            try:
                currency = Currency(currency_value)
            except ValueError:
                logger.warning("Skipping unsupported Bayse orderbook currency %s", currency_value)
                continue
            await self._subscribe_orderbook(currency=currency, market_ids=market_ids)

        self._last_subscription_plan_version = plan.version

    async def _load_subscription_plan(self) -> BayseSubscriptionPlan | None:
        cached_plan = await self.live_state.get_subscription_plan(identifier=MarketSource.BAYSE.value)
        if cached_plan is not None:
            try:
                return BayseSubscriptionPlan.model_validate(cached_plan)
            except Exception:
                logger.warning("Invalid Bayse subscription plan in Redis; rebuilding", exc_info=True)

        plan = await self._build_subscription_plan_from_db()
        await self.live_state.set_subscription_plan(
            identifier=MarketSource.BAYSE.value,
            payload=plan,
        )
        return plan

    async def _build_subscription_plan_from_db(self) -> BayseSubscriptionPlan:
        async with async_session_maker() as session:
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

            tracked_markets_result = await session.exec(
                select(TrackedMarket).where(
                    TrackedMarket.source == MarketSource.BAYSE,
                    TrackedMarket.tracking_enabled == True,
                    or_(
                        TrackedMarket.is_system_tracked == True,
                        tracked_event_filter,
                    ),
                )
            )
            tracked_markets = tracked_markets_result.all()

            event_ids = sorted({market.event_id for market in tracked_markets})
            currencies_by_event: dict[str, set[str]] = defaultdict(set)
            if event_ids:
                event_metric_result = await session.exec(
                    select(TrackedEventMetric).where(
                        TrackedEventMetric.source == MarketSource.BAYSE,
                        TrackedEventMetric.event_id.in_(event_ids),
                    )
                )
                event_metrics = event_metric_result.all()
                for metric in event_metrics:
                    currencies_by_event[metric.event_id].add(metric.currency.value)

        for event_id in event_ids:
            if not currencies_by_event[event_id]:
                currencies_by_event[event_id].add(Currency.DOLLAR.value)

        orderbook_market_ids_by_currency: dict[str, set[str]] = defaultdict(set)
        for market in tracked_markets:
            if market.engine != MarketEngine.CLOB:
                continue
            for currency_value in currencies_by_event.get(market.event_id, {Currency.DOLLAR.value}):
                orderbook_market_ids_by_currency[currency_value].add(market.market_id)

        return BayseSubscriptionPlan(
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

    async def _subscribe_prices(self, event_id: str) -> None:
        subscription_id = ("prices", event_id, None, None)
        if subscription_id in self._active_subscriptions or not self._ws:
            return

        payload = {
            "type": "subscribe",
            "channel": "prices",
            "eventId": event_id,
        }
        await self._ws.send(json.dumps(payload))
        self._active_subscriptions.add(subscription_id)
        await self.live_state.set_subscription_state(
            SubscriptionLiveState(
                source=MarketSource.BAYSE,
                event_id=event_id,
                channel="prices",
                active=True,
            )
        )
        logger.info("Subscribed to Bayse prices for event %s", event_id)

    async def _subscribe_activity(self, event_id: str) -> None:
        subscription_id = ("activity", event_id, None, None)
        if subscription_id in self._active_subscriptions or not self._ws:
            return

        payload = {
            "type": "subscribe",
            "channel": "activity",
            "eventId": event_id,
        }
        await self._ws.send(json.dumps(payload))
        self._active_subscriptions.add(subscription_id)
        await self.live_state.set_subscription_state(
            SubscriptionLiveState(
                source=MarketSource.BAYSE,
                event_id=event_id,
                channel="activity",
                active=True,
            )
        )
        logger.info("Subscribed to Bayse activity for event %s", event_id)

    async def _subscribe_orderbook(self, *, currency: Currency, market_ids: list[str]) -> None:
        if not self._ws:
            return

        pending_market_ids = [
            market_id
            for market_id in market_ids
            if ("orderbook", market_id, None, currency.value) not in self._active_subscriptions
        ]
        if not pending_market_ids:
            return

        subscribed_count = 0
        for start in range(0, len(pending_market_ids), self.ORDERBOOK_BATCH_SIZE):
            market_batch = pending_market_ids[start : start + self.ORDERBOOK_BATCH_SIZE]
            payload = {
                "type": "subscribe",
                "channel": "orderbook",
                "marketIds": market_batch,
                "currency": currency.value,
            }
            await self._ws.send(json.dumps(payload))

            for market_id in market_batch:
                self._active_subscriptions.add(("orderbook", market_id, None, currency.value))
                await self.live_state.set_subscription_state(
                    SubscriptionLiveState(
                        source=MarketSource.BAYSE,
                        event_id="",
                        market_id=market_id,
                        channel=f"orderbook:{currency.value}",
                        active=True,
                    )
                )
            subscribed_count += len(market_batch)

        logger.info(
            "Subscribed to Bayse orderbook for %s CLOB markets in %s",
            subscribed_count,
            currency.value,
        )

    async def _handle_raw_frame(self, raw_frame: str) -> None:
        frames = [chunk.strip() for chunk in raw_frame.splitlines() if chunk.strip()]
        for frame in frames:
            try:
                message = json.loads(frame)
            except json.JSONDecodeError:
                logger.warning("Failed to decode Bayse websocket frame: %s", frame)
                continue
            await self._handle_message(message)

    async def _handle_message(self, message: dict[str, Any]) -> None:
        self._last_message_at = datetime.now(timezone.utc).isoformat()
        message_type = message.get("type")
        if message_type == "connected":
            logger.info("Bayse websocket acknowledged connection")
            return
        if message_type == "pong":
            return
        if message_type == "unsubscribed":
            logger.info("Bayse websocket unsubscribed response: %s", message)
            return
        if message_type == "error":
            logger.warning("Bayse websocket error payload: %s", message)
            return
        if message_type == "price_update":
            await self._handle_price_update(message)
            return
        if message_type in {"buy_order", "sell_order"}:
            await self._handle_activity_update(message)
            return
        if message_type == "orderbook_update":
            await self._handle_orderbook_update(message)
            return
        logger.info("Ignoring unsupported Bayse websocket message type %s", message_type)

    async def _handle_price_update(self, message: dict[str, Any]) -> None:
        payload = message.get("data") or {}
        event_id = str(payload.get("id") or payload.get("eventId") or "")
        if not event_id:
            return

        currencies = await self._get_event_currencies(event_id)
        engine = self._safe_engine(payload.get("engine"))
        markets = payload.get("markets", [])

        for currency in currencies:
            existing_event_state = await self.live_state.get_event_state(
                source=MarketSource.BAYSE,
                event_id=event_id,
                currency=currency,
            )
            await self.live_state.set_event_state(
                EventLiveState(
                    source=MarketSource.BAYSE,
                    event_id=event_id,
                    currency=currency,
                    event_title=payload.get("title") or getattr(existing_event_state, "event_title", event_id),
                    event_slug=payload.get("slug") or getattr(existing_event_state, "event_slug", None),
                    engine=engine or getattr(existing_event_state, "engine", MarketEngine.AMM),
                    total_liquidity=payload.get("liquidity", getattr(existing_event_state, "total_liquidity", None)),
                    event_total_orders=payload.get("totalOrders", getattr(existing_event_state, "event_total_orders", None)),
                    tracked_markets_count=len(markets) or getattr(existing_event_state, "tracked_markets_count", 0),
                )
            )

        for market_payload in markets:
            market_id = str(market_payload.get("id") or "")
            if not market_id:
                continue

            current_probability = market_payload.get("outcome1Price")
            inverse_probability = market_payload.get("outcome2Price")
            prices = market_payload.get("prices") or {}
            if current_probability is None and isinstance(prices, dict):
                current_probability = prices.get("YES")
            if inverse_probability is None and isinstance(prices, dict):
                inverse_probability = prices.get("NO")

            for currency in currencies:
                await self._upsert_market_live_state(
                    event_id=event_id,
                    market_id=market_id,
                    currency=currency,
                    engine=engine or self._safe_engine(market_payload.get("engine")) or MarketEngine.AMM,
                    market_title=market_payload.get("title") or market_payload.get("question") or market_id,
                    current_probability=current_probability,
                    inverse_probability=inverse_probability,
                    event_liquidity=payload.get("liquidity"),
                    market_total_orders=market_payload.get("totalOrders"),
                    event_total_orders=payload.get("totalOrders"),
                )
                await self._score_market(
                    market_id=market_id,
                    currency=currency,
                )

    async def _handle_activity_update(self, message: dict[str, Any]) -> None:
        payload = message.get("data") or {}
        order = payload.get("order") or {}
        market = payload.get("market") or {}
        event = payload.get("event") or {}

        event_id = str(event.get("id") or payload.get("eventId") or "")
        market_id = str(market.get("id") or payload.get("marketId") or "")
        if not market_id:
            return

        side = "BUY" if message.get("type") == "buy_order" else "SELL"
        order_currency = self._safe_currency(order.get("currency") or payload.get("currency"))
        if order_currency:
            currencies = [order_currency]
        elif event_id:
            currencies = await self._get_event_currencies(event_id)
        else:
            currencies = [Currency.DOLLAR]

        amount = order.get("amount")
        quantity = order.get("quantity")
        price = order.get("price")
        notional = self._to_float(amount)
        if notional is None and quantity is not None and price is not None:
            quantity_value = self._to_float(quantity)
            price_value = self._to_float(price)
            if quantity_value is not None and price_value is not None:
                notional = quantity_value * price_value
        notional = notional or 0.0

        for currency in currencies:
            await self.live_state.increment_trade_flow(
                source=MarketSource.BAYSE,
                market_id=market_id,
                currency=currency,
                side=side,
                notional=notional,
            )
            await self._score_market(market_id=market_id, currency=currency)

    async def _handle_orderbook_update(self, message: dict[str, Any]) -> None:
        payload = message.get("data") or {}
        market_id = str(payload.get("marketId") or "")
        if not market_id:
            return

        currency = self._extract_orderbook_currency(message) or Currency.DOLLAR
        bids = payload.get("bids") or []
        asks = payload.get("asks") or []
        best_bid_price = self._to_float(bids[0].get("price")) if bids else None
        best_ask_price = self._to_float(asks[0].get("price")) if asks else None
        spread_bps = None
        if best_bid_price is not None and best_ask_price is not None:
            spread_bps = max(best_ask_price - best_bid_price, 0.0) * 10_000

        await self.live_state.update_market_state(
            source=MarketSource.BAYSE,
            market_id=market_id,
            currency=currency,
            top_bid_depth=self._extract_level_total(bids[0]) if bids else 0.0,
            top_ask_depth=self._extract_level_total(asks[0]) if asks else 0.0,
            top_5_bid_depth=sum(self._extract_level_total(level) for level in bids[:5]),
            top_5_ask_depth=sum(self._extract_level_total(level) for level in asks[:5]),
            spread_bps=spread_bps,
            orderbook_supported=True,
        )
        await self._score_market(market_id=market_id, currency=currency)

    async def _upsert_market_live_state(
        self,
        *,
        event_id: str,
        market_id: str,
        currency: Currency,
        engine: MarketEngine,
        market_title: str,
        current_probability: float | None,
        inverse_probability: float | None,
        event_liquidity: float | None,
        market_total_orders: int | None,
        event_total_orders: int | None,
    ) -> None:
        current = await self.live_state.get_market_state(
            source=MarketSource.BAYSE,
            market_id=market_id,
            currency=currency,
        )
        if current is None:
            await self.live_state.set_market_state(
                MarketLiveState(
                    source=MarketSource.BAYSE,
                    event_id=event_id,
                    market_id=market_id,
                    currency=currency,
                    engine=engine,
                    market_title=market_title,
                    current_probability=current_probability,
                    inverse_probability=inverse_probability,
                    event_liquidity=event_liquidity,
                    market_total_orders=market_total_orders,
                    event_total_orders=event_total_orders,
                )
            )
            return

        await self.live_state.update_market_state(
            source=MarketSource.BAYSE,
            market_id=market_id,
            currency=currency,
            current_probability=current_probability,
            inverse_probability=inverse_probability,
            event_liquidity=event_liquidity,
            market_total_orders=market_total_orders,
            event_total_orders=event_total_orders,
        )

    async def _score_market(self, *, market_id: str, currency: Currency) -> None:
        market_state = await self.live_state.get_market_state(
            source=MarketSource.BAYSE,
            market_id=market_id,
            currency=currency,
        )
        if not market_state:
            return

        previous_signal = await self.live_state.get_signal_state(
            source=MarketSource.BAYSE,
            market_id=market_id,
            currency=currency,
        )
        baseline_sigma = await self._get_baseline_sigma(market_id=market_id)
        scoring_input = self.live_state.build_scoring_input(
            market_state=market_state,
            baseline_sigma=baseline_sigma,
        )
        score_result = self.scoring_services.compute_signal_score(scoring_input)
        await self.live_state.set_signal_state(
            self.live_state.build_signal_state(
                market_state=market_state,
                score_result=score_result,
            )
        )
        if self._should_refresh_event_ai_insight(
            previous_signal=previous_signal,
            score_result=score_result,
        ):
            await self._invalidate_event_ai_insight(
                event_id=market_state.event_id,
                currency=currency,
            )
        snapshot_reason = self._determine_snapshot_reason(
            previous_signal=previous_signal,
            market_state=market_state,
            score_result=score_result,
        )
        if snapshot_reason:
            async with async_session_maker() as session:
                await self.signal_snapshot_services.persist_snapshot(
                    session=session,
                    market_state=market_state,
                    score_result=score_result,
                    snapshot_reason=snapshot_reason,
                )

    async def _get_baseline_sigma(self, *, market_id: str) -> float | None:
        cache_key = (market_id, "YES")
        if cache_key in self._baseline_cache:
            return self._baseline_cache[cache_key]

        async with async_session_maker() as session:
            baseline = await self.baseline_services.get_market_baseline(
                session=session,
                market_id=market_id,
            )
        sigma = baseline.volatility_sigma if baseline else None
        self._baseline_cache[cache_key] = sigma
        return sigma

    async def _get_event_currencies(self, event_id: str) -> list[Currency]:
        async with async_session_maker() as session:
            result = await session.exec(
                select(TrackedEventMetric.currency).where(
                    TrackedEventMetric.source == MarketSource.BAYSE,
                    TrackedEventMetric.event_id == event_id,
                )
            )
            currencies = list(dict.fromkeys(result.all()))
        return currencies or [Currency.DOLLAR]

    async def _mark_active_subscriptions_inactive(self) -> None:
        active_subscriptions = list(self._active_subscriptions)
        self._active_subscriptions.clear()

        for channel, event_id, market_id, currency in active_subscriptions:
            channel_name = channel if currency is None else f"{channel}:{currency}"
            await self.live_state.set_subscription_state(
                SubscriptionLiveState(
                    source=MarketSource.BAYSE,
                    event_id=event_id or "",
                    market_id=market_id,
                    channel=channel_name,
                    active=False,
                )
            )

    async def _resync_tracked_events_from_rest(self) -> None:
        async with async_session_maker() as session:
            tracked_event_ids = set(
                await session.exec(
                    select(UserTrackedEvent.event_id).where(UserTrackedEvent.tracking_enabled == True)
                )
            )
            system_tracked_event_ids = set(
                await session.exec(
                    select(TrackedMarket.event_id).where(TrackedMarket.is_system_tracked == True)
                )
            )
            all_event_ids = tracked_event_ids | system_tracked_event_ids
            if not all_event_ids:
                return

            # Only resync events that are actually sourced from Bayse — skip Polymarket events
            bayse_event_ids_result = await session.exec(
                select(TrackedMarket.event_id).where(
                    TrackedMarket.source == MarketSource.BAYSE,
                    TrackedMarket.event_id.in_(all_event_ids),
                    TrackedMarket.tracking_enabled == True,
                )
            )
            event_ids = sorted(set(bayse_event_ids_result.all()))
            if not event_ids:
                return

            metrics_result = await session.exec(
                select(TrackedEventMetric).where(
                    TrackedEventMetric.source == MarketSource.BAYSE,
                    TrackedEventMetric.event_id.in_(event_ids),
                )
            )
            metrics = metrics_result.all()

        event_currency_map: dict[str, set[Currency]] = defaultdict(set)
        for metric in metrics:
            event_currency_map[metric.event_id].add(metric.currency)
        for event_id in event_ids:
            if not event_currency_map[event_id]:
                event_currency_map[event_id].add(Currency.DOLLAR)

        for event_id in event_ids:
            for currency in event_currency_map[event_id]:
                try:
                    event_payload = await self.bayse.get_event_by_id(event_id=event_id, currency=currency)
                    await self._warm_event_and_markets_from_payload(event_payload=event_payload, currency=currency)
                except Exception:
                    logger.warning(
                        "Failed REST resync for event %s in %s",
                        event_id,
                        currency.value,
                        exc_info=True,
                    )

    async def _warm_event_and_markets_from_payload(
        self,
        *,
        event_payload: dict[str, Any],
        currency: Currency,
    ) -> None:
        event_id = str(event_payload.get("id") or "")
        if not event_id:
            return
        markets = event_payload.get("markets", [])
        engine = self._safe_engine(event_payload.get("engine")) or MarketEngine.AMM

        await self.live_state.set_event_state(
            EventLiveState(
                source=MarketSource.BAYSE,
                event_id=event_id,
                currency=currency,
                event_title=event_payload.get("title") or event_id,
                event_slug=event_payload.get("slug"),
                engine=engine,
                total_liquidity=event_payload.get("liquidity"),
                event_total_orders=event_payload.get("totalOrders"),
                tracked_markets_count=len(markets),
            )
        )

        for market_payload in markets:
            market_id = str(market_payload.get("id") or "")
            if not market_id:
                continue
            await self._upsert_market_live_state(
                event_id=event_id,
                market_id=market_id,
                currency=currency,
                engine=self._safe_engine(market_payload.get("engine")) or engine,
                market_title=market_payload.get("title") or market_payload.get("question") or market_id,
                current_probability=market_payload.get("outcome1Price"),
                inverse_probability=market_payload.get("outcome2Price"),
                event_liquidity=event_payload.get("liquidity"),
                market_total_orders=market_payload.get("totalOrders"),
                event_total_orders=event_payload.get("totalOrders"),
            )

    def _determine_snapshot_reason(
        self,
        *,
        previous_signal,
        market_state: MarketLiveState,
        score_result,
    ) -> str | None:
        if score_result.classification in {"strong", "high_conviction"}:
            return "high_signal"
        if previous_signal is None and score_result.score >= 40:
            return "initial_scored_signal"
        if previous_signal and previous_signal.classification != score_result.classification:
            return "classification_change"
        if market_state.has_recent_reversal and score_result.score >= 50:
            return "reversal_signal"
        return None

    def _should_refresh_event_ai_insight(self, *, previous_signal, score_result) -> bool:
        if previous_signal is None:
            return score_result.score >= 40
        if previous_signal.classification != score_result.classification:
            return True
        if abs(previous_signal.score - score_result.score) >= 12:
            return True
        previous_notes = tuple(previous_signal.notes or [])
        current_notes = tuple(score_result.notes or [])
        return previous_notes != current_notes

    async def _invalidate_event_ai_insight(self, *, event_id: str, currency: Currency) -> None:
        await self.live_state.delete_read_model(
            namespace="event-ai-insight",
            identifier=f"event-ai-insight:v2:{event_id}:{currency.value}",
        )
        await self.live_state.delete_read_model(
            namespace="event-detail",
            identifier=f"event-detail:{event_id}:{currency.value}",
        )

    def get_status(self) -> dict[str, Any]:
        return {
            "connected": self._ws is not None,
            "background_task_running": bool(self._task and not self._task.done()),
            "subscription_sync_running": bool(
                self._subscription_sync_task and not self._subscription_sync_task.done()
            ),
            "active_subscription_count": len(self._active_subscriptions),
            "last_connect_at": self._last_connect_at,
            "last_message_at": self._last_message_at,
            "reconnect_count": self._reconnect_count,
            "last_error": self._last_error,
            "baseline_cache_size": len(self._baseline_cache),
        }

    def reset_baseline_cache(self) -> None:
        self._baseline_cache.clear()

    def _extract_orderbook_currency(self, message: dict[str, Any]) -> Currency | None:
        room = message.get("room")
        if not room or not isinstance(room, str):
            return None
        if room.endswith(":NGN"):
            return Currency.NAIRA
        if room.endswith(":USD"):
            return Currency.DOLLAR
        return Currency.DOLLAR

    def _extract_level_total(self, level: dict[str, Any]) -> float:
        total = self._to_float(level.get("total"))
        if total is not None:
            return total
        quantity = self._to_float(level.get("quantity")) or 0.0
        price = self._to_float(level.get("price")) or 0.0
        return quantity * price

    def _safe_engine(self, raw_value: Any) -> MarketEngine | None:
        if raw_value is None:
            return None
        try:
            return MarketEngine(str(raw_value).upper())
        except ValueError:
            return None

    def _safe_currency(self, raw_value: Any) -> Currency | None:
        if raw_value is None:
            return None
        try:
            return Currency(str(raw_value).upper())
        except ValueError:
            return None

    def _to_float(self, value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
