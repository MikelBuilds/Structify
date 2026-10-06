export const API_TIMEOUT_MS = 120000;

export function normalizeApiBaseUrl(value) {
  return (value?.trim() || '/api').replace(/\/+$/, '');
}

export function apiErrorMessage(error) {
  if (error.code === 'ECONNABORTED' || error.code === 'ETIMEDOUT') {
    return 'The backend took too long to respond. It may be waking up. Wait a moment and try again; check History before uploading the same PDF again.';
  }
  if (!error.response && error.code !== 'ERR_CANCELED') {
    return 'Cannot reach the backend. Check your connection and try again shortly. If this continues, check the API URL and allowed frontend origin.';
  }
  const detail = error.response?.data?.detail || error.response?.data?.message;
  return typeof detail === 'string' ? detail : error.message || 'An unexpected error occurred';
}
