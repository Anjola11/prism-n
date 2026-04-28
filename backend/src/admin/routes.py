from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlmodel.ext.asyncio.session import AsyncSession

from src.admin.schemas import AdminLoginInput
from src.admin.services import AdminServices
from src.auth.services import AuthServices
from src.db.main import get_session
from src.markets.models import Currency, MarketSource
from src.markets.services import MarketServices
from src.markets.routes import get_market_services
from src.markets.schemas import SuccessResponse
from src.utils.dependencies import get_admin_user, get_admin_user_id
from src.utils.logger import logger
from src.utils.responses import success_response


admin_router = APIRouter()


def _build_paginated_payload(items: list, *, page: int, limit: int, total: int | None = None) -> dict:
    if total is None:
        total = len(items)
        start = (page - 1) * limit
        end = start + limit
        paginated_items = items[start:end]
    else:
        paginated_items = items
        end = page * limit
    return {
        "items": paginated_items,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "has_more": end < total,
        },
    }


def get_admin_services(
    market_services: MarketServices = Depends(get_market_services),
) -> AdminServices:
    return AdminServices(
        auth_services=AuthServices(),
        market_services=market_services,
    )


@admin_router.post(
    "/login",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
)
async def admin_login(
    login_input: AdminLoginInput,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
    admin_services: AdminServices = Depends(get_admin_services),
):
    logger.info("Admin login attempt for email: %s", login_input.email)
    result = await admin_services.login_admin(
        login_input=login_input,
        session=session,
        response=response,
        request=request,
    )
    return success_response(
        message="Admin login successful",
        data=result,
    )


@admin_router.get(
    "/me",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
)
async def admin_me(
    current_admin=Depends(get_admin_user),
):
    return success_response(
        message="Admin details fetched successfully",
        data={
            "uid": str(current_admin.uid),
            "email": current_admin.email,
            "email_verified": current_admin.email_verified,
            "role": current_admin.role,
        },
    )


@admin_router.get(
    "/overview",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
)
async def admin_overview(
    request: Request,
    currency: Currency = Currency.DOLLAR,
    session: AsyncSession = Depends(get_session),
    admin_services: AdminServices = Depends(get_admin_services),
    admin_user_id=Depends(get_admin_user_id),
):
    logger.info("Admin overview requested by %s in %s", admin_user_id, currency.value)
    result = await admin_services.get_admin_overview(
        session=session,
        currency=currency,
        websocket_status={
            "bayse": request.app.state.bayse_ws_manager.get_status(),
            "polymarket": request.app.state.polymarket_ws_manager.get_status(),
        },
        background_jobs={
            "baseline_scheduler_running": bool(
                request.app.state.baseline_scheduler._task and not request.app.state.baseline_scheduler._task.done()
            ),
            "discovery_worker_running": bool(
                request.app.state.discovery_worker._task and not request.app.state.discovery_worker._task.done()
            ),
        },
    )
    return success_response(
        message="Admin overview fetched successfully",
        data=result.model_dump(),
    )


@admin_router.get(
    "/discovery",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
)
async def admin_discovery(
    source: MarketSource | None = None,
    currency: Currency = Currency.DOLLAR,
    category: str | None = None,
    sort_by: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    market_services: MarketServices = Depends(get_market_services),
    admin_user_id=Depends(get_admin_user_id),
):
    logger.info("Admin discovery requested by %s in %s", admin_user_id, currency.value)
    result, total_count = await market_services.get_discovery_feed_for_system(
        session=session,
        source=source,
        currency=currency,
        category=category,
        sort_by=sort_by,
        page=page,
        limit=limit,
    )
    return success_response(
        message="Admin discovery fetched successfully",
        data=_build_paginated_payload(
            [item.model_dump() for item in result],
            page=page,
            limit=limit,
            total=total_count,
        ),
    )


@admin_router.get(
    "/events/{event_id}/score-history",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
)
async def admin_event_score_history(
    event_id: str,
    source: MarketSource = MarketSource.BAYSE,
    currency: Currency = Currency.DOLLAR,
    market_id: str | None = None,
    hours: int = Query(default=48, ge=1, le=168),
    session: AsyncSession = Depends(get_session),
    market_services: MarketServices = Depends(get_market_services),
    admin_user_id=Depends(get_admin_user_id),
):
    logger.info(
        "Admin score history requested by %s for event %s market %s window=%sh",
        admin_user_id,
        event_id,
        market_id or "top",
        hours,
    )
    result = await market_services.get_score_history_for_market(
        session=session,
        event_id=event_id,
        source=source,
        currency=currency,
        market_id=market_id,
        hours=hours,
    )
    return success_response(
        message="Admin score history fetched successfully",
        data=result.model_dump(mode="json"),
    )


