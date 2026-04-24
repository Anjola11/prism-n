import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Activity, BarChart3, Database, Radio, Server, ShieldCheck, Users } from 'lucide-react';

import { adminApi } from '../../lib/api/admin';
import { mapDiscoveryEvent } from '../../lib/api/adapters';
import type { DiscoveryCardViewModel } from '../../lib/api/types';
import { SignalCard } from '../../components/ui/SignalCard';

function StatCard({
  label,
  value,
  icon,
}: {
  label: string;
  value: string | number;
  icon: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="mb-3 flex items-center gap-2 font-mono text-[10px] uppercase tracking-wider text-text-muted">
        {icon}
        {label}
      </div>
      <div className="font-mono text-3xl text-text-primary">{value}</div>
    </div>
  );
}

function StatusTile({
  label,
  value,
  emphasized = false,
}: {
  label: string;
  value: React.ReactNode;
  emphasized?: boolean;
}) {
  return (
    <div className="rounded-lg border border-border/60 bg-navy p-4">
      <div className="font-mono text-[10px] uppercase tracking-wider text-text-muted">{label}</div>
      <div className={`mt-2 font-mono ${emphasized ? 'text-lg' : 'text-xs break-all'} text-text-primary`}>
        {value}
      </div>
    </div>
  );
}

