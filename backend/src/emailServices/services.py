from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import HTTPException, status
import uuid
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from brevo import Brevo
from brevo.core.api_error import ApiError
from brevo.transactional_emails import (
    SendTransacEmailRequestSender,
    SendTransacEmailRequestToItem,
)

from src.config import Config
from src.auth.models import SignupOtp, ForgotPasswordOtp  
from src.auth.schemas import OtpTypes
from src.utils.otp import generate_otp

# Setup template directory paths
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = BASE_DIR / "templates"

# Initialize Jinja2 template environment
template_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR)
)

class EmailServices:
    def __init__(self):
        # Configuration from your Config class
        self.BREVO_API_KEY = Config.BREVO_API_KEY
        self.BREVO_EMAIL = Config.BREVO_EMAIL
        self.BREVO_SENDER_NAME = Config.BREVO_SENDER_NAME

        # Initialize the modern Brevo Client
        self.client = Brevo(api_key=self.BREVO_API_KEY) if self.BREVO_API_KEY else None

    async def save_otp(self, user_id: uuid.UUID, session: AsyncSession, type: OtpTypes):
        if type == OtpTypes.SIGNUP:
            model = SignupOtp
        elif type == OtpTypes.FORGOTPASSWORD:
            model = ForgotPasswordOtp
        else:
            raise ValueError("Invalid OTP Type")
            
        new_otp = model(
            otp=generate_otp(),
            uid=user_id 
        )

        try:
            session.add(new_otp)
            await session.commit()
            await session.refresh(new_otp)
            return new_otp
        except Exception:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
        
    def render_template(self, template_name: str, payload: dict = {}):
        try:
            template = template_env.get_template(f"{template_name}.html")
            return template.render(**payload)
        except Exception as err:
            print(f"Error rendering template '{template_name}': {err}")
            raise err
    
    def send_email(self, to_email: str, subject: str, html_content: str, text_content: str) -> bool:
        if not self.client:
            print(f"Brevo API key not configured. Mock sending email to: {to_email} | Subject: {subject} | Content: {text_content}")
            return True

        try:
            # Use the namespaced service for transactional emails
            self.client.transactional_emails.send_transac_email(
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                sender=SendTransacEmailRequestSender(
                    name=self.BREVO_SENDER_NAME,
                    email=self.BREVO_EMAIL,
                ),
                to=[
                    SendTransacEmailRequestToItem(
                        email=to_email
                    )
                ]
            )
            print(f"Email sent to {to_email}: {subject}")
            return True
        except ApiError as e:
            print(f"Error sending email: Status {e.status_code}, Body: {e.body}")
            return False
    
    def send_email_verification_otp(self, user_email: str, otp_code: str):
        html = self.render_template('email-otp-verification', {
            'username': user_email,
            'otpCode': otp_code,
            'expiryTime': '10 minutes'
        })
        text_content = f"Hello {user_email}, Your verification code is: {otp_code}"
        return self.send_email(user_email, 'Verify your email', html, text_content)

    def send_welcome_email(self, user_email: str):
        html = self.render_template('welcome', {
            'email': user_email
        })
        text_content = f"Welcome to Prism! Your email {user_email} has been verified and your account is ready."
        return self.send_email(user_email, 'Welcome to Prism Intelligence', html, text_content)
    
    def send_forgot_password_otp(self, user_email: str, otp_code: str):
        html = self.render_template('forgot-password-otp', {
            'username': user_email,
            'otpCode': otp_code,
            'expiryTime': '5 minutes'
        })
        text_content = f"Hello {user_email}, Your Password Reset Code is: {otp_code}"
        return self.send_email(user_email, 'Reset your password', html, text_content)
