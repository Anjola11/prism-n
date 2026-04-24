import React, { useEffect, useState } from 'react';
import { Outlet, useNavigate, useRouterState } from '@tanstack/react-router';
import { Activity, LogOut, Radar, Shield, ShieldCheck } from 'lucide-react';

import { PrismLogo } from '../brand/PrismLogo';
import { adminApi } from '../../lib/api/admin';
import { authApi } from '../../lib/api/auth';
import type { AuthUserApi } from '../../lib/api/types';

const adminBasePath = import.meta.env.VITE_ADMIN_ROUTE_PREFIX || '/control-room';

export function AdminLayout() {
  const navigate = useNavigate();
  const routerState = useRouterState();
  const [admin, setAdmin] = useState<AuthUserApi | null>(null);
  const [isLoading, setIsLoading] = useState(true);

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

  if (isLoading) {
    return <div className="flex min-h-screen items-center justify-center bg-void font-mono text-sm text-text-muted">Validating admin session...</div>;
  }

  return (
    <div className="min-h-[100dvh] bg-void">
      <header className="sticky top-0 z-50 flex h-14 items-center justify-between border-b border-border bg-navy/95 px-6 backdrop-blur-md">
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
        </div>

        <div className="flex items-center gap-4">
          <div className="hidden flex-col items-end sm:flex">
            <span className="font-mono text-[10px] uppercase tracking-wider text-text-muted">Admin Session</span>
            <span className="text-xs text-text-secondary">{admin?.email || 'Admin'}</span>
          </div>
          <button
            className="flex h-8 w-8 items-center justify-center rounded-full border border-prism-blue/40 bg-prism-blue/20 transition-colors hover:bg-prism-blue/30"
            onClick={handleLogout}
            title="Logout"
          >
            <LogOut size={14} className="text-prism-cyan" />
          </button>
        </div>
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
