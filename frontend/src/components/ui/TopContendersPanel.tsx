import React from 'react';
import { useQueries } from '@tanstack/react-query';

import { marketsApi } from '../../lib/api/markets';
import type { EventDetailApi, EventMarketApi } from '../../lib/api/types';
import { ScoreSparkline } from './ScoreSparkline';

interface TopContendersPanelProps {
  event: EventDetailApi;
  activeTabId: string;
  onSelect: (marketId: string) => void;
}

const getDirectionArrow = (direction: string) =>
  direction === 'RISING' ? '↑' : direction === 'FALLING' ? '↓' : '→';

export function TopContendersPanel({ event, activeTabId, onSelect }: TopContendersPanelProps) {
  const [showAll, setShowAll] = React.useState(false);
  const sortedMarkets = React.useMemo(
    () => [...event.markets].sort((a, b) => b.signal.score - a.signal.score),
    [event.markets],
  );
  const visibleMarkets = showAll ? sortedMarkets : sortedMarkets.slice(0, 5);

  const historyQueries = useQueries({
    queries: visibleMarkets.map((market) => ({
      queryKey: ['score-history', event.event_id, market.market_id, 48],
      queryFn: () => marketsApi.getScoreHistory(event.event_id, market.market_id, 48, event.currency, event.source.toLowerCase()),
      staleTime: 5 * 60 * 1000,
    })),
  });

  if (event.event_type !== 'combined' || event.markets.length < 3) {
    return null;
  }

  return (
    <div className="rounded-xl border border-border bg-card p-4 sm:p-5">
      <div className="mb-4 font-mono text-[10px] uppercase tracking-[0.22em] text-text-muted">All Outcomes</div>
      <div className="overflow-x-auto">
        <table className="min-w-full border-separate border-spacing-y-2">
          <thead>
            <tr className="font-mono text-[10px] uppercase tracking-wide text-text-muted">
              <th className="px-2 py-1 text-left">#</th>
              <th className="px-2 py-1 text-left">Candidate</th>
              <th className="hidden px-2 py-1 text-left md:table-cell">Probability</th>
              <th className="px-2 py-1 text-left">Score</th>
              <th className="px-2 py-1 text-left">48h</th>
              <th className="hidden px-2 py-1 text-left md:table-cell">Sparkline</th>
              <th className="px-2 py-1 text-right">Action</th>
            </tr>
          </thead>
          <tbody>
            {visibleMarkets.map((market, index) => {
              const scoreDelta = market.score_delta_48h;
              const history = historyQueries[index]?.data?.points ?? [];
              const isActive = market.market_id === activeTabId;
              return (
                <tr
                  key={market.market_id}
                  className={`rounded-lg ${isActive ? 'bg-navy-mid/60' : 'hover:bg-navy-mid/30'}`}
                >
                  <td className="px-2 py-3 font-mono text-sm text-text-secondary">{index + 1}</td>
                  <td className="px-2 py-3 text-sm font-medium text-text-primary">{market.market_title}</td>
                  <td className="hidden px-2 py-3 font-mono text-sm text-text-secondary md:table-cell">
                    {typeof market.current_probability === 'number' ? `${Math.round(market.current_probability * 100)}%` : '-'}
                  </td>
                  <td className="px-2 py-3">
                    <span className="rounded border border-border/60 px-2 py-1 font-mono text-[10px] text-text-primary">
                      {market.signal.score} {getDirectionArrow(market.signal.direction)}
                    </span>
                  </td>
                  <td className={`px-2 py-3 font-mono text-xs ${scoreDelta && scoreDelta > 0 ? 'signal-trend-up' : scoreDelta && scoreDelta < 0 ? 'signal-trend-down' : 'text-text-muted'}`}>
                    {typeof scoreDelta === 'number' && scoreDelta !== 0 ? `${scoreDelta > 0 ? '+' : ''}${Math.round(scoreDelta)} pts` : '-'}
                  </td>
                  <td className="hidden px-2 py-3 md:table-cell">
                    <ScoreSparkline points={history} width={60} height={20} loading={historyQueries[index]?.isLoading} />
                  </td>
                  <td className="px-2 py-3 text-right">
                    <button
                      type="button"
                      onClick={() => onSelect(market.market_id)}
                      className="font-mono text-[11px] text-prism-cyan underline-offset-2 hover:underline"
                    >
                      View
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {event.markets.length > 5 && (
        <button
          type="button"
          onClick={() => setShowAll((current) => !current)}
          className="mt-4 font-mono text-xs text-text-secondary hover:text-text-primary"
        >
          {showAll ? 'Show less' : `Show all ${event.markets.length} outcomes`}
        </button>
      )}
    </div>
  );
}
