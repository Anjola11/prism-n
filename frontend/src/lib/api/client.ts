import axios from 'axios';

function resolveApiBaseUrl(): string {
  if (import.meta.env.DEV) {
    return '/api/v1';
  }

  const envBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim();
  if (envBaseUrl) {
    const cleanUrl = envBaseUrl.replace(/\/+$/, '');
    if (!cleanUrl.endsWith('/api/v1')) {
      return `${cleanUrl}/api/v1`;
    }
    return cleanUrl;
  }

  return '/api/v1';
}

export const api = axios.create({
  baseURL: resolveApiBaseUrl(),
  withCredentials: true,
  timeout: 20000,
  headers: {
    'Content-Type': 'application/json',
  },
});

let refreshTokenPromise: Promise<void> | null = null;

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error?.config;

    if (!error?.response || error.response.status !== 401 || !originalRequest) {
      return Promise.reject(error);
    }

    const isAuthEndpoint =
      typeof originalRequest.url === 'string' &&
      (originalRequest.url.includes('/auth/') || originalRequest.url.includes('/admin/login'));

    if (originalRequest._retry || isAuthEndpoint) {
      if (!isAuthEndpoint && typeof window !== 'undefined' && !window.location.pathname.startsWith('/auth')) {
        window.location.href = '/auth/login';
      }
      return Promise.reject(error);
    }

    originalRequest._retry = true;

    if (!refreshTokenPromise) {
      refreshTokenPromise = api
        .post('/auth/renew-access-token')
        .then(() => {
          refreshTokenPromise = null;
        })
        .catch((refreshError) => {
          refreshTokenPromise = null;
          if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/auth')) {
            window.location.href = '/auth/login';
          }
          return Promise.reject(refreshError);
        });
    }

    try {
      await refreshTokenPromise;
      return api(originalRequest);
    } catch (refreshErr) {
      return Promise.reject(refreshErr);
    }
  },
);
