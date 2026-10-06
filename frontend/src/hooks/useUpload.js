import { useState, useRef, useCallback, useEffect } from 'react';
import { uploadDocument, getResult } from '../api/documentApi';

import { startResultPolling } from '../utils/resultPolling';

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
  const uploadRef = useRef(null);

  const stopPolling = useCallback(() => {
    pollRef.current?.();
    pollRef.current = null;
  }, []);

  useEffect(() => () => {
    stopPolling();
    uploadRef.current?.abort();
  }, [stopPolling]);

  const handleUpload = useCallback(async (file) => {
    if (!file) return;
    stopPolling();
    uploadRef.current?.abort();
    const controller = new AbortController();
    uploadRef.current = controller;
    setError(null);
    setResult(null);
    setUploadProgress(0);
    setUploadState('uploading');
    try {
      const { task_id } = await uploadDocument(file, (pct) => {
        if (!controller.signal.aborted) setUploadProgress(pct);
      }, controller.signal);
      if (controller.signal.aborted) return;
      setUploadState('processing');
      pollRef.current = startResultPolling(
        signal => getResult(task_id, signal),
        data => {
          if (data.status === 'completed') {
            setResult(data);
            setUploadState('completed');
            return false;
          }
          if (data.status === 'failed') {
            setError(data.error_message || 'Extraction failed. Please try again.');
            setUploadState('failed');
            return false;
          }
          return true;
        },
        err => {
          setError(err.message);
          setUploadState('failed');
        },
      );
    } catch (err) {
      if (controller.signal.aborted) return;
      setError(err.message);
      setUploadState('failed');
    }
  }, [stopPolling]);

  const reset = useCallback(() => {
    stopPolling();
    uploadRef.current?.abort();
    setUploadState('idle');
    setUploadProgress(0);
    setResult(null);
    setError(null);
  }, [stopPolling]);

  return { uploadState, uploadProgress, result, error, handleUpload, reset };
};
