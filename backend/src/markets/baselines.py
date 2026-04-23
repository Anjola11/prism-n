from datetime import datetime, timezone
from math import sqrt
from statistics import mean

from pydantic import BaseModel, Field
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.markets.models import MarketBaseline, MarketSource
from src.utils.bayse import BayseServices, HistoryWindow, Outcome
from src.utils.logger import logger


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
    def __init__(self, bayse: BayseServices):
        self.bayse = bayse

    async def refresh_event_baselines(
        self,
        *,
        session: AsyncSession,
        event_id: str,
        window: HistoryWindow = HistoryWindow.WEEK_1,
        outcome: Outcome = Outcome.YES,
        source: MarketSource = MarketSource.BAYSE,
    ) -> list[MarketBaselineSnapshot]:
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
