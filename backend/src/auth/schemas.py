from datetime import datetime
from typing import Any, Optional
import uuid
from pydantic import BaseModel, EmailStr, model_validator
from enum import Enum

class OtpTypes(str, Enum):
    SIGNUP = "signup"
    FORGOTPASSWORD = "forgotpassword"

class AuthUserOut(BaseModel):
    uid: uuid.UUID
    email: Optional[EmailStr] = None
    email_verified: Optional[bool] = None

class UserCreateInput(BaseModel):
    email: EmailStr
    password: str
    confirm_password: str

    @model_validator(mode='after')
    def validate_passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self

class VerifyOtpInput(BaseModel):
    uid: uuid.UUID
    otp: str
    otp_type: str

class UserLoginInput(BaseModel):
    email: EmailStr
    password: str

class ForgotPasswordInput(BaseModel):
    email: EmailStr

class ResetPasswordInput(BaseModel):
    reset_token: str
    new_password: str

class RenewAccessTokenInput(BaseModel):
    refresh_token: str

class ResendOtpInput(BaseModel):
    email: EmailStr
    otp_type: str

class LogoutInput(BaseModel):
    refresh_token: Optional[str] = None

class UserCreateResponse(BaseModel):
    success: bool
    message: str
    data: AuthUserOut

class UserLoginResponse(BaseModel):
    success: bool
    message: str
    data: AuthUserOut

class RenewAccessTokenResponse(BaseModel):
    success: bool
    message: str
    data: dict[str, str]

class LogoutResponse(BaseModel):
    success: bool
    message: str
    data: dict[str, Any]
