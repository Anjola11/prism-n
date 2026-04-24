from datetime import datetime, timezone
from math import sqrt
from statistics import mean

from pydantic import BaseModel, Field
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.markets.models import MarketBaseline, MarketSource
from src.utils.bayse import BayseServices, HistoryWindow, Outcome
from src.utils.logger import logger
from src.utils.polymarket_clob import ClobInterval, PolymarketCLOBServices


class PricePoint(BaseModel):
    timestamp_ms: int
    price: float


class MarketBaselineSnapshot(BaseModel):
    source: MarketSource
    event_id: str
    market_id: str
    window: str
    outcome: str
    sample_count: int = 0
    first_price: float | None = None
    previous_interval_price: float | None = None
    last_price: float | None = None
    absolute_move: float | None = None
    mean_return: float | None = None
    volatility_sigma: float | None = None
    max_absolute_return: float | None = None
    computed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BaselineServices:
    def __init__(
        self,
        bayse: BayseServices | None = None,
        polymarket_clob: PolymarketCLOBServices | None = None,
    ):
        self.bayse = bayse
        self.polymarket_clob = polymarket_clob

    async def refresh_event_baselines(
        self,
        *,
        session: AsyncSession,
        event_id: str,
        window: HistoryWindow = HistoryWindow.WEEK_1,
        outcome: Outcome = Outcome.YES,
        source: MarketSource = MarketSource.BAYSE,
    ) -> list[MarketBaselineSnapshot]:
        if source == MarketSource.POLYMARKET:
            return await self._refresh_polymarket_event_baselines(
                session=session,
                event_id=event_id,
                window=window,
                outcome=outcome,
            )

        if self.bayse is None:
            raise RuntimeError("Bayse baseline service is not configured")

        logger.info(
            "Refreshing baselines for event %s source %s window %s outcome %s",
            event_id,
            source.value,
            window.value,
            outcome.value,
        )
        history_payload = await self.bayse.get_price_history(
            event_id=event_id,
            window=window,
            outcome=outcome,
        )

        snapshots: list[MarketBaselineSnapshot] = []
        for market_payload in history_payload.get("markets", []):
            snapshot = self.compute_market_baseline(
                event_id=event_id,
                market_payload=market_payload,
                window=window,
                outcome=outcome,
                source=source,
            )
            await self._upsert_market_baseline(session=session, snapshot=snapshot)
            snapshots.append(snapshot)

        await session.commit()
        logger.info("Refreshed %s market baselines for event %s", len(snapshots), event_id)
        return snapshots

    async def _refresh_polymarket_event_baselines(
        self,
        *,
        session: AsyncSession,
        event_id: str,
        window: HistoryWindow,
        outcome: Outcome,
    ) -> list[MarketBaselineSnapshot]:
        if self.polymarket_clob is None:
            raise RuntimeError("Polymarket CLOB service is not configured")

        logger.info(
            "Refreshing Polymarket baselines for event %s window %s outcome %s",
            event_id,
            window.value,
            outcome.value,
        )
        from src.markets.models import TrackedMarket  # local import to avoid circular import at module load

        tracked_polymarket_markets = (
            await session.exec(
                select(TrackedMarket).where(
                    TrackedMarket.event_id == event_id,
                    TrackedMarket.source == MarketSource.POLYMARKET,
                    TrackedMarket.tracking_enabled == True,
                )
            )
        ).all()
        if not tracked_polymarket_markets:
            return []

        asset_ids = [market.yes_outcome_id for market in tracked_polymarket_markets if market.yes_outcome_id]
        history_by_asset = await self.polymarket_clob.get_batch_prices_history(
            asset_ids=asset_ids,
            interval=self._map_clob_interval(window),
            fidelity=5,
        )

        snapshots: list[MarketBaselineSnapshot] = []
        for market in tracked_polymarket_markets:
            history_payload = history_by_asset.get(market.yes_outcome_id) or {}
            snapshot = self.compute_polymarket_market_baseline(
                event_id=event_id,
                market_id=market.market_id,
                asset_id=market.yes_outcome_id,
                history_payload=history_payload,
                window=window,
                outcome=outcome,
            )
            await self._upsert_market_baseline(session=session, snapshot=snapshot)
            snapshots.append(snapshot)

        await session.commit()
        logger.info("Refreshed %s Polymarket market baselines for event %s", len(snapshots), event_id)
        return snapshots

    def compute_market_baseline(
        self,
        *,
        event_id: str,
        market_payload: dict,
        window: HistoryWindow = HistoryWindow.WEEK_1,
        outcome: Outcome = Outcome.YES,
        source: MarketSource = MarketSource.BAYSE,
    ) -> MarketBaselineSnapshot:
        price_points = self._extract_price_points(market_payload)
        returns = self._compute_returns(price_points)

        first_price = price_points[0].price if price_points else None
        last_price = price_points[-1].price if price_points else None
        previous_interval = market_payload.get("lastPriceAtPreviousInterval") or {}
        previous_price = previous_interval.get("p")

        absolute_move = None
        if first_price is not None and last_price is not None:
            absolute_move = last_price - first_price

        snapshot = MarketBaselineSnapshot(
            source=source,
            event_id=event_id,
            market_id=str(market_payload["marketId"]),
            window=window.value,
            outcome=outcome.value,
            sample_count=len(price_points),
            first_price=first_price,
            previous_interval_price=previous_price,
            last_price=last_price,
            absolute_move=absolute_move,
            mean_return=mean(returns) if returns else 0.0,
            volatility_sigma=self._compute_sigma(returns),
            max_absolute_return=max((abs(value) for value in returns), default=0.0),
        )
        return snapshot

    def compute_polymarket_market_baseline(
        self,
        *,
        event_id: str,
        market_id: str,
        asset_id: str,
        history_payload: dict,
        window: HistoryWindow = HistoryWindow.WEEK_1,
        outcome: Outcome = Outcome.YES,
    ) -> MarketBaselineSnapshot:
        price_points = self._extract_polymarket_price_points(history_payload)
        returns = self._compute_returns(price_points)

        first_price = price_points[0].price if price_points else None
        last_price = price_points[-1].price if price_points else None
        previous_price = price_points[-2].price if len(price_points) > 1 else first_price

        absolute_move = None
        if first_price is not None and last_price is not None:
            absolute_move = last_price - first_price

        return MarketBaselineSnapshot(
            source=MarketSource.POLYMARKET,
            event_id=event_id,
            market_id=market_id,
            window=window.value,
            outcome=outcome.value,
            sample_count=len(price_points),
            first_price=first_price,
            previous_interval_price=previous_price,
            last_price=last_price,
            absolute_move=absolute_move,
            mean_return=mean(returns) if returns else 0.0,
            volatility_sigma=self._compute_sigma(returns),
            max_absolute_return=max((abs(value) for value in returns), default=0.0),
        )

    async def get_market_baseline(
        self,
        *,
        session: AsyncSession,
        market_id: str,
        window: HistoryWindow = HistoryWindow.WEEK_1,
        outcome: Outcome = Outcome.YES,
        source: MarketSource = MarketSource.BAYSE,
    ) -> MarketBaseline | None:
        statement = select(MarketBaseline).where(
            MarketBaseline.market_id == market_id,
            MarketBaseline.source == source,
            MarketBaseline.window == window.value,
            MarketBaseline.outcome == outcome.value,
        )
        result = await session.exec(statement)
        return result.first()

    def _extract_price_points(self, market_payload: dict) -> list[PricePoint]:
        points: list[PricePoint] = []
        for entry in market_payload.get("priceHistory", []):
            price = entry.get("p")
            timestamp = entry.get("e")
            if price is None or timestamp is None:
                continue
            points.append(PricePoint(timestamp_ms=int(timestamp), price=float(price)))
        return points

    def _extract_polymarket_price_points(self, history_payload: dict) -> list[PricePoint]:
        points: list[PricePoint] = []
        for entry in history_payload.get("history", []):
            timestamp = entry.get("t")
            price = entry.get("p")
            if timestamp is None or price is None:
                continue
            points.append(PricePoint(timestamp_ms=int(timestamp), price=float(price)))
        return points

    def _compute_returns(self, points: list[PricePoint]) -> list[float]:
        if len(points) < 2:
            return []

        returns: list[float] = []
        previous_price = points[0].price
        for point in points[1:]:
            current_price = point.price
            returns.append(current_price - previous_price)
            previous_price = current_price
        return returns

    def _compute_sigma(self, returns: list[float]) -> float:
        if not returns:
            return 0.0
        mean_return = mean(returns)
        variance = sum((value - mean_return) ** 2 for value in returns) / len(returns)
        return sqrt(variance)

    async def _upsert_market_baseline(
        self,
        *,
        session: AsyncSession,
        snapshot: MarketBaselineSnapshot,
    ) -> MarketBaseline:
        statement = select(MarketBaseline).where(
            MarketBaseline.source == snapshot.source,
            MarketBaseline.event_id == snapshot.event_id,
            MarketBaseline.market_id == snapshot.market_id,
            MarketBaseline.window == snapshot.window,
            MarketBaseline.outcome == snapshot.outcome,
        )
        result = await session.exec(statement)
        existing = result.first()

        payload = snapshot.model_dump()
        payload["updated_at"] = datetime.now(timezone.utc)

        if existing:
            for key, value in payload.items():
                setattr(existing, key, value)
            session.add(existing)
            return existing

        baseline = MarketBaseline(**payload)
        session.add(baseline)
        return baseline

    def _map_clob_interval(self, window: HistoryWindow) -> ClobInterval:
        mapping = {
            HistoryWindow.WEEK_1: ClobInterval.WEEK_1,
            HistoryWindow.HOURS_24: ClobInterval.DAY_1,
            HistoryWindow.HOURS_12: ClobInterval.HOUR_6,
            HistoryWindow.MONTH_1: ClobInterval.WEEK_1,
            HistoryWindow.YEAR_1: ClobInterval.MAX,
        }
        return mapping.get(window, ClobInterval.WEEK_1)
