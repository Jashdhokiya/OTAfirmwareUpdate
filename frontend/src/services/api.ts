/**
 * API client — centralized HTTP layer for all backend calls.
 */
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || '';

const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
});

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 — redirect to login
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && window.location.pathname !== '/login') {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;

// ─── Auth ───
export const authAPI = {
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),
  refresh: (refresh_token: string) =>
    api.post('/auth/refresh', { refresh_token }),
  me: () => api.get('/auth/me'),
};

// ─── Devices ───
export const devicesAPI = {
  list: (params?: Record<string, unknown>) =>
    api.get('/devices', { params }),
  get: (id: string) => api.get(`/devices/${id}`),
  create: (data: Record<string, unknown>) =>
    api.post('/devices', data),
  update: (id: string, data: Record<string, unknown>) =>
    api.patch(`/devices/${id}`, data),
  revoke: (id: string) => api.post(`/devices/${id}/revoke`),
  events: (id: string, limit = 50) =>
    api.get(`/devices/${id}/events`, { params: { limit } }),
  telemetry: (id: string, limit = 100) =>
    api.get(`/devices/${id}/telemetry`, { params: { limit } }),
};

// ─── Firmware ───
export const firmwareAPI = {
  list: (params?: Record<string, unknown>) =>
    api.get('/firmware', { params }),
  get: (id: string) => api.get(`/firmware/${id}`),
  upload: (formData: FormData) =>
    api.post('/firmware', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  publish: (id: string) => api.post(`/firmware/${id}/publish`),
  deprecate: (id: string) => api.post(`/firmware/${id}/deprecate`),
};

// ─── Deployments ───
export const deploymentsAPI = {
  list: (params?: Record<string, unknown>) =>
    api.get('/deployments', { params }),
  get: (id: string) => api.get(`/deployments/${id}`),
  create: (data: Record<string, unknown>) =>
    api.post('/deployments', data),
  start: (id: string) => api.post(`/deployments/${id}/start`),
  cancel: (id: string) => api.post(`/deployments/${id}/cancel`),
  devices: (id: string) => api.get(`/deployments/${id}/devices`),
  stats: () => api.get('/deployments/stats'),
};
