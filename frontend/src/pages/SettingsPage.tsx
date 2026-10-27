/**
 * Settings page — system info and configuration.
 */
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Shield, Server, Wifi, Database } from 'lucide-react';
import api from '../services/api';

export default function SettingsPage() {
  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      const { data } = await api.get('/health', { baseURL: import.meta.env.VITE_API_URL || '' });
      return data;
    },
    refetchInterval: 10000,
  });

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Settings</h1>

      {/* System Health */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
        <h2 className="text-sm font-semibold text-gray-900 mb-4">System Health</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
            <Server className="w-5 h-5 text-gray-500" />
            <div>
              <p className="text-sm font-medium text-gray-900">Backend</p>
              <p className={`text-xs ${health?.status === 'healthy' ? 'text-emerald-600' : 'text-red-600'}`}>
                {health?.status || 'Unknown'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
            <Wifi className="w-5 h-5 text-gray-500" />
            <div>
              <p className="text-sm font-medium text-gray-900">MQTT Broker</p>
              <p className={`text-xs ${health?.mqtt_connected ? 'text-emerald-600' : 'text-red-600'}`}>
                {health?.mqtt_connected ? 'Connected' : 'Disconnected'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
            <Database className="w-5 h-5 text-gray-500" />
            <div>
              <p className="text-sm font-medium text-gray-900">Database</p>
              <p className="text-xs text-emerald-600">
                {health ? 'Connected' : 'Unknown'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Configuration info */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
        <h2 className="text-sm font-semibold text-gray-900 mb-4">Configuration</h2>
        <div className="space-y-3 text-sm">
          <div className="flex justify-between py-2 border-b border-gray-50">
            <span className="text-gray-500">API Version</span>
            <span className="text-gray-900">{health?.version || '—'}</span>
          </div>
          <div className="flex justify-between py-2 border-b border-gray-50">
            <span className="text-gray-500">API Endpoint</span>
            <span className="text-gray-900 font-mono text-xs">{import.meta.env.VITE_API_URL || 'localhost:8000'}</span>
          </div>
        </div>
      </div>

      {/* Security note */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-5">
        <div className="flex items-start gap-3">
          <Shield className="w-5 h-5 text-blue-600 mt-0.5" />
          <div>
            <h3 className="text-sm font-semibold text-blue-900">Security Notes</h3>
            <ul className="mt-2 text-sm text-blue-800 space-y-1">
              <li>• JWT tokens expire after 60 minutes</li>
              <li>• Device API keys are hashed with bcrypt</li>
              <li>• Firmware integrity verified via SHA-256</li>
              <li>• MQTT broker requires password authentication</li>
              <li>• For production, enable TLS on MQTT and HTTPS</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
