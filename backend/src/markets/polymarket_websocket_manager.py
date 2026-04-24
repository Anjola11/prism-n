import asyncio
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import websockets
from sqlalchemy import false, or_
from sqlmodel import select
from websockets.asyncio.client import ClientConnection

from src.db.main import async_session_maker
from src.markets.baselines import BaselineServices
from src.markets.live_state import (
    AssetMappingLiveState,
    EventLiveState,
    LiveStateServices,
    MarketLiveState,
    PolymarketSubscriptionPlan,
    PolymarketAssetBindingState,
    SubscriptionLiveState,
)
from src.markets.models import Currency, MarketEngine, MarketSource, TrackedEventMetric, TrackedMarket, UserTrackedEvent
from src.markets.scoring import ScoringServices
from src.markets.signal_snapshots import SignalSnapshotServices
from src.utils.logger import logger
from src.utils.polymarket_clob import PolymarketCLOBServices
from src.utils.polymarket_data import PolymarketDataServices


@dataclass
class AssetBinding:
    asset_id: str
    event_id: str
    market_id: str
    currency: Currency
    outcome_side: str


class PolymarketWebSocketManager:
    WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
    SUBSCRIPTION_BATCH_SIZE = 100

    def __init__(
        self,
        *,
        clob: PolymarketCLOBServices,
        data_api: PolymarketDataServices | None = None,
        live_state: LiveStateServices | None = None,
        baseline_services: BaselineServices | None = None,
        scoring_services: ScoringServices | None = None,
        signal_snapshot_services: SignalSnapshotServices | None = None,
        reconnect_base_seconds: float = 2.0,
        reconnect_cap_seconds: float = 30.0,
        subscription_sync_seconds: float = 30.0,
        ping_interval_seconds: float = 10.0,
    ):
        self.clob = clob
        self.data_api = data_api
        self.live_state = live_state or LiveStateServices()
        self.baseline_services = baseline_services
        self.scoring_services = scoring_services or ScoringServices()
        self.signal_snapshot_services = signal_snapshot_services or SignalSnapshotServices()
        self.reconnect_base_seconds = reconnect_base_seconds
        self.reconnect_cap_seconds = reconnect_cap_seconds
        self.subscription_sync_seconds = subscription_sync_seconds
        self.ping_interval_seconds = ping_interval_seconds

        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._ws: ClientConnection | None = None
        self._subscription_sync_task: asyncio.Task | None = None
        self._ping_task: asyncio.Task | None = None
        self._asset_bindings: dict[str, AssetBinding] = {}
        self._active_asset_ids: set[str] = set()
        self._asset_books: dict[str, dict[str, Any]] = {}
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
        self._task = asyncio.create_task(self.run(), name="polymarket-websocket-manager")
        logger.info("Polymarket websocket manager task started")

    async def stop(self) -> None:
        self._stop_event.set()

        for task in (self._subscription_sync_task, self._ping_task):
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        self._subscription_sync_task = None
        self._ping_task = None

        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                logger.warning("Failed to close Polymarket websocket cleanly", exc_info=True)
            self._ws = None

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        await self._mark_active_subscriptions_inactive()
        logger.info("Polymarket websocket manager stopped")

    async def run(self) -> None:
        attempt = 0
        while not self._stop_event.is_set():
            try:
                logger.info("Connecting to Polymarket websocket at %s", self.WS_URL)
                async with websockets.connect(
                    self.WS_URL,
                    ping_interval=None,
                    close_timeout=10,
                    max_size=None,
                ) as ws:
                    self._ws = ws
                    attempt = 0
                    self._last_connect_at = datetime.now(timezone.utc).isoformat()
                    self._last_error = None
                    logger.info("Connected to Polymarket websocket")
                    await self._handle_connection(ws)
            except asyncio.CancelledError:
                raise
            except Exception:
                attempt += 1
                self._reconnect_count += 1
                self._last_error = "Polymarket websocket disconnected"
                wait_seconds = min(
                    self.reconnect_base_seconds * (2 ** max(attempt - 1, 0)),
                    self.reconnect_cap_seconds,
                )
                # Only log full traceback on first disconnect; idle reconnects are expected
                if attempt <= 1:
                    logger.warning(
                        "Polymarket websocket disconnected; reconnecting in %.1fs (attempt %s)",
                        wait_seconds,
                        attempt,
                        exc_info=True,
                    )
                else:
                    logger.info(
                        "Polymarket websocket reconnecting in %.1fs (attempt %s)",
                        wait_seconds,
                        attempt,
                    )
                await self._mark_active_subscriptions_inactive()
                await asyncio.sleep(wait_seconds)
            finally:
                self._ws = None

    async def _handle_connection(self, ws: ClientConnection) -> None:
        self._active_asset_ids.clear()
        await self._resync_tracked_markets_from_rest()
        await self._sync_subscriptions()
        self._subscription_sync_task = asyncio.create_task(
            self._subscription_sync_loop(),
            name="polymarket-websocket-subscription-sync",
        )
        self._ping_task = asyncio.create_task(
            self._ping_loop(),
            name="polymarket-websocket-ping",
        )

        try:
            async for raw_frame in ws:
                await self._handle_raw_frame(raw_frame)
        finally:
            for task in (self._subscription_sync_task, self._ping_task):
                if task:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            self._subscription_sync_task = None
            self._ping_task = None
            await self._mark_active_subscriptions_inactive()

    async def _ping_loop(self) -> None:
        while not self._stop_event.is_set() and self._ws:
            await asyncio.sleep(self.ping_interval_seconds)
            if self._stop_event.is_set() or not self._ws:
                return
            await self._ws.send("PING")

    async def _subscription_sync_loop(self) -> None:
        while not self._stop_event.is_set() and self._ws:
            await asyncio.sleep(self.subscription_sync_seconds)
            if self._stop_event.is_set() or not self._ws:
                return
            await self._sync_subscriptions()

    async def _sync_subscriptions(self) -> None:
        if not self._ws:
            return

        desired_bindings, plan_version = await self._load_tracked_asset_bindings()
        if plan_version == self._last_subscription_plan_version and self._active_asset_ids:
            return
        desired_asset_ids = set(desired_bindings)

        self._asset_bindings = desired_bindings

        for binding in desired_bindings.values():
            await self.live_state.set_asset_mapping(
                AssetMappingLiveState(
                    source=MarketSource.POLYMARKET,
                    asset_id=binding.asset_id,
                    event_id=binding.event_id,
                    market_id=binding.market_id,
                    currency=binding.currency,
                    outcome_side=binding.outcome_side,
                )
            )

        to_unsubscribe = sorted(self._active_asset_ids - desired_asset_ids)
        to_subscribe = sorted(desired_asset_ids - self._active_asset_ids)

        if to_unsubscribe:
            for batch in self._chunk(to_unsubscribe, self.SUBSCRIPTION_BATCH_SIZE):
                payload = {"operation": "unsubscribe", "assets_ids": batch}
                await self._ws.send(json.dumps(payload))
            self._active_asset_ids -= set(to_unsubscribe)

        if to_subscribe:
            initial_dump = len(self._active_asset_ids) == 0
            for batch in self._chunk(to_subscribe, self.SUBSCRIPTION_BATCH_SIZE):
                payload: dict[str, Any] = {
                    "operation": "subscribe" if not initial_dump else None,
                    "assets_ids": batch,
                    "type": "market",
                    "initial_dump": initial_dump,
                    "level": 2,
                    "custom_feature_enabled": True,
                }
                if initial_dump:
                    payload.pop("operation", None)
                await self._ws.send(json.dumps(payload))
                initial_dump = False
            self._active_asset_ids |= set(to_subscribe)

        subscription_count = 0
        for binding in desired_bindings.values():
            await self.live_state.set_subscription_state(
                SubscriptionLiveState(
                    source=MarketSource.POLYMARKET,
                    event_id=binding.event_id,
                    market_id=binding.market_id,
                    channel=f"market:{binding.asset_id}",
                    active=binding.asset_id in self._active_asset_ids,
                )
            )
            subscription_count += 1

        logger.info(
            "Polymarket websocket subscription sync complete assets=%s active=%s",
            len(desired_asset_ids),
            len(self._active_asset_ids),
        )
        self._last_subscription_plan_version = plan_version

    async def _load_tracked_asset_bindings(self) -> tuple[dict[str, AssetBinding], str]:
        cached_plan = await self.live_state.get_subscription_plan(identifier=MarketSource.POLYMARKET.value)
        if cached_plan is not None:
            try:
                plan = PolymarketSubscriptionPlan.model_validate(cached_plan)
                return self._bindings_from_subscription_plan(plan), plan.version
            except Exception:
                logger.warning("Invalid Polymarket subscription plan in Redis; rebuilding", exc_info=True)

        plan = await self._build_subscription_plan_from_db()
        await self.live_state.set_subscription_plan(
            identifier=MarketSource.POLYMARKET.value,
            payload=plan,
        )
        return self._bindings_from_subscription_plan(plan), plan.version

    def _bindings_from_subscription_plan(self, plan: PolymarketSubscriptionPlan) -> dict[str, AssetBinding]:
        bindings: dict[str, AssetBinding] = {}
        for binding in plan.bindings:
            try:
                bindings[binding.asset_id] = AssetBinding(
                    asset_id=binding.asset_id,
                    event_id=binding.event_id,
                    market_id=binding.market_id,
                    currency=Currency(binding.currency),
                    outcome_side=binding.outcome_side,
                )
            except ValueError:
                logger.warning("Skipping unsupported Polymarket binding currency %s", binding.currency)
        return bindings

    async def _build_subscription_plan_from_db(self) -> PolymarketSubscriptionPlan:
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

        bindings: list[PolymarketAssetBindingState] = []
        for market in tracked_markets:
            bindings.append(
                PolymarketAssetBindingState(
                    asset_id=market.yes_outcome_id,
                    event_id=market.event_id,
                    market_id=market.market_id,
                    currency=Currency.DOLLAR.value,
                    outcome_side="YES",
                )
            )
            bindings.append(
                PolymarketAssetBindingState(
                    asset_id=market.no_outcome_id,
                    event_id=market.event_id,
                    market_id=market.market_id,
                    currency=Currency.DOLLAR.value,
                    outcome_side="NO",
                )
            )
        return PolymarketSubscriptionPlan(bindings=bindings)

    async def _handle_raw_frame(self, raw_frame: str) -> None:
        if raw_frame == "PONG":
            return
        try:
            payload = json.loads(raw_frame)
        except json.JSONDecodeError:
            logger.warning("Failed to decode Polymarket websocket frame: %s", raw_frame)
            return

        if isinstance(payload, list):
            for item in payload:
                if not isinstance(item, dict):
                    logger.info("Ignoring unsupported Polymarket websocket list item type %s", type(item).__name__)
                    continue
                await self._handle_message(item)
            return

        if not isinstance(payload, dict):
            logger.info("Ignoring unsupported Polymarket websocket payload type %s", type(payload).__name__)
            return

        await self._handle_message(payload)

    async def _handle_message(self, message: dict[str, Any]) -> None:
        self._last_message_at = datetime.now(timezone.utc).isoformat()
        event_type = message.get("event_type")
        if not event_type:
            logger.info("Ignoring Polymarket websocket frame without event_type")
            return
        if event_type == "book":
            await self._handle_book(message)
            return
        if event_type == "price_change":
            await self._handle_price_change(message)
            return
        if event_type == "last_trade_price":
            await self._handle_last_trade_price(message)
            return
        if event_type == "best_bid_ask":
            await self._handle_best_bid_ask(message)
            return
        if event_type in {"tick_size_change", "new_market", "market_resolved"}:
            logger.info("Received Polymarket lifecycle event %s", event_type)
            return
        logger.info("Ignoring unsupported Polymarket websocket message type %s", event_type)

    async def _handle_book(self, message: dict[str, Any]) -> None:
        asset_id = str(message.get("asset_id") or "")
        if not asset_id:
            return
        self._asset_books[asset_id] = message
        await self._apply_asset_book(asset_id=asset_id, book=message)

    async def _handle_price_change(self, message: dict[str, Any]) -> None:
        for change in message.get("price_changes") or []:
            asset_id = str(change.get("asset_id") or "")
            if not asset_id:
                continue
            current_book = self._asset_books.get(asset_id, {"asset_id": asset_id, "bids": [], "asks": []})
            side = str(change.get("side") or "").upper()
            price = self._to_float(change.get("price"))
            size = self._to_float(change.get("size"))
            if price is None or size is None:
                continue

            key = "bids" if side == "BUY" else "asks"
            current_levels = current_book.get(key) or []
            level_str = f"{price:.6f}".rstrip("0").rstrip(".")
            normalized_levels = [level for level in current_levels if str(level.get("price")) != level_str]
            if size > 0:
                normalized_levels.append({"price": level_str, "size": str(size)})
            normalized_levels.sort(
                key=lambda row: self._to_float(row.get("price")) or 0.0,
                reverse=side == "BUY",
            )
            current_book[key] = normalized_levels
            self._asset_books[asset_id] = current_book
            await self._apply_asset_book(asset_id=asset_id, book=current_book, best_bid=change.get("best_bid"), best_ask=change.get("best_ask"))

    async def _handle_last_trade_price(self, message: dict[str, Any]) -> None:
        asset_id = str(message.get("asset_id") or "")
        binding = await self._get_asset_binding(asset_id)
        if not asset_id or not binding:
            return

        price = self._to_float(message.get("price"))
        size = self._to_float(message.get("size")) or 0.0
        side = str(message.get("side") or "BUY").upper()
        if price is None:
            return

        current = await self.live_state.get_market_state(
            source=MarketSource.POLYMARKET,
            market_id=binding.market_id,
            currency=binding.currency,
        )
        if current is None:
            return

        updates = self._probability_updates_for_asset(
            binding=binding,
            market_state=current,
            asset_price=price,
        )
        await self.live_state.update_market_state(
            source=MarketSource.POLYMARKET,
            market_id=binding.market_id,
            currency=binding.currency,
            ticker_supported=True,
            **updates,
        )
        await self.live_state.increment_trade_flow(
            source=MarketSource.POLYMARKET,
            market_id=binding.market_id,
            currency=binding.currency,
            side=side,
            notional=size * price,
        )
        await self._score_market(market_id=binding.market_id, currency=binding.currency)

    async def _handle_best_bid_ask(self, message: dict[str, Any]) -> None:
        asset_id = str(message.get("asset_id") or "")
        binding = await self._get_asset_binding(asset_id)
        if not asset_id or not binding:
            return

        best_bid = self._to_float(message.get("best_bid"))
        best_ask = self._to_float(message.get("best_ask"))
        if best_bid is None and best_ask is None:
            return
        midpoint = self._midpoint(best_bid, best_ask)
        current = await self.live_state.get_market_state(
            source=MarketSource.POLYMARKET,
            market_id=binding.market_id,
            currency=binding.currency,
        )
        if current is None:
            return

        updates = self._probability_updates_for_asset(
            binding=binding,
            market_state=current,
            asset_price=midpoint,
        )
        updates["spread_bps"] = None if best_bid is None or best_ask is None else max(best_ask - best_bid, 0.0) * 10_000
        updates["ticker_supported"] = True
        updates["orderbook_supported"] = True
        await self.live_state.update_market_state(
            source=MarketSource.POLYMARKET,
            market_id=binding.market_id,
            currency=binding.currency,
            **updates,
        )
        await self._score_market(market_id=binding.market_id, currency=binding.currency)

    async def _apply_asset_book(
        self,
        *,
        asset_id: str,
        book: dict[str, Any],
        best_bid: str | None = None,
        best_ask: str | None = None,
    ) -> None:
        binding = await self._get_asset_binding(asset_id)
        if not binding:
            return

        current = await self.live_state.get_market_state(
            source=MarketSource.POLYMARKET,
            market_id=binding.market_id,
            currency=binding.currency,
        )
        if current is None:
            return

        midpoint = self.clob.midpoint_from_book(book)
        if midpoint is None:
            midpoint = self._midpoint(self._to_float(best_bid), self._to_float(best_ask))

        updates = self._probability_updates_for_asset(
            binding=binding,
            market_state=current,
            asset_price=midpoint,
        )
        if binding.outcome_side == "YES":
            bids = book.get("bids") or []
            asks = book.get("asks") or []
            updates.update(
                {
                    "top_bid_depth": self.clob.level_total(bids[0]) if bids else 0.0,
                    "top_ask_depth": self.clob.level_total(asks[0]) if asks else 0.0,
                    "top_5_bid_depth": sum(self.clob.level_total(level) for level in bids[:5]),
                    "top_5_ask_depth": sum(self.clob.level_total(level) for level in asks[:5]),
                    "spread_bps": self.clob.spread_bps_from_book(book),
                    "orderbook_supported": True,
                    "ticker_supported": True,
                }
            )
        await self.live_state.update_market_state(
            source=MarketSource.POLYMARKET,
            market_id=binding.market_id,
            currency=binding.currency,
            **updates,
        )
        await self._score_market(market_id=binding.market_id, currency=binding.currency)

    async def _score_market(self, *, market_id: str, currency: Currency) -> None:
        market_state = await self.live_state.get_market_state(
            source=MarketSource.POLYMARKET,
            market_id=market_id,
            currency=currency,
        )
        if not market_state:
            return

        previous_signal = await self.live_state.get_signal_state(
            source=MarketSource.POLYMARKET,
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

        if self.baseline_services is None:
            return None
        async with async_session_maker() as session:
            baseline = await self.baseline_services.get_market_baseline(
                session=session,
                market_id=market_id,
                source=MarketSource.POLYMARKET,
            )
        sigma = baseline.volatility_sigma if baseline else None
        self._baseline_cache[cache_key] = sigma
        return sigma

    async def _resync_tracked_markets_from_rest(self) -> None:
        bindings, _ = await self._load_tracked_asset_bindings()
        self._asset_bindings = bindings
        if not bindings:
            return

        async with async_session_maker() as session:
            tracked_markets = (
                await session.exec(
                    select(TrackedMarket).where(
                        TrackedMarket.source == MarketSource.POLYMARKET,
                        TrackedMarket.market_id.in_({binding.market_id for binding in bindings.values()}),
                    )
                )
            ).all()
            event_metrics = (
                await session.exec(
                    select(TrackedEventMetric).where(
                        TrackedEventMetric.source == MarketSource.POLYMARKET,
                        TrackedEventMetric.event_id.in_({market.event_id for market in tracked_markets}),
                    )
                )
            ).all()

        try:
            books = await self.clob.get_books(bindings.keys())
        except Exception:
            logger.warning("Failed to refresh Polymarket books during reconnect resync", exc_info=True)
            books = []
        book_map = {str(book.get("asset_id")): book for book in books if book.get("asset_id")}
        event_metric_map = {metric.event_id: metric for metric in event_metrics}

        event_ids = {market.event_id for market in tracked_markets}
        live_volume_map: dict[str, float | None] = {}
        if self.data_api:
            for event_id in event_ids:
                try:
                    live_volume_map[event_id] = await self.data_api.get_live_volume(event_id)
                except Exception:
                    logger.warning("Failed to fetch Polymarket live volume for event %s", event_id, exc_info=True)
                    live_volume_map[event_id] = None

        for market in tracked_markets:
            try:
                metric = event_metric_map.get(market.event_id)
                live_volume = live_volume_map.get(market.event_id)
                await self.live_state.warm_event_state_from_tracking(
                    tracked_market=market,
                    currency=Currency.DOLLAR,
                    total_liquidity=metric.total_liquidity if metric else None,
                    tracked_markets_count=1,
                )
                await self.live_state.update_event_state(
                    source=MarketSource.POLYMARKET,
                    event_id=market.event_id,
                    currency=Currency.DOLLAR,
                    event_total_orders=int(live_volume) if live_volume is not None else market.event_total_orders,
                )
                await self.live_state.warm_market_state_from_tracking(
                    tracked_market=market,
                    currency=Currency.DOLLAR,
                    total_liquidity=metric.total_liquidity if metric else None,
                )

                yes_book = book_map.get(market.yes_outcome_id)
                no_book = book_map.get(market.no_outcome_id)
                yes_bids = (yes_book or {}).get("bids") or []
                yes_asks = (yes_book or {}).get("asks") or []

                current_probability = self.clob.midpoint_from_book(yes_book)
                inverse_probability = self.clob.midpoint_from_book(no_book)
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
                    event_liquidity=metric.total_liquidity if metric else None,
                    market_total_orders=market.market_total_orders,
                    event_total_orders=int(live_volume) if live_volume is not None else market.event_total_orders,
                    top_bid_depth=self.clob.level_total(yes_bids[0]) if yes_bids else 0.0,
                    top_ask_depth=self.clob.level_total(yes_asks[0]) if yes_asks else 0.0,
                    top_5_bid_depth=sum(self.clob.level_total(level) for level in yes_bids[:5]),
                    top_5_ask_depth=sum(self.clob.level_total(level) for level in yes_asks[:5]),
                    spread_bps=self.clob.spread_bps_from_book(yes_book),
                    orderbook_supported=True,
                    ticker_supported=True,
                )
                await self._score_market(market_id=market.market_id, currency=Currency.DOLLAR)
            except Exception:
                logger.warning(
                    "Failed to resync Polymarket market %s for event %s during reconnect",
                    market.market_id,
                    market.event_id,
                    exc_info=True,
                )

    async def _mark_active_subscriptions_inactive(self) -> None:
        for asset_id, binding in list(self._asset_bindings.items()):
            await self.live_state.set_subscription_state(
                SubscriptionLiveState(
                    source=MarketSource.POLYMARKET,
                    event_id=binding.event_id,
                    market_id=binding.market_id,
                    channel=f"market:{asset_id}",
                    active=False,
                )
            )
        self._active_asset_ids.clear()

    async def _get_asset_binding(self, asset_id: str) -> AssetBinding | None:
        binding = self._asset_bindings.get(asset_id)
        if binding:
            return binding
        mapping = await self.live_state.get_asset_mapping(
            source=MarketSource.POLYMARKET,
            asset_id=asset_id,
        )
        if not mapping:
            return None
        return AssetBinding(
            asset_id=mapping.asset_id,
            event_id=mapping.event_id,
            market_id=mapping.market_id,
            currency=mapping.currency,
            outcome_side=mapping.outcome_side,
        )

    def _probability_updates_for_asset(
        self,
        *,
        binding: AssetBinding,
        market_state: MarketLiveState,
        asset_price: float | None,
    ) -> dict[str, Any]:
        if asset_price is None:
            return {}
        if binding.outcome_side == "YES":
            inverse = market_state.inverse_probability
            if inverse is None:
                inverse = 1 - asset_price
            return {
                "current_probability": asset_price,
                "inverse_probability": inverse,
            }
        current = market_state.current_probability
        if current is None:
            current = 1 - asset_price
        return {
            "current_probability": current,
            "inverse_probability": asset_price,
        }

    def _determine_snapshot_reason(self, *, previous_signal, market_state: MarketLiveState, score_result) -> str | None:
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
            "subscription_sync_running": bool(self._subscription_sync_task and not self._subscription_sync_task.done()),
            "ping_loop_running": bool(self._ping_task and not self._ping_task.done()),
            "active_asset_count": len(self._active_asset_ids),
            "bound_asset_count": len(self._asset_bindings),
            "last_connect_at": self._last_connect_at,
            "last_message_at": self._last_message_at,
            "reconnect_count": self._reconnect_count,
            "last_error": self._last_error,
            "baseline_cache_size": len(self._baseline_cache),
        }

    def reset_baseline_cache(self) -> None:
        self._baseline_cache.clear()

    def _chunk(self, values: list[str], size: int) -> list[list[str]]:
        return [values[index : index + size] for index in range(0, len(values), size)]

    def _to_float(self, value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _midpoint(self, best_bid: float | None, best_ask: float | None) -> float | None:
        if best_bid is not None and best_ask is not None:
            return (best_bid + best_ask) / 2
        if best_bid is not None:
            return best_bid
        if best_ask is not None:
            return best_ask
        return None
