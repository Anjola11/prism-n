from fastapi import APIRouter, Depends, status, Response, Cookie, BackgroundTasks
from sqlmodel.ext.asyncio.session import AsyncSession
from src.auth.schemas import (
    UserCreateInput,
    UserCreateResponse,
    UserLoginInput,
    UserLoginResponse,
    RenewAccessTokenResponse,
    LogoutResponse,
    VerifyOtpInput,
    ResendOtpInput,
    ForgotPasswordInput,
    ResetPasswordInput,
)
from src.db.main import get_session
from src.auth.services import AuthServices
from src.utils.logger import logger
from src.utils.dependencies import get_verified_user

auth_router = APIRouter()

def get_auth_services() -> AuthServices:
    return AuthServices()

@auth_router.post('/signup', response_model=UserCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_input: UserCreateInput, 
    background_tasks: BackgroundTasks,
    response: Response,
    session: AsyncSession = Depends(get_session),
    auth_services: AuthServices = Depends(get_auth_services)
):
    logger.info(f"Signup attempt for email: {user_input.email}")
    result = await auth_services.create_user(user_input, session, background_tasks, response)
    logger.info(f"Signup successful for email: {user_input.email}")
    return result

@auth_router.post('/verify-otp', status_code=status.HTTP_200_OK)
async def verify_otp(
    otp_input: VerifyOtpInput,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    auth_services: AuthServices = Depends(get_auth_services)
):
    logger.info(f"OTP Verification attempt for user ID: {otp_input.uid}")
    result = await auth_services.verify_otp(otp_input, session, background_tasks)
    return result

@auth_router.post('/resend-otp', status_code=status.HTTP_200_OK)
async def resend_otp(
    resend_otp_input: ResendOtpInput,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    auth_services: AuthServices = Depends(get_auth_services)
):
    logger.info(f"Resend OTP attempt for email: {resend_otp_input.email}")
    result = await auth_services.resend_otp(resend_otp_input, session, background_tasks)
    return result

@auth_router.post('/forgot-password', status_code=status.HTTP_200_OK)
async def forgot_password(
    forgot_password_input: ForgotPasswordInput,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    auth_services: AuthServices = Depends(get_auth_services)
):
    logger.info(f"Forgot password attempt for email: {forgot_password_input.email}")
    result = await auth_services.forgotPassword(forgot_password_input, session, background_tasks)
    return result

@auth_router.post('/reset-password', status_code=status.HTTP_200_OK)
async def reset_password(
    reset_password_input: ResetPasswordInput,
    session: AsyncSession = Depends(get_session),
    auth_services: AuthServices = Depends(get_auth_services)
):
    logger.info("Reset password attempt")
    result = await auth_services.resetPassword(reset_password_input, session)
    return result

@auth_router.post('/login', response_model=UserLoginResponse, status_code=status.HTTP_200_OK)
async def login(
    login_input: UserLoginInput,
    response: Response,
    session: AsyncSession = Depends(get_session),
    auth_services: AuthServices = Depends(get_auth_services)
):
    logger.info(f"Login attempt for email: {login_input.email}")
    result = await auth_services.login_user(login_input, session, response)
    logger.info(f"Login successful for email: {login_input.email}")
    return result

@auth_router.post('/renew-access-token', response_model=RenewAccessTokenResponse, status_code=status.HTTP_200_OK)
async def renew_access_token(
    response: Response,
    session: AsyncSession = Depends(get_session),
    auth_services: AuthServices = Depends(get_auth_services),
    refresh_token: str | None = Cookie(default=None)
):
    logger.info("Renew access token request received.")
    result = await auth_services.renewAccessToken(refresh_token, session, response)
    logger.info("Access token effectively renewed.")
    return result

@auth_router.post('/logout', response_model=LogoutResponse, status_code=status.HTTP_200_OK)
async def logout(
    response: Response,
    auth_services: AuthServices = Depends(get_auth_services),
    access_token: str | None = Cookie(default=None),
    refresh_token: str | None = Cookie(default=None)
):
    logger.info("Logout request received.")
    result = await auth_services.logout(response, access_token, refresh_token)
    logger.info("Logout successful.")
    return result


@auth_router.get("/me")
async def get_me(current_user = Depends(get_verified_user), auth_services: AuthServices = Depends(get_auth_services)):
    return await auth_services.get_me(current_user)
