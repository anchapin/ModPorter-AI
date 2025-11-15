import { useCallback } from 'react';
import axios from 'axios';

// Configure axios defaults
const api = axios.create({
  baseURL: process.env.NODE_ENV === 'production' 
    ? '/api/v1' 
    : 'http://localhost:8000/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized - redirect to login or clear token
      localStorage.removeItem('authToken');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export interface UseApiReturn {
  get: <T>(url: string, config?: any) => Promise<T>;
  post: <T>(url: string, data?: any, config?: any) => Promise<T>;
  put: <T>(url: string, data?: any, config?: any) => Promise<T>;
  delete: <T>(url: string, config?: any) => Promise<T>;
  patch: <T>(url: string, data?: any, config?: any) => Promise<T>;
}

export const useApi = (): UseApiReturn => {
  const get = useCallback((url: string, config?: any) => {
    return api.get(url, config).then(response => response.data);
  }, []);

  const post = useCallback((url: string, data?: any, config?: any) => {
    return api.post(url, data, config).then(response => response.data);
  }, []);

  const put = useCallback((url: string, data?: any, config?: any) => {
    return api.put(url, data, config).then(response => response.data);
  }, []);

  const remove = useCallback((url: string, config?: any) => {
    return api.delete(url, config).then(response => response.data);
  }, []);

  const patch = useCallback((url: string, data?: any, config?: any) => {
    return api.patch(url, data, config).then(response => response.data);
  }, []);

  return {
    get,
    post,
    put,
    delete: remove,
    patch,
  };
};

export default api;
