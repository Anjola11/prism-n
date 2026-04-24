import React, { useLayoutEffect, useRef, useState } from 'react';
import { useNavigate } from '@tanstack/react-router';
import { PrismLogo } from '../components/brand/PrismLogo';
import { Button } from '../components/ui/Button';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { Menu, X } from 'lucide-react';

gsap.registerPlugin(ScrollTrigger);
import { Target, Activity, Zap, TrendingUp, BrainCircuit, ShieldAlert, Bookmark, Layers, Clock, Plus } from 'lucide-react';

export function ExplanationPage() {
  const navigate = useNavigate();
  const container = useRef<HTMLDivElement>(null);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  
  const demoEvent = {
    source: "Bayse",
    title: "Federal Reserve rate cut by July 2026?",
    total_liquidity: 12500000,
    ai_insight: "Sustained buy pressure aligning with macroeconomic data releases supports the validity of the current move. The order book displays dense bids suggesting long-term conviction."
  };
  
  const demoTopMarket = {
    name: "YES",
    probability_delta: 6,
    signal: { score: 88 }
  };


  useLayoutEffect(() => {
    const ctx = gsap.context(() => {
      gsap.utils.toArray('.animate-section').forEach((section: any) => {
        gsap.fromTo(section, 
          { opacity: 0, y: 40 },
          { 
            scrollTrigger: {
              trigger: section,
              start: 'top 85%',
            },
            opacity: 1, 
            y: 0, 
            duration: 0.8, 
            ease: 'power3.out', 
            clearProps: 'opacity,transform' 
          }
        );
      });
    }, container);
    return () => ctx.revert();
  }, []);

  return (
    <div ref={container} className="relative min-h-screen bg-void text-text-primary">
      {/* Top Navigation */}
      <nav className="sticky top-0 z-50 h-16 px-6 md:px-12 flex items-center justify-between bg-navy/95 backdrop-blur-md border-b border-border">
        <div className="cursor-pointer" onClick={() => navigate({ to: '/' })}>
          <PrismLogo size={24} />
        </div>
        {/* Desktop Nav */}
        <div className="hidden md:flex gap-4">
          <Button variant="ghost" size="sm" onClick={() => navigate({ to: '/' })}>← Back Home</Button>
          <Button variant="primary" size="sm" onClick={() => navigate({ to: '/auth/signup' })}>Sign Up for Access</Button>
        </div>

        {/* Mobile Toggle */}
        <div className="md:hidden">
          <button onClick={() => setIsMobileMenuOpen(true)} className="text-text-primary p-2 -mr-2">
            <Menu size={24} />
          </button>
        </div>
      </nav>

      {/* Mobile Sidebar Overlay */}
      <div 
        className={`fixed inset-0 bg-void/80 backdrop-blur-sm z-[60] transition-opacity duration-300 md:hidden ${isMobileMenuOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'}`} 
        onClick={() => setIsMobileMenuOpen(false)} 
      />
      
      {/* Mobile Sidebar */}
      <div className={`fixed top-0 right-0 bottom-0 w-64 bg-navy-mid border-l border-border z-[70] transform transition-transform duration-500 ease-out flex flex-col p-6 shadow-2xl md:hidden ${isMobileMenuOpen ? 'translate-x-0' : 'translate-x-full'}`}>
        <div className="flex justify-between items-center mb-10">
           <span className="font-mono text-xs text-text-muted uppercase tracking-widest">Menu</span>
           <button onClick={() => setIsMobileMenuOpen(false)} className="text-text-secondary p-2 bg-navy rounded-full border border-border/50 hover:text-white transition-colors">
             <X size={16} />
           </button>
        </div>
        <div className="flex flex-col gap-4">
          <Button variant="ghost" className="justify-start w-full border border-border/30 hover:bg-white/5" onClick={() => navigate({ to: '/' })}>← Back Home</Button>
          <Button variant="primary" className="justify-start w-full border-prism-blue/50" onClick={() => navigate({ to: '/auth/signup' })}>Sign Up for Access</Button>
        </div>
      </div>

      {/* Hero Section */}
      <section className="animate-section py-20 md:py-28 px-6 md:px-12 lg:px-24 border-b border-border/50 relative overflow-hidden">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-prism-blue/5 rounded-full blur-[100px] pointer-events-none"></div>
        <div className="max-w-4xl relative z-10">
          <div className="mb-4 inline-flex items-center gap-2 border border-prism-blue/40 bg-prism-blue/10 text-prism-cyan rounded-full px-3 py-1 font-mono text-xs uppercase tracking-widest">
            Platform Workflow
          </div>
          <h1 className="font-heading text-4xl md:text-6xl font-bold leading-tight mb-6">Navigating the <span className="text-prism-cyan">Universal Markets</span>.</h1>
          <p className="font-body text-text-secondary text-lg leading-relaxed max-w-3xl">
            Whether evaluating a binary YES/NO decision or a multi-candidate sports tournament, PRISM unifies all prediction data into a single, cohesive workflow. Here is how our three-tier architecture helps you filter out noise and track smart money.
          </p>
        </div>
      </section>

      <main className="px-6 md:px-12 lg:px-24 max-w-7xl mx-auto py-16 flex flex-col gap-24">
        
        {/* Section 1: Discovery Feed & Signal Card */}
        <section className="animate-section scroll-mt-24">
          <h2 className="font-heading text-2xl md:text-3xl font-bold mb-10 flex items-center gap-3">
             <Activity className="text-prism-cyan" /> 1. The Discovery Feed & Signal Cards
          </h2>
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
             <div className="flex flex-col gap-6 font-body text-text-secondary leading-relaxed">
               <p>
                 Our Discovery feed is your "smart scanner". We normalize events from Polymarket and Bayse into our proprietary <strong>Signal Cards</strong>, surfaced only when actionable momentum is detected.
               </p>
               <ul className="space-y-6 mt-2">
                 <li className="flex gap-4">
                   <div className="w-8 h-8 rounded-full bg-navy border border-border flex items-center justify-center flex-shrink-0 text-white font-mono text-xs">1</div>
                   <div>
                     <strong className="text-text-primary block font-heading mb-1">Universal Context</strong>
                     <span className="text-sm">The title is the generic umbrella event. The subtitle targets the specific outcome currently spiking (e.g. <em>↳ Spiking on: Argentina</em> or <em>↳ Moving on: YES</em>).</span>
                   </div>
                 </li>
                 <li className="flex gap-4">
                   <div className="w-8 h-8 rounded-full bg-navy border border-border flex items-center justify-center flex-shrink-0 text-white font-mono text-xs">2</div>
                   <div>
                     <strong className="text-text-primary block font-heading mb-1">Instant Insights & Tracking</strong>
                     <span className="text-sm">An inline, AI-generated sentence explains the volume spike. See something interesting? Hit the <strong>+ TRACK</strong> button to instantly subscribe to live websocket updates for the event.</span>
                   </div>
                 </li>
               </ul>
             </div>
             
             <div className="flex justify-center bg-navy w-full h-full min-h-[400px] border border-border/50 rounded-2xl items-center p-8 relative overflow-hidden">
                {/* Replica Card */}
                <div className="max-w-[340px] w-full bg-navy-mid border border-emerald-400/50 rounded-xl p-5 relative z-10">
                  
                  {/* Callout Lines */}
                  <div className="flex absolute -left-8 md:-left-12 top-[40%] items-center gap-1 md:gap-2 pointer-events-none z-20">
                    <span className="font-mono text-[10px] text-text-muted bg-navy border border-border px-1.5 py-0.5 rounded shadow-xl">1</span>
                    <div className="w-4 md:w-6 h-px bg-border"></div>
                  </div>
                  
                  <div className="flex absolute -right-8 md:-right-12 bottom-[10%] flex-row-reverse items-center gap-1 md:gap-2 pointer-events-none z-20">
                     <span className="font-mono text-[10px] text-text-muted bg-navy border border-border px-1.5 py-0.5 rounded shadow-xl">2</span>
                     <div className="w-4 md:w-6 h-px bg-border"></div>
                  </div>

                  {/* Card Content Replica */}
                  <div className="flex justify-between items-start mb-2">
                    <span className="font-mono text-[10px] uppercase bg-navy border border-border/60 px-2 py-1 rounded text-text-secondary tracking-widest shadow-sm">
                      {demoEvent.source}
                    </span>
                    <span className="font-mono text-xs font-bold px-2 py-0.5 rounded border shadow-sm text-emerald-400 bg-emerald-400/10 border-emerald-400/20">
                      SCORE {demoTopMarket.signal.score}
                    </span>
                  </div>
                  
                  <h3 className="font-heading text-lg font-medium text-text-primary leading-[1.35] mb-1 pr-2">
                    {demoEvent.title}
                  </h3>
                  
                  <div className="mb-4">
                    <p className="font-mono text-[10px] text-text-muted mt-0.5">
                      ↳ Moving on: {demoTopMarket.name}
                    </p>
                  </div>

                  <div className="bg-navy border border-border/50 rounded-lg p-3 mb-5 mt-auto">
                    <p className="font-body text-xs text-text-secondary flex gap-2 line-clamp-2">
                      <span className="text-prism-cyan flex-shrink-0">↳</span>
                      {demoEvent.ai_insight}
                    </p>
                  </div>
                  
                  <div className="flex flex-col gap-3 border-t border-border/40 pt-4">
                    <div className="flex justify-between items-center">
                      <div className="flex flex-col gap-1">
                        <span className="font-mono text-[9px] text-text-muted tracking-widest uppercase flex items-center gap-1">
                          <Clock size={10} /> 12s ago
                        </span>
                        <span className="font-mono text-sm text-text-primary">
                          <span className="text-text-muted text-[10px] mr-1">POOL</span>
                          ${(demoEvent.total_liquidity / 1000000).toFixed(1)}M
                        </span>
                      </div>
                      <div className="flex flex-col items-end gap-1">
                        <span className="font-mono text-[9px] text-text-muted tracking-widest uppercase">
                          Delta <span className="text-emerald-400">(+{demoTopMarket.probability_delta}%)</span>
                        </span>
                        <span className="font-body text-sm font-medium flex items-center gap-1 text-emerald-400">
                          ↑ INFORMED
                        </span>
                      </div>
                    </div>
                    <div className="w-full flex justify-end mt-1">
                      <button className="font-mono text-[10px] px-3 py-1.5 rounded transition-all flex items-center gap-1 bg-prism-blue/10 text-prism-blue border border-prism-blue/20">
                        <Plus size={12}/> TRACK
                      </button>
                    </div>
                  </div>
                </div>
             </div>
          </div>
        </section>

        <hr className="border-border/50" />

        {/* Section 2: Tracker Page */}
        <section className="animate-section">
          <h2 className="font-heading text-2xl md:text-3xl font-bold mb-10 flex items-center gap-3">
             <Bookmark className="text-prism-cyan" /> 2. Personal Portfolio (The Tracker)
          </h2>
          <div className="flex flex-col md:flex-row gap-12 items-center">
             <div className="flex-1 font-body text-text-secondary leading-relaxed">
               <p className="mb-4">
                 Whenever you click the <strong>+ TRACK</strong> button on a Signal Card, it is pushed into your Tracker Portfolio. 
               </p>
               <p>
                 While the Discovery feed lists hundreds of static macro events, your Tracker forces active synchronization. Watched events jump to a rapid polling rate, querying the backend every 30-60 seconds to ensure you have split-second visibility into order book microstructure updates and shifting Trap Risks before the broad market reacts.
               </p>
             </div>
             <div className="flex-1 bg-navy-mid border border-border p-8 rounded-2xl flex flex-col items-center justify-center relative shadow-card">
               <Bookmark className="text-noise mb-6 animate-pulse-slow" size={48} />
               <p className="font-mono text-xs uppercase tracking-widest text-text-muted">Live synchronization active</p>
             </div>
          </div>
        </section>

        <hr className="border-border/50" />

        {/* Section 3: The Event Deep Dive */}
        <section className="animate-section">
          <h2 className="font-heading text-2xl md:text-3xl font-bold mb-10 flex items-center gap-3">
             <Layers className="text-prism-cyan" /> 3. The Universal Tab Deep Dive
          </h2>
          <p className="font-body text-text-secondary mb-10 max-w-3xl leading-relaxed">
             Clicking on any card drops you into the Event Detail page. Instead of juggling different UIs for binary "YES/NO" markets vs. multi-candidate "Election/Sports" markets, PRISM uses a <strong>Universal Tab Bar</strong>.
          </p>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
             <div className="bg-gradient-to-br from-navy-mid to-navy border border-border p-6 rounded-xl shadow-card flex flex-col lg:col-span-3">
                <div className="flex items-center gap-2 mb-4">
                  <BrainCircuit className="text-prism-cyan" size={24} />
                  <h3 className="font-heading font-semibold text-text-primary">AI Event Baseline</h3>
                </div>
                <p className="font-body text-sm text-text-secondary leading-relaxed">
                  Before diving into numbers, the page is topped with a live-generated AI narrative. The AI assesses all competing outcomes simultaneously (e.g., "Money is exiting France and pouring into Argentina under heavy institutional volume") to frame your bias instantly.
                </p>
             </div>

             <div className="bg-navy-mid border border-border p-6 rounded-xl shadow-card flex flex-col">
                <Target className="text-prism-cyan mb-4" size={24} />
                <h3 className="font-heading font-semibold text-text-primary mb-1">Dynamic Selected Outcome</h3>
                <div className="mb-4 text-[10px] text-prism-cyan font-mono border-b border-border/30 pb-2 leading-tight uppercase tracking-wider">Zero cross-contamination</div>
                <p className="font-body text-sm text-text-secondary leading-relaxed">
                  When you select an outcome tab (e.g., "YES" or "Brazil"), every statistic on the page immediately re-renders to reflect <strong>only that outcome's specific order book</strong>. 
                </p>
             </div>

             <div className="bg-navy-mid border border-border p-6 rounded-xl shadow-card flex flex-col">
                <ShieldAlert className="text-noise mb-4" size={24} />
                <h3 className="font-heading font-semibold text-text-primary mb-1">Quant Area: Trap Risk</h3>
                <div className="mb-4 text-[10px] text-noise font-mono border-b border-border/30 pb-2 leading-tight uppercase tracking-wider">Spoofing protection at a glance</div>
                <p className="font-body text-sm text-text-secondary leading-relaxed">
                  Calculates explicit distribution curves analyzing individual order depth. If the selected outcome's price spike was artificially generated via low-liquidity spoofing, the engine highlights HIGH TRAP RISK.
                </p>
             </div>

             <div className="bg-navy-mid border border-border p-6 rounded-xl shadow-card flex flex-col">
                <TrendingUp className="text-emerald-400 mb-4" size={24} />
                <h3 className="font-heading font-semibold text-text-primary mb-1">Quant Area: Momentum</h3>
                <div className="mb-4 text-[10px] text-emerald-400 font-mono border-b border-border/30 pb-2 leading-tight uppercase tracking-wider">Structural projection certainty</div>
                <p className="font-body text-sm text-text-secondary leading-relaxed">
                  A machine-learning baseline that estimates whether the outcome's current vector points toward continuous trajectory or immediate mean-reversion, paired with a confidence percentage.
                </p>
             </div>
          </div>
        </section>

      </main>
      
      {/* Footer CTA */}
      <div className="border-t border-border/40 py-12 text-center bg-navy/30">
        <h2 className="font-heading text-2xl font-bold text-text-primary mb-6">Stop trading blind. Follow the signal.</h2>
        <Button variant="primary" size="lg" onClick={() => navigate({ to: '/auth/signup' })}>Sign Up for Access</Button>
      </div>

    </div>
  );
}
