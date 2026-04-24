import type { DiscoveryEventApi, DiscoveryCardViewModel } from './types';

export function mapDiscoveryEvent(apiEvent: DiscoveryEventApi): DiscoveryCardViewModel {
  return {
    id: apiEvent.event_id,
    title: apiEvent.event_title,
    source: apiEvent.source,
    eventType: apiEvent.event_type,
    totalLiquidity: apiEvent.total_liquidity ?? 0,
    lastUpdated: apiEvent.last_updated,
    aiInsight: apiEvent.ai_insight,
    highestScoringMarket: apiEvent.highest_scoring_market,
  };
}