export function AdminOverviewPage() {
  const analyticsQuery = useQuery({
    queryKey: ['admin-analytics'],
    queryFn: () => adminApi.getAnalytics(),
    staleTime: 30_000,
    gcTime: 5 * 60_000,
    refetchInterval: 30_000,
    placeholderData: (previousData) => previousData,
  });

  const systemStatusQuery = useQuery({
    queryKey: ['admin-system-status'],
    queryFn: () => adminApi.getSystemStatus(),
    staleTime: 10_000,
    gcTime: 5 * 60_000,
    refetchInterval: 15_000,
    placeholderData: (previousData) => previousData,
  });

  const auditLogsQuery = useQuery({
    queryKey: ['admin-audit-logs', 10],
    queryFn: () => adminApi.getAuditLogs(10),
    staleTime: 20_000,
    gcTime: 5 * 60_000,
    refetchInterval: 30_000,
    placeholderData: (previousData) => previousData,
  });

  const systemTrackerPreviewQuery = useQuery({
    queryKey: ['admin-system-tracker-preview'],
    queryFn: async () => {
      const response = await adminApi.getSystemTracker();
      return response.map(mapDiscoveryEvent).slice(0, 4);
    },
    staleTime: 30_000,
    gcTime: 5 * 60_000,
    refetchInterval: 30_000,
    placeholderData: (previousData) => previousData,
  });

  const analytics = analyticsQuery.data;
  const systemStatus = systemStatusQuery.data;
  const auditLogs = auditLogsQuery.data || [];
  const systemTrackedEvents = systemTrackerPreviewQuery.data || [];
  const bayseStatus = systemStatus?.websocket?.bayse;
  const polymarketStatus = systemStatus?.websocket?.polymarket;
  const backgroundJobs = systemStatus?.background_jobs || {};
  const memberUsers = analytics ? Math.max(analytics.total_users - analytics.admin_users, 0) : 0;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="mb-1 font-heading text-2xl text-text-primary">Admin Overview</h1>
        <p className="font-body text-xs text-text-secondary">
          Users, system tracking, live backend status, and recent operational activity.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {analytics ? (
          <>
            <StatCard label="Platform Users" value={memberUsers} icon={<Users size={12} />} />
            <StatCard label="Admin Users" value={analytics.admin_users} icon={<ShieldCheck size={12} />} />
            <StatCard label="System Tracked Events" value={analytics.total_system_tracked_events} icon={<Activity size={12} />} />
            <StatCard label="Signal Snapshots" value={analytics.recent_signal_snapshot_count} icon={<BarChart3 size={12} />} />
          </>
        ) : (
          Array.from({ length: 4 }).map((_, index) => (
            <div key={`admin-stat-skeleton-${index}`} className="h-[104px] animate-pulse rounded-xl border border-border bg-card" />
          ))
        )}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1.4fr_1fr]">
        <div className="rounded-xl border border-border bg-card p-5">
          <div className="mb-4 flex items-center gap-2 font-mono text-xs uppercase tracking-wider text-text-muted">
            <Server size={14} /> System Status
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <StatusTile
              label="Redis"
              emphasized
              value={
                <span className={systemStatus?.redis_ok ? 'text-emerald-400' : 'text-amber-500'}>
                  {systemStatus?.redis_ok ? 'Healthy' : 'Needs attention'}
                </span>
              }
            />
            <StatusTile
              label="Discovery Worker"
              emphasized
              value={
                <span className={backgroundJobs.discovery_worker_running ? 'text-emerald-400' : 'text-amber-500'}>
                  {backgroundJobs.discovery_worker_running ? 'Running' : 'Stopped'}
                </span>
              }
            />
            <StatusTile
              label="Bayse Websocket"
              emphasized
              value={
                <span className={bayseStatus?.connected ? 'text-emerald-400' : 'text-amber-500'}>
                  {bayseStatus?.connected ? 'Connected' : 'Disconnected'}
                </span>
              }
            />
            <StatusTile
              label="Polymarket Websocket"
              emphasized
              value={
                <span className={polymarketStatus?.connected ? 'text-emerald-400' : 'text-amber-500'}>
                  {polymarketStatus?.connected ? 'Connected' : 'Disconnected'}
                </span>
              }
            />
            <StatusTile label="Bayse Last Message" value={String(bayseStatus?.last_message_at ?? 'Not available')} />
            <StatusTile label="Polymarket Last Message" value={String(polymarketStatus?.last_message_at ?? 'Not available')} />
            <StatusTile label="Bayse Reconnects" emphasized value={bayseStatus?.reconnect_count ?? 0} />
            <StatusTile label="Polymarket Reconnects" emphasized value={polymarketStatus?.reconnect_count ?? 0} />
          </div>
        </div>

        <div className="rounded-xl border border-border bg-card p-5">
          <div className="mb-4 flex items-center gap-2 font-mono text-xs uppercase tracking-wider text-text-muted">
            <Database size={14} /> Tracking Summary
          </div>
          <div className="flex flex-col gap-4">
            <div className="rounded-lg border border-border/60 bg-navy p-4">
              <div className="font-mono text-[10px] uppercase tracking-wider text-text-muted">User Event Links</div>
              <div className="mt-2 font-mono text-2xl text-text-primary">{analytics?.total_user_event_links ?? '...'}</div>
            </div>
            <div className="rounded-lg border border-border/60 bg-navy p-4">
              <div className="font-mono text-[10px] uppercase tracking-wider text-text-muted">Verified Users</div>
              <div className="mt-2 font-mono text-2xl text-text-primary">{analytics?.verified_users ?? '...'}</div>
            </div>
            <div className="rounded-lg border border-border/60 bg-navy p-4">
              <div className="font-mono text-[10px] uppercase tracking-wider text-text-muted">Distinct User Tracked Events</div>
              <div className="mt-2 font-mono text-2xl text-text-primary">{analytics?.total_user_tracked_events ?? '...'}</div>
            </div>
            <div className="rounded-lg border border-border/60 bg-navy p-4">
              <div className="font-mono text-[10px] uppercase tracking-wider text-text-muted">Baseline Scheduler</div>
              <div className={`mt-2 font-mono text-lg ${backgroundJobs.baseline_scheduler_running ? 'text-emerald-400' : 'text-amber-500'}`}>
                {backgroundJobs.baseline_scheduler_running ? 'Running' : 'Stopped'}
              </div>
            </div>
            <div className="rounded-lg border border-border/60 bg-navy p-4">
              <div className="font-mono text-[10px] uppercase tracking-wider text-text-muted">System Tracked Markets</div>
              <div className="mt-2 font-mono text-2xl text-text-primary">{analytics?.total_system_tracked_markets ?? '...'}</div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1.2fr_1fr]">
        <div className="rounded-xl border border-border bg-card p-5">
          <div className="mb-4 font-mono text-xs uppercase tracking-wider text-text-muted">Most Tracked Events</div>
          <div className="overflow-hidden rounded-lg border border-border/60">
            <table className="w-full">
              <thead className="bg-navy">
                <tr className="text-left">
                  <th className="px-4 py-3 font-mono text-[10px] uppercase tracking-wider text-text-muted">Event</th>
                  <th className="px-4 py-3 font-mono text-[10px] uppercase tracking-wider text-text-muted">Users</th>
                  <th className="px-4 py-3 font-mono text-[10px] uppercase tracking-wider text-text-muted">Markets</th>
                  <th className="px-4 py-3 font-mono text-[10px] uppercase tracking-wider text-text-muted">System</th>
                </tr>
              </thead>
              <tbody>
                {(analytics?.most_tracked_events || []).map((item) => (
                  <tr key={item.event_id} className="border-t border-border/60">
                    <td className="px-4 py-3 text-sm text-text-primary">{item.event_title}</td>
                    <td className="px-4 py-3 font-mono text-sm text-text-secondary">{item.tracker_count}</td>
                    <td className="px-4 py-3 font-mono text-sm text-text-secondary">{item.market_count}</td>
                    <td className="px-4 py-3 font-mono text-xs text-text-secondary">
                      {item.system_tracked ? 'YES' : 'NO'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!analytics && (
            <div className="mt-4 font-mono text-xs text-text-muted">Loading tracking analytics...</div>
          )}
        </div>

        <div className="rounded-xl border border-border bg-card p-5">
          <div className="mb-4 flex items-center gap-2 font-mono text-xs uppercase tracking-wider text-text-muted">
            <Radio size={14} /> Recent Admin Activity
          </div>
          <div className="flex flex-col gap-3">
            {!auditLogsQuery.isLoading && auditLogs.length === 0 && (
              <p className="text-sm text-text-muted">No admin actions logged yet.</p>
            )}
            {auditLogsQuery.isLoading && auditLogs.length === 0 && (
              Array.from({ length: 3 }).map((_, index) => (
                <div key={`admin-log-skeleton-${index}`} className="h-[84px] animate-pulse rounded-lg border border-border/60 bg-navy" />
              ))
            )}
            {auditLogs.map((log) => (
              <div key={log.id} className="rounded-lg border border-border/60 bg-navy p-4">
                <div className="font-mono text-[10px] uppercase tracking-wider text-prism-cyan">{log.action}</div>
                <div className="mt-2 text-sm text-text-primary">{log.event_id || 'General admin action'}</div>
                <div className="mt-1 font-mono text-[10px] text-text-muted">{log.created_at}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div>
        <div className="mb-4 flex items-center justify-between gap-3">
          <h2 className="font-heading text-xl text-text-primary">Currently System Tracked</h2>
          <span className="font-mono text-[10px] uppercase tracking-wider text-text-muted">
            Fast preview, full list in System Tracker
          </span>
        </div>
        <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
          {systemTrackerPreviewQuery.isLoading && systemTrackedEvents.length === 0 && Array.from({ length: 2 }).map((_, index) => (
            <div key={`admin-preview-skeleton-${index}`} className="h-[360px] animate-pulse rounded-xl border border-border bg-card" />
          ))}
          {systemTrackedEvents.map((event: DiscoveryCardViewModel) => (
            <SignalCard key={event.id} event={event} isTracked />
          ))}
          {!systemTrackerPreviewQuery.isLoading && systemTrackedEvents.length === 0 && (
            <p className="text-sm text-text-muted">The system is not tracking any events yet.</p>
          )}
        </div>
      </div>
    </div>
  );
}
