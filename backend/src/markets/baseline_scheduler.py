import asyncio

from sqlalchemy import false, or_
from sqlmodel import select

from src.db.main import async_session_maker
from src.markets.baselines import BaselineServices
from src.markets.models import MarketSource, TrackedMarket, UserTrackedEvent
from src.utils.logger import logger


class BaselineRefreshScheduler:
    def __init__(
        self,
        *,
        baseline_services: BaselineServices,
        interval_seconds: int = 1800,
        initial_delay_seconds: int = 60,
        on_refresh=None,
    ):
        self.baseline_services = baseline_services
        self.interval_seconds = interval_seconds
        self.initial_delay_seconds = initial_delay_seconds
        self.on_refresh = on_refresh
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self.run(), name="baseline-refresh-scheduler")
        logger.info("Baseline refresh scheduler started")

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Baseline refresh scheduler stopped")

    async def run(self) -> None:
        if self.initial_delay_seconds > 0:
            await asyncio.sleep(self.initial_delay_seconds)
        while not self._stop_event.is_set():
            try:
                refreshed = await self.refresh_all_tracked_events()
                if refreshed and self.on_refresh:
                    try:
                        result = self.on_refresh()
                        if asyncio.iscoroutine(result):
                            await result
                    except Exception:
                        logger.warning("Baseline refresh callback failed", exc_info=True)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.warning("Periodic baseline refresh failed", exc_info=True)
            await asyncio.sleep(self.interval_seconds)

    async def refresh_all_tracked_events(self) -> int:
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
            tracked_market_rows = (
                await session.exec(
                    select(TrackedMarket.event_id, TrackedMarket.source)
                    .where(
                        TrackedMarket.tracking_enabled == True,
                        or_(
                            TrackedMarket.is_system_tracked == True,
                            tracked_event_filter,
                        ),
                    )
                    .distinct()
                )
            ).all()

            refreshed = 0
            for event_id, source in tracked_market_rows:
                try:
                    await self.baseline_services.refresh_event_baselines(
                        session=session,
                        event_id=event_id,
                        source=source if isinstance(source, MarketSource) else MarketSource(str(source)),
                    )
                    refreshed += 1
                except Exception:
                    logger.warning("Failed refreshing baselines for event %s source %s", event_id, source, exc_info=True)
            if refreshed:
                logger.info("Refreshed baselines for %s tracked events", refreshed)
            return refreshed
