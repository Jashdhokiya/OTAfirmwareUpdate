/**
 * Utility functions for formatting values in the dashboard.
 */

/** Format bytes to human-readable string */
export function formatBytes(bytes: number | null): string {
  if (bytes === null || bytes === undefined) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

/** Format seconds to human-readable uptime */
export function formatUptime(seconds: number | null): string {
  if (seconds === null || seconds === undefined) return '—';
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (d > 0) return `${d}d ${h}h ${m}m`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

/** Format ISO date string to relative time */
export function timeAgo(dateStr: string | null): string {
  if (!dateStr) return 'Never';
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  if (diffSec < 60) return 'Just now';
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  return `${diffDay}d ago`;
}

/** Format ISO date to readable format */
export function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleString();
}

/** Get status color classes */
export function getStatusColor(status: string): string {
  switch (status) {
    case 'online': return 'bg-emerald-100 text-emerald-700';
    case 'offline': return 'bg-gray-100 text-gray-600';
    case 'updating': return 'bg-amber-100 text-amber-700';
    case 'success': case 'completed': return 'bg-emerald-100 text-emerald-700';
    case 'failed': case 'error': return 'bg-red-100 text-red-700';
    case 'pending': case 'created': return 'bg-blue-100 text-blue-700';
    case 'in_progress': case 'downloading': case 'installing': return 'bg-amber-100 text-amber-700';
    case 'paused': return 'bg-orange-100 text-orange-700';
    case 'cancelled': case 'timeout': return 'bg-gray-100 text-gray-600';
    case 'draft': return 'bg-gray-100 text-gray-600';
    case 'published': return 'bg-emerald-100 text-emerald-700';
    case 'deprecated': return 'bg-red-100 text-red-600';
    case 'command_sent': return 'bg-indigo-100 text-indigo-700';
    default: return 'bg-gray-100 text-gray-600';
  }
}

/** RSSI to signal quality description */
export function rssiToQuality(rssi: number | null): string {
  if (rssi === null) return '—';
  if (rssi >= -50) return 'Excellent';
  if (rssi >= -60) return 'Good';
  if (rssi >= -70) return 'Fair';
  return 'Weak';
}
