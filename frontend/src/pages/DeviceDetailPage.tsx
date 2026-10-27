/**
 * Device detail page — device info, telemetry, events, and actions.
 */
import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Edit2, ShieldOff, Wifi, HardDrive, Clock, Activity } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { devicesAPI } from '../services/api';
import StatusBadge from '../components/StatusBadge';
import ConfirmDialog from '../components/ConfirmDialog';
import { LoadingSpinner } from '../components/States';
import { formatBytes, formatUptime, timeAgo, formatDate } from '../utils/format';
import type { Device, DeviceEvent, TelemetryPoint } from '../types';

export default function DeviceDetailPage() {
  const { deviceId } = useParams<{ deviceId: string }>();
  const queryClient = useQueryClient();
  const [showRevoke, setShowRevoke] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState('');

  const { data: device, isLoading } = useQuery<Device>({
    queryKey: ['device', deviceId],
    queryFn: async () => {
      const { data } = await devicesAPI.get(deviceId!);
      return data;
    },
    refetchInterval: 10000,
  });

  const { data: eventsData } = useQuery({
    queryKey: ['device-events', deviceId],
    queryFn: async () => {
      const { data } = await devicesAPI.events(deviceId!);
      return data.events as DeviceEvent[];
    },
  });

  const { data: telemetryData } = useQuery({
    queryKey: ['device-telemetry', deviceId],
    queryFn: async () => {
      const { data } = await devicesAPI.telemetry(deviceId!);
      return data.telemetry as TelemetryPoint[];
    },
  });

  const revokeMutation = useMutation({
    mutationFn: () => devicesAPI.revoke(deviceId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['device', deviceId] });
      setShowRevoke(false);
    },
  });

  const updateMutation = useMutation({
    mutationFn: (name: string) => devicesAPI.update(deviceId!, { display_name: name }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['device', deviceId] });
      setEditing(false);
    },
  });

  if (isLoading || !device) return <LoadingSpinner />;

  const telemetry = (telemetryData || []).reverse();
  const rssiData = telemetry.filter(t => t.wifi_rssi !== null).map(t => ({
    time: new Date(t.recorded_at).toLocaleTimeString(),
    rssi: t.wifi_rssi,
  }));
  const heapData = telemetry.filter(t => t.free_heap_bytes !== null).map(t => ({
    time: new Date(t.recorded_at).toLocaleTimeString(),
    heap: Math.round((t.free_heap_bytes || 0) / 1024),
  }));

  return (
    <div>
      <Link to="/devices" className="flex items-center gap-1 text-sm text-gray-500 hover:text-primary-600 mb-4">
        <ArrowLeft className="w-4 h-4" /> Back to Devices
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          {editing ? (
            <div className="flex items-center gap-2">
              <input
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                className="px-3 py-1.5 border rounded-lg text-lg font-bold focus:ring-2 focus:ring-primary-500 outline-none"
              />
              <button onClick={() => updateMutation.mutate(editName)} className="px-3 py-1.5 bg-primary-600 text-white text-sm rounded-lg">Save</button>
              <button onClick={() => setEditing(false)} className="px-3 py-1.5 text-sm text-gray-500">Cancel</button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-gray-900">{device.display_name}</h1>
              <button onClick={() => { setEditing(true); setEditName(device.display_name); }} className="text-gray-400 hover:text-primary-600">
                <Edit2 className="w-4 h-4" />
              </button>
            </div>
          )}
          <p className="text-sm text-gray-500 mt-1 font-mono">{device.device_uid} · {device.hardware_model}</p>
        </div>
        <div className="flex items-center gap-3">
          <StatusBadge status={device.status} size="md" />
          {!device.is_revoked && (
            <button
              onClick={() => setShowRevoke(true)}
              className="flex items-center gap-1 px-3 py-1.5 text-sm text-red-600 border border-red-200 rounded-lg hover:bg-red-50"
            >
              <ShieldOff className="w-3.5 h-3.5" /> Revoke
            </button>
          )}
        </div>
      </div>

      {/* Info cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <div className="flex items-center gap-2 text-gray-500 text-xs mb-1">
            <Activity className="w-3.5 h-3.5" /> Firmware
          </div>
          <p className="text-lg font-semibold text-gray-900">{device.firmware_version || 'Unknown'}</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <div className="flex items-center gap-2 text-gray-500 text-xs mb-1">
            <Wifi className="w-3.5 h-3.5" /> WiFi RSSI
          </div>
          <p className="text-lg font-semibold text-gray-900">{device.wifi_rssi !== null ? `${device.wifi_rssi} dBm` : '—'}</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <div className="flex items-center gap-2 text-gray-500 text-xs mb-1">
            <HardDrive className="w-3.5 h-3.5" /> Free Heap
          </div>
          <p className="text-lg font-semibold text-gray-900">{formatBytes(device.free_heap_bytes)}</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <div className="flex items-center gap-2 text-gray-500 text-xs mb-1">
            <Clock className="w-3.5 h-3.5" /> Uptime
          </div>
          <p className="text-lg font-semibold text-gray-900">{formatUptime(device.uptime_seconds)}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* RSSI Chart */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">WiFi Signal Strength</h3>
          {rssiData.length > 1 ? (
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={rssiData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="time" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} domain={[-100, -20]} />
                <Tooltip />
                <Line type="monotone" dataKey="rssi" stroke="#3b82f6" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[180px] flex items-center justify-center text-gray-400 text-sm">Not enough data</div>
          )}
        </div>

        {/* Heap Chart */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">Free Heap Memory (KB)</h3>
          {heapData.length > 1 ? (
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={heapData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="time" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip />
                <Line type="monotone" dataKey="heap" stroke="#10b981" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[180px] flex items-center justify-center text-gray-400 text-sm">Not enough data</div>
          )}
        </div>
      </div>

      {/* Device info */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Device Information</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
          <div><span className="text-gray-500">IP Address:</span> <span className="ml-2 text-gray-900">{device.last_ip_address || '—'}</span></div>
          <div><span className="text-gray-500">Last Seen:</span> <span className="ml-2 text-gray-900">{formatDate(device.last_seen_at)}</span></div>
          <div><span className="text-gray-500">Registered:</span> <span className="ml-2 text-gray-900">{formatDate(device.registered_at)}</span></div>
          <div><span className="text-gray-500">Group:</span> <span className="ml-2 text-gray-900">{device.group_name || '—'}</span></div>
          <div><span className="text-gray-500">Revoked:</span> <span className="ml-2 text-gray-900">{device.is_revoked ? 'Yes' : 'No'}</span></div>
        </div>
      </div>

      {/* Events */}
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Recent Events</h3>
        {eventsData && eventsData.length > 0 ? (
          <div className="space-y-2">
            {eventsData.slice(0, 20).map((event: DeviceEvent) => (
              <div key={event.id} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                <div className="flex items-center gap-3">
                  <StatusBadge status={event.event_type} />
                  <span className="text-sm text-gray-700">{event.description || event.event_type}</span>
                </div>
                <span className="text-xs text-gray-400">{timeAgo(event.created_at)}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-400">No events recorded</p>
        )}
      </div>

      {/* Revoke dialog */}
      <ConfirmDialog
        open={showRevoke}
        title="Revoke Device Credentials"
        message="This will permanently revoke this device's API key. The device will no longer be able to check in or receive updates. This action cannot be undone."
        confirmLabel="Revoke"
        onConfirm={() => revokeMutation.mutate()}
        onCancel={() => setShowRevoke(false)}
        variant="danger"
      />
    </div>
  );
}
