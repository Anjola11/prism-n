import { useEffect, useState } from 'react';
import { Outlet, useNavigate, useRouterState } from '@tanstack/react-router';
import { Activity, LogOut, Menu, Radar, Shield, ShieldCheck, X } from 'lucide-react';

import { PrismLogo } from '../brand/PrismLogo';
import { adminApi } from '../../lib/api/admin';
import { authApi } from '../../lib/api/auth';
import type { AuthUserApi } from '../../lib/api/types';
import { ThemeToggle } from '../ui/ThemeToggle';

const adminBasePath = import.meta.env.VITE_ADMIN_ROUTE_PREFIX || '/control-room';

export function AdminLayout() {
  const navigate = useNavigate();
  const routerState = useRouterState();
  const [admin, setAdmin] = useState<AuthUserApi | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);

  useEffect(() => {
    let isMounted = true;

    async function checkAdminSession() {
      try {
        const currentAdmin = await adminApi.getMe();
        if (isMounted) {
          setAdmin(currentAdmin);
        }
      } catch (err: any) {
        if (err.response?.status === 401) {
          try {
            await authApi.renewAccessToken();
            const currentAdmin = await adminApi.getMe();
            if (isMounted) {
              setAdmin(currentAdmin);
            }
          } catch {
            if (isMounted) {
              navigate({ to: `${adminBasePath}/login` });
            }
          }
        } else if (isMounted) {
          navigate({ to: `${adminBasePath}/login` });
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    checkAdminSession();
    return () => {
      isMounted = false;
    };
  }, [navigate]);

  const handleLogout = async () => {
    try {
      await authApi.logout();
    } finally {
      navigate({ to: `${adminBasePath}/login` });
    }
  };

  const pathname = routerState.location.pathname;
  const isOverview = pathname === adminBasePath;
  const isDiscovery = pathname === `${adminBasePath}/discovery`;
  const isSystemTracker = pathname === `${adminBasePath}/system-tracker`;

  useEffect(() => {
    setIsMobileNavOpen(false);
  }, [pathname]);

  if (isLoading) {
    return <div className="flex min-h-screen items-center justify-center bg-void font-mono text-sm text-text-muted">Validating admin session...</div>;
  }

  return (
    <div className="min-h-[100dvh] bg-void">
      <header className="sticky top-0 z-50 border-b border-border bg-navy/95 px-4 backdrop-blur-md md:px-6">
        <div className="flex h-14 items-center justify-between">
        <div className="cursor-pointer" onClick={() => navigate({ to: adminBasePath })}>
          <PrismLogo size={26} />
        </div>

        <div className="hidden items-center gap-6 md:flex">
          <button
            onClick={() => navigate({ to: adminBasePath })}
            className={`relative flex h-full items-center px-2 font-body text-sm transition-colors ${isOverview ? 'text-text-primary' : 'text-text-secondary hover:text-text-primary'}`}
          >
            Overview
            {isOverview && <div className="absolute right-0 bottom-0 left-0 h-[2px] bg-prism-cyan" />}
          </button>
          <button
            onClick={() => navigate({ to: `${adminBasePath}/discovery` })}
            className={`relative flex h-full items-center px-2 font-body text-sm transition-colors ${isDiscovery ? 'text-text-primary' : 'text-text-secondary hover:text-text-primary'}`}
          >
            Discovery
            {isDiscovery && <div className="absolute right-0 bottom-0 left-0 h-[2px] bg-prism-cyan" />}
          </button>
          <button
            onClick={() => navigate({ to: `${adminBasePath}/system-tracker` })}
            className={`relative flex h-full items-center px-2 font-body text-sm transition-colors ${isSystemTracker ? 'text-text-primary' : 'text-text-secondary hover:text-text-primary'}`}
          >
            System Tracker
            {isSystemTracker && <div className="absolute right-0 bottom-0 left-0 h-[2px] bg-prism-cyan" />}
          </button>
          <button
            onClick={handleLogout}
            className="flex h-full items-center gap-2 px-2 font-body text-sm text-text-secondary transition-colors hover:text-text-primary"
            title="Logout"
          >
            <LogOut size={14} />
            Logout
          </button>
        </div>

        <div className="flex items-center gap-4">
          <ThemeToggle compact />
          <button
            className="flex h-8 w-8 items-center justify-center rounded-full border border-border bg-card/40 text-text-secondary transition-colors hover:text-text-primary md:hidden"
            onClick={() => setIsMobileNavOpen((prev) => !prev)}
            title={isMobileNavOpen ? 'Close navigation' : 'Open navigation'}
            aria-label={isMobileNavOpen ? 'Close navigation' : 'Open navigation'}
          >
            {isMobileNavOpen ? <X size={14} /> : <Menu size={14} />}
          </button>
          <div className="hidden flex-col items-end sm:flex">
            <span className="font-mono text-[10px] uppercase tracking-wider text-text-muted">Admin Session</span>
            <span className="text-xs text-text-secondary">{admin?.email || 'Admin'}</span>
          </div>
        </div>
        </div>

        {isMobileNavOpen && (
          <div className="border-t border-border py-2 md:hidden">
            <button
              onClick={() => navigate({ to: adminBasePath })}
              className={`flex w-full items-center rounded-lg px-3 py-2 text-left font-body text-sm transition-colors ${
                isOverview ? 'bg-prism-blue/20 text-text-primary' : 'text-text-secondary hover:bg-card hover:text-text-primary'
              }`}
            >
              Overview
            </button>
            <button
              onClick={() => navigate({ to: `${adminBasePath}/discovery` })}
              className={`mt-1 flex w-full items-center rounded-lg px-3 py-2 text-left font-body text-sm transition-colors ${
                isDiscovery ? 'bg-prism-blue/20 text-text-primary' : 'text-text-secondary hover:bg-card hover:text-text-primary'
              }`}
            >
              Discovery
            </button>
            <button
              onClick={() => navigate({ to: `${adminBasePath}/system-tracker` })}
              className={`mt-1 flex w-full items-center rounded-lg px-3 py-2 text-left font-body text-sm transition-colors ${
                isSystemTracker ? 'bg-prism-blue/20 text-text-primary' : 'text-text-secondary hover:bg-card hover:text-text-primary'
              }`}
            >
              System Tracker
            </button>
            <button
              onClick={handleLogout}
              className="mt-3 flex w-full items-center gap-2 rounded-lg border border-prism-blue/30 bg-prism-blue/10 px-3 py-2 text-left font-body text-sm text-prism-cyan transition-colors hover:bg-prism-blue/20"
            >
              <LogOut size={14} />
              Logout
            </button>
          </div>
        )}
      </header>

      <main className="mx-auto w-full max-w-6xl px-4 py-6 md:px-6">
        <div className="mb-6 flex flex-wrap items-center gap-3 rounded-xl border border-border bg-card px-4 py-3">
          <span className="inline-flex items-center gap-2 rounded-full border border-prism-blue/30 bg-prism-blue/10 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.2em] text-prism-cyan">
            <ShieldCheck size={12} /> Admin Surface
          </span>
          <span className="inline-flex items-center gap-2 font-mono text-[11px] text-text-muted">
            <Shield size={12} /> Restricted operational visibility
          </span>
          <span className="inline-flex items-center gap-2 font-mono text-[11px] text-text-muted">
            <Activity size={12} /> System analytics and controls
          </span>
          <span className="inline-flex items-center gap-2 font-mono text-[11px] text-text-muted">
            <Radar size={12} /> Discovery feeds for system tracking
          </span>
        </div>
        <Outlet />
      </main>
    </div>
  );
}
