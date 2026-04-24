from sqlmodel.ext.asyncio.session import AsyncSession

from src.markets.live_state import MarketLiveState
from src.markets.models import MarketSignalSnapshot
from src.markets.scoring import MarketScoreResult
from src.utils.logger import logger


class SignalSnapshotServices:
    async def persist_snapshot(
        self,
        *,
        session: AsyncSession,
        market_state: MarketLiveState,
        score_result: MarketScoreResult,
        snapshot_reason: str,
    ) -> MarketSignalSnapshot:
        previous_probability = market_state.previous_probability
        current_probability = market_state.current_probability
        probability_delta = None
        if previous_probability is not None and current_probability is not None:
            probability_delta = current_probability - previous_probability

        snapshot = MarketSignalSnapshot(
            source=market_state.source,
            event_id=market_state.event_id,
            market_id=market_state.market_id,
            currency=market_state.currency,
            score=score_result.score,
            classification=score_result.classification,
            formula=score_result.formula,
            factors=score_result.factors.model_dump(),
            notes=score_result.notes,
            current_probability=current_probability,
            previous_probability=previous_probability,
            probability_delta=probability_delta,
            event_liquidity=market_state.event_liquidity,
            market_total_orders=market_state.market_total_orders,
            event_total_orders=market_state.event_total_orders,
            buy_notional=market_state.buy_notional,
            sell_notional=market_state.sell_notional,
            persistence_ticks=market_state.persistence_ticks,
            snapshot_reason=snapshot_reason,
        )
        session.add(snapshot)
        await session.commit()
        logger.info(
            "Persisted signal snapshot for market %s score=%s reason=%s",
            market_state.market_id,
            score_result.score,
            snapshot_reason,
        )
        return snapshot
