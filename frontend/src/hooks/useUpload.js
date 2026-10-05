import { useState, useRef, useCallback } from 'react';
import { uploadDocument, getResult } from '../api/documentApi';

const POLL_INTERVAL_MS = 2000;

/**
 * useUpload
 * Handles the full upload + polling lifecycle.
 *
 * Returns:
 *  - uploadState  : 'idle' | 'uploading' | 'processing' | 'completed' | 'failed'
 *  - uploadProgress: 0-100 (HTTP upload percent)
 *  - result       : the final document result object
 *  - error        : string | null
 *  - handleUpload : (file: File) => void  – kick off upload
 *  - reset        : () => void
 */
export const useUpload = () => {
  const [uploadState, setUploadState]     = useState('idle');
  const [uploadProgress, setUploadProgress] = useState(0);
  const [result, setResult]               = useState(null);
  const [error, setError]                 = useState(null);

  const pollRef = useRef(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const startPolling = useCallback(
    (taskId) => {
      pollRef.current = setInterval(async () => {
        try {
          const data = await getResult(taskId);

          if (data.status === 'completed') {
            stopPolling();
            setResult(data);
            setUploadState('completed');
          } else if (data.status === 'failed') {
            stopPolling();
            setError(data.error_message || 'Extraction failed. Please try again.');
            setUploadState('failed');
          }
          // else still processing – keep polling
        } catch (err) {
          stopPolling();
          setError(err.message);
          setUploadState('failed');
        }
      }, POLL_INTERVAL_MS);
    },
    [stopPolling]
  );

  const handleUpload = useCallback(
    async (file) => {
      if (!file) return;

      // Reset state
      setError(null);
      setResult(null);
      setUploadProgress(0);
      setUploadState('uploading');

      try {
        const { task_id } = await uploadDocument(file, (pct) => {
          setUploadProgress(pct);
        });

        setUploadState('processing');
        startPolling(task_id);
      } catch (err) {
        setError(err.message);
        setUploadState('failed');
      }
    },
    [startPolling]
  );

  const reset = useCallback(() => {
    stopPolling();
    setUploadState('idle');
    setUploadProgress(0);
    setResult(null);
    setError(null);
  }, [stopPolling]);

  return { uploadState, uploadProgress, result, error, handleUpload, reset };
};
