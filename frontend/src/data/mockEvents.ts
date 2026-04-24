export type MarketSource = 'Bayse' | 'Polymarket';
export type SignalClassification = 'INFORMED_MOVE' | 'NOISE' | 'UNCERTAIN';
export type SignalDirection = 'RISING' | 'FALLING' | 'STABLE';
export type EventType = 'single' | 'combined';

export interface PrismSignal {
  score: number;
  classification: SignalClassification;
  direction: SignalDirection;
  detected_at?: string;
  previous_score?: number;
}

export interface EventOutcome {
  id: string;
  name: string;
  current_probability: number;
  probability_delta: number;
  liquidity: number;
  orders: number;
  volume_ratio: number;
  signal: PrismSignal;
  quant_data: {
    trap_risk: 'HIGH' | 'MEDIUM' | 'LOW';
    trap_reason: string;
    smart_money_dominant: 'Institutional' | 'Crowd' | 'Mixed';
    momentum_verdict: 'Likely to Continue' | 'Likely to Reverse' | 'Inconclusive';
    momentum_confidence: number;
  };
}

export interface HighestScoringMarket {
  id: string;
  name: string;
  current_probability: number;
  probability_delta: number;
  signal: PrismSignal;
}

export interface PrismEvent {
  id: string;
  source: MarketSource;
  title: string;
  event_type: EventType;
  total_liquidity: number;
  last_updated: string;
  highest_scoring_market: HighestScoringMarket;
  ai_insight: string;
  outcomes: EventOutcome[];
}

// -----------------------------------------------------
// MOCK DATA
// -----------------------------------------------------

export const mockEvents: PrismEvent[] = [];
