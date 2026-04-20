from sqlmodel import SQLModel, Field, Column
import uuid
from datetime import datetime, timezone, timedelta
from pydantic import EmailStr
import sqlalchemy.dialects.postgresql as pg

def utc_now():
    return datetime.now(timezone.utc)

class User(SQLModel, table=True):
    __tablename__ = "users"
    uid: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True
    )

    email: EmailStr = Field(unique=True, index=True)
    email_verified: bool = Field(default=False)

    password_hash: str = Field(exclude=True)

    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(pg.TIMESTAMP(timezone=True), index=True, nullable=False)
    )

def get_expiry_time(minutes):
    return datetime.now(timezone.utc) + timedelta(minutes=minutes)

class SignupOtp(SQLModel, table=True):
    __tablename__ = "signupOtp"
    
    otp_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    otp: str
    uid: uuid.UUID = Field(foreign_key="users.uid")
    max_attempts: int = Field(default=3)
    attempts:  int = Field(default=0)
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(pg.TIMESTAMP(timezone=True)))
    expires: datetime = Field(
        default_factory=lambda: get_expiry_time(10),
        sa_column=Column(pg.TIMESTAMP(timezone=True)))

class ForgotPasswordOtp(SQLModel, table=True):
    __tablename__ = "forgotPasswordOtp"
    
    otp_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    otp: str
    uid: uuid.UUID = Field(foreign_key="users.uid")
    max_attempts: int = Field(default=3)
    attempts:  int = Field(default=0)
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(pg.TIMESTAMP(timezone=True)))
    expires: datetime = Field(
        default_factory=lambda: get_expiry_time(10),
        sa_column=Column(pg.TIMESTAMP(timezone=True)))
