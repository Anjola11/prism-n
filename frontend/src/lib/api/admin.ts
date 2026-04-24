import { api } from './client';
import { DEFAULT_CURRENCY } from '../constants';
import type {
  AdminActionLogApi,
  AdminAnalyticsApi,
  AdminOverviewApi,
  AdminSystemStatusApi,
  ApiResponse,
  AuthUserApi,
  DiscoveryEventApi,
} from './types';

const unwrap = <T>(response: { data: ApiResponse<T> }): T => response.data.data;

export const adminApi = {
  login: async (email: string, password: string): Promise<AuthUserApi> => {
    const response = await api.post('/admin/login', { email, password });
    return unwrap(response);
  },
  getMe: async (): Promise<AuthUserApi> => {
    const response = await api.get('/admin/me');
    return unwrap(response);
  },
  getOverview: async (currency = DEFAULT_CURRENCY): Promise<AdminOverviewApi> => {
    const response = await api.get('/admin/overview', {
      params: { currency },
      timeout: 60000,
    });
    return unwrap(response);
  },
  getAnalytics: async (): Promise<AdminAnalyticsApi> => {
    const response = await api.get('/admin/analytics', {
      timeout: 15000,
    });
    return unwrap(response);
  },
  getSystemStatus: async (): Promise<AdminSystemStatusApi> => {
    const response = await api.get('/admin/system-status', {
      timeout: 10000,
    });
    return unwrap(response);
  },
  getDiscovery: async (currency = DEFAULT_CURRENCY, source?: string): Promise<DiscoveryEventApi[]> => {
    const response = await api.get('/admin/discovery', { params: { currency, source } });
    return unwrap(response) || [];
  },
  getSystemTracker: async (currency = DEFAULT_CURRENCY): Promise<DiscoveryEventApi[]> => {
    const response = await api.get('/admin/system-tracker', {
      params: { currency },
      timeout: 60000,
    });
    return unwrap(response) || [];
  },
  systemTrack: async (eventId: string, currency = DEFAULT_CURRENCY, source?: string): Promise<any> => {
    const response = await api.post(`/admin/system-track/${eventId}`, null, { params: { currency, source } });
    return unwrap(response);
  },
  systemUntrack: async (eventId: string, currency = DEFAULT_CURRENCY, source?: string): Promise<any> => {
    const response = await api.delete(`/admin/system-track/${eventId}`, { params: { currency, source } });
    return unwrap(response);
  },
  getAuditLogs: async (limit = 20): Promise<AdminActionLogApi[]> => {
    const response = await api.get('/admin/audit-logs', {
      params: { limit },
      timeout: 10000,
    });
    return unwrap(response) || [];
  },
};
