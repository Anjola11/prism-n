import React, { useLayoutEffect, useRef, useState, useEffect } from 'react';
import { useNavigate } from '@tanstack/react-router';
import { marketsApi } from '../../lib/api/markets';
import { mapDiscoveryEvent } from '../../lib/api/adapters';
import type { DiscoveryCardViewModel } from '../../lib/api/types';
import { SignalCard } from '../../components/ui/SignalCard';
import gsap from 'gsap';
import { Filter } from 'lucide-react';

export function DiscoveryPage() {
  const container = useRef<HTMLDivElement>(null);
  const [filter, setFilter] = useState<'ALL' | 'BAYSE' | 'POLYMARKET'>('ALL');
  const [tracked, setTracked] = useState<Record<string, boolean>>({});
  const [events, setEvents] = useState<DiscoveryCardViewModel[]>([]);

  useEffect(() => {
    async function fetchEvents() {
      try {
        const apiEvents = await marketsApi.getEvents();
        const mapped = apiEvents.map(mapDiscoveryEvent);
        setEvents(mapped);
      } catch (err) {
        console.error("Failed to fetch events", err);
      }
    }
    fetchEvents();
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
  }, [filter, events]);

  const filteredEvents = events.filter(e => {
    if (filter === 'ALL') return true;
    return e.source.toUpperCase() === filter;
  });

  const toggleTrack = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    const isTracking = !tracked[id];
    setTracked(prev => ({ ...prev, [id]: isTracking }));
    try {
      if (isTracking) {
         await marketsApi.trackEvent(id);
      } else {
         await marketsApi.untrackEvent(id);
      }
    } catch (err) {
      console.error("Tracking action failed", err);
      // Revert optimism
      setTracked(prev => ({ ...prev, [id]: !isTracking }));
    }
  };

  return (
    <div className="flex flex-col gap-6" ref={container}>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-border/50 pb-4">
        <div>
          <h1 className="font-heading text-2xl text-text-primary mb-1">Discovery Feed</h1>
          <p className="font-body text-xs text-text-secondary">Real-time signal feed across generic and combined markets.</p>
        </div>
        
        <div className="flex items-center gap-2 mt-4 sm:mt-0">
           <span className="font-mono text-xs text-text-muted flex items-center gap-1.5 mr-2">
             <Filter size={14} /> FILTERS:
           </span>
           <button onClick={() => setFilter('ALL')} className={`px-3 py-1.5 rounded-md font-mono text-[10px] sm:text-xs transition-colors ${filter === 'ALL' ? 'bg-prism-blue/20 text-prism-blue border border-prism-blue/30' : 'bg-navy border border-border text-text-secondary hover:text-text-primary'}`}>ALL</button>
           <button onClick={() => setFilter('BAYSE')} className={`px-3 py-1.5 rounded-md font-mono text-[10px] sm:text-xs transition-colors ${filter === 'BAYSE' ? 'bg-prism-blue/20 text-prism-blue border border-prism-blue/30' : 'bg-navy border border-border text-text-secondary hover:text-text-primary'}`}>BAYSE</button>
           <button onClick={() => setFilter('POLYMARKET')} className={`px-3 py-1.5 rounded-md font-mono text-[10px] sm:text-xs transition-colors ${filter === 'POLYMARKET' ? 'bg-prism-blue/20 text-prism-blue border border-prism-blue/30' : 'bg-navy border border-border text-text-secondary hover:text-text-primary'}`}>POLY</button>
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {filteredEvents.map(event => (
          <div key={event.id} className="event-card-wrapper h-full">
             <SignalCard 
               event={event} 
               onTrack={toggleTrack} 
               isTracked={!!tracked[event.id]} 
             />
          </div>
        ))}
      </div>
    </div>
  );
}
