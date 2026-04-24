import { api } from './client';
import { DEFAULT_CURRENCY } from '../constants';
import type { ApiResponse, DiscoveryEventApi, EventDetailApi } from './types';

const unwrap = <T>(response: { data: ApiResponse<T> }): T => response.data.data;

export const marketsApi = {
  getEvents: async (currency = DEFAULT_CURRENCY, source?: string): Promise<DiscoveryEventApi[]> => {
    const response = await api.get('/events', { params: { currency, source } });
    return unwrap(response) || [];
  },
  getEvent: async (eventId: string, currency = DEFAULT_CURRENCY, source?: string): Promise<EventDetailApi> => {
    const response = await api.get(`/events/${eventId}`, { params: { currency, source } });
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
  getTracker: async (currency = DEFAULT_CURRENCY): Promise<DiscoveryEventApi[]> => {
    const response = await api.get('/tracker', {
      params: { currency },
      timeout: 45000,
    });
    return unwrap(response) || [];
  },
};
