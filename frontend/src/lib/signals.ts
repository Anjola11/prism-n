export type FactorBucket = 'low' | 'mid' | 'high';

export const getFactorBucket = (value: number): FactorBucket => {
  if (value <= 30) return 'low';
  if (value <= 69) return 'mid';
  return 'high';
};

export const FACTOR_INTERPRETATIONS: Record<string, Record<FactorBucket, string>> = {
  move: {
    low: 'Price has not shifted in the current scoring window',
    mid: 'Moderate price movement detected - momentum building',
    high: 'Strong price movement - significant shift in probability',
  },
  liquidity: {
    low: 'Thin order book - large orders could move the price',
    mid: 'Adequate depth - normal order sizes absorbable',
    high: 'Deep order book - large positions can enter without slippage',
  },
  volume: {
    low: 'Low order activity - market is quiet right now',
    mid: 'Moderate order activity relative to baseline',
    high: 'High order activity - elevated trader interest',
  },
  persistence: {
    low: 'Signal is too new or inconsistent to confirm',
    mid: 'Signal has held for a few scoring windows - watch for continuation',
    high: 'Signal has persisted across multiple windows - confirmed direction',
  },
  order_flow: {
    low: 'Balanced buy/sell flow - no clear directional pressure',
    mid: 'Mild directional imbalance in order flow',
    high: 'Strong directional imbalance - one side is dominant',
  },
  confidence: {
    low: 'Low market participation - treat score with caution',
    mid: 'Moderate participation - score is reasonably grounded',
    high: 'High participation - score is well-supported by market activity',
  },
};

export const getFactorInterpretation = (factorName: string, value: number): string => {
  const key = factorName.toLowerCase().replace(/\s+/g, '_');
  const map = FACTOR_INTERPRETATIONS[key];
  if (!map) return '';
  return map[getFactorBucket(value)];
};

export type VerdictTone = 'bullish' | 'cautious' | 'bearish' | 'avoid' | 'neutral';

export interface Verdict {
  label: string;
  detail: string;
  tone: VerdictTone;
}

export const computeVerdict = (params: {
  score: number;
  direction: string;
  buyNotional?: number;
  sellNotional?: number;
  probabilityDelta?: number;
}): Verdict => {
  const { score, direction, buyNotional = 0, sellNotional = 0 } = params;
  const isRising = direction === 'RISING';
  const isFalling = direction === 'FALLING';
  const buyDominant = buyNotional > sellNotional * 1.5;
  const sellDominant = sellNotional > buyNotional * 1.5;
  const flowNote = buyDominant
    ? ' - buy flow dominant'
    : sellDominant
      ? ' - sell pressure building'
      : '';

  if (score >= 70 && isRising) {
    return { label: 'LEAN YES', detail: `High conviction, rising momentum${flowNote}`, tone: 'bullish' };
  }
  if (score >= 70 && isFalling) {
    return { label: 'CAUTION', detail: `Score strong but momentum rolling over${flowNote}`, tone: 'cautious' };
  }
  if (score >= 70) {
    return { label: 'LEAN YES', detail: `High conviction, stable${flowNote}`, tone: 'bullish' };
  }
  if (score >= 40 && isRising) {
    return { label: 'LEAN YES', detail: `Moderate conviction, building momentum${flowNote}`, tone: 'bullish' };
  }
  if (score >= 40 && isFalling) {
    return { label: 'LEAN NO', detail: `Momentum fading - watch for reversal${flowNote}`, tone: 'bearish' };
  }
  if (score >= 40) {
    return { label: 'WATCH', detail: 'Moderate signal, direction unclear', tone: 'neutral' };
  }
  return { label: 'AVOID', detail: 'Thin signal - not yet structured for trading', tone: 'avoid' };
};

export interface AlertHeadline {
  text: string;
  tone: VerdictTone;
}

export const generateAlertHeadline = (params: {
  score: number;
  scoreDelta?: number | null;
  direction: string;
  classification: string;
  buyNotional?: number;
  sellNotional?: number;
  marketTitle: string;
}): AlertHeadline => {
  const { scoreDelta, direction, buyNotional = 0, sellNotional = 0, marketTitle } = params;
  const delta = scoreDelta ?? 0;
  const absDelta = Math.abs(Math.round(delta));
  const buyDominant = buyNotional > sellNotional * 1.5;
  const sellDominant = sellNotional > buyNotional * 1.5;

  if (delta > 15 && direction === 'RISING') {
    return { text: `Conviction Building - Score up ${absDelta} pts in 48h`, tone: 'bullish' };
  }
  if (delta < -15 && direction === 'FALLING') {
    return { text: `Conviction Fading - Score down ${absDelta} pts in 48h`, tone: 'bearish' };
  }
  if (buyDominant) {
    return { text: 'Buy-side dominant - Smart money entering Yes', tone: 'bullish' };
  }
  if (sellDominant) {
    return { text: 'Sell pressure building - Money exiting Yes', tone: 'bearish' };
  }
  if (direction === 'RISING') {
    return { text: `Momentum building on ${marketTitle}`, tone: 'bullish' };
  }
  if (direction === 'FALLING') {
    return { text: 'Momentum fading - Monitor for reversal', tone: 'bearish' };
  }
  return { text: 'Balanced flow - No divergence signal', tone: 'neutral' };
};

export const getVerdictToneClass = (tone: VerdictTone) => {
  switch (tone) {
    case 'bullish':
      return 'signal-trend-up';
    case 'cautious':
    case 'bearish':
      return 'signal-trend-down';
    case 'avoid':
      return 'signal-trend-avoid';
    default:
      return 'signal-trend-neutral';
  }
};

export const getFactorBarClass = (value: number) => {
  const bucket = getFactorBucket(value);
  if (bucket === 'high') return 'signal-factor-bar-high';
  if (bucket === 'mid') return 'signal-factor-bar-mid';
  return 'signal-factor-bar-low';
};
