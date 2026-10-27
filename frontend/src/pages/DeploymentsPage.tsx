/**
 * Deployments page — create, start, cancel, and monitor deployments.
 */
import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Plus, Play, XCircle, Eye, X } from 'lucide-react';
import { deploymentsAPI, firmwareAPI, devicesAPI } from '../services/api';
import StatusBadge from '../components/StatusBadge';
import ConfirmDialog from '../components/ConfirmDialog';
import { LoadingSpinner, EmptyState } from '../components/States';
import { timeAgo, formatDate } from '../utils/format';
import type { Deployment, FirmwareRelease, Device } from '../types';

export default function DeploymentsPage() {
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [showDetail, setShowDetail] = useState<string | null>(null);
  const [cancelId, setCancelId] = useState<string | null>(null);
  const [createForm, setCreateForm] = useState({
    name: '', firmware_release_id: '', strategy: 'immediate',
    selected_devices: [] as string[], group_name: '',
  });

  const { data: deploymentsData, isLoading } = useQuery({
    queryKey: ['deployments'],
    queryFn: async () => {
      const { data } = await deploymentsAPI.list();
      return data.deployments as Deployment[];
    },
    refetchInterval: 5000,
  });

  const { data: firmwareList } = useQuery({
    queryKey: ['firmware-published'],
    queryFn: async () => {
      const { data } = await firmwareAPI.list({ status: 'published' });
      return data.releases as FirmwareRelease[];
    },
    enabled: showCreate,
  });

  const { data: devicesList } = useQuery({
    queryKey: ['devices-all'],
    queryFn: async () => {
      const { data } = await devicesAPI.list({ per_page: 100 });
      return data.devices as Device[];
    },
    enabled: showCreate,
  });

  const { data: attemptData } = useQuery({
    queryKey: ['deployment-attempts', showDetail],
    queryFn: async () => {
      if (!showDetail) return [];
      const { data } = await deploymentsAPI.devices(showDetail);
      return data.attempts;
    },
    enabled: !!showDetail,
    refetchInterval: 5000,
  });

  const createMutation = useMutation({
    mutationFn: async () => {
      const payload: Record<string, unknown> = {
        name: createForm.name,
        firmware_release_id: createForm.firmware_release_id,
        target_selection: createForm.selected_devices.length > 0
          ? { type: 'devices', device_ids: createForm.selected_devices }
          : createForm.group_name
            ? { type: 'group', group_name: createForm.group_name }
            : { type: 'all' },
        rollout_strategy: createForm.strategy === 'staged'
          ? {
            type: 'staged',
            stages: [
              { name: 'Canary', count: 1 },
              { name: '25%', percentage: 25 },
              { name: 'Remaining', percentage: 100 },
            ],
            max_failure_percentage: 20,
          }
          : { type: 'immediate', max_failure_percentage: 20 },
      };
      return deploymentsAPI.create(payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['deployments'] });
      setShowCreate(false);
      setCreateForm({ name: '', firmware_release_id: '', strategy: 'immediate', selected_devices: [], group_name: '' });
    },
  });

  const startMutation = useMutation({
    mutationFn: (id: string) => deploymentsAPI.start(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['deployments'] }),
  });

  const cancelMutation = useMutation({
    mutationFn: (id: string) => deploymentsAPI.cancel(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['deployments'] });
      setCancelId(null);
    },
  });

  const toggleDevice = (id: string) => {
    setCreateForm(prev => ({
      ...prev,
      selected_devices: prev.selected_devices.includes(id)
        ? prev.selected_devices.filter(d => d !== id)
        : [...prev.selected_devices, id],
    }));
  };

  const deployments = deploymentsData || [];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Deployments</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white text-sm font-medium rounded-lg hover:bg-primary-700 transition-colors"
        >
          <Plus className="w-4 h-4" /> New Deployment
        </button>
      </div>

      {isLoading ? (
        <LoadingSpinner />
      ) : deployments.length === 0 ? (
        <EmptyState
          title="No deployments yet"
          description="Create a deployment to push firmware to your devices"
        />
      ) : (
        <div className="space-y-3">
          {deployments.map((d) => (
            <div key={d.id} className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-sm transition-shadow">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-gray-900">{d.name}</h3>
                    <StatusBadge status={d.status} />
                  </div>
                  <p className="text-sm text-gray-500 mt-1">
                    {d.firmware_version && `v${d.firmware_version} · `}
                    {d.total_devices} devices · 
                    <span className="text-emerald-600"> {d.successful_devices} success</span>
                    {d.failed_devices > 0 && <span className="text-red-600"> · {d.failed_devices} failed</span>}
                  </p>
                  <p className="text-xs text-gray-400 mt-1">{formatDate(d.created_at)}</p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setShowDetail(d.id)}
                    className="p-2 text-gray-400 hover:text-primary-600 rounded-lg hover:bg-gray-50"
                    title="View details"
                  >
                    <Eye className="w-4 h-4" />
                  </button>
                  {d.status === 'created' && (
                    <button
                      onClick={() => startMutation.mutate(d.id)}
                      className="flex items-center gap-1 px-3 py-1.5 text-sm text-emerald-600 border border-emerald-200 rounded-lg hover:bg-emerald-50"
                    >
                      <Play className="w-3.5 h-3.5" /> Start
                    </button>
                  )}
                  {['created', 'in_progress', 'paused'].includes(d.status) && (
                    <button
                      onClick={() => setCancelId(d.id)}
                      className="flex items-center gap-1 px-3 py-1.5 text-sm text-red-600 border border-red-200 rounded-lg hover:bg-red-50"
                    >
                      <XCircle className="w-3.5 h-3.5" /> Cancel
                    </button>
                  )}
                  {d.status === 'paused' && (
                    <button
                      onClick={() => startMutation.mutate(d.id)}
                      className="flex items-center gap-1 px-3 py-1.5 text-sm text-amber-600 border border-amber-200 rounded-lg hover:bg-amber-50"
                    >
                      <Play className="w-3.5 h-3.5" /> Resume
                    </button>
                  )}
                </div>
              </div>

              {/* Progress bar */}
              {d.total_devices > 0 && (
                <div className="mt-3">
                  <div className="w-full bg-gray-100 rounded-full h-2">
                    <div
                      className="bg-emerald-500 h-2 rounded-full transition-all"
                      style={{ width: `${((d.successful_devices + d.failed_devices) / d.total_devices) * 100}%` }}
                    />
                  </div>
                  <p className="text-xs text-gray-400 mt-1">
                    {d.successful_devices + d.failed_devices} / {d.total_devices} completed
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Create Deployment Modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full mx-4 p-6 max-h-[90vh] overflow-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Create Deployment</h2>
              <button onClick={() => setShowCreate(false)} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={(e) => { e.preventDefault(); createMutation.mutate(); }} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Deployment Name</label>
                <input
                  value={createForm.name}
                  onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 outline-none"
                  placeholder="v2.0 rollout to lab sensors"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Firmware Release</label>
                <select
                  value={createForm.firmware_release_id}
                  onChange={(e) => setCreateForm({ ...createForm, firmware_release_id: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 outline-none bg-white"
                  required
                >
                  <option value="">Select firmware...</option>
                  {(firmwareList || []).map((fw) => (
                    <option key={fw.id} value={fw.id}>v{fw.version} — {fw.release_name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Rollout Strategy</label>
                <select
                  value={createForm.strategy}
                  onChange={(e) => setCreateForm({ ...createForm, strategy: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 outline-none bg-white"
                >
                  <option value="immediate">Immediate (all at once)</option>
                  <option value="staged">Staged (canary → 25% → all)</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Target Devices</label>
                <div className="border border-gray-200 rounded-lg max-h-48 overflow-auto">
                  {(devicesList || []).map((device) => (
                    <label key={device.id} className="flex items-center gap-3 px-3 py-2 hover:bg-gray-50 cursor-pointer border-b border-gray-50 last:border-0">
                      <input
                        type="checkbox"
                        checked={createForm.selected_devices.includes(device.id)}
                        onChange={() => toggleDevice(device.id)}
                        className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                      />
                      <div className="flex-1 min-w-0">
                        <span className="text-sm font-medium text-gray-900">{device.display_name}</span>
                        <span className="text-xs text-gray-500 ml-2">{device.firmware_version || 'unknown'}</span>
                      </div>
                      <StatusBadge status={device.status} />
                    </label>
                  ))}
                  {(!devicesList || devicesList.length === 0) && (
                    <p className="text-sm text-gray-400 p-3">No devices registered</p>
                  )}
                </div>
                <p className="text-xs text-gray-400 mt-1">
                  {createForm.selected_devices.length > 0
                    ? `${createForm.selected_devices.length} device(s) selected`
                    : 'No devices selected — will target all eligible devices'}
                </p>
              </div>

              {createMutation.isError && (
                <p className="text-sm text-red-600">
                  {(createMutation.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to create deployment'}
                </p>
              )}

              <button
                type="submit"
                disabled={createMutation.isPending || !createForm.firmware_release_id}
                className="w-full py-2.5 bg-primary-600 text-white text-sm font-medium rounded-lg hover:bg-primary-700 disabled:opacity-50"
              >
                {createMutation.isPending ? 'Creating...' : 'Create Deployment'}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Detail modal */}
      {showDetail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full mx-4 p-6 max-h-[85vh] overflow-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Deployment Details</h2>
              <button onClick={() => setShowDetail(null)} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            {attemptData && attemptData.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-100 bg-gray-50/50">
                      <th className="text-left px-3 py-2 font-medium text-gray-500">Device</th>
                      <th className="text-left px-3 py-2 font-medium text-gray-500">Status</th>
                      <th className="text-left px-3 py-2 font-medium text-gray-500">Stage</th>
                      <th className="text-left px-3 py-2 font-medium text-gray-500">Error</th>
                      <th className="text-left px-3 py-2 font-medium text-gray-500">Updated</th>
                    </tr>
                  </thead>
                  <tbody>
                    {attemptData.map((a: Record<string, unknown>) => (
                      <tr key={a.id as string} className="border-b border-gray-50">
                        <td className="px-3 py-2 font-medium text-gray-900">{(a.device_name as string) || (a.device_uid as string) || '—'}</td>
                        <td className="px-3 py-2"><StatusBadge status={a.status as string} /></td>
                        <td className="px-3 py-2 text-gray-600">{a.stage_number !== null ? `Stage ${a.stage_number}` : '—'}</td>
                        <td className="px-3 py-2 text-red-600 text-xs">{(a.error_message as string) || '—'}</td>
                        <td className="px-3 py-2 text-gray-400 text-xs">{a.updated_at ? timeAgo(a.updated_at as string) : '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-sm text-gray-400">No device attempts found</p>
            )}
          </div>
        </div>
      )}

      {/* Cancel confirmation */}
      <ConfirmDialog
        open={!!cancelId}
        title="Cancel Deployment"
        message="This will cancel all pending update commands. Devices already downloading or installing will not be affected."
        confirmLabel="Cancel Deployment"
        variant="danger"
        onConfirm={() => cancelId && cancelMutation.mutate(cancelId)}
        onCancel={() => setCancelId(null)}
      />
    </div>
  );
}
