import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { adminApi } from '../../lib/api/admin';
import { mapDiscoveryEvent } from '../../lib/api/adapters';
import type { DiscoveryCardViewModel } from '../../lib/api/types';
import { SignalCard } from '../../components/ui/SignalCard';

export function AdminDiscoveryPage() {
  const [filter, setFilter] = useState<'ALL' | 'BAYSE' | 'POLYMARKET'>('ALL');
  const queryClient = useQueryClient();

  const discoveryQuery = useQuery({
    queryKey: ['admin-discovery', filter],
    queryFn: async () => {
      const response = await adminApi.getDiscovery(undefined, filter === 'ALL' ? undefined : filter.toLowerCase());
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
        queryClient.invalidateQueries({ queryKey: ['admin-discovery'] }),
        queryClient.invalidateQueries({ queryKey: ['admin-system-tracker'] }),
        queryClient.invalidateQueries({ queryKey: ['admin-overview'] }),
      ]);
    },
  });

  const events = discoveryQuery.data || [];

  const toggleSystemTrack = async (e: React.MouseEvent, eventId: string, source: string) => {
    e.stopPropagation();
    const current = events.find((event) => event.id === eventId);
    const shouldTrack = !current?.trackingEnabled;
    await toggleMutation.mutateAsync({ eventId, shouldTrack, source });
  };

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="mb-1 font-heading text-2xl text-text-primary">Admin Discovery</h1>
        <p className="font-body text-xs text-text-secondary">
          Use this feed to pick events the system itself should track for richer downstream user discovery cards.
        </p>
      </div>

      <div className="flex items-center gap-2">
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

      {discoveryQuery.isLoading && !discoveryQuery.data && (
        <div className="font-mono text-sm text-text-muted">Loading admin discovery...</div>
      )}
      {discoveryQuery.isError && (
        <div className="rounded-xl border border-amber-500/20 bg-amber-500/10 p-4 text-sm text-amber-500">
          Failed to load admin discovery.
        </div>
      )}

      <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
        {events.map((event: DiscoveryCardViewModel) => (
          <SignalCard
            key={event.id}
            event={event}
            isTracked={!!event.trackingEnabled}
            onTrack={toggleSystemTrack}
          />
        ))}
      </div>
    </div>
  );
}
