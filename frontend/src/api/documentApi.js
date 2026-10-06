import axios from 'axios';
import { API_TIMEOUT_MS, apiErrorMessage, normalizeApiBaseUrl } from './apiConfig';

export const API_BASE_URL = normalizeApiBaseUrl(import.meta.env.VITE_API_BASE_URL);

// ── Base client ────────────────────────────────────────────────
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT_MS,
  headers: {
    Accept: 'application/json',
  },
});

// ── Request interceptor (logging / auth hooks) ─────────────────
api.interceptors.request.use(
  (config) => config,
  (error) => Promise.reject(error)
);

// ── Response interceptor ───────────────────────────────────────
api.interceptors.response.use(
  (response) => response,
  (error) => {
    return Promise.reject(new Error(apiErrorMessage(error)));
  }
);

// ── Document API calls ─────────────────────────────────────────

/**
 * Upload a PDF file.
 * @param {File} file
 * @param {function} onUploadProgress  - progress callback (0-100)
 * @returns {Promise<{task_id: number, status: string}>}
 */
export const uploadDocument = async (file, onUploadProgress, signal) => {
  const formData = new FormData();
  formData.append('file', file);

  const { data } = await api.post('/upload', formData, {
    signal,
    onUploadProgress: (event) => {
      if (onUploadProgress && event.total) {
        const percent = Math.round((event.loaded * 100) / event.total);
        onUploadProgress(percent);
      }
    },
  });

  return data;
};

/**
 * Poll for extraction result by task id.
 * @param {number|string} taskId
 * @returns {Promise<{id, filename, status, created_at, structured_data}>}
 */
export const getResult = async (taskId, signal) => {
  const { data } = await api.get(`/results/${taskId}`, { signal });
  return data;
};

/**
 * Fetch the list of all processed documents.
 * @returns {Promise<Array>}
 */
export const getDocuments = async () => {
  const { data } = await api.get('/documents');
  return data;
};

export default api;
