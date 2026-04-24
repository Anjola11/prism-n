from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.main import get_session
from src.markets.models import Currency, MarketSource
from src.markets.schemas import SuccessResponse
from src.markets.services import MarketServices
from src.utils.bayse import BayseServices
from src.utils.dependencies import get_verified_user_id
from src.utils.logger import logger
from src.utils.responses import success_response


markets_router = APIRouter()


def _build_paginated_payload(items: list, *, page: int, limit: int, total: int | None = None) -> dict:
    effective_total = total if total is not None else len(items)
    start = (page - 1) * limit
    end = start + limit
    paginated_items = items if total is not None else items[start:end]
    return {
        "items": paginated_items,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": effective_total,
            "has_more": end < effective_total,
        },
    }


def get_bayse_service(request: Request) -> BayseServices:
    return request.app.state.bayse


def get_market_services(
    request: Request,
    bayse: BayseServices = Depends(get_bayse_service),
) -> MarketServices:
    return MarketServices(
        bayse=bayse,
        polymarket=request.app.state.polymarket,
        polymarket_clob=request.app.state.polymarket_clob,
        polymarket_data=request.app.state.polymarket_data,
        live_state=request.app.state.live_state,
        baseline_services=request.app.state.baseline_services,
        scoring_services=request.app.state.scoring_services,
        ai_insight_services=request.app.state.ai_insight_services,
    )


@markets_router.post(
    "/track/{event_id}",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
)
async def track_event(
    event_id: str,
    source: MarketSource = MarketSource.BAYSE,
    currency: Currency = Currency.DOLLAR,
    session: AsyncSession = Depends(get_session),
    market_services: MarketServices = Depends(get_market_services),
    user_id: UUID = Depends(get_verified_user_id),
):
    logger.info("Track route called for user %s and event %s in %s", user_id, event_id, currency.value)
    result = await market_services.track_event_for_user(
        session=session,
        user_id=user_id,
        event_id=event_id,
        source=source,
        currency=currency,
    )
    return success_response(
        message="Event tracked successfully",
        data=result.model_dump(),
    )


@markets_router.get(
    "/events",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
)
async def get_discovery_events(
    source: MarketSource | None = None,
    currency: Currency = Currency.DOLLAR,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    market_services: MarketServices = Depends(get_market_services),
    user_id: UUID = Depends(get_verified_user_id),
):
    logger.info("Discovery route called for user %s in %s", user_id, currency.value)
    result, total_count = await market_services.get_discovery_feed_for_user(
        session=session,
        user_id=user_id,
        source=source,
        currency=currency,
        page=page,
        limit=limit,
    )
    return success_response(
        message="Discovery events fetched successfully",
        data=_build_paginated_payload(
            [item.model_dump() for item in result],
            page=page,
            limit=limit,
            total=total_count,
        ),
    )


@markets_router.get(
    "/events/{event_id}",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
)
async def get_event_detail(
    event_id: str,
    source: MarketSource = MarketSource.BAYSE,
    currency: Currency = Currency.DOLLAR,
    session: AsyncSession = Depends(get_session),
    market_services: MarketServices = Depends(get_market_services),
    user_id: UUID = Depends(get_verified_user_id),
):
    logger.info("Event detail route called for user %s and event %s in %s", user_id, event_id, currency.value)
    result = await market_services.get_event_detail_for_user(
        session=session,
        user_id=user_id,
        event_id=event_id,
        source=source,
        currency=currency,
    )
    return success_response(
        message="Event detail fetched successfully",
        data=result.model_dump(),
    )


@markets_router.delete(
    "/track/{event_id}",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
)
async def untrack_event(
    event_id: str,
    source: MarketSource = MarketSource.BAYSE,
    currency: Currency = Currency.DOLLAR,
    session: AsyncSession = Depends(get_session),
    market_services: MarketServices = Depends(get_market_services),
    user_id: UUID = Depends(get_verified_user_id),
):
    logger.info("Untrack route called for user %s and event %s in %s", user_id, event_id, currency.value)
    result = await market_services.untrack_event_for_user(
        session=session,
        user_id=user_id,
        event_id=event_id,
        source=source,
        currency=currency,
    )
    return success_response(
        message="Event untracked successfully",
        data=result.model_dump(),
    )


@markets_router.get(
    "/tracker",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
)
async def list_tracked_events(
    currency: Currency = Currency.DOLLAR,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    market_services: MarketServices = Depends(get_market_services),
    user_id: UUID = Depends(get_verified_user_id),
):
    logger.info("Tracker route called for user %s in %s", user_id, currency.value)
    result, total_count = await market_services.list_tracked_events_page_for_user(
        session=session,
        user_id=user_id,
        currency=currency,
        page=page,
        limit=limit,
    )
    return success_response(
        message="Tracked events fetched successfully",
        data=_build_paginated_payload(
            [item.model_dump() for item in result],
            page=page,
            limit=limit,
            total=total_count,
        ),
    )
