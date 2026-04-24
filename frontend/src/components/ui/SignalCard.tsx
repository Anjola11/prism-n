import React from 'react';
import type { DiscoveryCardViewModel } from '../../lib/api/types';
import { Clock, Plus, Check } from 'lucide-react';
import { useNavigate } from '@tanstack/react-router';

interface SignalCardProps {
  event: DiscoveryCardViewModel;
  onTrack?: (e: React.MouseEvent, id: string) => void;
  isTracked?: boolean;
}

export function SignalCard({ event, onTrack, isTracked = false }: SignalCardProps) {
  const navigate = useNavigate();
  const topMarket = event.highest_scoring_market;
  const signal = topMarket.signal;

  const isInformed = signal.classification === 'INFORMED_MOVE';
  const isUncertain = signal.classification === 'UNCERTAIN';

  let borderColor = 'border-border hover:border-prism-blue/40';
  let badgeColor = 'bg-amber-500/10 text-amber-500 border-amber-500/20'; // default noise
  let signalTextColor = 'text-amber-500';

  if (isInformed) {
    borderColor = 'border-border hover:border-emerald-400/50';
    badgeColor = 'bg-emerald-400/10 text-emerald-400 border-emerald-400/20';
    signalTextColor = 'text-emerald-400';
  } else if (isUncertain) {
    borderColor = 'border-border hover:border-slate-400/50';
    badgeColor = 'bg-slate-400/10 text-slate-400 border-slate-400/20';
    signalTextColor = 'text-slate-400';
  } else {
    // Noise
    borderColor = 'border-border hover:border-amber-500/50';
  }

  const directionArrow = signal.direction === 'RISING' ? '↑' : signal.direction === 'FALLING' ? '↓' : '→';
  const ptsPrefix = topMarket.probability_delta > 0 ? '+' : '';
  const ptsColor = topMarket.probability_delta > 0 ? 'text-emerald-400' : topMarket.probability_delta < 0 ? 'text-amber-500' : 'text-slate-400';

  const handleCardClick = () => {
    navigate({ to: `/app/events/${event.id}` });
  };

  return (
    <div 
      className={`group relative bg-navy-mid border ${borderColor} rounded-xl p-5 cursor-pointer transition-all duration-300 shadow-card hover:shadow-modal flex flex-col h-full overflow-hidden`}
      onClick={handleCardClick}
    >
      {/* Top Row */}
      <div className="flex justify-between items-start mb-2 relative z-10">
        <span className="font-mono text-[10px] uppercase bg-navy border border-border/60 px-2 py-1 rounded text-text-secondary tracking-widest shadow-sm">
          {event.source}
        </span>
        <span className={`font-mono text-xs font-bold px-2 py-0.5 rounded border shadow-sm ${badgeColor}`}>
          SCORE {signal.score}
        </span>
      </div>
      
      {/* Event Title */}
      <h3 className="font-heading text-lg font-medium text-text-primary leading-[1.35] mb-1 pr-2 relative z-10 transition-colors group-hover:text-white line-clamp-2">
        {event.title}
      </h3>

      {/* Target Subtitle (Conditional) */}
      <div className="mb-4 relative z-10">
        {event.eventType === 'combined' ? (
          <p className="font-mono text-xs text-prism-teal">
            ↳ Spiking on: {topMarket.name} (Score: {signal.score})
          </p>
        ) : (
          <p className="font-mono text-[10px] text-text-muted mt-0.5">
            ↳ Moving on: {topMarket.name}
          </p>
        )}
      </div>

      {/* AI Insight */}
      <div className="bg-navy border border-border/50 rounded-lg p-3 mb-5 mt-auto">
        <p className="font-body text-xs text-text-secondary flex gap-2 line-clamp-2">
          <span className="text-prism-cyan flex-shrink-0">↳</span>
          {event.aiInsight}
        </p>
      </div>
      
      {/* Details Row */}
      <div className="flex flex-col gap-3 border-t border-border/40 pt-4 relative z-10">
        <div className="flex items-center justify-between">
          <div className="flex flex-col gap-1">
            <span className="font-mono text-[9px] text-text-muted tracking-widest uppercase flex items-center gap-1">
              <Clock size={10} /> {event.lastUpdated || "Just now"}
            </span>
            <span className="font-mono text-sm text-text-primary">
              <span className="text-text-muted text-[10px] mr-1">POOL</span>
              ${(event.totalLiquidity / 1000000).toFixed(1)}M
            </span>
          </div>
          
          <div className="flex flex-col items-end gap-1">
            <span className="font-mono text-[9px] text-text-muted tracking-widest uppercase">
              Delta <span className={ptsColor}>({ptsPrefix}{topMarket.probability_delta}%)</span>
            </span>
            <span className={`font-body text-sm font-medium flex items-center gap-1 ${signalTextColor}`}>
              {directionArrow} {signal.classification.replace('_MOVE', '')}
            </span>
          </div>
        </div>

        {/* Track Action */}
        <div className="w-full flex justify-end mt-1">
          <button 
            onClick={(e) => onTrack?.(e, event.id)}
            className={`font-mono text-[10px] px-3 py-1.5 rounded transition-all flex items-center gap-1 ${isTracked ? 'bg-emerald-400/10 text-emerald-400 border border-emerald-400/20' : 'bg-prism-blue/10 text-prism-blue border border-prism-blue/20 hover:bg-prism-blue/20'}`}
          >
            {isTracked ? <><Check size={12}/> TRACKED</> : <><Plus size={12}/> TRACK</>}
          </button>
        </div>
      </div>
    </div>
  );
}
