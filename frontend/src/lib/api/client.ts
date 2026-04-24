import axios from 'axios';

const LOCAL_API_BASE_URL = '/api/v1';
const LIVE_API_BASE_URL = 'https://prism-60b21aab4083.herokuapp.com/api/v1';

function isLocalFrontendHost(hostname: string): boolean {
  return hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '::1';
}

function resolveApiBaseUrl(): string {
  const envBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim();
  if (envBaseUrl) {
    return envBaseUrl;
  }

  if (typeof window !== 'undefined' && isLocalFrontendHost(window.location.hostname)) {
    return LOCAL_API_BASE_URL;
  }

  return LIVE_API_BASE_URL;
}

export const api = axios.create({
  baseURL: resolveApiBaseUrl(),
  withCredentials: true,
  timeout: 20000,
  headers: {
    'Content-Type': 'application/json',
  },
});
