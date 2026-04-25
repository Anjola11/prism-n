import React, { useLayoutEffect, useRef } from 'react';
import { useNavigate } from '@tanstack/react-router';
import { PrismLogo } from '../components/brand/PrismLogo';
import { Button } from '../components/ui/Button';
import { ThemeToggle } from '../components/ui/ThemeToggle';
import gsap from 'gsap';
import {
  Activity,
  Bookmark,
  BrainCircuit,
  Clock,
  Layers,
  Plus,
  ShieldAlert,
  Target,
  TrendingUp,
} from 'lucide-react';

export function LandingPage() {
  const navigate = useNavigate();
  const container = useRef<HTMLDivElement>(null);
  const scrollToWorkflow = () => {
    document.getElementById('how-prism-works')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  useLayoutEffect(() => {
    const ctx = gsap.context(() => {
      gsap.fromTo(
        '.hero-animate',
        { opacity: 0, y: 30 },
        { opacity: 1, y: 0, duration: 0.8, stagger: 0.15, ease: 'power3.out', clearProps: 'all' },
      );

      gsap.fromTo(
        '.card-animate',
        { opacity: 0, x: 40 },
        { opacity: 1, x: 0, duration: 1, stagger: 0.2, ease: 'power3.out', delay: 0.5, clearProps: 'all' },
      );

      gsap.fromTo(
        '.explain-animate',
        { opacity: 0, y: 32 },
        { opacity: 1, y: 0, duration: 0.75, stagger: 0.12, ease: 'power3.out', delay: 0.25, clearProps: 'all' },
      );
    }, container);
    return () => ctx.revert();
  }, []);

  return (
    <div className="relative min-h-screen overflow-hidden bg-void text-text-primary" ref={container}>
      <nav className="fixed top-0 left-0 right-0 z-50 flex h-16 items-center justify-between border-b border-border bg-navy/92 px-6 backdrop-blur-lg md:px-12 lg:px-20">
        <PrismLogo size={28} />
        <div className="flex items-center gap-3">
          <ThemeToggle compact />
          <Button variant="ghost" size="sm" onClick={() => navigate({ to: '/auth/login' })}>
            Sign In
          </Button>
          <Button variant="primary" size="sm" onClick={() => navigate({ to: '/auth/signup' })}>
            Get Access
          </Button>
        </div>
      </nav>

      <section className="relative z-10 px-6 pt-20 md:px-12 lg:px-20">
        <div className="mx-auto grid min-h-screen w-full max-w-[1400px] items-center gap-12 lg:grid-cols-[minmax(0,720px)_340px]">
          <div className="max-w-[800px]">
            <div className="hero-animate mb-6 inline-flex w-max items-center gap-2 rounded-full border border-prism-blue/40 bg-prism-blue/8 px-3 py-1 font-mono text-xs uppercase tracking-[0.2em] text-prism-cyan">
              <div className="h-1.5 w-1.5 rounded-full bg-prism-cyan animate-pulse-slow"></div>
              Real-Time Signal Intelligence
            </div>

            <h1 className="font-heading text-[clamp(2.8rem,5vw,4.5rem)] font-bold leading-[1.05] tracking-tight">
              <div className="hero-animate text-text-primary">Filter the Noise.</div>
              <div className="hero-animate text-prism-cyan">Trade the Signal.</div>
            </h1>

            <p className="hero-animate mt-6 max-w-[460px] font-body text-[clamp(0.9rem,1.5vw,1.0625rem)] leading-relaxed text-text-secondary">
              Prism applies institutional-grade market microstructure analysis to prediction markets and helps you see whether a move is being driven by informed traders or by noise.
            </p>

            <div className="hero-animate mt-8 flex flex-col gap-3 sm:flex-row">
              <Button variant="primary" size="lg" onClick={() => navigate({ to: '/auth/signup' })}>
                Start Analyzing Markets
              </Button>
              <Button variant="outline" size="lg" onClick={scrollToWorkflow}>
                How Prism Works
              </Button>
            </div>

            <p className="hero-animate mt-5 font-mono text-xs tracking-wide text-text-muted">
              Live data from Bayse · Polymarket · Powered by AI
            </p>
          </div>

          <div className="relative z-20 hidden w-[340px] lg:block">
            <div className="card-animate relative z-10 rounded-2xl border border-informed/30 bg-navy-mid p-5 shadow-glow-informed transform -rotate-[1.5deg]" style={{ animation: 'float 4s ease-in-out infinite' }}>
              <div className="absolute -top-3 -right-2 flex items-center gap-1.5 rounded-full border border-noise/30 bg-noise-bg px-2 py-0.5 font-mono text-[10px] text-noise shadow-md">
                <div className="h-1.5 w-1.5 rounded-full bg-noise animate-pulse-slow"></div>
                LIVE
              </div>

              <div className="mb-3 flex items-start justify-between">
                <span className="rounded border border-border bg-navy px-2 py-0.5 font-mono text-xs text-text-secondary">Bayse</span>
                <span className="rounded border border-informed/30 bg-informed-bg px-2 py-0.5 font-mono text-xs font-bold text-informed">SCORE 84</span>
              </div>
              <h3 className="mb-4 pr-4 font-heading text-lg font-bold leading-tight text-text-primary">Will Tinubu win re-election?</h3>
              <div className="flex items-center justify-between border-t border-informed/20 pt-3">
                <span className="font-body text-sm font-semibold text-informed flex items-center gap-1">Uptrend (+7 pts)</span>
                <span className="font-mono text-[10px] tracking-wider text-text-muted">INFORMED MOVE</span>
              </div>
            </div>

            <div className="card-animate absolute top-0 right-0 z-0 rounded-2xl border border-border bg-navy p-5 shadow-card transform translate-x-4 translate-y-6 rotate-[2deg] scale-[0.96] opacity-80" style={{ animation: 'float 4s ease-in-out infinite 1s' }}>
              <div className="mb-3 flex items-start justify-between">
                <span className="rounded border border-border bg-navy-mid px-2 py-0.5 font-mono text-xs text-text-secondary">Polymarket</span>
                <span className="rounded border border-noise/30 bg-noise-bg px-2 py-0.5 font-mono text-xs text-noise">SCORE 31</span>
              </div>
              <h3 className="mb-4 pr-4 font-heading text-lg leading-tight text-text-primary">BTC above $100k by Dec 2025?</h3>
              <div className="flex items-center justify-between border-t border-border/50 pt-3">
                <span className="font-body text-sm text-noise flex items-center gap-1">Cooling off</span>
                <span className="font-mono text-[10px] tracking-wider text-text-muted">NOISE</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <main className="relative z-10 mx-auto flex max-w-7xl flex-col gap-24 px-6 py-20 md:px-12 lg:px-24">
        <section id="how-prism-works" className="explain-animate border-t border-border/40 pt-12">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-prism-blue/40 bg-prism-blue/10 px-3 py-1 font-mono text-xs uppercase tracking-widest text-prism-cyan">
            Platform Workflow
          </div>
          <h2 className="font-heading text-3xl font-bold leading-tight md:text-5xl">
            How Prism works,
            <br />
            without the noise.
          </h2>
          <p className="mt-6 max-w-3xl font-body text-lg leading-relaxed text-text-secondary">
            Whether you are evaluating a binary YES/NO event or a larger multi-outcome market, Prism keeps the workflow simple:
            discover the strongest move, track it into live focus, and read the event through one unified analysis page.
          </p>
        </section>

        <section className="explain-animate">
          <h3 className="mb-10 flex items-center gap-3 font-heading text-2xl font-bold md:text-3xl">
            <Activity className="text-prism-cyan" /> 1. Discovery surfaces the strongest event
          </h3>

          <div className="grid grid-cols-1 items-center gap-12 lg:grid-cols-2">
            <div className="flex flex-col gap-6 font-body leading-relaxed text-text-secondary">
              <p>
                Discovery is your smart scanner. Prism normalizes events from Bayse and Polymarket into Signal Cards,
                then lets the strongest event rise with score, direction, and context already attached.
              </p>
              <ul className="mt-2 space-y-6">
                <li className="flex gap-4">
                  <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full border border-border bg-navy font-mono text-xs text-text-primary">1</div>
                  <div>
                    <strong className="mb-1 block font-heading text-text-primary">Universal context</strong>
                    <span className="text-sm">
                      The title gives you the umbrella event. The subtitle shows which outcome is actually carrying the move right now.
                    </span>
                  </div>
                </li>
                <li className="flex gap-4">
                  <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full border border-border bg-navy font-mono text-xs text-text-primary">2</div>
                  <div>
                    <strong className="mb-1 block font-heading text-text-primary">Instant explanation</strong>
                    <span className="text-sm">
                      A short AI sentence explains why the event is showing up, so the feed already feels interpretable at first glance.
                    </span>
                  </div>
                </li>
              </ul>
            </div>

            <div className="relative flex min-h-[400px] w-full items-center justify-center overflow-hidden rounded-2xl border border-border/50 bg-navy p-8">
              <div className="relative z-10 w-full max-w-[340px] rounded-xl border border-emerald-400/50 bg-navy-mid p-5">
                <div className="absolute -left-8 top-[40%] z-20 flex items-center gap-1 pointer-events-none md:-left-12 md:gap-2">
                  <span className="rounded border border-border bg-navy px-1.5 py-0.5 font-mono text-[10px] text-text-muted shadow-xl">1</span>
                  <div className="h-px w-4 bg-border md:w-6"></div>
                </div>

                <div className="absolute -right-8 bottom-[10%] z-20 flex flex-row-reverse items-center gap-1 pointer-events-none md:-right-12 md:gap-2">
                  <span className="rounded border border-border bg-navy px-1.5 py-0.5 font-mono text-[10px] text-text-muted shadow-xl">2</span>
                  <div className="h-px w-4 bg-border md:w-6"></div>
                </div>

                <div className="mb-2 flex items-start justify-between">
                  <span className="rounded border border-border/60 bg-navy px-2 py-1 font-mono text-[10px] uppercase tracking-widest text-text-secondary shadow-sm">
                    Bayse
                  </span>
                  <span className="signal-badge-high rounded px-2 py-0.5 font-mono text-xs font-bold shadow-sm">
                    SCORE 88
                  </span>
                </div>

                <h3 className="mb-1 pr-2 font-heading text-lg font-medium leading-[1.35] text-text-primary">
                  Federal Reserve rate cut by July 2026?
                </h3>

                <div className="mb-4">
                  <p className="mt-0.5 font-mono text-[10px] text-text-muted">Focus outcome: YES</p>
                </div>

                <div className="mb-5 mt-auto rounded-lg border border-border/50 bg-navy p-3">
                  <p className="flex gap-2 font-body text-xs text-text-secondary">
                    <span className="flex-shrink-0 text-prism-cyan">Note</span>
                    Sustained buy pressure is aligning with macro releases, and the order book is showing real conviction.
                  </p>
                </div>

                <div className="flex flex-col gap-3 border-t border-border/40 pt-4">
                  <div className="flex items-center justify-between">
                    <div className="flex flex-col gap-1">
                      <span className="flex items-center gap-1 font-mono text-[9px] uppercase tracking-widest text-text-muted">
                        <Clock size={10} /> 12s ago
                      </span>
                      <span className="font-mono text-sm text-text-primary">
                        <span className="mr-1 text-[10px] text-text-muted">POOL</span>
                        $12.5M
                      </span>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <span className="font-mono text-[9px] uppercase tracking-widest text-text-muted">
                        Delta <span className="text-emerald-400">(+6%)</span>
                      </span>
                      <span className="flex items-center gap-1 font-body text-sm font-medium text-emerald-400">INFORMED</span>
                    </div>
                  </div>
                  <div className="mt-1 flex w-full justify-end">
                    <button className="flex items-center gap-1 rounded border border-prism-blue/20 bg-prism-blue/10 px-3 py-1.5 font-mono text-[10px] text-prism-blue transition-all">
                      <Plus size={12} /> TRACK
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="explain-animate border-t border-border/50 pt-12">
          <h3 className="mb-10 flex items-center gap-3 font-heading text-2xl font-bold md:text-3xl">
            <Bookmark className="text-prism-cyan" /> 2. Tracking promotes it into live focus
          </h3>
          <div className="flex flex-col items-center gap-12 md:flex-row">
            <div className="flex-1 font-body leading-relaxed text-text-secondary">
              <p className="mb-4">
                When you press <strong>TRACK</strong>, the event moves from passive browsing into your active monitored set.
              </p>
              <p>
                That is where Prism becomes more than a feed. Tracked events are prepared for deeper synchronization so the analysis page can move from a lightweight snapshot toward a more trustworthy live read.
              </p>
            </div>
            <div className="relative flex flex-1 flex-col items-center justify-center rounded-2xl border border-border bg-navy-mid p-8 shadow-card">
              <Bookmark className="mb-6 animate-pulse-slow text-noise" size={48} />
              <p className="font-mono text-xs uppercase tracking-widest text-text-muted">Live synchronization active</p>
            </div>
          </div>
        </section>

        <section className="explain-animate border-t border-border/50 pt-12">
          <h3 className="mb-10 flex items-center gap-3 font-heading text-2xl font-bold md:text-3xl">
            <Layers className="text-prism-cyan" /> 3. Analysis stays in one frame
          </h3>
          <p className="mb-10 max-w-3xl font-body leading-relaxed text-text-secondary">
            Clicking into an event opens one unified analysis page. Instead of juggling different workflows for simple and complex markets, Prism keeps the event readable through one consistent structure.
          </p>

          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            <div className="flex flex-col rounded-xl border border-border bg-gradient-to-br from-navy-mid to-navy p-6 shadow-card lg:col-span-3">
              <div className="mb-4 flex items-center gap-2">
                <BrainCircuit className="text-prism-cyan" size={24} />
                <h3 className="font-heading font-semibold text-text-primary">AI Event Baseline</h3>
              </div>
              <p className="font-body text-sm leading-relaxed text-text-secondary">
                Before you dive into numbers, Prism gives you an AI baseline for the event. It frames the market in plain language so you understand the shape of the move before scanning the microstructure.
              </p>
            </div>

            <div className="flex flex-col rounded-xl border border-border bg-navy-mid p-6 shadow-card">
              <Target className="mb-4 text-prism-cyan" size={24} />
              <h3 className="mb-1 font-heading font-semibold text-text-primary">Dynamic Selected Outcome</h3>
              <div className="mb-4 border-b border-border/30 pb-2 font-mono text-[10px] uppercase tracking-wider text-prism-cyan">Zero cross-contamination</div>
              <p className="font-body text-sm leading-relaxed text-text-secondary">
                Selecting an outcome re-renders the page around that specific side of the event, keeping the read clean and outcome-specific.
              </p>
            </div>

            <div className="flex flex-col rounded-xl border border-border bg-navy-mid p-6 shadow-card">
              <ShieldAlert className="mb-4 text-noise" size={24} />
              <h3 className="mb-1 font-heading font-semibold text-text-primary">Trap Risk</h3>
              <div className="mb-4 border-b border-border/30 pb-2 font-mono text-[10px] uppercase tracking-wider text-noise">Spoofing protection</div>
              <p className="font-body text-sm leading-relaxed text-text-secondary">
                Prism checks whether a move looks structurally supported or suspiciously thin, so a sharp spike does not automatically get mistaken for conviction.
              </p>
            </div>

            <div className="flex flex-col rounded-xl border border-border bg-navy-mid p-6 shadow-card">
              <TrendingUp className="mb-4 text-emerald-400" size={24} />
              <h3 className="mb-1 font-heading font-semibold text-text-primary">Momentum</h3>
              <div className="mb-4 border-b border-border/30 pb-2 font-mono text-[10px] uppercase tracking-wider text-emerald-400">Direction with context</div>
              <p className="font-body text-sm leading-relaxed text-text-secondary">
                Momentum helps show whether the current path looks persistent or fragile, adding confidence to the read without pretending every move will last.
              </p>
            </div>
          </div>
        </section>

        <section className="explain-animate border-t border-border/40 bg-navy/30 py-12 text-center">
          <h2 className="mb-6 font-heading text-2xl font-bold text-text-primary">Stop trading blind. Follow the signal.</h2>
          <Button variant="primary" size="lg" onClick={() => navigate({ to: '/auth/signup' })}>
            Sign Up for Access
          </Button>
        </section>
      </main>
    </div>
  );
}


