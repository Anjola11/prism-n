import React, { useEffect, useState } from 'react';

import { adminApi } from '../../lib/api/admin';
import { mapDiscoveryEvent } from '../../lib/api/adapters';
import type { DiscoveryCardViewModel } from '../../lib/api/types';
import { SignalCard } from '../../components/ui/SignalCard';

export function AdminSystemTrackerPage() {
  const [events, setEvents] = useState<DiscoveryCardViewModel[]>([]);
  const [tracked, setTracked] = useState<Record<string, boolean>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;

    async function fetchSystemTracker(attempt = 1) {
      try {
        setError('');
        const response = await adminApi.getSystemTracker();
        if (cancelled) return;
        const mapped = response.map(mapDiscoveryEvent);
        setEvents(mapped);
        setTracked(Object.fromEntries(mapped.map((event) => [event.id, true])));
      } catch (err) {
        console.error('Failed to load system tracker', err);
        if (!cancelled && attempt < 3) {
          setError(`Loading system tracker (attempt ${attempt + 1})...`);
          setTimeout(() => fetchSystemTracker(attempt + 1), 2000);
          return;
        }
        if (!cancelled) setError('Failed to load system tracker.');
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    fetchSystemTracker();
    return () => { cancelled = true; };
  }, []);

  const toggleSystemTrack = async (e: React.MouseEvent, eventId: string, source: string) => {
    e.stopPropagation();
    const nextState = !tracked[eventId];
    setTracked((prev) => ({ ...prev, [eventId]: nextState }));

    try {
      if (nextState) {
        await adminApi.systemTrack(eventId, undefined, source);
      } else {
        await adminApi.systemUntrack(eventId, undefined, source);
        setEvents((prev) => prev.filter((event) => event.id !== eventId));
      }
    } catch (err) {
      console.error('System tracking action failed', err);
      setTracked((prev) => ({ ...prev, [eventId]: !nextState }));
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

      {isLoading && <div className="font-mono text-sm text-text-muted">Loading system tracked events...</div>}
      {error && !isLoading && (
        <div className="rounded-xl border border-amber-500/20 bg-amber-500/10 p-4 text-sm text-amber-500">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
        {!isLoading && events.map((event) => (
          <SignalCard
            key={event.id}
            event={event}
            isTracked={!!tracked[event.id]}
            onTrack={toggleSystemTrack}
          />
        ))}

        {!isLoading && events.length === 0 && (
          <p className="text-sm text-text-muted">No events are currently being system-tracked.</p>
        )}
      </div>
    </div>
  );
}
