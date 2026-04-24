import uuid
from datetime import datetime, timezone
from enum import Enum

import sqlalchemy.dialects.postgresql as pg
from sqlalchemy import UniqueConstraint
from sqlmodel import SQLModel, Field, Column


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Currency(str, Enum):
    NAIRA = "NGN"
    DOLLAR = "USD"


class MarketSource(str, Enum):
    BAYSE = "bayse"
    POLYMARKET = "polymarket"


class MarketEngine(str, Enum):
    AMM = "AMM"
    CLOB = "CLOB"


class EventType(str, Enum):
    COMBINED = "combined"
    SINGLE = "single"


class TrackedMarket(SQLModel, table=True):
    __tablename__ = "tracked_markets"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    event_id: str = Field(index=True)
    market_id: str = Field(unique=True, index=True)

    event_slug: str | None = Field(default=None, index=True)
    event_title: str
    source: MarketSource = Field(default=MarketSource.BAYSE, index=True)
    event_type: EventType = Field(index=True)
    category: str | None = None
    status: str | None = Field(default=None, index=True)
    engine: MarketEngine = Field(index=True)

    market_title: str
    market_image_url: str | None = None
    market_image_128_url: str | None = None
    rules: str | None = None

    yes_outcome_id: str
    yes_outcome_label: str = "Yes"
    no_outcome_id: str
    no_outcome_label: str = "No"

    current_probability: float | None = None
    inverse_probability: float | None = None
    market_total_orders: int | None = None
    event_total_orders: int | None = None
    closing_date: datetime | None = Field(
        default=None,
        sa_column=Column(pg.TIMESTAMP(timezone=True), nullable=True),
    )

    tracking_enabled: bool = Field(default=True, index=True)
    is_system_tracked: bool = Field(default=False, index=True)

    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(pg.TIMESTAMP(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            onupdate=utc_now,
        ),
    )


class TrackedEventMetric(SQLModel, table=True):
    __tablename__ = "tracked_event_metrics"
    __table_args__ = (
        UniqueConstraint("event_id", "source", "currency", name="uq_tracked_event_metrics_event_source_currency"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    event_id: str = Field(index=True)
    source: MarketSource = Field(default=MarketSource.BAYSE, index=True)
    currency: Currency = Field(default=Currency.DOLLAR, index=True)
    total_liquidity: float | None = None

    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(pg.TIMESTAMP(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            onupdate=utc_now,
        ),
    )


class MarketBaseline(SQLModel, table=True):
    __tablename__ = "market_baselines"
    __table_args__ = (
        UniqueConstraint(
            "source",
            "event_id",
            "market_id",
            "window",
            "outcome",
            name="uq_market_baselines_source_event_market_window_outcome",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    source: MarketSource = Field(default=MarketSource.BAYSE, index=True)
    event_id: str = Field(index=True)
    market_id: str = Field(index=True)
    window: str = Field(default="1W", index=True)
    outcome: str = Field(default="YES", index=True)

    sample_count: int = Field(default=0)
    first_price: float | None = None
    previous_interval_price: float | None = None
    last_price: float | None = None
    absolute_move: float | None = None
    mean_return: float | None = None
    volatility_sigma: float | None = None
    max_absolute_return: float | None = None

    computed_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(pg.TIMESTAMP(timezone=True), nullable=False),
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(pg.TIMESTAMP(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            onupdate=utc_now,
        ),
    )


class MarketSignalSnapshot(SQLModel, table=True):
    __tablename__ = "market_signal_snapshots"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    source: MarketSource = Field(default=MarketSource.BAYSE, index=True)
    event_id: str = Field(index=True)
    market_id: str = Field(index=True)
    currency: Currency = Field(default=Currency.DOLLAR, index=True)

    score: float
    classification: str = Field(index=True)
    formula: str | None = None
    factors: dict | None = Field(default=None, sa_column=Column(pg.JSONB, nullable=True))
    notes: list[str] | None = Field(default=None, sa_column=Column(pg.JSONB, nullable=True))

    current_probability: float | None = None
    previous_probability: float | None = None
    probability_delta: float | None = None
    event_liquidity: float | None = None
    market_total_orders: int | None = None
    event_total_orders: int | None = None
    buy_notional: float | None = None
    sell_notional: float | None = None
    persistence_ticks: int | None = None

    snapshot_reason: str = Field(default="signal_update", index=True)
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(pg.TIMESTAMP(timezone=True), nullable=False),
    )


class UserTrackedEvent(SQLModel, table=True):
    __tablename__ = "user_tracked_events"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.uid", index=True)
    event_id: str = Field(index=True)
    tracking_enabled: bool = Field(default=True, index=True)

    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(pg.TIMESTAMP(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            onupdate=utc_now,
        ),
    )
