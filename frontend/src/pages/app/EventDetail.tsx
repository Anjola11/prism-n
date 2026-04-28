import React, { useLayoutEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate, useParams, useSearch } from '@tanstack/react-router';
import { Activity, ArrowLeft, Droplets, ExternalLink, Sparkles, TrendingDown, TrendingUp, Users, Zap } from 'lucide-react';
import gsap from 'gsap';

import { marketsApi } from '../../lib/api/markets';
import type { EventDetailApi, EventMarketApi } from '../../lib/api/types';
import { formatCurrencyCompact, formatRelative } from '../../lib/format';
import { computeVerdict, getFactorBarClass, getFactorInterpretation, getVerdictToneClass } from '../../lib/signals';
import { ConvictionChart } from '../../components/ui/ConvictionChart';
import { FlowDivergenceBar } from '../../components/ui/FlowDivergenceBar';
import { TopContendersPanel } from '../../components/ui/TopContendersPanel';

function resolveMarketFocus(market: EventMarketApi | null | undefined) {
  if (!market) {
    return {
      side: 'YES',
      label: 'YES',
      probability: null as number | null,
    };
  }

  if (market.probability_delta > 0 || market.signal.direction === 'RISING') {
    return {
      side: 'YES',
      label: market.yes_outcome_label || 'YES',
      probability: market.current_probability,
    };
  }

  if (market.probability_delta < 0 || market.signal.direction === 'FALLING') {
    return {
      side: 'NO',
      label: market.no_outcome_label || 'NO',
      probability: market.inverse_probability,
    };
  }

  if (
    typeof market.current_probability === 'number' &&
    typeof market.inverse_probability === 'number' &&
    market.inverse_probability > market.current_probability
  ) {
    return {
      side: 'NO',
      label: market.no_outcome_label || 'NO',
      probability: market.inverse_probability,
    };
  }

  return {
    side: 'YES',
    label: market.yes_outcome_label || 'YES',
    probability: market.current_probability,
  };
}

function getTradeSourceUrl(event: EventDetailApi | null) {
  if (!event) {
    return null;
  }

  const normalizedSource = event.source?.toUpperCase?.() || '';
  const slugCandidate =
    event.event_slug ||
    event.event_title
      ?.toLowerCase()
      .trim()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '') ||
    event.event_id;

  if (normalizedSource === 'BAYSE') {
    return `https://app.bayse.markets/market/${event.event_id}`;
  }

  if (normalizedSource === 'POLYMARKET') {
    return `https://polymarket.com/event/${slugCandidate}`;
  }

  return null;
}

