import React, { useState, useLayoutEffect, useRef } from 'react';
import { useParams, useNavigate } from '@tanstack/react-router';
import { mockEvents } from '../../data/mockEvents';
import type { EventOutcome } from '../../data/mockEvents';
import { ShieldAlert, TrendingUp, TrendingDown, Activity, Sparkles, AlertTriangle, Users, Droplets, Zap, CheckCircle, ArrowLeft } from 'lucide-react';
import gsap from 'gsap';

export function EventDetail() {
  const { marketId: eventId } = useParams({ strict: false }) as { marketId: string };
  const navigate = useNavigate();
  const container = useRef<HTMLDivElement>(null);
  
  // Actually look for eventId, since the router passes marketId right now we map it.
  const event = mockEvents.find(e => e.id === eventId) || mockEvents[0];
  
  const [activeTabId, setActiveTabId] = useState<string>(event.highest_scoring_market.id);
  const selectedOutcome = event.outcomes.find(o => o.id === activeTabId) || event.outcomes[0];

  useLayoutEffect(() => {
    const ctx = gsap.context(() => {
      // Animate dynamic panel content when tab changes
      gsap.fromTo('.dynamic-panel', 
        { opacity: 0, y: 10 },
        { opacity: 1, y: 0, duration: 0.4, ease: 'power2.out' }
      );
    }, container);
    return () => ctx.revert();
  }, [activeTabId]);

  if (!event) return <div className="text-white p-10 text-center">Event not found</div>;

  const getScoreColor = (score: number) => {
    if (score >= 70) return 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20';
    if (score >= 40) return 'text-slate-400 bg-slate-400/10 border-slate-400/20';
    return 'text-amber-500 bg-amber-500/10 border-amber-500/20';
  };

  const getRiskColor = (risk: string) => {
    if (risk === 'HIGH') return 'text-amber-500 border-amber-500/20 bg-amber-500/5';
    if (risk === 'MEDIUM') return 'text-slate-400 border-slate-400/20 bg-slate-400/5';
    return 'text-emerald-400 border-emerald-400/20 bg-emerald-400/5';
  };

  return (
    <div ref={container} className="max-w-4xl mx-auto px-6 py-8 flex flex-col gap-6">
      
      {/* Breadcrumbs & Back */}
      <div className="flex items-center gap-2">
        <button onClick={() => navigate({ to: '/app' })} className="flex items-center gap-1 font-mono text-xs text-text-muted hover:text-text-secondary transition-colors">
          <ArrowLeft size={14} /> Back
        </button>
        <span className="text-text-dim">/</span>
        <span className="font-mono text-xs text-text-muted hidden sm:inline-block truncate max-w-[300px]">
          Tracker → {event.title}
        </span>
      </div>

      {/* Section A: The Header */}
      <div>
        <h1 className="font-heading text-2xl sm:text-3xl text-text-primary font-bold leading-tight mt-2 mb-4">
          {event.title}
        </h1>
        
        <div className="flex flex-wrap items-center gap-4">
          <span className="font-mono text-[10px] uppercase bg-navy border border-border/60 px-2 py-1 rounded text-text-secondary tracking-widest shadow-sm">
            {event.source}
          </span>
          <span className={`font-mono text-xs font-bold px-3 py-1 rounded border shadow-sm ${getScoreColor(event.highest_scoring_market.signal.score)}`}>
            HEAT SCORE {event.highest_scoring_market.signal.score}
          </span>
          <span className="font-mono text-xs text-text-muted">
            Total Pool: ${(event.total_liquidity / 1000000).toFixed(1)}M
          </span>
          <span className="font-mono text-xs text-text-muted ml-auto">
            Updated {event.last_updated}
          </span>
        </div>
      </div>

      {/* Section B: The AI Insight */}
      <div className="mt-2 bg-navy-mid border border-prism-blue/25 rounded-2xl p-6 relative overflow-hidden">
        <div className="absolute left-0 top-0 bottom-0 w-[3px] bg-gradient-to-b from-prism-violet to-prism-cyan" />
        <div className="flex justify-between items-center mb-3">
          <h2 className="font-mono text-xs text-prism-cyan flex items-center gap-2 uppercase tracking-wide">
            <Sparkles size={14} /> AI Interpretation
          </h2>
          <span className="font-mono text-[10px] text-text-dim">Powered by Google Gemini</span>
        </div>
        <blockquote className="pl-4 border-l-2 border-prism-blue/40 font-body italic text-text-primary text-[0.9375rem] leading-[1.75]">
          {event.ai_insight}
        </blockquote>
      </div>

      {/* Section C: The Universal Tab Bar */}
      <div className="mt-4 border-b border-border/50">
        <div className="flex overflow-x-auto hide-scrollbar gap-2 pb-[-1px]">
          {event.outcomes.map((outcome) => (
            <button
              key={outcome.id}
              onClick={() => setActiveTabId(outcome.id)}
              className={`whitespace-nowrap px-4 py-3 font-mono text-sm transition-all border-b-2 flex flex-col items-center gap-1 min-w-[120px] ${
                activeTabId === outcome.id
                  ? 'border-prism-blue text-text-primary bg-navy-mid/50 rounded-t-lg'
                  : 'border-transparent text-text-muted hover:text-text-secondary hover:bg-navy-mid/30 rounded-t-lg'
              }`}
            >
              <span>{outcome.name}</span>
              <span className={`text-[10px] px-1.5 rounded-full ${getScoreColor(outcome.signal.score)}`}>
                Score {outcome.signal.score}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Section D: The Outcome Details (Dynamic Panel) */}
      <div className="dynamic-panel flex flex-col gap-6 w-full">
        
        {/* Core Outcome Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="md:col-span-1 bg-card border border-border rounded-xl p-6 flex flex-col items-center justify-center text-center">
            <span className="font-mono text-xs text-text-muted uppercase mb-4 tracking-wider">Current Probability</span>
            <div className="flex items-baseline gap-2">
              <span className="font-mono text-4xl font-bold text-text-primary flex items-baseline">
                {selectedOutcome.current_probability}<span className="text-2xl">%</span>
              </span>
            </div>
            <div className={`mt-2 font-mono text-xs ${selectedOutcome.probability_delta > 0 ? 'text-emerald-400' : 'text-amber-500'}`}>
              ({selectedOutcome.probability_delta > 0 ? '+' : ''}{selectedOutcome.probability_delta}% move)
            </div>
          </div>

          <div className="md:col-span-2 bg-card border border-border rounded-xl p-6 flex flex-col justify-center">
            <div className="flex items-center gap-2 mb-6">
              <Activity size={16} className="text-prism-blue" />
              <h3 className="font-mono text-xs text-text-muted uppercase tracking-wide">Live Microstructure</h3>
            </div>
            <div className="grid grid-cols-3 gap-4 divide-x divide-border">
              <div className="flex flex-col items-center justify-center px-2">
                <span className="font-mono text-xl font-bold text-text-primary mb-1">${(selectedOutcome.liquidity / 1000).toFixed(0)}k</span>
                <span className="font-mono text-[10px] text-text-muted flex items-center gap-1 uppercase"><Droplets size={10}/> Liquidity</span>
              </div>
              <div className="flex flex-col items-center justify-center px-2">
                <span className="font-mono text-xl font-bold text-text-primary mb-1">{selectedOutcome.orders.toLocaleString()}</span>
                <span className="font-mono text-[10px] text-text-muted flex items-center gap-1 uppercase"><Users size={10}/> Orders</span>
              </div>
              <div className="flex flex-col items-center justify-center px-2">
                <span className="font-mono text-xl font-bold text-text-primary mb-1">{selectedOutcome.volume_ratio}x</span>
                <span className="font-mono text-[10px] text-text-muted flex items-center gap-1 uppercase"><Zap size={10}/> Vol Spk</span>
              </div>
            </div>
          </div>
        </div>

        {/* Quant Boxes */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          
          <div className={`border rounded-xl p-6 relative overflow-hidden ${getRiskColor(selectedOutcome.quant_data.trap_risk)}`}>
            <div className="flex items-center gap-2 mb-4">
              <AlertTriangle size={16} />
              <h3 className="font-mono text-xs uppercase tracking-wide font-bold">Trap Risk: {selectedOutcome.quant_data.trap_risk}</h3>
            </div>
            <p className="font-body text-sm leading-relaxed opacity-90">
              {selectedOutcome.quant_data.trap_reason}
            </p>
          </div>

          <div className="bg-navy-mid border border-border rounded-xl p-6">
            <div className="flex items-center gap-2 mb-4">
              {selectedOutcome.quant_data.momentum_verdict === 'Likely to Continue' ? <TrendingUp size={16} className="text-emerald-400" /> : <TrendingDown size={16} className="text-amber-500" />}
              <h3 className="font-mono text-xs text-text-muted uppercase tracking-wide">Momentum Assessment</h3>
            </div>
            <div className="font-mono font-bold text-lg text-text-primary mb-3">
              {selectedOutcome.quant_data.momentum_verdict}
            </div>
            <div className="w-full bg-navy rounded-full h-1.5 overflow-hidden">
               <div 
                 className={`h-full ${selectedOutcome.quant_data.momentum_verdict === 'Likely to Continue' ? 'bg-emerald-400' : 'bg-amber-500'}`} 
                 style={{ width: `${selectedOutcome.quant_data.momentum_confidence}%` }}
               />
            </div>
            <div className="mt-2 text-right font-mono text-[10px] text-text-muted">
              {selectedOutcome.quant_data.momentum_confidence}% Confidence
            </div>
          </div>

        </div>

      </div>
    </div>
  );
}
