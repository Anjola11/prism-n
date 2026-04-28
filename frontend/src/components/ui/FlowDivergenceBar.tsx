import React from 'react';

import type { FlowSignalApi } from '../../lib/api/types';
import { formatCurrencyCompact } from '../../lib/format';

interface FlowDivergenceBarProps {
  flow: FlowSignalApi;
  currency: string;
}

export function FlowDivergenceBar({ flow, currency }: FlowDivergenceBarProps) {
  const buyWidth = Math.max(0, Math.min(100, flow.buy_ratio * 100));
  const sellWidth = 100 - buyWidth;
  const buyPct = Math.round(buyWidth);
  const sellPct = Math.round(sellWidth);
  const dominantSide = buyWidth > 65 ? 'buy' : buyWidth < 35 ? 'sell' : null;

  return (
    <div className="w-full">
      <div className="mb-2 flex items-center justify-between">
        <span className="font-mono text-[10px] uppercase tracking-widest text-text-muted">Buy</span>
        <span className="font-mono text-[10px] uppercase tracking-widest text-text-muted">Sell</span>
      </div>
      {flow.unusual_flow && (
        <div className="mb-2 inline-flex rounded border border-prism-amber/30 bg-prism-amber/10 px-2 py-1 font-mono text-[10px] uppercase tracking-wide text-prism-amber">
          Unusual flow detected
        </div>
      )}
      <div className="relative h-2 overflow-hidden rounded-full bg-card">
        <div className="absolute inset-y-0 left-0 bg-prism-teal" style={{ width: `${buyWidth}%` }} />
        <div className="absolute inset-y-0 right-0 bg-prism-amber" style={{ width: `${sellWidth}%` }} />
        {dominantSide && (
          <div
            className={`absolute -top-1 h-4 w-4 rounded-full border border-card ${dominantSide === 'buy' ? 'bg-prism-teal' : 'bg-prism-amber'}`}
            style={{ left: `calc(${buyWidth}% - 8px)` }}
          />
        )}
      </div>
      <div className="mt-3 flex items-start justify-between gap-4">
        <div className="font-mono text-xs text-text-secondary">
          <div>{formatCurrencyCompact(currency, flow.buy_notional)}</div>
          <div className="text-[10px] uppercase tracking-wide text-text-muted">Buy {buyPct}%</div>
        </div>
        <div className="text-right font-mono text-xs text-text-secondary">
          <div>{formatCurrencyCompact(currency, flow.sell_notional)}</div>
          <div className="text-[10px] uppercase tracking-wide text-text-muted">Sell {sellPct}%</div>
        </div>
      </div>
    </div>
  );
}
