/**
 * Device inventory page — list, search, filter, and manage devices.
 */
import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Search, Plus, X, Copy, Check } from 'lucide-react';
import { devicesAPI } from '../services/api';
import StatusBadge from '../components/StatusBadge';
import { LoadingSpinner, EmptyState } from '../components/States';
import { timeAgo, formatBytes, rssiToQuality } from '../utils/format';
import type { Device, DeviceListResponse } from '../types';

export default function DevicesPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [page, setPage] = useState(1);
  const [showRegister, setShowRegister] = useState(false);
  const [newDevice, setNewDevice] = useState({ device_uid: '', display_name: '', hardware_model: 'ESP32', group_name: '' });
  const [apiKeyResult, setApiKeyResult] = useState<{ api_key: string; device_uid: string } | null>(null);
  const [copied, setCopied] = useState(false);

  const { data, isLoading } = useQuery<DeviceListResponse>({
    queryKey: ['devices', page, search, statusFilter],
    queryFn: async () => {
      const params: Record<string, unknown> = { page, per_page: 20 };
      if (search) params.search = search;
      if (statusFilter) params.status = statusFilter;
      const { data } = await devicesAPI.list(params);
      return data;
    },
    refetchInterval: 10000,
  });

  const registerMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => devicesAPI.create(data),
    onSuccess: (res) => {
      setApiKeyResult({ api_key: res.data.api_key, device_uid: newDevice.device_uid });
      setNewDevice({ device_uid: '', display_name: '', hardware_model: 'ESP32', group_name: '' });
      queryClient.invalidateQueries({ queryKey: ['devices'] });
    },
  });

  const handleRegister = (e: React.FormEvent) => {
    e.preventDefault();
    registerMutation.mutate({
      device_uid: newDevice.device_uid,
      display_name: newDevice.display_name,
      hardware_model: newDevice.hardware_model,
      group_name: newDevice.group_name || undefined,
    });
  };

  const copyApiKey = () => {
    if (apiKeyResult) {
      navigator.clipboard.writeText(apiKeyResult.api_key);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const devices = data?.devices || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / 20);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Devices</h1>
        <button
          onClick={() => { setShowRegister(true); setApiKeyResult(null); }}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white text-sm font-medium rounded-lg hover:bg-primary-700 transition-colors"
        >
          <Plus className="w-4 h-4" /> Register Device
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-4">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search by ID or name..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 outline-none bg-white"
        >
          <option value="">All Status</option>
          <option value="online">Online</option>
          <option value="offline">Offline</option>
          <option value="updating">Updating</option>
        </select>
      </div>

      {/* Device table */}
      {isLoading ? (
        <LoadingSpinner />
      ) : devices.length === 0 ? (
        <EmptyState
          title="No devices registered"
          description="Register your first ESP32 device to get started"
          action={
            <button onClick={() => setShowRegister(true)} className="px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700">
              Register Device
            </button>
          }
        />
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50/50">
                  <th className="text-left px-4 py-3 font-medium text-gray-500">Device</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500">UID</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500">Firmware</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500">Status</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500">RSSI</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500">Last Seen</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500">Group</th>
                </tr>
              </thead>
              <tbody>
                {devices.map((device) => (
                  <tr key={device.id} className="border-b border-gray-50 hover:bg-gray-50/50 transition-colors">
                    <td className="px-4 py-3">
                      <Link to={`/devices/${device.id}`} className="font-medium text-primary-600 hover:text-primary-700">
                        {device.display_name}
                      </Link>
                      <div className="text-xs text-gray-400">{device.hardware_model}</div>
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-gray-600">{device.device_uid}</td>
                    <td className="px-4 py-3 text-gray-700">{device.firmware_version || '—'}</td>
                    <td className="px-4 py-3"><StatusBadge status={device.status} /></td>
                    <td className="px-4 py-3 text-gray-600">
                      {device.wifi_rssi !== null ? `${device.wifi_rssi} dBm` : '—'}
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs">{timeAgo(device.last_seen_at)}</td>
                    <td className="px-4 py-3 text-gray-500">{device.group_name || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100">
              <p className="text-xs text-gray-500">{total} device{total !== 1 ? 's' : ''}</p>
              <div className="flex gap-1">
                {Array.from({ length: totalPages }, (_, i) => (
                  <button
                    key={i}
                    onClick={() => setPage(i + 1)}
                    className={`px-3 py-1 text-xs rounded ${page === i + 1 ? 'bg-primary-600 text-white' : 'text-gray-600 hover:bg-gray-100'}`}
                  >
                    {i + 1}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Register Device Modal */}
      {showRegister && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full mx-4 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">
                {apiKeyResult ? 'Device Registered' : 'Register New Device'}
              </h2>
              <button onClick={() => { setShowRegister(false); setApiKeyResult(null); }} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            {apiKeyResult ? (
              <div>
                <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4 mb-4">
                  <p className="text-sm font-medium text-emerald-800 mb-2">Device registered successfully!</p>
                  <p className="text-xs text-emerald-700">Save this API key — it will not be shown again.</p>
                </div>
                <label className="block text-sm font-medium text-gray-700 mb-1">API Key</label>
                <div className="flex items-center gap-2">
                  <code className="flex-1 px-3 py-2 bg-gray-50 border rounded-lg text-xs font-mono break-all">{apiKeyResult.api_key}</code>
                  <button onClick={copyApiKey} className="p-2 text-gray-400 hover:text-primary-600">
                    {copied ? <Check className="w-4 h-4 text-emerald-500" /> : <Copy className="w-4 h-4" />}
                  </button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleRegister} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Device UID (MAC Address)</label>
                  <input
                    value={newDevice.device_uid}
                    onChange={(e) => setNewDevice({ ...newDevice, device_uid: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 outline-none"
                    placeholder="AABBCCDDEEFF"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Display Name</label>
                  <input
                    value={newDevice.display_name}
                    onChange={(e) => setNewDevice({ ...newDevice, display_name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 outline-none"
                    placeholder="Lab Sensor 1"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Group (optional)</label>
                  <input
                    value={newDevice.group_name}
                    onChange={(e) => setNewDevice({ ...newDevice, group_name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 outline-none"
                    placeholder="lab-sensors"
                  />
                </div>
                <button
                  type="submit"
                  disabled={registerMutation.isPending}
                  className="w-full py-2.5 bg-primary-600 text-white text-sm font-medium rounded-lg hover:bg-primary-700 disabled:opacity-50"
                >
                  {registerMutation.isPending ? 'Registering...' : 'Register Device'}
                </button>
                {registerMutation.isError && (
                  <p className="text-sm text-red-600">
                    {(registerMutation.error as Error)?.message || 'Registration failed'}
                  </p>
                )}
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
