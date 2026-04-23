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
from src.utils.responses import success_response

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
    return success_response(
        message="Signup successful, an OTP has been sent to your email to verify your account.",
        data=result,
    )

@auth_router.post('/verify-otp', status_code=status.HTTP_200_OK)
async def verify_otp(
    otp_input: VerifyOtpInput,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    auth_services: AuthServices = Depends(get_auth_services)
):
    logger.info(f"OTP Verification attempt for user ID: {otp_input.uid}")
    result = await auth_services.verify_otp(otp_input, session, background_tasks)
    message = "OTP verified successfully"
    if otp_input.otp_type == "signup":
        message = "OTP verified successfully. You can now login."
    return success_response(
        message=message,
        data=result,
    )

@auth_router.post('/resend-otp', status_code=status.HTTP_200_OK)
async def resend_otp(
    resend_otp_input: ResendOtpInput,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    auth_services: AuthServices = Depends(get_auth_services)
):
    logger.info(f"Resend OTP attempt for email: {resend_otp_input.email}")
    result = await auth_services.resend_otp(resend_otp_input, session, background_tasks)
    message = "OTP resent successfully"
    if resend_otp_input.otp_type == "signup":
        message = "Signup OTP resent successfully"
    elif resend_otp_input.otp_type == "forgotpassword":
        message = "Password reset OTP resent successfully"
    return success_response(
        message=message,
        data=result,
    )

@auth_router.post('/forgot-password', status_code=status.HTTP_200_OK)
async def forgot_password(
    forgot_password_input: ForgotPasswordInput,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    auth_services: AuthServices = Depends(get_auth_services)
):
    logger.info(f"Forgot password attempt for email: {forgot_password_input.email}")
    result = await auth_services.forgot_password(forgot_password_input, session, background_tasks)
    return success_response(
        message="An OTP to reset password has been sent to your email.",
        data=result,
    )

@auth_router.post('/reset-password', status_code=status.HTTP_200_OK)
async def reset_password(
    reset_password_input: ResetPasswordInput,
    session: AsyncSession = Depends(get_session),
    auth_services: AuthServices = Depends(get_auth_services)
):
    logger.info("Reset password attempt")
    result = await auth_services.reset_password(reset_password_input, session)
    return success_response(
        message="Password reset successfully",
        data=result,
    )

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
    return success_response(
        message="Login successful",
        data=result,
    )

@auth_router.post('/renew-access-token', response_model=RenewAccessTokenResponse, status_code=status.HTTP_200_OK)
async def renew_access_token(
    response: Response,
    session: AsyncSession = Depends(get_session),
    auth_services: AuthServices = Depends(get_auth_services),
    refresh_token: str | None = Cookie(default=None)
):
    logger.info("Renew access token request received.")
    result = await auth_services.renew_access_token(refresh_token, session, response)
    logger.info("Access token effectively renewed.")
    return success_response(
        message="Access token renewed",
        data=result,
    )

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
    return success_response(
        message="Logged out successfully",
        data=result,
    )


@auth_router.get("/me")
async def get_me(current_user = Depends(get_verified_user), auth_services: AuthServices = Depends(get_auth_services)):
    result = await auth_services.get_me(current_user)
    return success_response(
        message="User details fetched successfully",
        data=result,
    )
