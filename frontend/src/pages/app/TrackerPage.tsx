import React, { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import gsap from 'gsap';

import { marketsApi } from '../../lib/api/markets';
import { mapDiscoveryEvent } from '../../lib/api/adapters';
import type { DiscoveryCardViewModel } from '../../lib/api/types';
import { SignalCard } from '../../components/ui/SignalCard';

export function TrackerPage() {
  const container = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();
  const [tracked, setTracked] = useState<Record<string, boolean>>({});
  const [syncTimer, setSyncTimer] = useState(12);
  const trackerQuery = useQuery({
    queryKey: ['tracker-feed'],
    queryFn: async () => {
      const apiEvents = await marketsApi.getTracker();
      return apiEvents.map(mapDiscoveryEvent);
    },
    staleTime: 15_000,
    gcTime: 5 * 60_000,
    refetchInterval: 30_000,
    placeholderData: (previousData) => previousData,
  });

  const events: DiscoveryCardViewModel[] = trackerQuery.data || [];

  useEffect(() => {
    if (events.length > 0) {
      setTracked(Object.fromEntries(events.map((event) => [event.id, true])));
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

  const toggleTrack = async (e: React.MouseEvent, id: string, source: string) => {
    e.stopPropagation();

    const isTracking = !tracked[id];
    setTracked((prev) => ({ ...prev, [id]: isTracking }));

    try {
      if (isTracking) {
        await marketsApi.trackEvent(id, undefined, source);
      } else {
        await marketsApi.untrackEvent(id, undefined, source);
        queryClient.setQueryData<DiscoveryCardViewModel[] | undefined>(['tracker-feed'], (prev) =>
          (prev || []).filter((event) => event.id !== id),
        );
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

      {trackerQuery.isError && !trackerQuery.isLoading && (
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
          <div key={event.id} className="event-card-wrapper h-full">
            <SignalCard event={event} onTrack={toggleTrack} isTracked={!!tracked[event.id]} />
          </div>
        ))}

        {!trackerQuery.isLoading && events.length === 0 && (
          <p className="mt-4 text-sm text-text-muted">You are not tracking any events yet.</p>
        )}
      </div>
    </div>
  );
}
