import React, { useState, useEffect, useLayoutEffect, useRef } from 'react';
import { mockEvents } from '../../data/mockEvents';
import { SignalCard } from '../../components/ui/SignalCard';
import gsap from 'gsap';

export function TrackerPage() {
  const container = useRef<HTMLDivElement>(null);
  
  // Pre-seed with actual volatile markets natively to prevent empty state per intelligence plan
  const trackedEvents = [mockEvents[0], mockEvents[2]];
  
  const [syncTimer, setSyncTimer] = useState(12);

  // Fake live polling
  useEffect(() => {
    const interval = setInterval(() => {
      setSyncTimer(prev => (prev >= 30 ? 0 : prev + 1));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  useLayoutEffect(() => {
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
  }, []);

  // Use the same track/untrack local mock state for UI responsiveness
  const [tracked, setTracked] = useState<Record<string, boolean>>(
    Object.fromEntries(trackedEvents.map(e => [e.id, true]))
  );

  const toggleTrack = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setTracked(prev => ({ ...prev, [id]: !prev[id] }));
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
        {trackedEvents.map(event => (
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
