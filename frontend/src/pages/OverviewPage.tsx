/**
 * Overview dashboard — key fleet metrics and charts.
 */
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Cpu, Wifi, WifiOff, AlertTriangle, Package, Rocket, CheckCircle2 } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';
import { deploymentsAPI } from '../services/api';
import StatCard from '../components/StatCard';
import StatusBadge from '../components/StatusBadge';
import { LoadingSpinner, EmptyState } from '../components/States';
import { timeAgo } from '../utils/format';
import type { DashboardStats } from '../types';

const CHART_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#f97316'];

export default function OverviewPage() {
  const { data: stats, isLoading, error } = useQuery<DashboardStats>({
    queryKey: ['dashboard-stats'],
    queryFn: async () => {
      const { data } = await deploymentsAPI.stats();
      return data;
    },
    refetchInterval: 15000, // Poll every 15s
  });

  if (isLoading) return <LoadingSpinner message="Loading dashboard..." />;
  if (error || !stats) return <EmptyState title="Could not load dashboard" description="Check backend connection" />;

  // Firmware distribution chart data
  const fwChartData = Object.entries(stats.firmware_distribution).map(([version, count]) => ({
    name: `v${version}`,
    value: count,
  }));

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Fleet Overview</h1>

      {/* Stats grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard title="Total Devices" value={stats.total_devices} icon={Cpu} color="blue" />
        <StatCard title="Online" value={stats.online_devices} icon={Wifi} color="emerald" />
        <StatCard title="Offline" value={stats.offline_devices} icon={WifiOff} color="gray" />
        <StatCard title="Need Attention" value={stats.devices_needing_attention} icon={AlertTriangle} color={stats.devices_needing_attention > 0 ? 'amber' : 'gray'} />
        <StatCard title="Firmware Releases" value={stats.total_firmware_releases} icon={Package} color="blue" />
        <StatCard title="Active Deployments" value={stats.active_deployments} icon={Rocket} color="amber" />
        <StatCard title="Success Rate" value={`${stats.deployment_success_rate}%`} icon={CheckCircle2} color="emerald" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Firmware Distribution */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-900 mb-4">Firmware Distribution</h2>
          {fwChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={fwChartData}
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  dataKey="value"
                  label={({ name, value }) => `${name} (${value})`}
                  labelLine={false}
                >
                  {fwChartData.map((_, i) => (
                    <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-[220px] text-gray-400 text-sm">
              No devices reporting firmware yet
            </div>
          )}
        </div>

        {/* Recent Deployments */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-900 mb-4">Recent Deployments</h2>
          {stats.recent_deployments.length > 0 ? (
            <div className="space-y-3">
              {stats.recent_deployments.map((d) => (
                <div key={d.id} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{d.name}</p>
                    <p className="text-xs text-gray-500">
                      {d.firmware_version && `v${d.firmware_version} · `}
                      {d.total_devices} devices · {timeAgo(d.created_at)}
                    </p>
                  </div>
                  <StatusBadge status={d.status} />
                </div>
              ))}
            </div>
          ) : (
            <div className="flex items-center justify-center h-[220px] text-gray-400 text-sm">
              No deployments yet
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
