import { useState, useEffect, useCallback } from 'react';
import { getDocuments, getResult } from '../api/documentApi';

/**
 * useDocuments
 * Fetches the list of documents and provides a way to load a single document.
 *
 * Returns:
 *  - documents       : array of document summaries
 *  - loading         : boolean
 *  - error           : string | null
 *  - selectedDoc     : full document result object | null
 *  - loadingDoc      : boolean
 *  - fetchDocuments  : () => void  – manually refresh list
 *  - selectDocument  : (id) => void – load full document detail
 *  - clearSelection  : () => void
 */
export const useDocuments = () => {
  const [documents, setDocuments]   = useState([]);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState(null);

  const [selectedDoc, setSelectedDoc]   = useState(null);
  const [loadingDoc, setLoadingDoc]     = useState(false);
  const [docError, setDocError]         = useState(null);

  const fetchDocuments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getDocuments();
      setDocuments(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const selectDocument = useCallback(async (id) => {
    setLoadingDoc(true);
    setDocError(null);
    setSelectedDoc(null);
    try {
      const data = await getResult(id);
      setSelectedDoc(data);
    } catch (err) {
      setDocError(err.message);
    } finally {
      setLoadingDoc(false);
    }
  }, []);

  const clearSelection = useCallback(() => {
    setSelectedDoc(null);
    setDocError(null);
  }, []);

  // Initial load
  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  return {
    documents,
    loading,
    error,
    selectedDoc,
    loadingDoc,
    docError,
    fetchDocuments,
    selectDocument,
    clearSelection,
  };
};
