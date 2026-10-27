/**
 * Shared TypeScript types for the fleet manager frontend.
 */

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
}

export interface Device {
  id: string;
  device_uid: string;
  display_name: string;
  hardware_model: string;
  firmware_version: string | null;
  desired_firmware_version: string | null;
  status: 'online' | 'offline' | 'updating';
  last_seen_at: string | null;
  last_ip_address: string | null;
  wifi_rssi: number | null;
  uptime_seconds: number | null;
  free_heap_bytes: number | null;
  tags: Record<string, string>;
  group_name: string | null;
  is_revoked: boolean;
  registered_at: string;
}

export interface DeviceListResponse {
  devices: Device[];
  total: number;
  page: number;
  per_page: number;
}

export interface FirmwareRelease {
  id: string;
  version: string;
  release_name: string;
  description: string | null;
  hardware_model: string;
  file_size: number;
  sha256_hash: string;
  min_compatible_version: string | null;
  status: 'draft' | 'published' | 'deprecated';
  created_at: string;
  published_at: string | null;
}

export interface Deployment {
  id: string;
  name: string;
  firmware_release_id: string;
  target_selection: Record<string, unknown>;
  rollout_strategy: Record<string, unknown>;
  status: 'created' | 'in_progress' | 'paused' | 'completed' | 'cancelled' | 'failed';
  current_stage: number | null;
  total_devices: number;
  successful_devices: number;
  failed_devices: number;
  created_by: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  firmware_version?: string;
  firmware_release_name?: string;
}

export interface DeploymentAttempt {
  id: string;
  deployment_id: string;
  device_id: string;
  status: string;
  attempt_number: number;
  stage_number: number | null;
  command_id: string | null;
  error_code: string | null;
  error_message: string | null;
  started_at: string | null;
  updated_at: string | null;
  completed_at: string | null;
  device_name?: string;
  device_uid?: string;
}

export interface DashboardStats {
  total_devices: number;
  online_devices: number;
  offline_devices: number;
  devices_needing_attention: number;
  total_firmware_releases: number;
  active_deployments: number;
  deployment_success_rate: number;
  recent_deployments: Deployment[];
  firmware_distribution: Record<string, number>;
}

export interface DeviceEvent {
  id: string;
  event_type: string;
  description: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface TelemetryPoint {
  id: string;
  uptime_seconds: number | null;
  free_heap_bytes: number | null;
  wifi_rssi: number | null;
  temperature: number | null;
  firmware_version: string | null;
  recorded_at: string;
}
