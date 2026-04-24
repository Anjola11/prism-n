import React from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { adminApi } from '../../lib/api/admin';
import { mapDiscoveryEvent } from '../../lib/api/adapters';
import type { DiscoveryCardViewModel } from '../../lib/api/types';
import { SignalCard } from '../../components/ui/SignalCard';

export function AdminSystemTrackerPage() {
  const queryClient = useQueryClient();

  const systemTrackerQuery = useQuery({
    queryKey: ['admin-system-tracker'],
    queryFn: async () => {
      const response = await adminApi.getSystemTracker();
      return response.map(mapDiscoveryEvent);
    },
    staleTime: 30_000,
    gcTime: 5 * 60_000,
    refetchInterval: 30_000,
    placeholderData: (previousData) => previousData,
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

  const events = systemTrackerQuery.data || [];

  const toggleSystemTrack = async (e: React.MouseEvent, eventId: string, source: string) => {
    e.stopPropagation();
    const current = events.find((event) => event.id === eventId);
    const shouldTrack = !current?.trackingEnabled;
    await toggleMutation.mutateAsync({ eventId, shouldTrack, source });
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
            isTracked={!!event.trackingEnabled}
            onTrack={toggleSystemTrack}
          />
        ))}

        {!systemTrackerQuery.isLoading && events.length === 0 && (
          <p className="text-sm text-text-muted">No events are currently being system-tracked.</p>
        )}
      </div>
    </div>
  );
}
