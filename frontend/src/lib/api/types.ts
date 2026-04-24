export interface DiscoveryEventApi {
  event_id: string;
  event_title: string;
  event_slug: string | null;
  source: string;
  currency: string;
  event_type: string;
  category: string | null;
  status: string | null;
  engine: string;
  total_liquidity: number | null;
  event_total_orders: number;
  closing_date: string | null;
  tracked_markets_count: number;
  tracking_enabled: boolean;
  last_updated: string | null;
  ai_insight: string;
  highest_scoring_market?: any;
}

export interface DiscoveryCardViewModel {
  id: string;
  title: string;
  source: string;
  eventType: string;
  totalLiquidity: number;
  lastUpdated: string | null;
  aiInsight: string;
  highestScoringMarket: any;
}