export function EventDetail() {
  const { eventId } = useParams({ strict: false }) as { eventId: string };
  const search = useSearch({ from: '/app/events/$eventId' }) as { source?: string; origin?: string };
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
  const isTrackedEvent = Boolean(event?.tracking_enabled);
  const isLiveSynced = Boolean(event && event.data_mode === 'tracked_live' && event.last_updated);
  const isAnalyzing = Boolean(event) && isTrackedEvent && !isLiveSynced;
  const originLabel = search.origin === 'tracker' ? 'Tracker' : 'Discovery';
  const backTarget = search.origin === 'tracker' ? '/app/tracker' : '/app';

  React.useEffect(() => {
    if (!event) return;
    const canonicalSource = event.source?.toLowerCase?.();
    if (!canonicalSource || canonicalSource === (search.source || '').toLowerCase()) return;
    navigate({
      to: '/app/events/$eventId',
      params: { eventId },
      search: { source: canonicalSource, origin: search.origin || '' },
      replace: true,
    });
  }, [event, eventId, navigate, search.origin, search.source]);

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
  const leaderFocusLabel = eventLeader?.focus_outcome_label || eventLeader?.focus_outcome_side || null;
  const selectedFocus = React.useMemo(() => resolveMarketFocus(selectedOutcome), [selectedOutcome]);
  const tradeSourceUrl = React.useMemo(() => getTradeSourceUrl(event), [event]);
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
  const tradeThesis = React.useMemo(() => {
    if (!selectedOutcome) {
      return null;
    }

    const score = selectedOutcome.signal.score;
    const confidence =
      score >= 70 ? 'Strong conviction' : score >= 40 ? 'Moderate conviction' : 'Weak conviction';
    const traderStance =
      score >= 70
        ? 'Momentum is believable enough to trade with, as long as the order flow keeps supporting it.'
        : score >= 40
          ? 'There is a usable read here, but it still needs confirmation before taking serious size.'
          : 'This is better treated as a watchlist setup than a clean trade signal right now.';

    const support: string[] = [];
    if (selectedOutcome.probability_delta > 0.01) {
      support.push(`price is expanding toward ${selectedFocus.label}`);
    } else if (selectedOutcome.probability_delta < -0.01) {
      support.push(`price is backing away from ${selectedOutcome.yes_outcome_label}, which strengthens ${selectedFocus.label}`);
    } else {
      support.push('price is not expanding much yet');
    }

    if ((selectedOutcome.buy_notional || 0) > (selectedOutcome.sell_notional || 0)) {
      support.push('buy flow is outweighing sell flow');
    } else if ((selectedOutcome.sell_notional || 0) > (selectedOutcome.buy_notional || 0)) {
      support.push('sell flow is heavier than buy flow');
    } else if (displaySelectedFlow > 0) {
      support.push('there is activity, but not a clean flow imbalance yet');
    }

    if (selectedOutcome.signal.direction === 'RISING') {
      support.push('the live direction is still rising');
    } else if (selectedOutcome.signal.direction === 'FALLING') {
      support.push('the live direction is rolling over');
    } else {
      support.push('the live direction is flat for now');
    }

    const invalidate =
      selectedFocus.side === 'YES'
        ? 'Invalidate the long idea if delta flips negative, the score fades more, or sell flow starts dominating.'
        : 'Invalidate the fade idea if delta flips back up, the score firms up, or buy flow retakes control.';

    return {
      bias: `${selectedFocus.label} on ${selectedOutcome.market_title}`,
      confidence,
      traderStance,
      support: support.slice(0, 3),
      invalidate,
      focusProbability:
        typeof selectedFocus.probability === 'number' ? Math.round(selectedFocus.probability * 100) : null,
    };
  }, [displaySelectedFlow, selectedFocus, selectedOutcome]);
  const verdict = React.useMemo(
    () =>
      selectedOutcome
        ? computeVerdict({
            score: selectedOutcome.signal.score,
            direction: selectedOutcome.signal.direction,
            buyNotional: selectedOutcome.buy_notional || 0,
            sellNotional: selectedOutcome.sell_notional || 0,
            probabilityDelta: selectedOutcome.probability_delta,
          })
        : null,
    [selectedOutcome],
  );
  const scoreHistoryQuery = useQuery({
    queryKey: ['score-history', eventId, selectedOutcome?.market_id, requestedSource],
    queryFn: () => marketsApi.getScoreHistory(eventId, selectedOutcome?.market_id, 48, undefined, requestedSource),
    enabled: !!eventId && !!selectedOutcome?.market_id,
    staleTime: 5 * 60_000,
    gcTime: 10 * 60_000,
  });
  const selectedFlowSignal = React.useMemo(() => {
    if (!selectedOutcome) {
      return null;
    }
    const buy = selectedOutcome.buy_notional || 0;
    const sell = selectedOutcome.sell_notional || 0;
    const total = buy + sell;
    const buyRatio = total > 0 ? buy / total : 0.5;
    const divergence = buyRatio > 0.65 || buyRatio < 0.35;
    return {
      buy_ratio: buyRatio,
      buy_notional: buy,
      sell_notional: sell,
      unusual_flow: event?.flow_signal?.unusual_flow ?? false,
      divergence,
      flow_note:
        event?.flow_signal?.flow_note ||
        (buyRatio > 0.65
          ? 'Buy flow is dominant on the selected market.'
          : buyRatio < 0.35
            ? 'Sell pressure is dominant on the selected market.'
            : 'Balanced flow - no clear directional pressure'),
    };
  }, [event?.flow_signal?.flow_note, event?.flow_signal?.unusual_flow, selectedOutcome]);

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
  if (!event || !selectedOutcome) return <div className="p-10 text-center text-text-primary">Event not found</div>;

  const getScoreColor = (score: number) => {
    if (score >= 70) return 'signal-badge-high';
    if (score >= 40) return 'signal-badge-mid';
    return 'signal-badge-low';
  };

  const factorEntries = selectedOutcome.signal?.factors
    ? Object.entries(selectedOutcome.signal.factors).filter(([, value]) => typeof value === 'number')
    : [];

  return (
    <div ref={container} className="mx-auto flex max-w-4xl flex-col gap-6 px-6 py-8">
      <div className="flex items-center gap-2">
        <button
          onClick={() => navigate({ to: backTarget })}
          className="flex items-center gap-1 font-mono text-xs text-text-muted transition-colors hover:text-text-secondary"
        >
          <ArrowLeft size={14} /> Back
        </button>
        <span className="text-text-dim">/</span>
        <span className="hidden max-w-[300px] truncate font-mono text-xs text-text-muted sm:inline-block">
          {originLabel} / {event.event_title}
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
            {isAnalyzing ? 'Analyzing live state...' : `Updated ${formatRelative(event.last_updated)}`}
          </span>
          {tradeSourceUrl && (
            <button
              type="button"
              onClick={() => window.open(tradeSourceUrl, '_blank', 'noopener,noreferrer')}
              className="inline-flex items-center gap-2 rounded border border-prism-blue/30 bg-navy px-3 py-1.5 font-mono text-[11px] uppercase tracking-wide text-prism-cyan transition-colors hover:border-prism-blue hover:text-text-primary"
            >
              View trade on {event.source} <ExternalLink size={12} />
            </button>
          )}
        </div>
      </div>

      {isAnalyzing && (
        <div className="rounded-xl border border-prism-blue/25 bg-prism-blue/8 px-4 py-3 font-mono text-[11px] uppercase tracking-[0.18em] text-prism-cyan">
          Initial snapshot loaded. Waiting for first live sync.
        </div>
      )}

      {eventLeader && (
        <div className="rounded-xl border border-border bg-card p-4 sm:p-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0">
              <div className="font-mono text-[10px] uppercase tracking-[0.24em] text-text-muted">Overall Event Leader</div>
              <div className="mt-2 break-words font-body text-base leading-7 text-text-primary sm:text-lg">
                {eventLeader.market_title}
              </div>
              {leaderFocusLabel && (
                <div className="mt-2 font-mono text-[11px] uppercase tracking-[0.18em] text-prism-cyan">
                  Focus side: {leaderFocusLabel}
                </div>
              )}
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

      {verdict && (
        <div className="overflow-hidden rounded-r-xl border border-border bg-card">
          <div className={`flex items-center justify-between gap-4 border-l-[3px] px-4 py-3 ${getVerdictToneClass(verdict.tone)}`}>
            <span className={`truncate font-mono text-sm font-bold uppercase tracking-[0.24em] ${getVerdictToneClass(verdict.tone)}`}>
              {verdict.label}
            </span>
            <span className="truncate font-body text-sm text-text-secondary">{verdict.detail}</span>
          </div>
        </div>
      )}

      <div className="relative mt-2 overflow-hidden rounded-2xl border border-prism-blue/25 bg-navy-mid p-6">
        <div className="absolute top-0 bottom-0 left-0 w-[3px] bg-gradient-to-b from-prism-violet to-prism-cyan" />
        <div className="mb-3 flex items-center justify-between">
          <h2 className="flex items-center gap-2 font-mono text-xs uppercase tracking-wide text-prism-cyan">
            <Sparkles size={14} /> AI Interpretation
          </h2>
          <span className="font-mono text-[10px] text-text-dim">{isAnalyzing ? 'Building first live read' : 'Live event read'}</span>
        </div>
        <blockquote className="border-l-2 border-prism-blue/40 pl-4 font-body text-[0.9375rem] leading-[1.75] text-text-primary not-italic">
          {event.ai_insight || 'AI insight unavailable'}
        </blockquote>
      </div>

      {tradeThesis && (
        <div className="rounded-2xl border border-border bg-card p-5 sm:p-6">
          <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div className="font-mono text-[10px] uppercase tracking-[0.22em] text-text-muted">Trade Thesis</div>
              <h2 className="mt-2 font-heading text-lg text-text-primary sm:text-xl">{tradeThesis.bias}</h2>
            </div>
            <div className={`rounded border px-3 py-1 font-mono text-xs font-bold shadow-sm ${getScoreColor(selectedOutcome.signal.score)}`}>
              {tradeThesis.confidence}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div className="rounded-xl border border-border/60 bg-navy p-4">
              <div className="font-mono text-[10px] uppercase tracking-wider text-text-muted">What Prism is saying</div>
              <p className="mt-3 font-body text-sm leading-7 text-text-primary/90">{tradeThesis.traderStance}</p>
            </div>

            <div className="rounded-xl border border-border/60 bg-navy p-4">
              <div className="font-mono text-[10px] uppercase tracking-wider text-text-muted">What supports it</div>
              <div className="mt-3 flex flex-col gap-2">
                {tradeThesis.support.map((item) => (
                  <p key={item} className="font-body text-sm leading-7 text-text-primary/90">
                    {item}
                  </p>
                ))}
              </div>
            </div>

            <div className="rounded-xl border border-border/60 bg-navy p-4">
              <div className="font-mono text-[10px] uppercase tracking-wider text-text-muted">What would invalidate it</div>
              <p className="mt-3 font-body text-sm leading-7 text-text-primary/90">{tradeThesis.invalidate}</p>
              {tradeThesis.focusProbability !== null && (
                <div className="mt-4 font-mono text-[11px] uppercase tracking-wide text-prism-cyan">
                  Focus side priced near {tradeThesis.focusProbability}%
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="relative mt-4 border-b border-border/50">
        <div className="hide-scrollbar flex gap-2 overflow-x-auto pb-1 pr-10">
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
        <div className="pointer-events-none absolute top-0 right-0 bottom-0 w-10 bg-gradient-to-r from-transparent to-void" />
      </div>

      <div className="dynamic-panel mt-4 flex w-full flex-col gap-6">
        <div className="rounded-xl border border-border bg-card p-5 sm:p-6">
          <div className="mb-4 font-mono text-[10px] uppercase tracking-[0.22em] text-text-muted">
            Conviction & Probability - 48h
          </div>
          <ConvictionChart points={scoreHistoryQuery.data?.points ?? []} loading={scoreHistoryQuery.isLoading} />
        </div>

        <TopContendersPanel event={event} activeTabId={activeTabId} onSelect={setActiveTabId} />

        <div className="flex flex-col justify-center rounded-xl border border-border bg-card p-5 sm:p-6">
            <div className="mb-6 flex items-center gap-2">
              <Activity size={16} className="text-prism-blue" />
              <h3 className="font-mono text-xs uppercase tracking-wide text-text-muted">Live Microstructure</h3>
              <span className="truncate font-mono text-[10px] text-text-dim">
                / {selectedOutcome.market_title}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-4 xl:grid-cols-4 xl:divide-x xl:divide-border xl:gap-0">
              <div className="flex min-w-0 flex-col items-center justify-center border-b border-border/60 px-2 pb-4 text-center xl:border-b-0 xl:px-4 xl:pb-0">
                <span className="mb-1 break-words text-center font-mono text-2xl font-bold leading-tight text-text-primary sm:text-xl lg:text-2xl">
                  {formatCurrencyCompact(event.currency, selectedOutcome.event_liquidity)}
                </span>
                <span className="flex flex-wrap items-center justify-center gap-1 text-center font-mono text-[10px] uppercase text-text-muted">
                  <Droplets size={10} /> Event Pool
                </span>
              </div>
              <div className="flex min-w-0 flex-col items-center justify-center border-b border-border/60 px-2 pb-4 text-center xl:border-b-0 xl:px-4 xl:pb-0">
                <span className="mb-1 break-words text-center font-mono text-2xl font-bold leading-tight text-text-primary sm:text-xl lg:text-2xl">
                  {displaySelectedFlow > 0 ? formatCurrencyCompact(event.currency, displaySelectedFlow) : 'N/A'}
                </span>
                <span className="flex flex-wrap items-center justify-center gap-1 text-center font-mono text-[10px] uppercase text-text-muted">
                  <Activity size={10} /> Selected Flow
                </span>
              </div>
              <div className="flex min-w-0 flex-col items-center justify-center px-2 text-center xl:px-4">
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
            {selectedFlowSignal ? (
              <div className="mt-5">
                <FlowDivergenceBar flow={selectedFlowSignal} currency={event.currency} />
              </div>
            ) : hasObservedFlow ? (
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

        {selectedFlowSignal && (selectedFlowSignal.divergence || selectedFlowSignal.unusual_flow) && (
          <div className="overflow-hidden rounded-r-xl border border-border bg-card">
            <div className={`flex flex-col gap-2 border-l-[3px] px-4 py-3 ${selectedFlowSignal.buy_ratio >= 0.5 ? 'signal-trend-up' : 'signal-trend-down'}`}>
              <span className="font-mono text-sm font-bold uppercase tracking-[0.2em]">
                Smart Flow Signal
              </span>
              <span className="font-body text-sm text-text-secondary">{selectedFlowSignal.flow_note}</span>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="rounded-xl border border-border bg-navy-mid p-6">
            <div className="mb-4 flex items-center gap-2">
              {selectedOutcome.signal.direction === 'RISING' ? (
                <TrendingUp size={16} className="signal-icon-up" />
              ) : (
                <TrendingDown size={16} className="signal-icon-down" />
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
                    ? 'signal-bar-up'
                    : selectedOutcome.signal.direction === 'FALLING'
                      ? 'signal-bar-down'
                      : 'signal-bar-flat'
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
            <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-4">
              {factorEntries.map(([label, value]) => (
                <div key={label} className="rounded-lg border border-border/60 bg-navy p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="font-mono text-[10px] uppercase tracking-wider text-text-muted">{label}</div>
                    <div className="font-mono text-sm text-text-primary">
                      {Math.round(((value as number) || 0) * 100)}%
                    </div>
                  </div>
                  <div className="mt-3 h-1 rounded-full bg-card">
                    <div
                      className={`h-full rounded-full ${getFactorBarClass(Math.round(((value as number) || 0) * 100))}`}
                      style={{ width: `${Math.round(((value as number) || 0) * 100)}%` }}
                    />
                  </div>
                  <p className="mt-3 font-body text-xs leading-6 text-text-muted">
                    {getFactorInterpretation(label, Math.round(((value as number) || 0) * 100))}
                  </p>
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
