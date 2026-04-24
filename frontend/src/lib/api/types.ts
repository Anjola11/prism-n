export interface ApiResponse<T> {
  success: boolean;
  message: string;
  data: T;
}

export interface PaginationMeta {
  page: number;
  limit: number;
  total: number;
  has_more: boolean;
}

export interface PaginatedResponse<T> {
  items: T[];
  pagination: PaginationMeta;
}

export interface AuthUserApi {
  uid: string;
  email: string | null;
  email_verified: boolean | null;
  role: string;
}

export interface SignalApi {
  score: number;
  classification: string;
  direction: string;
  formula?: string | null;
  factors?: Record<string, number | null> | null;
  notes?: string[];
  detected_at?: string | null;
}

export interface HighestScoringMarketApi {
  market_id: string;
  market_title: string;
  current_probability: number | null;
  probability_delta: number;
  signal: SignalApi;
}

export interface DiscoveryEventApi {
  event_id: string;
  event_title: string;
  event_slug: string | null;
  event_icon_url?: string | null;
  source: string;
  currency: string;
  event_type: string;
  category: string | null;
  status: string | null;
  engine: string;
  total_liquidity: number | null;
  event_total_orders: number | null;
  closing_date: string | null;
  tracked_markets_count: number;
  tracking_enabled: boolean;
  data_mode: string;
  last_updated: string | null;
  ai_insight: string;
  highest_scoring_market?: HighestScoringMarketApi | null;
}

export interface EventMarketApi {
  market_id: string;
  market_title: string;
  market_image_url: string | null;
  market_image_128_url: string | null;
  rules: string | null;
  yes_outcome_id: string;
  yes_outcome_label: string;
  no_outcome_id: string;
  no_outcome_label: string;
  current_probability: number | null;
  inverse_probability: number | null;
  market_total_orders: number | null;
  buy_notional: number | null;
  sell_notional: number | null;
  probability_delta: number;
  event_liquidity: number | null;
  signal: SignalApi;
  last_updated: string | null;
}

export interface EventDetailApi extends DiscoveryEventApi {
  event_total_orders: number | null;
  markets: EventMarketApi[];
}

export interface MostTrackedEventApi {
  event_id: string;
  event_title: string;
  event_slug: string | null;
  tracker_count: number;
  market_count: number;
  system_tracked: boolean;
}

export interface AdminSystemStatusApi {
  redis_ok: boolean;
  websocket: {
    bayse?: {
      connected: boolean;
      reconnect_count?: number;
      last_message_at?: string | null;
      active_subscription_count?: number;
      [key: string]: unknown;
    };
    polymarket?: {
      connected: boolean;
      reconnect_count?: number;
      last_message_at?: string | null;
      active_asset_count?: number;
      [key: string]: unknown;
    };
    [key: string]: unknown;
  };
  background_jobs?: Record<string, boolean>;
}

export interface AdminOverviewApi {
  total_users: number;
  verified_users: number;
  admin_users: number;
  total_user_tracked_events: number;
  total_user_event_links: number;
  total_system_tracked_events: number;
  total_system_tracked_markets: number;
  recent_signal_snapshot_count: number;
  most_tracked_events: MostTrackedEventApi[];
  system_tracked_events: DiscoveryEventApi[];
  system_status: AdminSystemStatusApi;
}

export interface AdminAnalyticsApi {
  total_users: number;
  verified_users: number;
  admin_users: number;
  total_user_tracked_events: number;
  total_user_event_links: number;
  total_system_tracked_events: number;
  total_system_tracked_markets: number;
  recent_signal_snapshot_count: number;
  most_tracked_events: MostTrackedEventApi[];
}

export interface AdminActionLogApi {
  id: string;
  admin_user_id: string;
  action: string;
  event_id: string | null;
  currency: string | null;
  details: Record<string, unknown> | null;
  created_at: string;
}

export interface HighestScoringMarketViewModel {
  marketId: string;
  marketTitle: string;
  currentProbability: number | null;
  probabilityDelta: number;
  signal: SignalApi;
}

export interface DiscoveryCardViewModel {
  id: string;
  title: string;
  iconUrl: string | null;
  source: string;
  currency: string;
  eventType: string;
  totalLiquidity: number;
  lastUpdated: string | null;
  aiInsight: string;
  trackingEnabled: boolean;
  dataMode: string;
  highestScoringMarket: HighestScoringMarketViewModel | null;
}
