import { api } from './client';
import { DEFAULT_CURRENCY } from '../constants';
import type { ApiResponse, DiscoveryEventApi, EventDetailApi, PaginatedResponse, ScoreHistoryApi } from './types';

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

export const marketsApi = {
  getEventsPage: async (
    page = 1,
    limit = 20,
    currency = DEFAULT_CURRENCY,
    source?: string,
    category?: string,
    sortBy?: string,
  ): Promise<PaginatedResponse<DiscoveryEventApi>> => {
    const response = await api.get('/events', {
      params: { currency, source, category, sort_by: sortBy, page, limit },
      timeout: 45000,
    });
    return normalizePaginated(unwrap(response), page, limit);
  },
  getEvents: async (currency = DEFAULT_CURRENCY, source?: string, category?: string, sortBy?: string): Promise<DiscoveryEventApi[]> => {
    const paged = await marketsApi.getEventsPage(1, 100, currency, source, category, sortBy);
    return paged.items;
  },
  getEvent: async (eventId: string, currency = DEFAULT_CURRENCY, source?: string): Promise<EventDetailApi> => {
    const response = await api.get(`/events/${eventId}`, { params: { currency, source } });
    return unwrap(response);
  },
  getScoreHistory: async (
    eventId: string,
    marketId?: string,
    hours = 48,
    currency = DEFAULT_CURRENCY,
    source?: string,
  ): Promise<ScoreHistoryApi> => {
    const response = await api.get(`/events/${eventId}/score-history`, {
      params: { market_id: marketId, hours, currency, source },
      timeout: 45000,
    });
    return unwrap(response);
  },
  trackEvent: async (eventId: string, currency = DEFAULT_CURRENCY, source?: string): Promise<any> => {
    const response = await api.post(`/track/${eventId}`, null, { params: { currency, source } });
    return unwrap(response);
  },
  untrackEvent: async (eventId: string, currency = DEFAULT_CURRENCY, source?: string): Promise<any> => {
    const response = await api.delete(`/track/${eventId}`, { params: { currency, source } });
    return unwrap(response);
  },
  getTrackerPage: async (
    page = 1,
    limit = 20,
    currency = DEFAULT_CURRENCY,
  ): Promise<PaginatedResponse<DiscoveryEventApi>> => {
    const response = await api.get('/tracker', {
      params: { currency, page, limit },
      timeout: 45000,
    });
    return normalizePaginated(unwrap(response), page, limit);
  },
  getTracker: async (currency = DEFAULT_CURRENCY): Promise<DiscoveryEventApi[]> => {
    const paged = await marketsApi.getTrackerPage(1, 100, currency);
    return paged.items;
  },
};
