import asyncio

from fastapi import HTTPException, Request, Response, status
from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.admin.schemas import (
    AdminActionLogRead,
    AdminAnalyticsRead,
    AdminLoginInput,
    AdminOverviewRead,
    AdminSystemStatusRead,
    MostTrackedEventRead,
)
from src.admin.models import AdminActionLog
from src.auth.models import User, UserRole
from src.auth.services import AuthServices
from src.db.redis import redis_client
from src.markets.models import Currency, MarketSignalSnapshot, MarketSource, TrackedMarket, UserTrackedEvent
from src.markets.services import MarketServices
from src.utils.logger import logger


class AdminServices:
    ANALYTICS_CACHE_TTL = 60
    OVERVIEW_CACHE_TTL = 20

    def __init__(self, *, auth_services: AuthServices, market_services: MarketServices):
        self.auth_services = auth_services
        self.market_services = market_services

    def _analytics_cache_id(self) -> str:
        return "admin-analytics"

    def _overview_cache_id(self, *, currency: Currency) -> str:
        return f"admin-overview:{currency.value}"

    async def _get_cached_analytics(self) -> AdminAnalyticsRead | None:
        if not self.market_services.live_state:
            return None
        payload = await self.market_services.live_state.get_read_model(
            namespace="admin-analytics",
            identifier=self._analytics_cache_id(),
        )
        if not payload:
            return None
        return AdminAnalyticsRead.model_validate(payload)

    async def _set_cached_analytics(self, analytics: AdminAnalyticsRead) -> None:
        if not self.market_services.live_state:
            return
        await self.market_services.live_state.set_read_model(
            namespace="admin-analytics",
            identifier=self._analytics_cache_id(),
            payload=analytics.model_dump(mode="json"),
            ttl_seconds=self.ANALYTICS_CACHE_TTL,
        )

    async def _get_cached_overview(self, *, currency: Currency) -> AdminOverviewRead | None:
        if not self.market_services.live_state:
            return None
        payload = await self.market_services.live_state.get_read_model(
            namespace="admin-overview",
            identifier=self._overview_cache_id(currency=currency),
        )
        if not payload:
            return None
        return AdminOverviewRead.model_validate(payload)

    async def _set_cached_overview(self, *, currency: Currency, overview: AdminOverviewRead) -> None:
        if not self.market_services.live_state:
            return
        await self.market_services.live_state.set_read_model(
            namespace="admin-overview",
            identifier=self._overview_cache_id(currency=currency),
            payload=overview.model_dump(mode="json"),
            ttl_seconds=self.OVERVIEW_CACHE_TTL,
        )

    async def _invalidate_admin_caches(self, *, currency: Currency | None = None) -> None:
        if not self.market_services.live_state:
            return
        await self.market_services.live_state.delete_read_model(
            namespace="admin-analytics",
            identifier=self._analytics_cache_id(),
        )
        if currency is not None:
            await self.market_services.live_state.delete_read_model(
                namespace="admin-overview",
                identifier=self._overview_cache_id(currency=currency),
            )

    async def login_admin(
        self,
        *,
        login_input: AdminLoginInput,
        session: AsyncSession,
        response: Response,
        request: Request,
    ) -> dict:
        return await self.auth_services.login_user(
            login_input,
            session,
            response,
            request=request,
            required_role=UserRole.ADMIN.value,
        )

    async def get_admin_overview(
        self,
        *,
        session: AsyncSession,
        currency: Currency,
        websocket_status: dict,
        background_jobs: dict | None = None,
    ) -> AdminOverviewRead:
        cached_overview = await self._get_cached_overview(currency=currency)
        if cached_overview is not None:
            cached_overview.system_status = (
                await self.get_system_status(
                    websocket_status=websocket_status,
                    background_jobs=background_jobs,
                )
            ).model_dump()
            return cached_overview

        analytics, system_status, system_tracked_events = await asyncio.gather(
            self.get_admin_analytics(session=session),
            self.get_system_status(
                websocket_status=websocket_status,
                background_jobs=background_jobs,
            ),
            self.market_services.list_system_tracked_events(
                session=session,
                currency=currency,
            ),
        )

        overview = AdminOverviewRead(
            total_users=analytics.total_users,
            verified_users=analytics.verified_users,
            admin_users=analytics.admin_users,
            total_user_tracked_events=analytics.total_user_tracked_events,
            total_user_event_links=analytics.total_user_event_links,
            total_system_tracked_events=analytics.total_system_tracked_events,
            total_system_tracked_markets=analytics.total_system_tracked_markets,
            recent_signal_snapshot_count=analytics.recent_signal_snapshot_count,
            most_tracked_events=analytics.most_tracked_events,
            system_tracked_events=system_tracked_events,
            system_status=system_status.model_dump(),
        )
        await self._set_cached_overview(currency=currency, overview=overview)
        return overview

    async def get_admin_analytics(
        self,
        *,
        session: AsyncSession,
    ) -> AdminAnalyticsRead:
        cached_analytics = await self._get_cached_analytics()
        if cached_analytics is not None:
            return cached_analytics

        total_users = (await session.exec(select(func.count()).select_from(User))).one()
        verified_users = (
            await session.exec(
                select(func.count()).select_from(User).where(User.email_verified == True)
            )
        ).one()
        admin_users = (
            await session.exec(
                select(func.count()).select_from(User).where(User.role == UserRole.ADMIN)
            )
        ).one()
        total_user_event_links = (
            await session.exec(
                select(func.count()).select_from(UserTrackedEvent).where(UserTrackedEvent.tracking_enabled == True)
            )
        ).one()

        tracked_event_rows = (
            await session.exec(
                select(UserTrackedEvent.event_id, func.count(UserTrackedEvent.id))
                .where(UserTrackedEvent.tracking_enabled == True)
                .group_by(UserTrackedEvent.event_id)
            )
        ).all()
        total_user_tracked_events = (
            await session.exec(
                select(func.count(func.distinct(UserTrackedEvent.event_id))).where(
                    UserTrackedEvent.tracking_enabled == True
                )
            )
        ).one()

        total_system_tracked_markets = (
            await session.exec(
                select(func.count()).select_from(TrackedMarket).where(
                    TrackedMarket.is_system_tracked == True,
                    TrackedMarket.tracking_enabled == True,
                )
            )
        ).one()

        total_system_tracked_events = (
            await session.exec(
                select(func.count(func.distinct(TrackedMarket.event_id))).where(
                    TrackedMarket.is_system_tracked == True,
                    TrackedMarket.tracking_enabled == True,
                )
            )
        ).one()

        recent_signal_snapshot_count = (
            await session.exec(select(func.count()).select_from(MarketSignalSnapshot))
        ).one()

        event_meta = {}
        if tracked_event_rows:
            event_ids = [event_id for event_id, _ in tracked_event_rows]
            tracked_market_rows = (
                await session.exec(select(TrackedMarket).where(TrackedMarket.event_id.in_(event_ids)))
            ).all()
            for market in tracked_market_rows:
                if market.event_id not in event_meta:
                    event_meta[market.event_id] = {
                        "title": market.event_title,
                        "slug": market.event_slug,
                        "market_count": 0,
                        "system_tracked": False,
                    }
                event_meta[market.event_id]["market_count"] += 1
                if market.is_system_tracked:
                    event_meta[market.event_id]["system_tracked"] = True

        most_tracked_events = []
        for event_id, tracker_count in sorted(tracked_event_rows, key=lambda item: item[1], reverse=True)[:10]:
            meta = event_meta.get(event_id, {})
            most_tracked_events.append(
                MostTrackedEventRead(
                    event_id=event_id,
                    event_title=meta.get("title", event_id),
                    event_slug=meta.get("slug"),
                    tracker_count=tracker_count,
                    market_count=meta.get("market_count", 0),
                    system_tracked=meta.get("system_tracked", False),
                )
            )

        analytics = AdminAnalyticsRead(
            total_users=total_users,
            verified_users=verified_users,
            admin_users=admin_users,
            total_user_tracked_events=total_user_tracked_events,
            total_user_event_links=total_user_event_links,
            total_system_tracked_events=total_system_tracked_events,
            total_system_tracked_markets=total_system_tracked_markets,
            recent_signal_snapshot_count=recent_signal_snapshot_count,
            most_tracked_events=most_tracked_events,
        )
        await self._set_cached_analytics(analytics)
        return analytics

    async def get_system_status(
        self,
        *,
        websocket_status: dict,
        background_jobs: dict | None = None,
    ) -> AdminSystemStatusRead:
        return AdminSystemStatusRead(
            redis_ok=await self._redis_ok(),
            websocket=websocket_status,
            background_jobs=background_jobs or {},
        )

    async def track_event_for_system(
        self,
        *,
        session: AsyncSession,
        admin_user_id,
        event_id: str,
        source: MarketSource,
        currency: Currency,
    ) -> dict:
        result = await self.market_services.track_event_for_system(
            session=session,
            event_id=event_id,
            source=source,
            currency=currency,
        )
        await self._log_admin_action(
            session=session,
            admin_user_id=admin_user_id,
            action="system_track_event",
            event_id=event_id,
            currency=currency,
            details={
                "tracked_markets_count": result.tracked_markets_count,
                "event_title": result.event_title,
                "source": source.value,
            },
        )
        await self._invalidate_admin_caches(currency=currency)
        return result.model_dump()

    async def untrack_event_for_system(
        self,
        *,
        session: AsyncSession,
        admin_user_id,
        event_id: str,
        source: MarketSource,
        currency: Currency,
    ) -> dict:
        result = await self.market_services.untrack_event_for_system(
            session=session,
            event_id=event_id,
            source=source,
            currency=currency,
        )
        await self._log_admin_action(
            session=session,
            admin_user_id=admin_user_id,
            action="system_untrack_event",
            event_id=event_id,
            currency=currency,
            details={
                "tracked_markets_count": result.tracked_markets_count,
                "event_title": result.event_title,
                "source": source.value,
            },
        )
        await self._invalidate_admin_caches(currency=currency)
        return result.model_dump()

    async def list_admin_action_logs(
        self,
        *,
        session: AsyncSession,
        limit: int = 50,
    ) -> list[AdminActionLogRead]:
        logs = (
            await session.exec(
                select(AdminActionLog).order_by(AdminActionLog.created_at.desc()).limit(limit)
            )
        ).all()
        return [
            AdminActionLogRead(
                id=str(log.id),
                admin_user_id=str(log.admin_user_id),
                action=log.action,
                event_id=log.event_id,
                currency=log.currency.value if log.currency else None,
                details=log.details,
                created_at=log.created_at.isoformat(),
            )
            for log in logs
        ]

    async def _log_admin_action(
        self,
        *,
        session: AsyncSession,
        admin_user_id,
        action: str,
        event_id: str | None,
        currency: Currency | None,
        details: dict | None = None,
    ) -> None:
        session.add(
            AdminActionLog(
                admin_user_id=admin_user_id,
                action=action,
                event_id=event_id,
                currency=currency,
                details=details,
            )
        )
        await session.commit()

    async def _redis_ok(self) -> bool:
        try:
            return bool(await redis_client.ping())
        except Exception:
            logger.warning("Redis ping failed during admin overview check", exc_info=True)
            return False
