from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.main import get_session
from src.markets.models import Currency
from src.markets.schemas import SuccessResponse
from src.markets.services import MarketServices
from src.utils.bayse import BayseServices
from src.utils.dependencies import get_verified_user_id
from src.utils.logger import logger
from src.utils.responses import success_response


markets_router = APIRouter()


def get_bayse_service(request: Request) -> BayseServices:
    return request.app.state.bayse


def get_market_services(
    request: Request,
    bayse: BayseServices = Depends(get_bayse_service),
) -> MarketServices:
    return MarketServices(
        bayse=bayse,
        live_state=request.app.state.live_state,
        baseline_services=request.app.state.baseline_services,
    )


@markets_router.post(
    "/track/{event_id}",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
)
async def track_event(
    event_id: str,
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
    currency: Currency = Currency.DOLLAR,
    session: AsyncSession = Depends(get_session),
    market_services: MarketServices = Depends(get_market_services),
    user_id: UUID = Depends(get_verified_user_id),
):
    logger.info("Discovery route called for user %s in %s", user_id, currency.value)
    result = await market_services.get_discovery_feed_for_user(
        session=session,
        user_id=user_id,
        currency=currency,
    )
    return success_response(
        message="Discovery events fetched successfully",
        data=[item.model_dump() for item in result],
    )


@markets_router.get(
    "/events/{event_id}",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
)
async def get_event_detail(
    event_id: str,
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
    session: AsyncSession = Depends(get_session),
    market_services: MarketServices = Depends(get_market_services),
    user_id: UUID = Depends(get_verified_user_id),
):
    logger.info("Tracker route called for user %s in %s", user_id, currency.value)
    result = await market_services.list_tracked_events_for_user(
        session=session,
        user_id=user_id,
        currency=currency,
    )
    return success_response(
        message="Tracked events fetched successfully",
        data=[item.model_dump() for item in result],
    )
