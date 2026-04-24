import React from 'react';
import { Clock, Plus, Check } from 'lucide-react';
import { useNavigate } from '@tanstack/react-router';

import type { DiscoveryCardViewModel } from '../../lib/api/types';
import { formatCurrencyCompact, formatRelative } from '../../lib/format';

interface SignalCardProps {
  event: DiscoveryCardViewModel;
  onTrack?: (e: React.MouseEvent, id: string, source: string) => void;
  isTracked?: boolean;
}

export function SignalCard({ event, onTrack, isTracked = false }: SignalCardProps) {
  const navigate = useNavigate();
  const topMarket = event.highestScoringMarket;
  const signal = topMarket?.signal;

  const isHighSignal = signal?.classification === 'high_conviction' || signal?.classification === 'strong';
  const isModerateSignal = signal?.classification === 'moderate';

  let borderColor = 'border-border hover:border-prism-blue/40';
  let badgeColor = 'bg-amber-500/10 text-amber-500 border-amber-500/20';
  let signalTextColor = 'text-amber-500';

  if (isHighSignal) {
    borderColor = 'border-border hover:border-emerald-400/50';
    badgeColor = 'bg-emerald-400/10 text-emerald-400 border-emerald-400/20';
    signalTextColor = 'text-emerald-400';
  } else if (isModerateSignal) {
    borderColor = 'border-border hover:border-slate-400/50';
    badgeColor = 'bg-slate-400/10 text-slate-300 border-slate-400/20';
    signalTextColor = 'text-slate-300';
  }

  const directionLabel =
    signal?.direction === 'RISING'
      ? 'UP'
      : signal?.direction === 'FALLING'
        ? 'DOWN'
        : 'FLAT';

  const probabilityDelta = topMarket ? topMarket.probabilityDelta * 100 : 0;
  const ptsPrefix = probabilityDelta > 0 ? '+' : '';
  const ptsColor =
    probabilityDelta > 0
      ? 'text-emerald-400'
      : probabilityDelta < 0
        ? 'text-amber-500'
        : 'text-slate-400';

  const classificationLabel = signal?.classification
    ? signal.classification.replace(/_/g, ' ').toUpperCase()
    : 'UNSCORED';
  const isLite = event.dataMode === 'lite_snapshot';
  const isTrackedAwaitingSignal = isTracked && isLite;

  const handleCardClick = () => {
    navigate({ to: `/app/events/${event.id}`, search: { source: event.source.toLowerCase() } });
  };

  const iconFallback = event.source === 'POLYMARKET' ? 'P' : 'B';

  return (
    <div
      className={`group relative flex h-full cursor-pointer flex-col overflow-hidden rounded-xl border bg-navy-mid p-5 shadow-card transition-all duration-300 hover:shadow-modal ${borderColor}`}
      onClick={handleCardClick}
    >
      <div className="relative z-10 mb-2 flex items-start justify-between">
        <span className="rounded border border-border/60 bg-navy px-2 py-1 font-mono text-[10px] uppercase tracking-widest text-text-secondary shadow-sm">
          {event.source} / {event.currency}
        </span>
        <span className={`rounded border px-2 py-0.5 font-mono text-xs font-bold shadow-sm ${badgeColor}`}>
          {isTrackedAwaitingSignal ? 'TRACKED' : isLite ? 'LITE' : `SCORE ${signal?.score ?? 0}`}
        </span>
      </div>

      <div className="relative z-10 mb-2 flex items-start gap-3 pr-2">
        <div className="mt-0.5 flex h-11 w-11 shrink-0 items-center justify-center overflow-hidden rounded-xl border border-border/60 bg-navy shadow-sm">
          {event.iconUrl ? (
            <img
              src={event.iconUrl}
              alt=""
              className="h-full w-full object-cover"
              loading="lazy"
            />
          ) : (
            <span className="font-mono text-sm font-bold text-text-secondary">{iconFallback}</span>
          )}
        </div>
        <h3 className="min-w-0 flex-1 font-heading text-lg font-medium leading-[1.35] text-text-primary transition-colors group-hover:text-white line-clamp-2">
          {event.title}
        </h3>
      </div>

      <div className="relative z-10 mb-4">
        {event.eventType === 'combined' && topMarket ? (
          <p className="font-mono text-xs text-prism-teal">
            Spiking on: {topMarket.marketTitle} (Score: {signal?.score ?? 0})
          </p>
        ) : (
          <p className="mt-0.5 font-mono text-[10px] text-text-muted">
            {topMarket ? `Moving on: ${topMarket.marketTitle}` : 'Signal still warming up'}
          </p>
        )}
      </div>

      <div className="mb-5 mt-auto rounded-lg border border-border/50 bg-navy p-3">
        <p className="flex gap-2 font-body text-xs text-text-secondary line-clamp-2">
          <span className="flex-shrink-0 text-prism-cyan">{'>'}</span>
          {event.aiInsight || 'Insight unavailable'}
        </p>
      </div>

      <div className="relative z-10 flex flex-col gap-3 border-t border-border/40 pt-4">
        <div className="flex items-center justify-between">
          <div className="flex flex-col gap-1">
            <span className="flex items-center gap-1 font-mono text-[9px] uppercase tracking-widest text-text-muted">
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
                <>Delta <span className={ptsColor}>({ptsPrefix}{probabilityDelta.toFixed(2)} pts)</span></>
              )}
            </span>
            <span className={`flex items-center gap-1 font-body text-sm font-medium ${signalTextColor}`}>
              {isTrackedAwaitingSignal ? 'TRACKED / WARMING UP' : isLite ? 'LITE SNAPSHOT' : `${directionLabel} ${classificationLabel}`}
            </span>
          </div>
        </div>

        <div className="mt-1 flex w-full justify-end">
          <button
            onClick={(e) => onTrack?.(e, event.id, event.source.toLowerCase())}
            className={`flex items-center gap-1 rounded px-3 py-1.5 font-mono text-[10px] transition-all ${
              isTracked
                ? 'border border-emerald-400/20 bg-emerald-400/10 text-emerald-400'
                : 'border border-prism-blue/20 bg-prism-blue/10 text-prism-blue hover:bg-prism-blue/20'
            }`}
          >
            {isTracked ? <><Check size={12} /> TRACKED</> : <><Plus size={12} /> TRACK</>}
          </button>
        </div>
      </div>
    </div>
  );
}
