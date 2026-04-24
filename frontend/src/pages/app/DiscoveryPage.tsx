import React, { useLayoutEffect, useMemo, useRef, useState } from 'react';
import { useInfiniteQuery } from '@tanstack/react-query';
import gsap from 'gsap';
import { Filter } from 'lucide-react';

import { marketsApi } from '../../lib/api/markets';
import { mapDiscoveryEvent } from '../../lib/api/adapters';
import type { DiscoveryCardViewModel } from '../../lib/api/types';
import { DEFAULT_PAGE_SIZE } from '../../lib/constants';
import { SignalCard } from '../../components/ui/SignalCard';
import { useInfiniteScrollSentinel } from '../../hooks/useInfiniteScrollSentinel';

export function DiscoveryPage() {
  const container = useRef<HTMLDivElement>(null);
  const hasAnimatedForFilterRef = useRef(false);
  const previousEventIdsRef = useRef<string[]>([]);
  const [filter, setFilter] = useState<'ALL' | 'BAYSE' | 'POLYMARKET'>('ALL');
  const [tracked, setTracked] = useState<Record<string, boolean>>({});
  const discoveryQuery = useInfiniteQuery({
    queryKey: ['discovery-feed', filter, DEFAULT_PAGE_SIZE],
    queryFn: async ({ pageParam }) => {
      const source = filter === 'ALL' ? undefined : filter.toLowerCase();
      return marketsApi.getEventsPage(pageParam, DEFAULT_PAGE_SIZE, undefined, source);
    },
    initialPageParam: 1,
    getNextPageParam: (lastPage) => {
      if (!lastPage.pagination.has_more) {
        return undefined;
      }
      return lastPage.pagination.page + 1;
    },
    staleTime: 30_000,
    gcTime: 5 * 60_000,
    refetchInterval: 30_000,
    retry: (failureCount, error) => {
      if ((error as any)?.response?.status === 503 && failureCount < 5) return true;
      return failureCount < 2;
    },
    retryDelay: (attemptIndex) => Math.min(3000 * (attemptIndex + 1), 10000),
  });

  const events: DiscoveryCardViewModel[] = useMemo(
    () => discoveryQuery.data?.pages.flatMap((page) => page.items.map(mapDiscoveryEvent)) || [],
    [discoveryQuery.data],
  );

  const loadMoreRef = useInfiniteScrollSentinel({
    hasNextPage: !!discoveryQuery.hasNextPage,
    isFetchingNextPage: discoveryQuery.isFetchingNextPage,
    fetchNextPage: discoveryQuery.fetchNextPage,
    enabled: !discoveryQuery.isLoading,
  });

  React.useEffect(() => {
    hasAnimatedForFilterRef.current = false;
    previousEventIdsRef.current = [];
  }, [filter]);

  useLayoutEffect(() => {
    if (events.length === 0) return;
    if (hasAnimatedForFilterRef.current) return;
    hasAnimatedForFilterRef.current = true;

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
  }, [events, filter]);

  useLayoutEffect(() => {
    if (!container.current || events.length === 0) {
      previousEventIdsRef.current = events.map((event) => event.id);
      return;
    }

    const previousIds = previousEventIdsRef.current;
    const currentIds = events.map((event) => event.id);
    const newIds = currentIds.filter((id) => !previousIds.includes(id));

    if (previousIds.length > 0 && newIds.length > 0) {
      const newNodes = newIds
        .map((id) => container.current?.querySelector(`.event-card-wrapper[data-event-id="${id}"]`))
        .filter((node): node is Element => node !== null);

      if (newNodes.length > 0) {
        gsap.fromTo(
          newNodes,
          { opacity: 0, y: 10 },
          {
            opacity: 1,
            y: 0,
            duration: 0.28,
            stagger: 0.04,
            ease: 'power2.out',
            clearProps: 'all',
          },
        );
      }
    }

    previousEventIdsRef.current = currentIds;
  }, [events]);

  const filteredEvents = events;
  const showDiscoveryError =
    discoveryQuery.isError && !discoveryQuery.isLoading && filteredEvents.length === 0;

  React.useEffect(() => {
    if (events.length > 0) {
      setTracked((prev) => {
        const next = Object.fromEntries(events.map((event) => [event.id, event.trackingEnabled]));
        const prevKeys = Object.keys(prev);
        const nextKeys = Object.keys(next);
        const isUnchanged =
          prevKeys.length === nextKeys.length &&
          nextKeys.every((key) => prev[key] === next[key]);

        return isUnchanged ? prev : next;
      });
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

      {showDiscoveryError && (
        <div className={`rounded-xl border p-4 text-sm ${
          (discoveryQuery.error as any)?.response?.status === 503
            ? 'border-prism-blue/20 bg-prism-blue/10 text-prism-blue'
            : 'border-amber-500/20 bg-amber-500/10 text-amber-500'
        }`}>
          {(discoveryQuery.error as any)?.response?.status === 503
            ? 'Discovery feed is warming up. Data will appear shortly.'
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
          <div key={event.id} className="event-card-wrapper h-full" data-event-id={event.id}>
            <SignalCard event={event} onTrack={toggleTrack} isTracked={!!tracked[event.id]} />
          </div>
        ))}

        {!discoveryQuery.isLoading && filteredEvents.length === 0 && (
          <div className="col-span-full rounded-xl border border-border bg-card p-6 text-sm text-text-muted">
            No events matched the current filter.
          </div>
        )}
      </div>

      {!discoveryQuery.isLoading && filteredEvents.length > 0 && (
        <div ref={loadMoreRef} className="flex min-h-10 items-center justify-center">
          {discoveryQuery.isFetchingNextPage && (
            <span className="font-mono text-xs text-text-muted">Loading more events...</span>
          )}
        </div>
      )}
    </div>
  );
}
