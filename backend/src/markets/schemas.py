import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from src.markets.models import Currency, EventType, MarketEngine, MarketSource


class TrackedMarketBase(BaseModel):
    event_id: str
    market_id: str
    event_slug: str | None = None
    event_title: str
    source: MarketSource = MarketSource.BAYSE
    event_type: EventType
    category: str | None = None
    status: str | None = None
    engine: MarketEngine
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
    closing_date: datetime | None = None
    tracking_enabled: bool = True


class TrackedMarketCreate(TrackedMarketBase):
    pass


class TrackedMarketRead(TrackedMarketBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class NormalizeEventResult(BaseModel):
    event_id: str
    event_title: str
    event_slug: str | None = None
    source: MarketSource
    currency: Currency
    total_liquidity: float | None = None
    event_type: EventType
    engine: MarketEngine
    markets: list[TrackedMarketCreate]


class TrackEventResponse(BaseModel):
    event_id: str
    event_title: str
    event_slug: str | None = None
    source: MarketSource
    currency: Currency
    event_type: EventType
    engine: MarketEngine
    tracked_markets_count: int
    tracking_enabled: bool = True


class SignalRead(BaseModel):
    score: float = 0.0
    classification: str = "unscored"
    direction: str = "STABLE"
    formula: str | None = None
    factors: dict | None = None
    notes: list[str] = Field(default_factory=list)
    detected_at: str | None = None


class HighestScoringMarketRead(BaseModel):
    market_id: str
    market_title: str
    focus_outcome_side: str | None = None
    focus_outcome_label: str | None = None
    current_probability: float | None = None
    probability_delta: float = 0.0
    signal: SignalRead


class TrackedEventRead(BaseModel):
    event_id: str
    event_title: str
    event_slug: str | None = None
    event_icon_url: str | None = None
    source: MarketSource
    currency: Currency
    event_type: EventType
    category: str | None = None
    status: str | None = None
    engine: MarketEngine
    total_liquidity: float | None = None
    event_total_orders: int | None = None
    closing_date: datetime | None = None
    tracked_markets_count: int
    tracking_enabled: bool
    data_mode: str = "tracked_live"
    last_updated: str | None = None
    ai_insight: str = "Insight unavailable"
    highest_scoring_market: HighestScoringMarketRead | None = None


class EventMarketRead(BaseModel):
    market_id: str
    market_title: str
    market_image_url: str | None = None
    market_image_128_url: str | None = None
    rules: str | None = None
    yes_outcome_id: str
    yes_outcome_label: str
    no_outcome_id: str
    no_outcome_label: str
    current_probability: float | None = None
    inverse_probability: float | None = None
    market_total_orders: int | None = None
    buy_notional: float | None = None
    sell_notional: float | None = None
    probability_delta: float = 0.0
    event_liquidity: float | None = None
    signal: SignalRead = Field(default_factory=SignalRead)
    last_updated: str | None = None


class EventDetailRead(BaseModel):
    event_id: str
    event_title: str
    event_slug: str | None = None
    event_icon_url: str | None = None
    source: MarketSource
    currency: Currency
    event_type: EventType
    category: str | None = None
    status: str | None = None
    engine: MarketEngine
    total_liquidity: float | None = None
    event_total_orders: int | None = None
    closing_date: datetime | None = None
    tracked_markets_count: int
    tracking_enabled: bool = False
    data_mode: str = "lite_snapshot"
    last_updated: str | None = None
    ai_insight: str = "Insight unavailable"
    highest_scoring_market: HighestScoringMarketRead | None = None
    markets: list[EventMarketRead]


class DiscoveryEventRead(BaseModel):
    event_id: str
    event_title: str
    event_slug: str | None = None
    event_icon_url: str | None = None
    source: MarketSource
    currency: Currency
    event_type: EventType
    category: str | None = None
    status: str | None = None
    engine: MarketEngine
    total_liquidity: float | None = None
    event_total_orders: int | None = None
    closing_date: datetime | None = None
    tracked_markets_count: int
    tracking_enabled: bool = False
    data_mode: str = "lite_snapshot"
    last_updated: str | None = None
    ai_insight: str = "Insight unavailable"
    highest_scoring_market: HighestScoringMarketRead | None = None


class SuccessResponse(BaseModel):
    success: bool
    message: str
    data: dict | list | None = None
