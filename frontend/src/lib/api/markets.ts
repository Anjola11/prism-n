import { api } from './client';
import type { DiscoveryEventApi } from './types';

export const marketsApi = {
  getEvents: async (): Promise<DiscoveryEventApi[]> => {
    const response = await api.get('/events');
    return response.data?.data || [];
  },
  getEvent: async (eventId: string): Promise<any> => {
    const response = await api.get(`/events/${eventId}`);
    return response.data?.data;
  },
  trackEvent: async (eventId: string): Promise<any> => {
    const response = await api.post(`/track/${eventId}`);
    return response.data?.data;
  },
  untrackEvent: async (eventId: string): Promise<any> => {
    const response = await api.delete(`/track/${eventId}`);
    return response.data?.data;
  },
  getTracker: async (): Promise<DiscoveryEventApi[]> => {
    const response = await api.get('/tracker');
    return response.data?.data || [];
  }
};
