import React from 'react';
import { Clock, Plus, Minus, ChevronDown, ChevronUp } from 'lucide-react';
import { useNavigate } from '@tanstack/react-router';
import { useQuery, useQueryClient } from '@tanstack/react-query';

import { marketsApi } from '../../lib/api/markets';
import { adminApi } from '../../lib/api/admin';
import type { DiscoveryCardViewModel } from '../../lib/api/types';
import { formatCurrencyCompact, formatRelative } from '../../lib/format';
import { generateAlertHeadline, getVerdictToneClass } from '../../lib/signals';
import { ScoreSparkline } from './ScoreSparkline';

interface SignalCardProps {
  event: DiscoveryCardViewModel;
  onTrack?: (e: React.MouseEvent, id: string, source: string) => void;
  isTracked?: boolean;
  isTrackPending?: boolean;
  origin?: 'discovery' | 'tracker' | 'admin';
  index?: number;
}

export function SignalCard({
  event,
  onTrack,
  isTracked = false,
  isTrackPending = false,
  origin = 'discovery',
  index = 0,
}: SignalCardProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [iconFailed, setIconFailed] = React.useState(false);
  const [ready, setReady] = React.useState(index === 0);
  const [insightExpanded, setInsightExpanded] = React.useState(false);
  const [flashUpdate, setFlashUpdate] = React.useState(false);

  React.useEffect(() => {
    if (index === 0) return;
    const timer = setTimeout(() => {
      setReady(true);
    }, Math.min(index * 100, 1000));
    return () => clearTimeout(timer);
  }, [index]);

  const topMarket = event.highestScoringMarket;
  const signal = topMarket?.signal;
  const topMarketFocusLabel = topMarket?.focusOutcomeLabel || topMarket?.focusOutcomeSide || null;
  const topMarketDescriptor = topMarketFocusLabel ? `${topMarket?.marketTitle} (${topMarketFocusLabel})` : topMarket?.marketTitle;

  const currentScoreVal = signal?.score ?? 0;
  const scoreDeltaVal = event.scoreDelta48h;
  let scoreDeltaLabel = '';
  if (scoreDeltaVal !== null && scoreDeltaVal !== undefined && scoreDeltaVal !== 0) {
    const roundedDelta = Math.round(scoreDeltaVal);
    if (roundedDelta > 0) scoreDeltaLabel = ` ▲+${roundedDelta}`;
    else if (roundedDelta < 0) scoreDeltaLabel = ` ▼${roundedDelta}`;
  }

  let borderColor = 'border-border hover:border-prism-blue/40';
  let badgeColor = 'border-slate-700 bg-slate-800/80 text-slate-400';
  let classificationBadgeColor = 'border-slate-700 bg-slate-800/80 text-slate-400';

  if (currentScoreVal >= 85 || signal?.classification === 'high_conviction') {
    borderColor = 'border-border hover:border-prism-cyan/50';
    badgeColor = 'border-prism-cyan/50 bg-prism-blue/20 text-prism-cyan shadow-[0_0_12px_rgba(56,189,248,0.25)]';
    classificationBadgeColor = 'border-prism-cyan/40 bg-prism-blue/20 text-prism-cyan';
  } else if (currentScoreVal >= 70 || signal?.classification === 'strong') {
    borderColor = 'border-border hover:border-emerald-400/50';
    badgeColor = 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400';
    classificationBadgeColor = 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400';
  } else if (currentScoreVal >= 40 || signal?.classification === 'moderate') {
    borderColor = 'border-border hover:border-amber-500/40';
    badgeColor = 'border-amber-500/40 bg-amber-500/10 text-amber-400';
    classificationBadgeColor = 'border-amber-500/40 bg-amber-500/10 text-amber-400';
  }

  if (signal?.classification?.toLowerCase() === 'noise') {
    classificationBadgeColor = 'border-slate-700 bg-slate-800/80 text-slate-400';
  }

  const normalizedDirection = (signal?.direction ?? 'STABLE').toUpperCase();
  const directionLabel =
    normalizedDirection === 'RISING' || normalizedDirection === 'UP'
      ? 'UP'
      : normalizedDirection === 'FALLING' || normalizedDirection === 'DOWN'
        ? 'DOWN'
        : 'FLAT';

  const directionArrow =
    directionLabel === 'UP'
      ? '^'
      : directionLabel === 'DOWN'
        ? 'v'
        : '-';

  const probabilityDelta = topMarket ? topMarket.probabilityDelta * 100 : 0;
  const ptsColor =
    probabilityDelta > 0
      ? 'text-emerald-400'
      : probabilityDelta < 0
        ? 'text-rose-400'
        : 'text-text-muted';

  const classificationLabel = signal?.classification
    ? signal.classification.replace(/_/g, ' ').toUpperCase()
    : 'UNSCORED';
  const isLite = event.dataMode === 'lite_snapshot';
  const isTrackedAwaitingSignal = isTracked && isLite;

  const isFresh = React.useMemo(() => {
    if (!event.lastUpdated) return false;
    const parsed = new Date(event.lastUpdated).getTime();
    return !isNaN(parsed) && Date.now() - parsed < 15000;
  }, [event.lastUpdated]);

  const prevValuesRef = React.useRef({ score: currentScoreVal, liquidity: event.totalLiquidity, prob: topMarket?.currentProbability });

  React.useEffect(() => {
    const prev = prevValuesRef.current;
    if (
      (prev.score !== currentScoreVal && prev.score > 0) ||
      (prev.liquidity !== event.totalLiquidity && prev.liquidity !== null) ||
      (prev.prob !== topMarket?.currentProbability && prev.prob !== null)
    ) {
      setFlashUpdate(true);
      const timer = setTimeout(() => setFlashUpdate(false), 700);
      prevValuesRef.current = { score: currentScoreVal, liquidity: event.totalLiquidity, prob: topMarket?.currentProbability };
      return () => clearTimeout(timer);
    }
    prevValuesRef.current = { score: currentScoreVal, liquidity: event.totalLiquidity, prob: topMarket?.currentProbability };
  }, [currentScoreVal, event.totalLiquidity, topMarket?.currentProbability]);

  const alertHeadline = React.useMemo(
    () =>
      generateAlertHeadline({
        score: signal?.score ?? 0,
        scoreDelta: event.scoreDelta48h,
        direction: signal?.direction ?? 'STABLE',
        classification: signal?.classification ?? 'unscored',
        buyNotional: topMarket?.buyNotional ?? 0,
        sellNotional: topMarket?.sellNotional ?? 0,
        marketTitle: topMarket?.marketTitle ?? event.title,
      }),
    [
      event.scoreDelta48h,
      event.title,
      signal?.classification,
      signal?.direction,
      signal?.score,
      topMarket?.buyNotional,
      topMarket?.marketTitle,
      topMarket?.sellNotional,
    ],
  );

  const fallbackInsight = React.useMemo(() => {
    if (!topMarket) {
      return isTrackedAwaitingSignal
        ? 'Prism is tracking this event live and is still waiting for enough structure to call the move clearly.'
        : 'This card is still an early snapshot. Open the event for more detail or track it so Prism can build a live read.';
    }

    const probabilityText =
      topMarket.currentProbability !== null ? `${Math.round(topMarket.currentProbability * 100)}%` : 'an early level';
    const note = signal?.notes?.find((entry) => typeof entry === 'string' && entry.trim())?.trim();

    if (isTrackedAwaitingSignal) {
      return (
        `Prism is tracking '${topMarketDescriptor}' live, and the market is currently leaning around ${probabilityText}. ` +
        (note ? `The first thing standing out is ${note.toLowerCase()}.` : 'The first live read is still settling in.')
      );
    }

    return (
      `At first glance, '${topMarketDescriptor}' is the outcome Prism would watch first, with the market sitting near ${probabilityText}. ` +
      (note ? `Early clue: ${note}.` : 'Treat this as an early clue until the event is being tracked live.')
    );
  }, [isTrackedAwaitingSignal, signal?.notes, topMarket, topMarketDescriptor]);

  const scoreHistoryQuery = useQuery({
    queryKey: ['score-history', event.id, topMarket?.marketId, 48, event.source],
    queryFn: () =>
      origin === 'admin'
        ? adminApi.getScoreHistory(event.id, topMarket?.marketId, 48, event.currency, event.source.toLowerCase())
        : marketsApi.getScoreHistory(event.id, topMarket?.marketId, 48, event.currency, event.source.toLowerCase()),
    enabled: !!topMarket?.marketId && ready,
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });

  const sparklinePoints = React.useMemo(() => {
    const historyPoints = scoreHistoryQuery.data?.points ?? [];
    if (historyPoints.length > 0) {
      return historyPoints;
    }

    if (!signal) {
      return [];
    }

    const currentScore = Math.max(0, Math.min(100, signal.score ?? 0));
    const delta = event.scoreDelta48h ?? 0;
    const baselineScore = Math.max(0, Math.min(100, currentScore - delta));

    return [
      { score: baselineScore, created_at: new Date(Date.now() - 48 * 60 * 60 * 1000).toISOString() },
      { score: (baselineScore + currentScore) / 2, created_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString() },
      { score: currentScore, created_at: new Date().toISOString() },
    ];
  }, [event.scoreDelta48h, scoreHistoryQuery.data?.points, signal]);

  const handlePrefetch = () => {
    queryClient.prefetchQuery({
      queryKey: ['event-detail', event.id, event.source.toLowerCase()],
      queryFn: () => marketsApi.getEvent(event.id, undefined, event.source.toLowerCase()),
      staleTime: 30_000,
    });
  };

  const handleCardClick = () => {
    navigate({ to: `/app/events/${event.id}`, search: { source: event.source.toLowerCase(), origin } });
  };

  const iconFallback = event.source === 'POLYMARKET' ? 'P' : 'B';
  const shouldShowImage = !!event.iconUrl && !iconFailed;
  const insightText = event.aiInsight || fallbackInsight;

  return (
    <div
      className={`group relative flex h-full cursor-pointer flex-col overflow-hidden rounded-xl border bg-navy-mid p-5 shadow-card transition-all duration-300 hover:shadow-modal ${borderColor} ${isLite ? 'opacity-90' : ''} ${flashUpdate ? 'ring-2 ring-prism-cyan/60 bg-prism-blue/10' : ''}`}
      onClick={handleCardClick}
      onMouseEnter={handlePrefetch}
    >
      <div className="relative z-10 mb-2 flex items-start justify-between">
        <span className="rounded border border-border/60 bg-navy px-2 py-1 font-mono text-[10px] uppercase tracking-widest text-text-secondary shadow-sm">
          {event.source} / {event.currency}
        </span>
        <span className={`rounded border px-2 py-0.5 font-mono text-xs font-bold shadow-sm transition-all duration-300 ${badgeColor}`}>
          {isTrackedAwaitingSignal ? 'TRACKED' : `SCORE ${signal?.score ?? 0}${scoreDeltaLabel}`}
        </span>
      </div>

      <div className="relative z-10 mb-2 flex items-start gap-3 pr-2">
        <div className="mt-0.5 flex h-11 w-11 shrink-0 items-center justify-center overflow-hidden rounded-xl border border-border/60 bg-navy shadow-sm">
          {shouldShowImage ? (
            <img
              src={event.iconUrl ?? undefined}
              alt=""
              className="h-full w-full object-cover"
              loading="lazy"
              onError={() => setIconFailed(true)}
            />
          ) : (
            <span className="font-mono text-sm font-bold text-text-secondary">{iconFallback}</span>
          )}
        </div>
        <h3 className="prism-card-title min-w-0 flex-1 font-heading text-lg font-medium leading-[1.35] transition-colors line-clamp-2">
          {event.title}
        </h3>
      </div>

      <div className="relative z-10 mb-4">
        <p className={`font-mono text-[11px] leading-relaxed ${getVerdictToneClass(alertHeadline.tone)}`}>
          {topMarket ? alertHeadline.text : 'Signal still warming up'}
        </p>
        <p className="mt-1 font-mono text-[10px] text-text-muted">
          {topMarket ? `${event.eventType === 'combined' ? 'Focus outcome' : 'Moving on'}: ${topMarketDescriptor}` : 'Waiting for the market structure to separate'}
        </p>
        {topMarket && (
          <div className="mt-3 flex items-center justify-between gap-3">
            <ScoreSparkline points={sparklinePoints} loading={scoreHistoryQuery.isLoading && sparklinePoints.length === 0} />
            {event.scoreDelta48h !== null && event.scoreDelta48h !== 0 ? (
              <span className={`shrink-0 rounded border px-2 py-0.5 font-mono text-[10px] shadow-sm ${event.scoreDelta48h > 0 ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400' : 'border-rose-500/40 bg-rose-500/10 text-rose-400'}`}>
                {event.scoreDelta48h > 0 ? '+' : ''}{Math.round(event.scoreDelta48h)} pts
              </span>
            ) : null}
          </div>
        )}
      </div>

      <div className="mb-5 mt-auto rounded-lg border border-border/50 bg-navy p-3">
        <div className="flex items-start gap-2">
          <span className="flex-shrink-0 font-mono text-xs text-prism-cyan">{'>'}</span>
          <p className={`font-body text-xs text-text-secondary transition-all ${insightExpanded ? '' : 'line-clamp-2'}`}>
            {insightText}
          </p>
        </div>
        {insightText.length > 110 && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setInsightExpanded(!insightExpanded);
            }}
            className="mt-1.5 flex items-center gap-1 font-mono text-[10px] text-prism-cyan hover:underline"
          >
            {insightExpanded ? <>less <ChevronUp size={12} /></> : <>more <ChevronDown size={12} /></>}
          </button>
        )}
      </div>

      <div className={`relative z-10 flex flex-col gap-3 border-t border-border/40 pt-4 ${isLite ? 'animate-pulse-slow' : ''}`}>
        <div className="flex items-center justify-between">
          <div className="flex flex-col gap-1">
            <span className="flex items-center gap-1.5 font-mono text-[9px] uppercase tracking-widest text-text-muted">
              {isFresh && (
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500"></span>
                </span>
              )}
              <Clock size={10} /> {formatRelative(event.lastUpdated)}
            </span>
            <span className="font-mono text-sm text-text-primary">
              <span className="mr-1 text-[10px] text-text-muted">POOL</span>
              {formatCurrencyCompact(event.currency, event.totalLiquidity)}
            </span>
          </div>

          <div className="flex flex-col items-end gap-1">
            <span className="font-mono text-[9px] uppercase tracking-widest text-text-muted">
              {isTrackedAwaitingSignal ? (
                <span className="text-text-muted">Waiting for live signal</span>
              ) : isLite ? (
                <span className="text-text-muted">Lite snapshot</span>
              ) : (
                <>Direction <span className={ptsColor}>{directionArrow}</span></>
              )}
            </span>
            <span className={`rounded border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide shadow-sm ${isTrackedAwaitingSignal ? 'border-amber-500/40 bg-amber-500/10 text-amber-400' : isLite ? 'border-slate-700 bg-slate-800/80 text-slate-300' : classificationBadgeColor}`}>
              {isTrackedAwaitingSignal ? 'TRACKED / WARMING UP' : isLite ? 'LITE SNAPSHOT' : `${directionLabel} ${classificationLabel}`}
            </span>
          </div>
        </div>

        <div className="mt-1 flex w-full justify-end">
          <button
            onClick={(e) => onTrack?.(e, event.id, event.source.toLowerCase())}
            disabled={isTrackPending}
            className={`flex items-center gap-1 rounded px-3 py-1.5 font-mono text-[10px] transition-all ${
              isTrackPending
                ? 'cursor-not-allowed border border-border bg-card text-text-muted'
                : isTracked
                  ? 'border border-amber-400/30 bg-amber-500/10 text-amber-300 hover:bg-amber-500/20'
                  : 'border border-prism-blue/20 bg-prism-blue/10 text-prism-blue hover:bg-prism-blue/20'
            }`}
          >
            {isTrackPending ? 'WORKING...' : isTracked ? <><Minus size={12} /> UNTRACK</> : <><Plus size={12} /> TRACK</>}
          </button>
        </div>
      </div>
    </div>
  );
}
