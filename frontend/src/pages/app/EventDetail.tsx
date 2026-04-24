import React, { useLayoutEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate, useParams, useSearch } from '@tanstack/react-router';
import { Activity, ArrowLeft, Droplets, Sparkles, TrendingDown, TrendingUp, Users, Zap } from 'lucide-react';
import gsap from 'gsap';

import { marketsApi } from '../../lib/api/markets';
import type { EventDetailApi } from '../../lib/api/types';
import { formatCurrencyCompact, formatRelative } from '../../lib/format';

export function EventDetail() {
  const { eventId } = useParams({ strict: false }) as { eventId: string };
  const search = useSearch({ from: '/app/events/$eventId' }) as { source?: string };
  const navigate = useNavigate();
  const container = useRef<HTMLDivElement>(null);

  const [activeTabId, setActiveTabId] = useState('');
  const requestedSource = search.source || undefined;
  const eventQuery = useQuery({
    queryKey: ['event-detail', eventId, requestedSource],
    queryFn: async () => marketsApi.getEvent(eventId, undefined, requestedSource),
    enabled: !!eventId,
    staleTime: 15_000,
    gcTime: 5 * 60_000,
    refetchInterval: 30_000,
    placeholderData: (previousData) => previousData,
  });

  const event: EventDetailApi | null = eventQuery.data || null;

  React.useEffect(() => {
    if (!event) return;
    const canonicalSource = event.source?.toLowerCase?.();
    if (!canonicalSource || canonicalSource === (search.source || '').toLowerCase()) return;
    navigate({
      to: '/app/events/$eventId',
      params: { eventId },
      search: { source: canonicalSource },
      replace: true,
    });
  }, [event, eventId, navigate, search.source]);

  React.useEffect(() => {
    if (!event) return;
    if (activeTabId && event.markets.some((market) => market.market_id === activeTabId)) {
      return;
    }
    if (event.highest_scoring_market && event.markets.some((market) => market.market_id === event.highest_scoring_market?.market_id)) {
      setActiveTabId(event.highest_scoring_market.market_id);
      return;
    }
    if (event.markets.length > 0) {
      setActiveTabId(event.markets[0].market_id);
    }
  }, [activeTabId, event]);

  const selectedOutcome = event?.markets.find((market) => market.market_id === activeTabId) || event?.markets[0];
  const eventLeader = event?.highest_scoring_market || null;
  const selectedMarketFlow = (selectedOutcome?.buy_notional || 0) + (selectedOutcome?.sell_notional || 0);
  const hasObservedFlow =
    (selectedOutcome?.buy_notional || 0) > 0 || (selectedOutcome?.sell_notional || 0) > 0;
  const marketVolumeProxy = event?.source === 'POLYMARKET' ? (selectedOutcome?.market_total_orders || 0) : 0;
  const displaySelectedFlow = hasObservedFlow ? selectedMarketFlow : marketVolumeProxy;
  const signalNotes = React.useMemo(() => {
    const notes = selectedOutcome?.signal.notes || [];
    const deduped = Array.from(new Set(notes));
    return deduped;
  }, [selectedOutcome?.signal.notes]);

  useLayoutEffect(() => {
    if (!event || !selectedOutcome) return;

    const ctx = gsap.context(() => {
      gsap.fromTo(
        '.dynamic-panel',
        { opacity: 0, y: 10 },
        { opacity: 1, y: 0, duration: 0.4, ease: 'power2.out' },
      );
    }, container);

    return () => ctx.revert();
  }, [activeTabId, event, selectedOutcome]);

  if (eventQuery.isLoading) {
    return (
      <div className="mx-auto flex max-w-4xl flex-col gap-6 px-6 py-8">
        <div className="h-8 w-64 animate-pulse rounded bg-card" />
        <div className="h-40 animate-pulse rounded-2xl border border-border bg-card" />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <div className="h-40 animate-pulse rounded-xl border border-border bg-card" />
          <div className="md:col-span-2 h-40 animate-pulse rounded-xl border border-border bg-card" />
        </div>
      </div>
    );
  }
  if (eventQuery.isError) return <div className="p-10 text-center text-amber-500">Failed to fetch event detail.</div>;
  if (!event || !selectedOutcome) return <div className="p-10 text-center text-white">Event not found</div>;

  const getScoreColor = (score: number) => {
    if (score >= 70) return 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20';
    if (score >= 40) return 'text-slate-300 bg-slate-400/10 border-slate-400/20';
    return 'text-amber-500 bg-amber-500/10 border-amber-500/20';
  };

  const factorEntries = selectedOutcome.signal?.factors
    ? Object.entries(selectedOutcome.signal.factors).filter(([, value]) => typeof value === 'number')
    : [];

  return (
    <div ref={container} className="mx-auto flex max-w-4xl flex-col gap-6 px-6 py-8">
      <div className="flex items-center gap-2">
        <button
          onClick={() => navigate({ to: '/app' })}
          className="flex items-center gap-1 font-mono text-xs text-text-muted transition-colors hover:text-text-secondary"
        >
          <ArrowLeft size={14} /> Back
        </button>
        <span className="text-text-dim">/</span>
        <span className="hidden max-w-[300px] truncate font-mono text-xs text-text-muted sm:inline-block">
          Tracker / {event.event_title}
        </span>
      </div>

      <div>
        <h1 className="mt-2 mb-4 font-heading text-2xl font-bold leading-tight text-text-primary sm:text-3xl">
          {event.event_title}
        </h1>

        <div className="flex flex-wrap items-center gap-4">
          <span className="rounded border border-border/60 bg-navy px-2 py-1 font-mono text-[10px] uppercase tracking-widest text-text-secondary shadow-sm">
            {event.source} / {event.currency}
          </span>
          {event.highest_scoring_market?.signal && (
            <span className={`rounded border px-3 py-1 font-mono text-xs font-bold shadow-sm ${getScoreColor(event.highest_scoring_market.signal.score)}`}>
              HEAT SCORE {event.highest_scoring_market.signal.score}
            </span>
          )}
          <span className="font-mono text-xs text-text-muted">
            Total Pool: {formatCurrencyCompact(event.currency, event.total_liquidity)}
          </span>
          <span className="ml-auto font-mono text-xs text-text-muted">
            Updated {formatRelative(event.last_updated)}
          </span>
        </div>
      </div>

      {eventLeader && (
        <div className="rounded-xl border border-border bg-card p-4 sm:p-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0">
              <div className="font-mono text-[10px] uppercase tracking-[0.24em] text-text-muted">Overall Event Leader</div>
              <div className="mt-2 break-words font-body text-base leading-7 text-text-primary sm:text-lg">
                {eventLeader.market_title}
              </div>
              <div className="mt-2 font-mono text-[11px] text-text-secondary">
                The overall event heat is led by score, not by order count alone.
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <span className={`rounded border px-3 py-1 font-mono text-xs font-bold shadow-sm ${getScoreColor(eventLeader.signal.score)}`}>
                Leader Score {eventLeader.signal.score}
              </span>
              {selectedOutcome && selectedOutcome.market_id !== eventLeader.market_id && (
                <button
                  onClick={() => setActiveTabId(eventLeader.market_id)}
                  className="rounded border border-prism-blue/30 bg-navy px-3 py-1 font-mono text-[11px] text-prism-cyan transition-colors hover:border-prism-blue hover:text-text-primary"
                >
                  View leader
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="relative mt-2 overflow-hidden rounded-2xl border border-prism-blue/25 bg-navy-mid p-6">
        <div className="absolute top-0 bottom-0 left-0 w-[3px] bg-gradient-to-b from-prism-violet to-prism-cyan" />
        <div className="mb-3 flex items-center justify-between">
          <h2 className="flex items-center gap-2 font-mono text-xs uppercase tracking-wide text-prism-cyan">
            <Sparkles size={14} /> AI Interpretation
          </h2>
          <span className="font-mono text-[10px] text-text-dim">Placeholder until AI layer is live</span>
        </div>
        <blockquote className="border-l-2 border-prism-blue/40 pl-4 font-body text-[0.9375rem] italic leading-[1.75] text-text-primary">
          {event.ai_insight || 'Insight unavailable'}
        </blockquote>
      </div>

      <div className="mt-4 border-b border-border/50">
        <div className="hide-scrollbar flex gap-2 overflow-x-auto pb-1">
          {event.markets.map((outcome) => (
            <button
              key={outcome.market_id}
              onClick={() => setActiveTabId(outcome.market_id)}
              className={`flex min-w-[180px] max-w-[240px] shrink-0 flex-col items-start gap-2 rounded-t-lg border-b-2 px-3 py-3 text-left font-mono text-sm transition-all sm:min-w-[220px] sm:px-4 ${
                activeTabId === outcome.market_id
                  ? 'border-prism-blue bg-navy-mid/50 text-text-primary'
                  : 'border-transparent text-text-muted hover:bg-navy-mid/30 hover:text-text-secondary'
              }`}
            >
              <span className="w-full break-words whitespace-normal text-xs leading-relaxed sm:text-sm">
                {outcome.market_title}
              </span>
              <span className={`rounded-full px-2 py-1 text-[10px] ${getScoreColor(outcome.signal.score)}`}>
                Score {outcome.signal.score}
              </span>
            </button>
          ))}
        </div>
      </div>

      <div className="dynamic-panel mt-4 flex w-full flex-col gap-6">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <div className="flex flex-col items-center justify-center rounded-xl border border-border bg-card p-6 text-center">
            <span className="mb-4 font-mono text-xs uppercase tracking-wider text-text-muted">Current Probability</span>
            <div className="flex items-baseline gap-2">
              <span className="flex items-baseline font-mono text-4xl font-bold text-text-primary">
                {Math.round((selectedOutcome.current_probability || 0) * 100)}<span className="text-2xl">%</span>
              </span>
            </div>
            <div
              className={`mt-2 font-mono text-xs ${
                selectedOutcome.probability_delta > 0
                  ? 'text-emerald-400'
                  : selectedOutcome.probability_delta < 0
                    ? 'text-amber-500'
                    : 'text-slate-400'
              }`}
            >
              ({selectedOutcome.probability_delta > 0 ? '+' : ''}
              {(selectedOutcome.probability_delta * 100).toFixed(2)} pts move)
            </div>
          </div>

          <div className="md:col-span-2 flex flex-col justify-center rounded-xl border border-border bg-card p-5 sm:p-6">
            <div className="mb-6 flex items-center gap-2">
              <Activity size={16} className="text-prism-blue" />
              <h3 className="font-mono text-xs uppercase tracking-wide text-text-muted">Live Microstructure</h3>
              <span className="truncate font-mono text-[10px] text-text-dim">
                / {selectedOutcome.market_title}
              </span>
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4 xl:divide-x xl:divide-border xl:gap-0">
              <div className="flex min-w-0 flex-col items-center justify-center border-b border-border/60 px-2 pb-4 text-center sm:border-b-0 sm:px-4 sm:pb-0">
                <span className="mb-1 break-words text-center font-mono text-2xl font-bold leading-tight text-text-primary sm:text-xl lg:text-2xl">
                  {formatCurrencyCompact(event.currency, selectedOutcome.event_liquidity)}
                </span>
                <span className="flex flex-wrap items-center justify-center gap-1 text-center font-mono text-[10px] uppercase text-text-muted">
                  <Droplets size={10} /> Event Pool
                </span>
              </div>
              <div className="flex min-w-0 flex-col items-center justify-center border-b border-border/60 px-2 pb-4 text-center sm:border-b-0 sm:px-4 sm:pb-0">
                <span className="mb-1 break-words text-center font-mono text-2xl font-bold leading-tight text-text-primary sm:text-xl lg:text-2xl">
                  {displaySelectedFlow > 0 ? formatCurrencyCompact(event.currency, displaySelectedFlow) : '—'}
                </span>
                <span className="flex flex-wrap items-center justify-center gap-1 text-center font-mono text-[10px] uppercase text-text-muted">
                  <Activity size={10} /> Selected Flow
                </span>
              </div>
              <div className="flex min-w-0 flex-col items-center justify-center border-b border-border/60 px-2 pb-4 text-center xl:border-b-0 xl:px-4 xl:pb-0">
                <span className="mb-1 break-words text-center font-mono text-2xl font-bold leading-tight text-text-primary sm:text-xl lg:text-2xl">
                  {selectedOutcome.market_total_orders?.toLocaleString() || 0}
                </span>
                <span className="flex flex-wrap items-center justify-center gap-1 text-center font-mono text-[10px] uppercase text-text-muted">
                  <Users size={10} /> Market Orders
                </span>
              </div>
              <div className="flex min-w-0 flex-col items-center justify-center px-2 text-center xl:px-4">
                <span className="mb-1 break-words text-center font-mono text-2xl font-bold leading-tight text-text-primary sm:text-xl lg:text-2xl">
                  {selectedOutcome.signal.score}
                </span>
                <span className="flex flex-wrap items-center justify-center gap-1 text-center font-mono text-[10px] uppercase text-text-muted">
                  <Zap size={10} /> Signal
                </span>
              </div>
            </div>
            {hasObservedFlow ? (
              <div className="mt-4 grid grid-cols-1 gap-2 font-mono text-[10px] uppercase tracking-wide text-text-dim sm:grid-cols-2">
                <div>Buy flow: {formatCurrencyCompact(event.currency, selectedOutcome.buy_notional || 0)}</div>
                <div>Sell flow: {formatCurrencyCompact(event.currency, selectedOutcome.sell_notional || 0)}</div>
              </div>
            ) : event.source === 'POLYMARKET' && marketVolumeProxy > 0 ? (
              <div className="mt-2 font-mono text-[10px] text-text-dim">
                Using Polymarket market volume as the selected-flow proxy until trade-side flow accumulates.
              </div>
            ) : null}
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="rounded-xl border border-border bg-navy-mid p-6">
            <div className="mb-4 flex items-center gap-2">
              {selectedOutcome.signal.direction === 'RISING' ? (
                <TrendingUp size={16} className="text-emerald-400" />
              ) : (
                <TrendingDown size={16} className="text-amber-500" />
              )}
              <h3 className="font-mono text-xs uppercase tracking-wide text-text-muted">Momentum Assessment</h3>
            </div>
            <div className="mb-3 font-mono text-lg font-bold text-text-primary">
              {selectedOutcome.signal.direction}
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-navy">
              <div
                className={`h-full ${
                  selectedOutcome.signal.direction === 'RISING'
                    ? 'bg-emerald-400'
                    : selectedOutcome.signal.direction === 'FALLING'
                      ? 'bg-amber-500'
                      : 'bg-slate-400'
                }`}
                style={{ width: `${Math.max(8, selectedOutcome.signal.score)}%` }}
              />
            </div>
            <div className="mt-2 text-right font-mono text-[10px] text-text-muted">
              {selectedOutcome.signal.classification.replace(/_/g, ' ')}
            </div>
          </div>

          <div className="rounded-xl border border-border bg-navy-mid p-5 sm:p-6">
            <div className="mb-4 flex items-center gap-2">
              <Activity size={16} className="text-prism-blue" />
              <h3 className="font-mono text-xs uppercase tracking-wide text-text-muted">Signal Notes</h3>
            </div>
            {signalNotes.length > 0 ? (
              <div className="flex flex-col gap-2">
                {signalNotes.map((note, index) => (
                  <p key={index} className="break-words font-body text-sm leading-8 text-text-primary/85">
                    {note}
                  </p>
                ))}
              </div>
            ) : (
              <p className="break-words font-body text-sm leading-8 text-text-primary/85">
                No additional signal notes yet. This market is still using the current live state and scoring snapshot.
              </p>
            )}
          </div>
        </div>

        <div className="rounded-xl border border-border bg-card p-6">
          <div className="mb-4 flex items-center gap-2">
            <Activity size={16} className="text-prism-blue" />
            <h3 className="font-mono text-xs uppercase tracking-wide text-text-muted">Factor Breakdown</h3>
          </div>
          {factorEntries.length > 0 ? (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {factorEntries.map(([label, value]) => (
                <div key={label} className="rounded-lg border border-border/60 bg-navy p-4">
                  <div className="font-mono text-[10px] uppercase tracking-wider text-text-muted">{label}</div>
                  <div className="mt-2 font-mono text-2xl text-text-primary">
                    {Math.round(((value as number) || 0) * 100)}%
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="font-body text-sm text-text-secondary">
              Factor details are not available yet for this market snapshot.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
