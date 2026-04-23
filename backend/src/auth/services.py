from sqlmodel import select, desc
from src.auth.models import User, SignupOtp, ForgotPasswordOtp
from src.auth.schemas import (
    UserCreateInput, VerifyOtpInput, UserLoginInput, ForgotPasswordInput, 
    ResetPasswordInput, RenewAccessTokenInput, ResendOtpInput, LogoutInput, OtpTypes
)
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import HTTPException, status, Response, BackgroundTasks
from src.utils.logger import logger
from src.utils.auth import generate_password_hash, verify_password_hash, create_token, decode_token, TokenType
from datetime import datetime, timezone, timedelta
import uuid
from src.db.redis import redis_client
from src.emailServices.services import EmailServices
from src.config import Config

email_services = EmailServices()

# Token expiration configurations
access_token_expiry = timedelta(hours=2)
refresh_token_expiry = timedelta(days=3)

cookie_settings = {
    "httponly": True,
    "secure": Config.IS_PRODUCTION,
    "samesite": "none" if Config.IS_PRODUCTION else "lax"
}

class AuthServices:

    async def get_user(self, email:str, session:AsyncSession, return_data: bool):
        
        statement = select(User).where(User.email == email.lower())
        result = await session.exec(statement)
        user = result.first()
        
        if user:
            if return_data:
                return user
            logger.warning(f"Conflict: Account with email {email} already exists")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail = f"An account with these details already exists"
            )
        return None

    async def create_user(self, userInput: UserCreateInput, session: AsyncSession, background_tasks: BackgroundTasks, response: Response):
        # Verify user doesn't already exist
        await self.get_user(userInput.email, session, return_data=False)
        
        # Hash password before storing (strip to prevent accidental whitespace issues)
        hashed_password = generate_password_hash(userInput.password.strip())

        # Create new user instance
        new_user = User(
            email=userInput.email,
            password_hash=hashed_password,
        )

        try:
            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)

            # Generate tokens for cookie-based auth
            user_dict = new_user.model_dump()
            access_token = create_token(user_dict, token_type="access")
            refresh_token = create_token(user_dict, token_type="refresh")
            
            otp_record = await email_services.save_otp(new_user.uid, session, type=OtpTypes.SIGNUP)
            
            background_tasks.add_task(
                email_services.send_email_verification_otp, 
                userInput.email, 
                otp_record.otp
            )

            response.set_cookie(
                key="access_token",
                value=access_token,
                **cookie_settings,
                max_age=int(access_token_expiry.total_seconds())
            )

            response.set_cookie(
                key="refresh_token",
                value=refresh_token,
                **cookie_settings,
                max_age=int(refresh_token_expiry.total_seconds())
            )
            
            return {
                "uid": str(new_user.uid),
                "email": new_user.email,
                "email_verified": new_user.email_verified,
            }

        except Exception as e:
            logger.error(f"Error creating user: {e}")
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
    
    async def verify_otp(self, otp_input: VerifyOtpInput, session: AsyncSession, background_tasks: BackgroundTasks):
        """Verify a user's OTP and activate their account."""
        
        model = SignupOtp if otp_input.otp_type == OtpTypes.SIGNUP else ForgotPasswordOtp
        
        # Retrieve the most recent OTP record for this user
        otp_statement = (select(model)
                       .where(model.uid == otp_input.uid)
                       .order_by(desc(model.created_at)))
        
        result = await session.exec(otp_statement)
        latest_otp_record = result.first()

        # Validate OTP record exists
        if not latest_otp_record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="No OTP found for this user"
            )
        
        # Validate OTP code matches
        if latest_otp_record.otp != otp_input.otp:
            latest_otp_record.attempts += 1
            if latest_otp_record.attempts >= latest_otp_record.max_attempts:  
                await session.delete(latest_otp_record)
                await session.commit()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="OTP expired due to too many failed attempts"
                )
            
            await session.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"Invalid OTP. {latest_otp_record.max_attempts - latest_otp_record.attempts} attempts remaining"
            )

        # Check if OTP has expired
        if datetime.now(timezone.utc) > latest_otp_record.expires:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP expired, please request a new one"
            )
        
        if otp_input.otp_type == OtpTypes.SIGNUP:
            user_statement = select(User).where(User.uid == otp_input.uid)
            result = await session.exec(user_statement)
            user = result.first()

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, 
                    detail="User not found"
                )
        
            try:
                user.email_verified = True
                session.add(user)
                await session.delete(latest_otp_record)
                await session.commit()
                await session.refresh(user)

                background_tasks.add_task(
                    email_services.send_welcome_email,
                    user.email
                )

                return user.model_dump()

            except Exception as e:
                logger.error(f"Error validating otp user logic: {e}")
                await session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal server error"
                )
        
        elif otp_input.otp_type == OtpTypes.FORGOTPASSWORD:
            try:
                await session.delete(latest_otp_record)
                await session.commit()

                token_data = {"uid": str(latest_otp_record.uid)}
                reset_password_token = create_token(token_data, token_type=TokenType.RESET)
                
                return {
                    "uid": str(latest_otp_record.uid),
                    "reset_token": reset_password_token,
                }
            except Exception as e:
                logger.error(f"Error removing forgotpassword otp: {e}")
                await session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal server error"
                )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP type provided"
        )

    async def resend_otp(self, resend_otp_input: ResendOtpInput, session: AsyncSession, background_tasks: BackgroundTasks):
        """Resends an OTP to the user if applicable."""
        
        user = await self.get_user(resend_otp_input.email, session, True)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User with this email does not exist"
            )
        
        datetime_now = datetime.now(timezone.utc)

        if resend_otp_input.otp_type == OtpTypes.SIGNUP:
            if user.email_verified:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User is already verified. Please login."
                )
            
            signup_otp_statement = select(SignupOtp).where(SignupOtp.uid == user.uid).order_by(
                SignupOtp.created_at.desc()
            )
            result = await session.exec(signup_otp_statement)
            signup_otp = result.first()

            if signup_otp and signup_otp.expires > datetime_now:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You already requested for an otp, check your email"
                )
            
            otp_record = await email_services.save_otp(user.uid, session, type =OtpTypes.SIGNUP)

            background_tasks.add_task(
                email_services.send_email_verification_otp, 
                user.email, 
                otp_record.otp
            )
            
            return {"uid": str(user.uid)}

        elif resend_otp_input.otp_type == OtpTypes.FORGOTPASSWORD:
             
            forgot_password_otp_statement = select(ForgotPasswordOtp).where(ForgotPasswordOtp.uid == user.uid).order_by(
                ForgotPasswordOtp.created_at.desc()
            )
            result = await session.exec(forgot_password_otp_statement)
            forgot_password_otp = result.first()

            if forgot_password_otp and forgot_password_otp.expires > datetime_now:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You already requested for an otp, check your email"
                )
            
            otp_record = await email_services.save_otp(user.uid, session, type =OtpTypes.FORGOTPASSWORD)

            background_tasks.add_task(
                email_services.send_forgot_password_otp, 
                user.email, 
                otp_record.otp
            )
            return {"uid": str(user.uid)}
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP type provided"
        )
            
    async def login_user(self, loginInput: UserLoginInput, session: AsyncSession, response: Response):
        user = await self.get_user(loginInput.email, session, True)
        
        INVALID_CREDENTIALS = HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Credentials"
        )

        if not user:
            raise INVALID_CREDENTIALS
        
        if not user.email_verified:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Please verify your account before you can login. [UID:{user.uid}]"
            )

        # Verify password (strip to prevent accidental whitespace issues)
        verified_password = verify_password_hash(loginInput.password.strip(), user.password_hash)

        if not verified_password:
            raise INVALID_CREDENTIALS

        user_dict = user.model_dump()
        access_token = create_token(user_dict, token_type="access")
        refresh_token = create_token(user_dict, token_type="refresh")
        
        response.set_cookie(
            key="access_token",
            value=access_token,
            **cookie_settings,
            max_age=int(access_token_expiry.total_seconds())
        )

        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            **cookie_settings,
            max_age=int(refresh_token_expiry.total_seconds())
        )

        return {
            'uid': str(user.uid),
            'email': user.email,
            'email_verified': user.email_verified,
        }

    async def forgot_password(self, forgot_password_input: ForgotPasswordInput, session: AsyncSession, background_tasks: BackgroundTasks):
        user = await self.get_user(forgot_password_input.email, session, True)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is not registered"
            ) 
            
        otp_record = await email_services.save_otp(user.uid, session, type=OtpTypes.FORGOTPASSWORD)
        
        background_tasks.add_task(
            email_services.send_forgot_password_otp, 
            user.email, 
            otp_record.otp
        )

        return {"uid": str(user.uid)}
    
    async def reset_password(self, reset_password_input: ResetPasswordInput, session: AsyncSession):
        token_decode = decode_token(reset_password_input.reset_token)

        if token_decode.get('type') != "reset":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Invalid token type"
            )

        uid_from_token = token_decode.get('sub')

        statement = select(User).where(User.uid == uuid.UUID(uid_from_token))
        result = await session.exec(statement)
        user = result.first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="User not found"
            )

        new_hashed_password = generate_password_hash(reset_password_input.new_password.strip())
        user.password_hash = new_hashed_password
        user.email_verified = True  # Successful reset via OTP proves email ownership

        try:
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return {}
        except Exception:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
        
    async def renew_access_token(self, old_refresh_token_str: str, session: AsyncSession, response: Response):
        old_refresh_token_decode = decode_token(old_refresh_token_str)

        if old_refresh_token_decode.get('type') != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid token type"
            )
        
        jti = old_refresh_token_decode.get('jti')
        if await self.is_token_blacklisted(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Refresh token reused. Login required."
            )

        uid = old_refresh_token_decode.get("sub") 
        statement = select(User).where(User.uid == uuid.UUID(uid))
        result = await session.exec(statement)
        user = result.first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="User not found"
            )
            
        user_data = {"uid": user.uid, "email": user.email}

        new_token = create_token(user_data, token_type="access")
        await self.add_token_to_blocklist(old_refresh_token_str)
        new_refresh_token = create_token(user_data, token_type="refresh")
        
        response.set_cookie(
            key="access_token",
            value=new_token,
            **cookie_settings,
            max_age=int(access_token_expiry.total_seconds())
        )

        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            **cookie_settings,
            max_age=int(refresh_token_expiry.total_seconds())
        )

        return {}
    
    async def add_token_to_blocklist(self, token):
        token_decoded = decode_token(token)
        token_id = token_decoded.get('jti')
        exp_timestamp = token_decoded.get('exp')

        current_time = datetime.now(timezone.utc).timestamp()
        time_to_live = int(exp_timestamp - current_time)

        if time_to_live > 0:
            try:
                await redis_client.setex(name=token_id, time=time_to_live, value="true")
            except Exception as e:
                logger.error(f"Redis error in add_token_to_blocklist: {e}")
                pass
        
    async def is_token_blacklisted(self, jti: str) -> bool:
        try:
            result = await redis_client.get(jti)
            return result is not None
        except Exception as e:
            logger.error(f"Redis error in is_token_blacklisted: {e}")
            return False
    
    async def logout(self, response: Response, access_token: str = None, refresh_token: str = None):
        if access_token == None and refresh_token == None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tokens missing"
            )

        if access_token:
            await self.add_token_to_blocklist(access_token)
        if refresh_token:
            await self.add_token_to_blocklist(refresh_token)

        response.delete_cookie(
            key="access_token",
            httponly=cookie_settings["httponly"],
            samesite=cookie_settings["samesite"],
            secure=cookie_settings["secure"],
        )
        response.delete_cookie(
            key="refresh_token",
            httponly=cookie_settings["httponly"],
            samesite=cookie_settings["samesite"],
            secure=cookie_settings["secure"],
        )
        
        return {}

    async def get_me(self, current_user):
        user_dict = current_user.model_dump()

        return user_dict
