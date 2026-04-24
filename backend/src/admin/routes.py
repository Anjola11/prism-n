from fastapi import APIRouter, Depends, Request, Response, status
from sqlmodel.ext.asyncio.session import AsyncSession

from src.admin.schemas import AdminLoginInput
from src.admin.services import AdminServices
from src.auth.services import AuthServices
from src.db.main import get_session
from src.markets.models import Currency
from src.markets.services import MarketServices
from src.markets.routes import get_market_services
from src.markets.schemas import SuccessResponse
from src.utils.dependencies import get_admin_user, get_admin_user_id
from src.utils.logger import logger
from src.utils.responses import success_response


admin_router = APIRouter()


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
    response: Response,
    session: AsyncSession = Depends(get_session),
    admin_services: AdminServices = Depends(get_admin_services),
):
    logger.info("Admin login attempt for email: %s", login_input.email)
    result = await admin_services.login_admin(
        login_input=login_input,
        session=session,
        response=response,
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
        data=current_admin.model_dump(),
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
        websocket_status=request.app.state.bayse_ws_manager.get_status(),
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
    currency: Currency = Currency.DOLLAR,
    session: AsyncSession = Depends(get_session),
    market_services: MarketServices = Depends(get_market_services),
    admin_user_id=Depends(get_admin_user_id),
):
    logger.info("Admin discovery requested by %s in %s", admin_user_id, currency.value)
    result = await market_services.get_discovery_feed_for_system(
        session=session,
        currency=currency,
    )
    return success_response(
        message="Admin discovery fetched successfully",
        data=[item.model_dump() for item in result],
    )


@admin_router.get(
    "/system-tracker",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
)
async def admin_system_tracker(
    currency: Currency = Currency.DOLLAR,
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
        data=[item.model_dump() for item in result],
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
        websocket_status=request.app.state.bayse_ws_manager.get_status(),
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
