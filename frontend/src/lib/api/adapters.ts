import type {
  DiscoveryEventApi,
  DiscoveryCardViewModel,
  HighestScoringMarketViewModel,
} from './types';

function mapHighestScoringMarket(apiEvent: DiscoveryEventApi): HighestScoringMarketViewModel | null {
  const topMarket = apiEvent.highest_scoring_market;
  if (!topMarket) {
    return null;
  }

  return {
    marketId: topMarket.market_id,
    marketTitle: topMarket.market_title,
    currentProbability: topMarket.current_probability,
    probabilityDelta: topMarket.probability_delta,
    signal: topMarket.signal,
  };
}

export function mapDiscoveryEvent(apiEvent: DiscoveryEventApi): DiscoveryCardViewModel {
  return {
    id: apiEvent.event_id,
    title: apiEvent.event_title,
    iconUrl: apiEvent.event_icon_url || null,
    source: apiEvent.source,
    currency: apiEvent.currency,
    eventType: apiEvent.event_type,
    totalLiquidity: apiEvent.total_liquidity ?? 0,
    lastUpdated: apiEvent.last_updated,
    aiInsight: apiEvent.ai_insight || 'Insight unavailable',
    trackingEnabled: apiEvent.tracking_enabled,
    dataMode: apiEvent.data_mode,
    highestScoringMarket: mapHighestScoringMarket(apiEvent),
  };
}
