import uuid
from datetime import datetime, timezone

import sqlalchemy.dialects.postgresql as pg
from sqlmodel import SQLModel, Column, Field

from src.markets.models import Currency


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AdminActionLog(SQLModel, table=True):
    __tablename__ = "admin_action_logs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    admin_user_id: uuid.UUID = Field(foreign_key="users.uid", index=True)
    action: str = Field(index=True)
    event_id: str | None = Field(default=None, index=True)
    currency: Currency | None = Field(default=None, index=True)
    details: dict | None = Field(default=None, sa_column=Column(pg.JSONB, nullable=True))
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(pg.TIMESTAMP(timezone=True), nullable=False),
    )
