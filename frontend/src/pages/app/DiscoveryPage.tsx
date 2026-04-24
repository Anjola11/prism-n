import React, { useLayoutEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import gsap from 'gsap';
import { Filter } from 'lucide-react';

import { marketsApi } from '../../lib/api/markets';
import { mapDiscoveryEvent } from '../../lib/api/adapters';
import type { DiscoveryCardViewModel } from '../../lib/api/types';
import { SignalCard } from '../../components/ui/SignalCard';

export function DiscoveryPage() {
  const container = useRef<HTMLDivElement>(null);
  const [filter, setFilter] = useState<'ALL' | 'BAYSE' | 'POLYMARKET'>('ALL');
  const [tracked, setTracked] = useState<Record<string, boolean>>({});
  const discoveryQuery = useQuery({
    queryKey: ['discovery-feed', filter],
    queryFn: async () => {
      const source = filter === 'ALL' ? undefined : filter.toLowerCase();
      const apiEvents = await marketsApi.getEvents(undefined, source);
      return apiEvents.map(mapDiscoveryEvent);
    },
    staleTime: 30_000,
    gcTime: 5 * 60_000,
    refetchInterval: 30_000,
    placeholderData: (previousData) => previousData,
    retry: (failureCount, error) => {
      if ((error as any)?.response?.status === 503 && failureCount < 5) return true;
      return failureCount < 2;
    },
    retryDelay: (attemptIndex) => Math.min(3000 * (attemptIndex + 1), 10000),
  });

  const events: DiscoveryCardViewModel[] = discoveryQuery.data || [];

  useLayoutEffect(() => {
    if (events.length === 0) return;

    const ctx = gsap.context(() => {
      gsap.fromTo(
        '.event-card-wrapper',
        { opacity: 0, y: 15 },
        {
          opacity: 1,
          y: 0,
          duration: 0.5,
          stagger: 0.08,
          ease: 'power3.out',
          clearProps: 'all',
        },
      );
    }, container);

    return () => ctx.revert();
  }, [filter, events]);

  const filteredEvents = events;

  React.useEffect(() => {
    if (events.length > 0) {
      setTracked(Object.fromEntries(events.map((event) => [event.id, event.trackingEnabled])));
    }
  }, [events]);

  const toggleTrack = async (e: React.MouseEvent, id: string, source: string) => {
    e.stopPropagation();

    const isTracking = !tracked[id];
    setTracked((prev) => ({ ...prev, [id]: isTracking }));

    try {
      if (isTracking) {
        await marketsApi.trackEvent(id, undefined, source);
      } else {
        await marketsApi.untrackEvent(id, undefined, source);
      }
      } catch {
        setTracked((prev) => ({ ...prev, [id]: !isTracking }));
      }
  };

  const skeletonCards = Array.from({ length: 6 });

  return (
    <div className="flex flex-col gap-6" ref={container}>
      <div className="flex flex-col justify-between border-b border-border/50 pb-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="mb-1 font-heading text-2xl text-text-primary">Discovery Feed</h1>
          <p className="font-body text-xs text-text-secondary">
            Real-time signal feed across generic and combined markets.
          </p>
        </div>

        <div className="mt-4 flex items-center gap-2 sm:mt-0">
          <span className="mr-2 flex items-center gap-1.5 font-mono text-xs text-text-muted">
            <Filter size={14} /> FILTERS:
          </span>
          <button
            onClick={() => setFilter('ALL')}
            className={`rounded-md px-3 py-1.5 font-mono text-[10px] transition-colors sm:text-xs ${filter === 'ALL' ? 'border border-prism-blue/30 bg-prism-blue/20 text-prism-blue' : 'border border-border bg-navy text-text-secondary hover:text-text-primary'}`}
          >
            ALL
          </button>
          <button
            onClick={() => setFilter('BAYSE')}
            className={`rounded-md px-3 py-1.5 font-mono text-[10px] transition-colors sm:text-xs ${filter === 'BAYSE' ? 'border border-prism-blue/30 bg-prism-blue/20 text-prism-blue' : 'border border-border bg-navy text-text-secondary hover:text-text-primary'}`}
          >
            BAYSE
          </button>
          <button
            onClick={() => setFilter('POLYMARKET')}
            className={`rounded-md px-3 py-1.5 font-mono text-[10px] transition-colors sm:text-xs ${filter === 'POLYMARKET' ? 'border border-prism-blue/30 bg-prism-blue/20 text-prism-blue' : 'border border-border bg-navy text-text-secondary hover:text-text-primary'}`}
          >
            POLY
          </button>
        </div>
      </div>

      {discoveryQuery.isError && !discoveryQuery.isLoading && (
        <div className={`rounded-xl border p-4 text-sm ${
          (discoveryQuery.error as any)?.response?.status === 503
            ? 'border-prism-blue/20 bg-prism-blue/10 text-prism-blue'
            : 'border-amber-500/20 bg-amber-500/10 text-amber-500'
        }`}>
          {(discoveryQuery.error as any)?.response?.status === 503
            ? 'Discovery feed is warming up — data will appear shortly.'
            : 'Failed to load discovery feed.'}
        </div>
      )}

      <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
        {discoveryQuery.isLoading && skeletonCards.map((_, index) => (
          <div
            key={`discovery-skeleton-${index}`}
            className="h-[420px] animate-pulse rounded-xl border border-border bg-card"
          />
        ))}

        {!discoveryQuery.isLoading && filteredEvents.map((event) => (
          <div key={event.id} className="event-card-wrapper h-full">
            <SignalCard event={event} onTrack={toggleTrack} isTracked={!!tracked[event.id]} />
          </div>
        ))}

        {!discoveryQuery.isLoading && filteredEvents.length === 0 && (
          <div className="col-span-full rounded-xl border border-border bg-card p-6 text-sm text-text-muted">
            No events matched the current filter.
          </div>
        )}
      </div>
    </div>
  );
}
