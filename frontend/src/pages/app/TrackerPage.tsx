import React, { useState, useEffect, useLayoutEffect, useRef } from 'react';
import { marketsApi } from '../../lib/api/markets';
import { mapDiscoveryEvent } from '../../lib/api/adapters';
import { DiscoveryCardViewModel } from '../../lib/api/types';
import { SignalCard } from '../../components/ui/SignalCard';
import gsap from 'gsap';

export function TrackerPage() {
  const container = useRef<HTMLDivElement>(null);
  const [events, setEvents] = useState<DiscoveryCardViewModel[]>([]);
  const [syncTimer, setSyncTimer] = useState(12);

  useEffect(() => {
    async function fetchTracker() {
      try {
        const apiEvents = await marketsApi.getTracker();
        const mapped = apiEvents.map(mapDiscoveryEvent);
        setEvents(mapped);
      } catch (err) {
        console.error("Failed to fetch tracked events", err);
      }
    }
    fetchTracker();
  }, []);

  // Fake live polling visualization
  useEffect(() => {
    const interval = setInterval(() => {
      setSyncTimer(prev => (prev >= 30 ? 0 : prev + 1));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  useLayoutEffect(() => {
    if (events.length === 0) return;
    const ctx = gsap.context(() => {
      gsap.fromTo('.event-card-wrapper', 
        { opacity: 0, y: 15 },
        { 
          opacity: 1, 
          y: 0, 
          duration: 0.5, 
          stagger: 0.08, 
          ease: 'power3.out', 
          clearProps: 'all' 
        }
      );
    }, container);
    return () => ctx.revert();
  }, [events]);

  const [tracked, setTracked] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (events.length > 0) {
      setTracked(Object.fromEntries(events.map(e => [e.id, true])));
    }
  }, [events]);

  const toggleTrack = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    const isTracking = !tracked[id];
    setTracked(prev => ({ ...prev, [id]: isTracking }));
    try {
      if (isTracking) {
         await marketsApi.trackEvent(id);
      } else {
         await marketsApi.untrackEvent(id);
         // Optionally remove from the list instantly:
         setEvents(prev => prev.filter(ev => ev.id !== id));
      }
    } catch (err) {
      console.error("Tracking action failed", err);
      setTracked(prev => ({ ...prev, [id]: !isTracking }));
    }
  };

  return (
    <div className="flex flex-col gap-6 w-full max-w-5xl mx-auto" ref={container}>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-border/50 pb-4">
        <div>
          <h1 className="font-heading text-2xl text-text-primary mb-1">Your Tracker</h1>
          <p className="font-body text-xs text-text-secondary">Live signal synchronization active.</p>
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-5">
        {events.map(event => (
          <div key={event.id} className="event-card-wrapper h-full">
            <SignalCard 
               event={event} 
               onTrack={toggleTrack} 
               isTracked={!!tracked[event.id]} 
            />
          </div>
        ))}
        {events.length === 0 && (
          <p className="text-sm text-text-muted mt-4">You are not tracking any events yet.</p>
        )}
      </div>
    </div>
  );
}
