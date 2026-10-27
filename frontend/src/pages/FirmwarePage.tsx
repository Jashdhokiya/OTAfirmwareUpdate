/**
 * Firmware releases page — upload, publish, deprecate firmware.
 */
import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Upload, Package, CheckCircle, XCircle, X } from 'lucide-react';
import { firmwareAPI } from '../services/api';
import StatusBadge from '../components/StatusBadge';
import ConfirmDialog from '../components/ConfirmDialog';
import { LoadingSpinner, EmptyState } from '../components/States';
import { formatBytes, formatDate } from '../utils/format';
import type { FirmwareRelease } from '../types';

export default function FirmwarePage() {
  const queryClient = useQueryClient();
  const [showUpload, setShowUpload] = useState(false);
  const [uploadForm, setUploadForm] = useState({
    version: '', release_name: '', description: '', hardware_model: 'ESP32', min_compatible_version: '',
  });
  const [file, setFile] = useState<File | null>(null);
  const [publishId, setPublishId] = useState<string | null>(null);
  const [deprecateId, setDeprecateId] = useState<string | null>(null);

  const { data: releasesData, isLoading } = useQuery({
    queryKey: ['firmware'],
    queryFn: async () => {
      const { data } = await firmwareAPI.list();
      return data.releases as FirmwareRelease[];
    },
  });

  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error('No file selected');
      const formData = new FormData();
      formData.append('file', file);
      formData.append('version', uploadForm.version);
      formData.append('release_name', uploadForm.release_name);
      formData.append('description', uploadForm.description);
      formData.append('hardware_model', uploadForm.hardware_model);
      if (uploadForm.min_compatible_version) {
        formData.append('min_compatible_version', uploadForm.min_compatible_version);
      }
      return firmwareAPI.upload(formData);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['firmware'] });
      setShowUpload(false);
      setFile(null);
      setUploadForm({ version: '', release_name: '', description: '', hardware_model: 'ESP32', min_compatible_version: '' });
    },
  });

  const publishMutation = useMutation({
    mutationFn: (id: string) => firmwareAPI.publish(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['firmware'] });
      setPublishId(null);
    },
  });

  const deprecateMutation = useMutation({
    mutationFn: (id: string) => firmwareAPI.deprecate(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['firmware'] });
      setDeprecateId(null);
    },
  });

  const releases = releasesData || [];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Firmware Releases</h1>
        <button
          onClick={() => setShowUpload(true)}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white text-sm font-medium rounded-lg hover:bg-primary-700 transition-colors"
        >
          <Upload className="w-4 h-4" /> Upload Firmware
        </button>
      </div>

      {isLoading ? (
        <LoadingSpinner />
      ) : releases.length === 0 ? (
        <EmptyState
          title="No firmware releases"
          description="Upload your first firmware binary to get started"
          action={
            <button onClick={() => setShowUpload(true)} className="px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700">
              Upload Firmware
            </button>
          }
        />
      ) : (
        <div className="space-y-3">
          {releases.map((release) => (
            <div key={release.id} className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-sm transition-shadow">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-blue-50 rounded-lg">
                    <Package className="w-5 h-5 text-blue-600" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-gray-900">{release.release_name}</h3>
                      <StatusBadge status={release.status} />
                    </div>
                    <p className="text-sm text-gray-500 mt-0.5">
                      v{release.version} · {release.hardware_model} · {formatBytes(release.file_size)}
                    </p>
                    {release.description && (
                      <p className="text-sm text-gray-500 mt-1">{release.description}</p>
                    )}
                    <p className="text-xs text-gray-400 mt-1">
                      Created {formatDate(release.created_at)}
                      {release.published_at && ` · Published ${formatDate(release.published_at)}`}
                    </p>
                    <p className="text-xs text-gray-400 font-mono mt-1">SHA256: {release.sha256_hash.slice(0, 16)}...</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {release.status === 'draft' && (
                    <button
                      onClick={() => setPublishId(release.id)}
                      className="flex items-center gap-1 px-3 py-1.5 text-sm text-emerald-600 border border-emerald-200 rounded-lg hover:bg-emerald-50"
                    >
                      <CheckCircle className="w-3.5 h-3.5" /> Publish
                    </button>
                  )}
                  {release.status === 'published' && (
                    <button
                      onClick={() => setDeprecateId(release.id)}
                      className="flex items-center gap-1 px-3 py-1.5 text-sm text-red-600 border border-red-200 rounded-lg hover:bg-red-50"
                    >
                      <XCircle className="w-3.5 h-3.5" /> Deprecate
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Upload Modal */}
      {showUpload && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full mx-4 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Upload Firmware</h2>
              <button onClick={() => setShowUpload(false)} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={(e) => { e.preventDefault(); uploadMutation.mutate(); }} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Firmware File (.bin)</label>
                <input
                  type="file"
                  accept=".bin"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  className="w-full text-sm border border-gray-300 rounded-lg p-2 file:mr-3 file:px-3 file:py-1 file:rounded file:border-0 file:bg-primary-50 file:text-primary-700 file:text-sm file:font-medium"
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Version</label>
                  <input
                    value={uploadForm.version}
                    onChange={(e) => setUploadForm({ ...uploadForm, version: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 outline-none"
                    placeholder="1.0.0"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Release Name</label>
                  <input
                    value={uploadForm.release_name}
                    onChange={(e) => setUploadForm({ ...uploadForm, release_name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 outline-none"
                    placeholder="Initial Release"
                    required
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <textarea
                  value={uploadForm.description}
                  onChange={(e) => setUploadForm({ ...uploadForm, description: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 outline-none"
                  rows={2}
                  placeholder="What changed in this release..."
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Min Compatible Version (optional)</label>
                <input
                  value={uploadForm.min_compatible_version}
                  onChange={(e) => setUploadForm({ ...uploadForm, min_compatible_version: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 outline-none"
                  placeholder="0.9.0"
                />
              </div>
              {uploadMutation.isError && (
                <p className="text-sm text-red-600">
                  {(uploadMutation.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Upload failed'}
                </p>
              )}
              <button
                type="submit"
                disabled={uploadMutation.isPending || !file}
                className="w-full py-2.5 bg-primary-600 text-white text-sm font-medium rounded-lg hover:bg-primary-700 disabled:opacity-50"
              >
                {uploadMutation.isPending ? 'Uploading...' : 'Upload Firmware'}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Publish confirmation */}
      <ConfirmDialog
        open={!!publishId}
        title="Publish Firmware Release"
        message="Publishing makes this firmware available for deployment to devices. Ensure the binary has been tested."
        confirmLabel="Publish"
        variant="warning"
        onConfirm={() => publishId && publishMutation.mutate(publishId)}
        onCancel={() => setPublishId(null)}
      />

      {/* Deprecate confirmation */}
      <ConfirmDialog
        open={!!deprecateId}
        title="Deprecate Firmware Release"
        message="Deprecating prevents this firmware from being used in new deployments. Existing deployments will not be affected."
        confirmLabel="Deprecate"
        variant="danger"
        onConfirm={() => deprecateId && deprecateMutation.mutate(deprecateId)}
        onCancel={() => setDeprecateId(null)}
      />
    </div>
  );
}
