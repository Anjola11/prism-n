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

export const mockEvents: PrismEvent[] = [
  {
    id: "evt_fed",
    source: "Bayse",
    title: "Federal Reserve rate cut by July 2026?",
    event_type: "single",
    total_liquidity: 12500000,
    last_updated: "12s ago",
    highest_scoring_market: {
      id: "mkt_fed_yes",
      name: "YES",
      current_probability: 78,
      probability_delta: 6,
      signal: {
        score: 88,
        classification: "INFORMED_MOVE",
        direction: "RISING",
        previous_score: 81
      }
    },
    ai_insight: "Sustained buy pressure aligning with macroeconomic data releases supports the validity of the current move. The order book displays dense bids suggesting long-term conviction.",
    outcomes: [
      {
        id: "mkt_fed_yes",
        name: "YES",
        current_probability: 78,
        probability_delta: 6,
        liquidity: 8200000,
        orders: 5400,
        volume_ratio: 3.8,
        signal: {
          score: 88,
          classification: "INFORMED_MOVE",
          direction: "RISING",
          previous_score: 81
        },
        quant_data: {
          trap_risk: "LOW",
          trap_reason: "High liquidity absorption prevents rapid artificial spikes.",
          smart_money_dominant: "Institutional",
          momentum_verdict: "Likely to Continue",
          momentum_confidence: 88
        }
      },
      {
        id: "mkt_fed_no",
        name: "NO",
        current_probability: 22,
        probability_delta: -6,
        liquidity: 4300000,
        orders: 1200,
        volume_ratio: 0.8,
        signal: {
          score: 12,
          classification: "NOISE",
          direction: "FALLING"
        },
        quant_data: {
          trap_risk: "LOW",
          trap_reason: "Standard liquidity on the inverse side.",
          smart_money_dominant: "Mixed",
          momentum_verdict: "Likely to Reverse",
          momentum_confidence: 88
        }
      }
    ]
  },
  {
    id: "evt_worldcup",
    source: "Polymarket",
    title: "Who will win the 2026 FIFA World Cup?",
    event_type: "combined",
    total_liquidity: 4200000,
    last_updated: "45s ago",
    highest_scoring_market: {
      id: "mkt_wc_arg",
      name: "Argentina",
      current_probability: 16,
      probability_delta: -4,
      signal: {
        score: 79,
        classification: "INFORMED_MOVE",
        direction: "FALLING",
        previous_score: 83
      }
    },
    ai_insight: "Money is slowly exiting Argentina and being distributed across France and Brazil with highly localized volume clusters.",
    outcomes: [
      {
        id: "mkt_wc_arg",
        name: "Argentina",
        current_probability: 16,
        probability_delta: -4,
        liquidity: 1200000,
        orders: 3400,
        volume_ratio: 2.1,
        signal: {
          score: 79,
          classification: "INFORMED_MOVE",
          direction: "FALLING"
        },
        quant_data: {
          trap_risk: "LOW",
          trap_reason: "Broad distribution indicates structural rebalancing.",
          smart_money_dominant: "Institutional",
          momentum_verdict: "Likely to Continue",
          momentum_confidence: 79
        }
      },
      {
        id: "mkt_wc_fra",
        name: "France",
        current_probability: 14,
        probability_delta: 2,
        liquidity: 950000,
        orders: 1200,
        volume_ratio: 1.4,
        signal: {
          score: 42,
          classification: "UNCERTAIN",
          direction: "RISING"
        },
        quant_data: {
          trap_risk: "MEDIUM",
          trap_reason: "Moderate liquidity absorbing standard limit orders.",
          smart_money_dominant: "Mixed",
          momentum_verdict: "Inconclusive",
          momentum_confidence: 42
        }
      },
      {
        id: "mkt_wc_bra",
        name: "Brazil",
        current_probability: 14,
        probability_delta: 0,
        liquidity: 1050000,
        orders: 2200,
        volume_ratio: 1.0,
        signal: {
          score: 34,
          classification: "UNCERTAIN",
          direction: "STABLE"
        },
        quant_data: {
          trap_risk: "LOW",
          trap_reason: "Deep liquidity means price is hard to manipulate.",
          smart_money_dominant: "Crowd",
          momentum_verdict: "Inconclusive",
          momentum_confidence: 66
        }
      }
    ]
  },
  {
    id: "evt_btc",
    source: "Polymarket",
    title: "Bitcoin strictly above $120,000 before End of Year?",
    event_type: "single",
    total_liquidity: 22100000,
    last_updated: "2s ago",
    highest_scoring_market: {
      id: "mkt_btc_yes",
      name: "YES",
      current_probability: 45,
      probability_delta: 12,
      signal: {
        score: 21,
        classification: "NOISE",
        direction: "RISING",
        previous_score: 9
      }
    },
    ai_insight: "This is a classic retail cascade driven by cross-platform virality rather than fundamental conviction. A lack of deep liquidity acting as a floor means this price action is exceptionally fragile.",
    outcomes: [
       {
        id: "mkt_btc_yes",
        name: "YES",
        current_probability: 45,
        probability_delta: 12,
        liquidity: 11000000,
        orders: 42100,
        volume_ratio: 5.2,
        signal: {
          score: 21,
          classification: "NOISE",
          direction: "RISING",
          previous_score: 9
        },
        quant_data: {
          trap_risk: "HIGH",
          trap_reason: "Rapid low-liquidity spike created an artificial vacuum. High likelihood of immediate reversion.",
          smart_money_dominant: "Crowd",
          momentum_verdict: "Likely to Reverse",
          momentum_confidence: 79
        }
      },
      {
        id: "mkt_btc_no",
        name: "NO",
        current_probability: 55,
        probability_delta: -12,
        liquidity: 11100000,
        orders: 14000,
        volume_ratio: 1.2,
        signal: {
          score: 18,
          classification: "NOISE",
          direction: "FALLING"
        },
        quant_data: {
          trap_risk: "LOW",
          trap_reason: "Baseline inverse correlation.",
          smart_money_dominant: "Institutional",
          momentum_verdict: "Inconclusive",
          momentum_confidence: 50
        }
      }
    ]
  }
];
