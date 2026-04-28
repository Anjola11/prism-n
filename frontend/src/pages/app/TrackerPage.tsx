import React, { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { useInfiniteQuery } from '@tanstack/react-query';
import gsap from 'gsap';

import { marketsApi } from '../../lib/api/markets';
import { mapDiscoveryEvent } from '../../lib/api/adapters';
import type { DiscoveryCardViewModel } from '../../lib/api/types';
import { DEFAULT_PAGE_SIZE } from '../../lib/constants';
import { SignalCard } from '../../components/ui/SignalCard';
import { useInfiniteScrollSentinel } from '../../hooks/useInfiniteScrollSentinel';

export function TrackerPage() {
  const container = useRef<HTMLDivElement>(null);
  const hasAnimatedRef = useRef(false);
  const previousEventIdsRef = useRef<string[]>([]);
  const [tracked, setTracked] = useState<Record<string, boolean>>({});
  const [syncTimer, setSyncTimer] = useState(12);
  const trackerQuery = useInfiniteQuery({
    queryKey: ['tracker-feed', DEFAULT_PAGE_SIZE],
    queryFn: ({ pageParam }) => {
      return marketsApi.getTrackerPage(pageParam, DEFAULT_PAGE_SIZE);
    },
    initialPageParam: 1,
    getNextPageParam: (lastPage) => {
      if (!lastPage.pagination.has_more) {
        return undefined;
      }
      return lastPage.pagination.page + 1;
    },
    staleTime: 15_000,
    gcTime: 5 * 60_000,
    refetchInterval: 30_000,
    retry: 2,
  });

  const events: DiscoveryCardViewModel[] = useMemo(
    () => trackerQuery.data?.pages.flatMap((page) => page.items.map(mapDiscoveryEvent)) || [],
    [trackerQuery.data],
  );

  const loadMoreRef = useInfiniteScrollSentinel({
    hasNextPage: !!trackerQuery.hasNextPage,
    isFetchingNextPage: trackerQuery.isFetchingNextPage,
    fetchNextPage: trackerQuery.fetchNextPage,
    enabled: !trackerQuery.isLoading,
  });

  useEffect(() => {
    if (events.length > 0) {
      setTracked((prev) => {
        const next = Object.fromEntries(events.map((event) => [event.id, true]));
        const prevKeys = Object.keys(prev);
        const nextKeys = Object.keys(next);
        const isUnchanged =
          prevKeys.length === nextKeys.length &&
          nextKeys.every((key) => prev[key] === next[key]);

        return isUnchanged ? prev : next;
      });
    }
  }, [events]);

  useEffect(() => {
    const interval = setInterval(() => {
      setSyncTimer((prev) => (prev >= 30 ? 0 : prev + 1));
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  useLayoutEffect(() => {
    if (events.length === 0) return;
    if (hasAnimatedRef.current) return;
    hasAnimatedRef.current = true;

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
  }, [events]);

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

  const toggleTrack = async (e: React.MouseEvent, id: string, source: string) => {
    e.stopPropagation();

    const isTracking = !tracked[id];
    setTracked((prev) => ({ ...prev, [id]: isTracking }));

    try {
      if (isTracking) {
        await marketsApi.trackEvent(id, undefined, source);
      } else {
        await marketsApi.untrackEvent(id, undefined, source);
        await trackerQuery.refetch();
      }
    } catch (err) {
        console.error('Tracking action failed', err);
        setTracked((prev) => ({ ...prev, [id]: !isTracking }));
      }
  };

  const skeletonCards = Array.from({ length: 4 });

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6" ref={container}>
      <div className="flex flex-col justify-between border-b border-border/50 pb-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="mb-1 font-heading text-2xl text-text-primary">Your Tracker</h1>
          <p className="font-body text-xs text-text-secondary">
            Live signal synchronization active. Last cycle: {syncTimer}s ago.
          </p>
        </div>
      </div>

      {trackerQuery.isError && !trackerQuery.isLoading && events.length === 0 && (
        <div className="rounded-xl border border-amber-500/20 bg-amber-500/10 p-4 text-sm text-amber-500">
          Failed to load tracked events.
        </div>
      )}

      <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-2">
        {trackerQuery.isLoading && skeletonCards.map((_, index) => (
          <div
            key={`tracker-skeleton-${index}`}
            className="h-[420px] animate-pulse rounded-xl border border-border bg-card"
          />
        ))}

        {!trackerQuery.isLoading && events.map((event) => (
          <div key={event.id} className="event-card-wrapper h-full" data-event-id={event.id}>
            <SignalCard event={event} onTrack={toggleTrack} isTracked={!!tracked[event.id]} origin="tracker" />
          </div>
        ))}

        {!trackerQuery.isLoading && events.length === 0 && (
          <p className="mt-4 text-sm text-text-muted">You are not tracking any events yet.</p>
        )}
      </div>

      {!trackerQuery.isLoading && events.length > 0 && (
        <div ref={loadMoreRef} className="flex min-h-10 items-center justify-center">
          {trackerQuery.isFetchingNextPage && (
            <span className="font-mono text-xs text-text-muted">Loading more tracked events...</span>
          )}
        </div>
      )}
    </div>
  );
}
