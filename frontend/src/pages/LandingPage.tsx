import React, { useLayoutEffect, useRef, useState } from 'react';
import { useNavigate } from '@tanstack/react-router';
import { PrismLogo } from '../components/brand/PrismLogo';
import { Button } from '../components/ui/Button';
import gsap from 'gsap';
import { Menu, X } from 'lucide-react';

export function LandingPage() {
  const navigate = useNavigate();
  const container = useRef<HTMLDivElement>(null);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  useLayoutEffect(() => {
    const ctx = gsap.context(() => {
      gsap.fromTo('.hero-animate', 
        { opacity: 0, y: 30 },
        { opacity: 1, y: 0, duration: 0.8, stagger: 0.15, ease: 'power3.out', clearProps: 'opacity,transform' }
      );
      
      gsap.fromTo('.card-animate',
        { opacity: 0, x: 40 },
        { opacity: 1, x: 0, duration: 1, stagger: 0.2, ease: 'power3.out', delay: 0.5, clearProps: 'opacity,transform' }
      );
    }, container);
    return () => ctx.revert();
  }, []);

  return (
    <div className="relative min-h-screen bg-void text-text-primary overflow-hidden" ref={container}>
      <nav className="fixed top-0 left-0 right-0 z-50 h-16 px-6 md:px-12 lg:px-20 flex items-center justify-between transition-all bg-navy/92 backdrop-blur-lg border-b border-border">
        <PrismLogo size={28} />
        
        {/* Desktop Nav */}
        <div className="hidden md:flex gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate({ to: '/how-it-works' })} className="flex" >How it Works</Button>
          <Button variant="ghost" size="sm" onClick={() => navigate({ to: '/auth/login' })}>Sign In</Button>
          <Button variant="primary" size="sm" onClick={() => navigate({ to: '/auth/signup' })}>Get Access</Button>
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
          <Button variant="ghost" className="justify-start w-full border border-border/30 hover:bg-white/5" onClick={() => navigate({ to: '/how-it-works' })}>How it Works</Button>
          <Button variant="ghost" className="justify-start w-full border border-border/30 hover:bg-white/5" onClick={() => navigate({ to: '/auth/login' })}>Sign In</Button>
          <Button variant="primary" className="justify-start w-full border-prism-blue/50" onClick={() => navigate({ to: '/auth/signup' })}>Get Access</Button>
        </div>
        <div className="mt-auto pt-8 border-t border-border/50">
          <p className="font-mono text-[10px] text-text-muted">PRISM ALPHA v0.9<br/>Built for speed.</p>
        </div>
      </div>

      <section className="relative min-h-screen flex flex-col justify-center px-6 md:pl-12 lg:pl-20 max-w-[800px] z-10 pt-20">
        <div className="hero-animate mb-6 inline-flex items-center gap-2 border border-prism-blue/40 bg-prism-blue/8 text-prism-cyan rounded-full px-3 py-1 font-mono text-xs tracking-[0.2em] uppercase w-max">
          <div className="w-1.5 h-1.5 rounded-full bg-prism-cyan animate-pulse-slow"></div>
          Real-Time Signal Intelligence
        </div>
        
        <h1 className="font-heading font-bold text-[clamp(2.8rem,5vw,4.5rem)] leading-[1.05] tracking-tight">
          <div className="text-text-primary hero-animate">Filter the Noise.</div>
          <div className="text-prism-cyan hero-animate">Trade the Signal.</div>
        </h1>
        
        <p className="hero-animate font-body text-text-secondary mt-6 text-[clamp(0.9rem,1.5vw,1.0625rem)] leading-relaxed max-w-[460px]">
          Prism applies institutional-grade market microstructure analysis to prediction markets — quantifying whether a price movement is driven by informed traders or just noise.
        </p>

        <div className="hero-animate flex flex-col sm:flex-row gap-3 mt-8">
          <Button variant="primary" size="lg" onClick={() => navigate({ to: '/auth/signup' })}>Start Analyzing Markets</Button>
          <Button variant="outline" size="lg" onClick={() => navigate({ to: '/auth/login' })}>Sign In</Button>
        </div>

        <p className="hero-animate font-mono text-xs text-text-muted tracking-wide mt-5">
          Live data from Bayse · Polymarket · Powered by Google Gemini AI
        </p>
      </section>

      {/* Floating Market Card Preview (Desktop Only) */}
      <div className="hidden lg:block absolute right-[6%] top-1/2 -translate-y-1/2 w-[340px] z-20">
        
        {/* Card 1 (Top) */}
        <div className="card-animate relative z-10 bg-navy-mid border border-informed/30 rounded-2xl p-5 shadow-glow-informed transform -rotate-[1.5deg]" style={{ animation: 'float 4s ease-in-out infinite' }}>
          <div className="absolute -top-3 -right-2 font-mono text-[10px] text-noise bg-noise-bg border border-noise/30 rounded-full px-2 py-0.5 flex items-center gap-1.5 shadow-md">
            <div className="w-1.5 h-1.5 bg-noise rounded-full animate-pulse-slow"></div>
            LIVE
          </div>
          
          <div className="flex justify-between items-start mb-3">
            <span className="font-mono text-xs bg-navy border border-border px-2 py-0.5 rounded text-text-secondary">Bayse</span>
            <span className="font-mono text-xs text-informed font-bold bg-informed-bg border border-informed/30 px-2 py-0.5 rounded">SCORE 84</span>
          </div>
          <h3 className="font-heading text-lg font-bold text-text-primary leading-tight mb-4 pr-4">Will Tinubu win re-election?</h3>
          <div className="flex items-center justify-between border-t border-informed/20 pt-3">
             <span className="font-body text-sm font-semibold text-informed flex items-center gap-1">↑ Rising (+7 pts)</span>
             <span className="font-mono text-[10px] tracking-wider text-text-muted">INFORMED MOVE</span>
          </div>
        </div>

        {/* Card 2 (Bottom) */}
        <div className="card-animate absolute top-0 right-0 z-0 bg-navy border border-border rounded-2xl p-5 shadow-card transform rotate-[2deg] translate-y-6 translate-x-4 scale-[0.96] opacity-80" style={{ animation: 'float 4s ease-in-out infinite 1s' }}>
          <div className="flex justify-between items-start mb-3">
            <span className="font-mono text-xs bg-navy-mid border border-border px-2 py-0.5 rounded text-text-secondary">Polymarket</span>
            <span className="font-mono text-xs text-noise bg-noise-bg border border-noise/30 px-2 py-0.5 rounded">SCORE 31</span>
          </div>
          <h3 className="font-heading text-lg text-text-primary leading-tight mb-4 pr-4">BTC above $100k by Dec 2025?</h3>
          <div className="flex items-center justify-between border-t border-border/50 pt-3">
             <span className="font-body text-sm text-noise flex items-center gap-1">↓ Falling</span>
             <span className="font-mono text-[10px] tracking-wider text-text-muted">NOISE</span>
          </div>
        </div>

      </div>
    </div>
  );
}
