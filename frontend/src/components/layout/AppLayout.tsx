import React, { useEffect, useState } from 'react';
import { Outlet, useNavigate, useRouterState } from '@tanstack/react-router';
import { PrismLogo } from '../brand/PrismLogo';
import { Search, Bookmark, LogOut } from 'lucide-react';
import { authApi } from '../../lib/api/auth';
import type { AuthUserApi } from '../../lib/api/types';

export function AppLayout() {
  const navigate = useNavigate();
  const routerState = useRouterState();
  const [isAuthLoading, setIsAuthLoading] = useState(true);
  const [currentUser, setCurrentUser] = useState<AuthUserApi | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function checkAuth() {
      try {
        const user = await authApi.getMe();
        if (isMounted) {
          setCurrentUser(user);
        }
      } catch (err: any) {
        if (err.response?.status === 401) {
           try {
             await authApi.renewAccessToken();
             const user = await authApi.getMe();
             if (isMounted) {
               setCurrentUser(user);
             }
           } catch (renewErr) {
             if (isMounted) {
               navigate({ to: '/auth/login' });
             }
           }
        } else {
           if (isMounted) {
             navigate({ to: '/auth/login' });
           }
        }
      } finally {
        if (isMounted) {
          setIsAuthLoading(false);
        }
      }
    }
    checkAuth();
    return () => {
      isMounted = false;
    };
  }, [navigate]);

  const handleLogout = async () => {
    try {
      await authApi.logout();
      navigate({ to: '/auth/login' });
    } catch (err) {
      console.error(err);
    }
  };

  const isDiscover = routerState.location.pathname === '/app';
  const isTracker = routerState.location.pathname === '/app/tracker';

  if (isAuthLoading) {
    return <div className="min-h-screen bg-void flex items-center justify-center text-text-muted font-mono text-sm">Authenticating...</div>;
  }

  return (
    <div className="min-h-[100dvh] bg-void flex flex-col">
      {/* Desktop Topbar */}
      <header className="sticky top-0 z-50 h-14 bg-navy/95 backdrop-blur-md border-b border-border px-6 flex items-center justify-between">
        <div className="cursor-pointer" onClick={() => navigate({ to: '/app' })}>
          <PrismLogo size={26} />
        </div>

        {/* Center Nav (Desktop) */}
        <div className="hidden md:flex relative gap-6 h-full items-center">
          <button onClick={() => navigate({ to: '/app' })} className={`h-full font-body text-sm px-2 transition-colors flex items-center relative ${isDiscover ? 'text-text-primary' : 'text-text-secondary hover:text-text-primary'}`}>
            Discover
            {isDiscover && <div className="absolute bottom-0 left-0 right-0 h-[2px] bg-prism-cyan" />}
          </button>
          <button onClick={() => navigate({ to: '/app/tracker' })} className={`h-full font-body text-sm px-2 transition-colors flex items-center relative ${isTracker ? 'text-text-primary' : 'text-text-secondary hover:text-text-primary'}`}>
            Tracker
            {isTracker && <div className="absolute bottom-0 left-0 right-0 h-[2px] bg-prism-cyan" />}
          </button>
        </div>

        {/* Right Section */}
        <div className="flex items-center gap-4">
          <div className="hidden sm:flex flex-col items-end">
            <span className="font-mono text-[10px] uppercase tracking-wider text-text-muted">Signed In</span>
            <span className="text-xs text-text-secondary">{currentUser?.email || 'Session active'}</span>
          </div>
          <div className="w-8 h-8 rounded-full bg-prism-blue/20 border border-prism-blue/40 flex items-center justify-center cursor-pointer hover:bg-prism-blue/30 transition-colors" onClick={handleLogout} title="Logout">
            <LogOut size={14} className="text-prism-cyan" />
          </div>
        </div>
      </header>
      
      <main className="flex-1 w-full max-w-6xl mx-auto px-4 md:px-6 py-6 pb-24 md:pb-6 relative">
        <Outlet />
      </main>

      {/* Mobile Nav */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 h-16 z-50 bg-navy/95 backdrop-blur-md border-t border-border flex items-center">
        <button className="flex-1 flex flex-col items-center justify-center gap-1 h-full relative" onClick={() => navigate({ to: '/app' })}>
          {isDiscover && <div className="absolute top-0 w-6 h-[2px] bg-prism-cyan rounded-full" />}
          <Search size={20} className={isDiscover ? 'text-prism-blue' : 'text-text-muted'} />
          <span className={`font-body text-xs ${isDiscover ? 'text-prism-blue' : 'text-text-muted'}`}>Discover</span>
        </button>
        <button className="flex-1 flex flex-col items-center justify-center gap-1 h-full relative" onClick={() => navigate({ to: '/app/tracker' })}>
           {isTracker && <div className="absolute top-0 w-6 h-[2px] bg-prism-cyan rounded-full" />}
          <Bookmark size={20} className={isTracker ? 'text-prism-blue' : 'text-text-muted'} />
          <span className={`font-body text-xs ${isTracker ? 'text-prism-blue' : 'text-text-muted'}`}>Tracker</span>
        </button>
      </nav>
    </div>
  );
}
