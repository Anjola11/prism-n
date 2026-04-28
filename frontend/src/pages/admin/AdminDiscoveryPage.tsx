import React, { useState } from 'react';
import { useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Filter } from 'lucide-react';

import { adminApi } from '../../lib/api/admin';
import { mapDiscoveryEvent } from '../../lib/api/adapters';
import type { DiscoveryCardViewModel } from '../../lib/api/types';
import { DEFAULT_PAGE_SIZE } from '../../lib/constants';
import { SignalCard } from '../../components/ui/SignalCard';
import { useInfiniteScrollSentinel } from '../../hooks/useInfiniteScrollSentinel';

export function AdminDiscoveryPage() {
  const [filter, setFilter] = useState<'ALL' | 'BAYSE' | 'POLYMARKET'>('ALL');
  const [categoryFilter, setCategoryFilter] = useState<'ALL' | 'POLITICS' | 'SPORTS' | 'ECONOMICS' | 'CRYPTO' | 'NIGERIA'>('ALL');
  const [sortBy, setSortBy] = useState<'latest' | 'conviction_rise'>('latest');
  const [tracked, setTracked] = useState<Record<string, boolean>>({});
  const [pendingByEvent, setPendingByEvent] = useState<Record<string, boolean>>({});
  const queryClient = useQueryClient();

  const discoveryQuery = useInfiniteQuery({
    queryKey: ['admin-discovery', filter, categoryFilter, sortBy, DEFAULT_PAGE_SIZE],
    queryFn: ({ pageParam }) => {
      return adminApi.getDiscoveryPage(
        pageParam,
        DEFAULT_PAGE_SIZE,
        undefined,
        filter === 'ALL' ? undefined : filter.toLowerCase(),
        categoryFilter === 'ALL' ? undefined : categoryFilter.toLowerCase(),
        sortBy,
      );
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

  const toggleMutation = useMutation({
    mutationFn: async ({ eventId, shouldTrack, source }: { eventId: string; shouldTrack: boolean; source: string }) => {
      if (shouldTrack) {
        return adminApi.systemTrack(eventId, undefined, source);
      }
      return adminApi.systemUntrack(eventId, undefined, source);
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['admin-discovery'] }),
        queryClient.invalidateQueries({ queryKey: ['admin-system-tracker'] }),
        queryClient.invalidateQueries({ queryKey: ['admin-overview'] }),
      ]);
    },
  });

  const events: DiscoveryCardViewModel[] =
    discoveryQuery.data?.pages.flatMap((page) => page.items.map(mapDiscoveryEvent)) || [];
  const showDiscoveryError =
    discoveryQuery.isError && !discoveryQuery.isLoading && events.length === 0;

  React.useEffect(() => {
    if (events.length > 0) {
      setTracked((prev) => {
        const next = Object.fromEntries(events.map((event) => [event.id, !!event.trackingEnabled]));
        const prevKeys = Object.keys(prev);
        const nextKeys = Object.keys(next);
        const isUnchanged =
          prevKeys.length === nextKeys.length &&
          nextKeys.every((key) => prev[key] === next[key]);
        return isUnchanged ? prev : next;
      });
    }
  }, [events]);

  const loadMoreRef = useInfiniteScrollSentinel({
    hasNextPage: !!discoveryQuery.hasNextPage,
    isFetchingNextPage: discoveryQuery.isFetchingNextPage,
    fetchNextPage: discoveryQuery.fetchNextPage,
    enabled: !discoveryQuery.isLoading,
  });

  const toggleSystemTrack = async (e: React.MouseEvent, eventId: string, source: string) => {
    e.stopPropagation();
    if (pendingByEvent[eventId]) {
      return;
    }

    const shouldTrack = !tracked[eventId];
    setPendingByEvent((prev) => ({ ...prev, [eventId]: true }));
    setTracked((prev) => ({ ...prev, [eventId]: shouldTrack }));

    try {
      await toggleMutation.mutateAsync({ eventId, shouldTrack, source });
    } catch {
      setTracked((prev) => ({ ...prev, [eventId]: !shouldTrack }));
    } finally {
      setPendingByEvent((prev) => ({ ...prev, [eventId]: false }));
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="mb-1 font-heading text-2xl text-text-primary">Admin Discovery</h1>
        <p className="font-body text-xs text-text-secondary">
          Use this feed to pick events the system itself should track for richer downstream user discovery cards.
        </p>
      </div>

      <div className="flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <span className="mr-2 flex items-center gap-1.5 font-mono text-xs text-text-muted">
            Sort:
          </span>
          {(['latest', 'conviction_rise'] as const).map((option) => (
            <button
              key={option}
              onClick={() => setSortBy(option)}
              className={`rounded-md px-3 py-1.5 font-mono text-xs transition-colors ${sortBy === option ? 'border border-prism-blue/30 bg-prism-blue/20 text-prism-blue' : 'border border-border bg-navy text-text-secondary hover:text-text-primary'}`}
            >
              {option === 'latest' ? 'LATEST' : 'CONVICTION RISE'}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <span className="mr-2 flex items-center gap-1.5 font-mono text-xs text-text-muted">
            <Filter size={14} /> FILTERS:
          </span>
          {(['ALL', 'BAYSE', 'POLYMARKET'] as const).map((option) => (
            <button
              key={option}
              onClick={() => setFilter(option)}
              className={`rounded-md px-3 py-1.5 font-mono text-xs transition-colors ${filter === option ? 'border border-prism-blue/30 bg-prism-blue/20 text-prism-blue' : 'border border-border bg-navy text-text-secondary hover:text-text-primary'}`}
            >
              {option === 'POLYMARKET' ? 'POLY' : option}
            </button>
          ))}
        </div>
        <div className="hide-scrollbar flex max-w-full items-center gap-2 overflow-x-auto whitespace-nowrap">
          {(['ALL', 'POLITICS', 'SPORTS', 'ECONOMICS', 'CRYPTO', 'NIGERIA'] as const).map((option) => (
            <button
              key={option}
              onClick={() => setCategoryFilter(option)}
              className={`rounded-md px-3 py-1.5 font-mono text-xs transition-colors ${categoryFilter === option ? 'border border-prism-blue/30 bg-prism-blue/20 text-prism-blue' : 'border border-border bg-navy text-text-secondary hover:text-text-primary'}`}
            >
              {option}
            </button>
          ))}
        </div>
      </div>

      {discoveryQuery.isLoading && !discoveryQuery.data && (
        <div className="font-mono text-sm text-text-muted">Loading admin discovery...</div>
      )}
      {showDiscoveryError && (
        <div className={`rounded-xl border p-4 text-sm ${
          (discoveryQuery.error as any)?.response?.status === 503
            ? 'border-prism-blue/20 bg-prism-blue/10 text-prism-blue'
            : 'border-amber-500/20 bg-amber-500/10 text-amber-500'
        }`}>
          {(discoveryQuery.error as any)?.response?.status === 503
            ? 'Admin discovery feed is warming up. Data will appear shortly.'
            : 'Failed to load admin discovery.'}
        </div>
      )}

      <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
        {events.map((event: DiscoveryCardViewModel) => (
          <SignalCard
            key={event.id}
            event={event}
            isTracked={!!tracked[event.id]}
            isTrackPending={!!pendingByEvent[event.id]}
            onTrack={toggleSystemTrack}
            origin="admin"
          />
        ))}
      </div>

      {!discoveryQuery.isLoading && events.length > 0 && (
        <div ref={loadMoreRef} className="flex min-h-10 items-center justify-center">
          {discoveryQuery.isFetchingNextPage && (
            <span className="font-mono text-xs text-text-muted">Loading more events...</span>
          )}
        </div>
      )}
    </div>
  );
}