@admin_router.get(
    "/system-tracker",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
)
async def admin_system_tracker(
    currency: Currency = Currency.DOLLAR,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    market_services: MarketServices = Depends(get_market_services),
    admin_user_id=Depends(get_admin_user_id),
):
    logger.info("Admin system tracker requested by %s in %s", admin_user_id, currency.value)
    result = await market_services.list_system_tracked_events(
        session=session,
        currency=currency,
    )
    return success_response(
        message="System tracked events fetched successfully",
        data=_build_paginated_payload(
            [item.model_dump() for item in result],
            page=page,
            limit=limit,
        ),
    )


@admin_router.get(
    "/analytics",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
)
async def admin_analytics(
    session: AsyncSession = Depends(get_session),
    admin_services: AdminServices = Depends(get_admin_services),
    admin_user_id=Depends(get_admin_user_id),
):
    logger.info("Admin analytics requested by %s", admin_user_id)
    result = await admin_services.get_admin_analytics(session=session)
    return success_response(
        message="Admin analytics fetched successfully",
        data=result.model_dump(),
    )


@admin_router.get(
    "/system-status",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
)
async def admin_system_status(
    request: Request,
    admin_services: AdminServices = Depends(get_admin_services),
    admin_user_id=Depends(get_admin_user_id),
):
    logger.info("Admin system status requested by %s", admin_user_id)
    result = await admin_services.get_system_status(
        websocket_status={
            "bayse": request.app.state.bayse_ws_manager.get_status(),
            "polymarket": request.app.state.polymarket_ws_manager.get_status(),
        },
        background_jobs={
            "baseline_scheduler_running": bool(
                request.app.state.baseline_scheduler._task and not request.app.state.baseline_scheduler._task.done()
            ),
            "discovery_worker_running": bool(
                request.app.state.discovery_worker._task and not request.app.state.discovery_worker._task.done()
            ),
        },
    )
    return success_response(
        message="Admin system status fetched successfully",
        data=result.model_dump(),
    )


@admin_router.post(
    "/system-track/{event_id}",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
)
async def admin_track_for_system(
    event_id: str,
    source: MarketSource = MarketSource.BAYSE,
    currency: Currency = Currency.DOLLAR,
    session: AsyncSession = Depends(get_session),
    admin_services: AdminServices = Depends(get_admin_services),
    admin_user_id=Depends(get_admin_user_id),
):
    logger.info("Admin %s system-tracking event %s in %s", admin_user_id, event_id, currency.value)
    result = await admin_services.track_event_for_system(
        session=session,
        admin_user_id=admin_user_id,
        event_id=event_id,
        source=source,
        currency=currency,
    )
    return success_response(
        message="Event added to system tracking successfully",
        data=result,
    )


@admin_router.delete(
    "/system-track/{event_id}",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
)
async def admin_untrack_for_system(
    event_id: str,
    source: MarketSource = MarketSource.BAYSE,
    currency: Currency = Currency.DOLLAR,
    session: AsyncSession = Depends(get_session),
    admin_services: AdminServices = Depends(get_admin_services),
    admin_user_id=Depends(get_admin_user_id),
):
    logger.info("Admin %s removing system tracking for event %s in %s", admin_user_id, event_id, currency.value)
    result = await admin_services.untrack_event_for_system(
        session=session,
        admin_user_id=admin_user_id,
        event_id=event_id,
        source=source,
        currency=currency,
    )
    return success_response(
        message="Event removed from system tracking successfully",
        data=result,
    )


@admin_router.get(
    "/audit-logs",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
)
async def admin_audit_logs(
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
    admin_services: AdminServices = Depends(get_admin_services),
    admin_user_id=Depends(get_admin_user_id),
):
    logger.info("Admin audit logs requested by %s", admin_user_id)
    result = await admin_services.list_admin_action_logs(
        session=session,
        limit=limit,
    )
    return success_response(
        message="Admin audit logs fetched successfully",
        data=[item.model_dump() for item in result],
    )
