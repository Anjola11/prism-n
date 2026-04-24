import React, { useEffect, useState } from 'react';
import { Activity, BarChart3, Database, Server, ShieldCheck, Users } from 'lucide-react';

import { adminApi } from '../../lib/api/admin';
import { mapDiscoveryEvent } from '../../lib/api/adapters';
import type { AdminActionLogApi, AdminOverviewApi, DiscoveryCardViewModel } from '../../lib/api/types';
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

export function AdminOverviewPage() {
  const [overview, setOverview] = useState<AdminOverviewApi | null>(null);
  const [auditLogs, setAuditLogs] = useState<AdminActionLogApi[]>([]);
  const [systemTrackedEvents, setSystemTrackedEvents] = useState<DiscoveryCardViewModel[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function fetchOverview() {
      try {
        const [overviewResponse, logsResponse] = await Promise.all([
          adminApi.getOverview(),
          adminApi.getAuditLogs(10),
        ]);
        setOverview(overviewResponse);
        setAuditLogs(logsResponse);
        setSystemTrackedEvents(overviewResponse.system_tracked_events.map(mapDiscoveryEvent));
      } catch (err) {
        console.error('Failed to load admin overview', err);
        setError('Failed to load admin overview.');
      } finally {
        setIsLoading(false);
      }
    }

    fetchOverview();
  }, []);

  if (isLoading) {
    return <div className="font-mono text-sm text-text-muted">Loading admin overview...</div>;
  }

  if (error || !overview) {
    return (
      <div className="rounded-xl border border-amber-500/20 bg-amber-500/10 p-4 text-sm text-amber-500">
        {error || 'Overview unavailable.'}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="mb-1 font-heading text-2xl text-text-primary">Admin Overview</h1>
        <p className="font-body text-xs text-text-secondary">
          Users, system tracking, live backend status, and recent operational activity.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Registered Users" value={overview.total_users} icon={<Users size={12} />} />
        <StatCard label="Verified Users" value={overview.verified_users} icon={<ShieldCheck size={12} />} />
        <StatCard label="System Tracked Events" value={overview.total_system_tracked_events} icon={<Activity size={12} />} />
        <StatCard label="Signal Snapshots" value={overview.recent_signal_snapshot_count} icon={<BarChart3 size={12} />} />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1.4fr_1fr]">
        <div className="rounded-xl border border-border bg-card p-5">
          <div className="mb-4 flex items-center gap-2 font-mono text-xs uppercase tracking-wider text-text-muted">
            <Server size={14} /> System Status
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="rounded-lg border border-border/60 bg-navy p-4">
              <div className="font-mono text-[10px] uppercase tracking-wider text-text-muted">Redis</div>
              <div className={`mt-2 font-mono text-lg ${overview.system_status.redis_ok ? 'text-emerald-400' : 'text-amber-500'}`}>
                {overview.system_status.redis_ok ? 'Healthy' : 'Needs attention'}
              </div>
            </div>
            <div className="rounded-lg border border-border/60 bg-navy p-4">
              <div className="font-mono text-[10px] uppercase tracking-wider text-text-muted">WebSocket</div>
              <div className={`mt-2 font-mono text-lg ${overview.system_status.websocket?.connected ? 'text-emerald-400' : 'text-amber-500'}`}>
                {overview.system_status.websocket?.connected ? 'Connected' : 'Disconnected'}
              </div>
            </div>
            <div className="rounded-lg border border-border/60 bg-navy p-4">
              <div className="font-mono text-[10px] uppercase tracking-wider text-text-muted">Reconnect Count</div>
              <div className="mt-2 font-mono text-lg text-text-primary">
                {overview.system_status.websocket?.reconnect_count ?? 0}
              </div>
            </div>
            <div className="rounded-lg border border-border/60 bg-navy p-4">
              <div className="font-mono text-[10px] uppercase tracking-wider text-text-muted">Last Message</div>
              <div className="mt-2 break-all font-mono text-xs text-text-secondary">
                {String(overview.system_status.websocket?.last_message_at ?? 'Not available')}
              </div>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-border bg-card p-5">
          <div className="mb-4 flex items-center gap-2 font-mono text-xs uppercase tracking-wider text-text-muted">
            <Database size={14} /> Tracking Summary
          </div>
          <div className="flex flex-col gap-4">
            <div className="rounded-lg border border-border/60 bg-navy p-4">
              <div className="font-mono text-[10px] uppercase tracking-wider text-text-muted">User Event Links</div>
              <div className="mt-2 font-mono text-2xl text-text-primary">{overview.total_user_event_links}</div>
            </div>
            <div className="rounded-lg border border-border/60 bg-navy p-4">
              <div className="font-mono text-[10px] uppercase tracking-wider text-text-muted">Distinct User Tracked Events</div>
              <div className="mt-2 font-mono text-2xl text-text-primary">{overview.total_user_tracked_events}</div>
            </div>
            <div className="rounded-lg border border-border/60 bg-navy p-4">
              <div className="font-mono text-[10px] uppercase tracking-wider text-text-muted">System Tracked Markets</div>
              <div className="mt-2 font-mono text-2xl text-text-primary">{overview.total_system_tracked_markets}</div>
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
                {overview.most_tracked_events.map((item) => (
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
        </div>

        <div className="rounded-xl border border-border bg-card p-5">
          <div className="mb-4 font-mono text-xs uppercase tracking-wider text-text-muted">Recent Admin Activity</div>
          <div className="flex flex-col gap-3">
            {auditLogs.length === 0 && (
              <p className="text-sm text-text-muted">No admin actions logged yet.</p>
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
        <h2 className="mb-4 font-heading text-xl text-text-primary">Currently System Tracked</h2>
        <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
          {systemTrackedEvents.map((event) => (
            <SignalCard key={event.id} event={event} isTracked />
          ))}
          {systemTrackedEvents.length === 0 && (
            <p className="text-sm text-text-muted">The system is not tracking any events yet.</p>
          )}
        </div>
      </div>
    </div>
  );
}
