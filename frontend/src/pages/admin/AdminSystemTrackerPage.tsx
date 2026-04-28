import React from 'react';
import { useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { adminApi } from '../../lib/api/admin';
import { mapDiscoveryEvent } from '../../lib/api/adapters';
import type { DiscoveryCardViewModel } from '../../lib/api/types';
import { DEFAULT_PAGE_SIZE } from '../../lib/constants';
import { SignalCard } from '../../components/ui/SignalCard';
import { useInfiniteScrollSentinel } from '../../hooks/useInfiniteScrollSentinel';

export function AdminSystemTrackerPage() {
  const [tracked, setTracked] = React.useState<Record<string, boolean>>({});
  const [pendingByEvent, setPendingByEvent] = React.useState<Record<string, boolean>>({});
  const queryClient = useQueryClient();

  const systemTrackerQuery = useInfiniteQuery({
    queryKey: ['admin-system-tracker', DEFAULT_PAGE_SIZE],
    queryFn: ({ pageParam }) => {
      return adminApi.getSystemTrackerPage(pageParam, DEFAULT_PAGE_SIZE);
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
        queryClient.invalidateQueries({ queryKey: ['admin-system-tracker'] }),
        queryClient.invalidateQueries({ queryKey: ['admin-discovery'] }),
        queryClient.invalidateQueries({ queryKey: ['admin-overview'] }),
      ]);
    },
  });

  const events: DiscoveryCardViewModel[] =
    systemTrackerQuery.data?.pages.flatMap((page) => page.items.map(mapDiscoveryEvent)) || [];

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
    hasNextPage: !!systemTrackerQuery.hasNextPage,
    isFetchingNextPage: systemTrackerQuery.isFetchingNextPage,
    fetchNextPage: systemTrackerQuery.fetchNextPage,
    enabled: !systemTrackerQuery.isLoading,
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
        <h1 className="mb-1 font-heading text-2xl text-text-primary">System Tracker</h1>
        <p className="font-body text-xs text-text-secondary">
          Events the system is actively tracking independent of any single user.
        </p>
      </div>

      {systemTrackerQuery.isLoading && !systemTrackerQuery.data && (
        <div className="font-mono text-sm text-text-muted">Loading system tracked events...</div>
      )}
      {systemTrackerQuery.isError && (
        <div className="rounded-xl border border-amber-500/20 bg-amber-500/10 p-4 text-sm text-amber-500">
          Failed to load system tracker.
        </div>
      )}

      <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
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

        {!systemTrackerQuery.isLoading && events.length === 0 && (
          <p className="text-sm text-text-muted">No events are currently being system-tracked.</p>
        )}
      </div>

      {!systemTrackerQuery.isLoading && events.length > 0 && (
        <div ref={loadMoreRef} className="flex min-h-10 items-center justify-center">
          {systemTrackerQuery.isFetchingNextPage && (
            <span className="font-mono text-xs text-text-muted">Loading more tracked events...</span>
          )}
        </div>
      )}
    </div>
  );
}
