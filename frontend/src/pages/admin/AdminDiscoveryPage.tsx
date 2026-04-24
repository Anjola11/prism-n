import React, { useEffect, useState } from 'react';

import { adminApi } from '../../lib/api/admin';
import { mapDiscoveryEvent } from '../../lib/api/adapters';
import type { DiscoveryCardViewModel } from '../../lib/api/types';
import { SignalCard } from '../../components/ui/SignalCard';

export function AdminDiscoveryPage() {
  const [filter, setFilter] = useState<'ALL' | 'BAYSE' | 'POLYMARKET'>('ALL');
  const [events, setEvents] = useState<DiscoveryCardViewModel[]>([]);
  const [tracked, setTracked] = useState<Record<string, boolean>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function fetchDiscovery() {
      try {
        const response = await adminApi.getDiscovery(undefined, filter === 'ALL' ? undefined : filter.toLowerCase());
        const mapped = response.map(mapDiscoveryEvent);
        setEvents(mapped);
        setTracked(Object.fromEntries(mapped.map((event) => [event.id, event.trackingEnabled])));
      } catch (err) {
        console.error('Failed to load admin discovery', err);
        setError('Failed to load admin discovery.');
      } finally {
        setIsLoading(false);
      }
    }

    fetchDiscovery();
  }, [filter]);

  const toggleSystemTrack = async (e: React.MouseEvent, eventId: string, source: string) => {
    e.stopPropagation();
    const nextState = !tracked[eventId];
    setTracked((prev) => ({ ...prev, [eventId]: nextState }));

    try {
      if (nextState) {
        await adminApi.systemTrack(eventId, undefined, source);
      } else {
        await adminApi.systemUntrack(eventId, undefined, source);
      }
    } catch (err) {
      console.error('System tracking action failed', err);
      setTracked((prev) => ({ ...prev, [eventId]: !nextState }));
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

      {isLoading && <div className="font-mono text-sm text-text-muted">Loading admin discovery...</div>}
      {error && !isLoading && (
        <div className="rounded-xl border border-amber-500/20 bg-amber-500/10 p-4 text-sm text-amber-500">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
        {!isLoading && events.map((event) => (
          <SignalCard
            key={event.id}
            event={event}
            isTracked={!!tracked[event.id]}
            onTrack={toggleSystemTrack}
          />
        ))}
      </div>
    </div>
  );
}
