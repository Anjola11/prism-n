from pydantic import BaseModel

from src.markets.schemas import DiscoveryEventRead, TrackedEventRead


class AdminOverviewMetric(BaseModel):
    label: str
    value: int | float | str | None


class MostTrackedEventRead(BaseModel):
    event_id: str
    event_title: str
    event_slug: str | None = None
    tracker_count: int
    market_count: int
    system_tracked: bool


class AdminOverviewRead(BaseModel):
    total_users: int
    verified_users: int
    admin_users: int
    total_user_tracked_events: int
    total_user_event_links: int
    total_system_tracked_events: int
    total_system_tracked_markets: int
    recent_signal_snapshot_count: int
    most_tracked_events: list[MostTrackedEventRead]
    system_tracked_events: list[TrackedEventRead]
    system_status: dict


class AdminSystemStatusRead(BaseModel):
    redis_ok: bool
    websocket: dict
    background_jobs: dict | None = None


class AdminAnalyticsRead(BaseModel):
    total_users: int
    verified_users: int
    admin_users: int
    total_user_tracked_events: int
    total_user_event_links: int
    total_system_tracked_events: int
    total_system_tracked_markets: int
    recent_signal_snapshot_count: int
    most_tracked_events: list[MostTrackedEventRead]


class AdminActionLogRead(BaseModel):
    id: str
    admin_user_id: str
    action: str
    event_id: str | None = None
    currency: str | None = None
    details: dict | None = None
    created_at: str


class AdminLoginInput(BaseModel):
    email: str
    password: str


class AdminDiscoveryRead(BaseModel):
    events: list[DiscoveryEventRead]
