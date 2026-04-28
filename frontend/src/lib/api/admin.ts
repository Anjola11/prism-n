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
  PaginatedResponse,
  ScoreHistoryApi,
} from './types';

const unwrap = <T>(response: { data: ApiResponse<T> }): T => response.data.data;

const normalizePaginated = <T>(
  data: T[] | PaginatedResponse<T> | null | undefined,
  page: number,
  limit: number,
): PaginatedResponse<T> => {
  if (Array.isArray(data)) {
    return {
      items: data,
      pagination: {
        page,
        limit,
        total: data.length,
        has_more: false,
      },
    };
  }

  if (data && Array.isArray((data as PaginatedResponse<T>).items) && (data as PaginatedResponse<T>).pagination) {
    return data as PaginatedResponse<T>;
  }

  return {
    items: [],
    pagination: {
      page,
      limit,
      total: 0,
      has_more: false,
    },
  };
};

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
  getDiscoveryPage: async (
    page = 1,
    limit = 20,
    currency = DEFAULT_CURRENCY,
    source?: string,
    category?: string,
    sortBy?: string,
  ): Promise<PaginatedResponse<DiscoveryEventApi>> => {
    const response = await api.get('/admin/discovery', {
      params: { currency, source, category, sort_by: sortBy, page, limit },
      timeout: 45000,
    });
    return normalizePaginated(unwrap(response), page, limit);
  },
  getDiscovery: async (currency = DEFAULT_CURRENCY, source?: string, category?: string, sortBy?: string): Promise<DiscoveryEventApi[]> => {
    const paged = await adminApi.getDiscoveryPage(1, 100, currency, source, category, sortBy);
    return paged.items;
  },
  getSystemTrackerPage: async (
    page = 1,
    limit = 20,
    currency = DEFAULT_CURRENCY,
  ): Promise<PaginatedResponse<DiscoveryEventApi>> => {
    const response = await api.get('/admin/system-tracker', {
      params: { currency, page, limit },
      timeout: 60000,
    });
    return normalizePaginated(unwrap(response), page, limit);
  },
  getSystemTracker: async (currency = DEFAULT_CURRENCY): Promise<DiscoveryEventApi[]> => {
    const paged = await adminApi.getSystemTrackerPage(1, 100, currency);
    return paged.items;
  },
  getScoreHistory: async (
    eventId: string,
    marketId?: string,
    hours = 48,
    currency = DEFAULT_CURRENCY,
    source?: string,
  ): Promise<ScoreHistoryApi> => {
    const response = await api.get(`/admin/events/${eventId}/score-history`, {
      params: { market_id: marketId, hours, currency, source },
      timeout: 45000,
    });
    return unwrap(response);
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
