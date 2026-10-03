import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';

// Development talks to the backend on :8000. A production build is served by the backend itself (as when
// PowerPilot runs from Power BI Desktop's External Tools ribbon, on a port chosen at launch), so it must use
// its own origin. An explicitly empty VITE_API_BASE_URL also means same-origin.
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? (import.meta.env.DEV ? 'http://localhost:8000' : '');

export const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 60000, // 60s timeout for deep intelligence pipeline execution
  headers: {
    'Accept': 'application/json',
  },
});

apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Inject auth token or custom request headers here when auth is active
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ detail?: string }>) => {
    const message = error.response?.data?.detail || error.message || 'An unexpected API error occurred.';
    // Keep the HTTP status and axios's error code: callers sometimes need to tell a missing session (401)
    // from a server error, or a server that is not there (ERR_NETWORK) from a request that merely timed out.
    return Promise.reject(
      Object.assign(new Error(message), { status: error.response?.status, code: error.code })
    );
  }
);
