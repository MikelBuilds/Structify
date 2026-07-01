import { useState, useMemo } from 'react';
import { useNavigate }  from 'react-router-dom';
import { useDocuments } from '../hooks/useDocuments';
import DocumentList     from '../components/documents/DocumentList';
import SearchBar        from '../components/SearchBar';
import FilterChips      from '../components/FilterChips';

/**
 * History page
 * Route: /history
 * Full document list with live search + functional filter chips.
 */
const History = () => {
  const navigate = useNavigate();

  const [searchQuery, setSearchQuery]   = useState('');
  const [activeFilter, setActiveFilter] = useState('all');

  const {
    documents,
    loading,
    error,
    fetchDocuments,
  } = useDocuments();

  const total      = documents.length;
  const completed  = documents.filter((d) => d.status === 'completed').length;
  const processing = documents.filter((d) => d.status === 'processing').length;
  const failed     = documents.filter((d) => d.status === 'failed').length;

  const counts = { all: total, completed, processing, failed };

  const filteredDocs = useMemo(() => {
    const q = searchQuery.toLowerCase().trim();

    return documents.filter((doc) => {
      if (activeFilter !== 'all' && doc.status !== activeFilter) return false;
      if (q) {
        return (
          doc.filename?.toLowerCase().includes(q) ||
          doc.status?.toLowerCase().includes(q) ||
          String(doc.id).includes(q)
        );
      }
      return true;
    });
  }, [documents, searchQuery, activeFilter]);

  return (
    <main className="page-content">
      {/* Header */}
      <div className="section-header" style={{ marginBottom: 24 }}>
        <div>
          <h1 className="section-title" style={{ fontSize: '1.5rem' }}>Document History</h1>
          <p className="section-subtitle">
            {filteredDocs.length} of {total} total · {completed} completed ·{' '}
            {processing} processing · {failed} failed
          </p>
        </div>
        <button
          className="btn btn-ghost"
          onClick={fetchDocuments}
          style={{ fontSize: '0.8125rem', padding: '8px 14px' }}
        >
          ↺ Refresh
        </button>
      </div>

      {/* Search Bar */}
      <div style={{ marginBottom: 12 }}>
        <SearchBar
          value={searchQuery}
          onChange={setSearchQuery}
          placeholder="Search by filename, status, ID…"
        />
      </div>

      {/* Filter Chips */}
      <div style={{ marginBottom: 20 }}>
        <FilterChips
          active={activeFilter}
          onChange={setActiveFilter}
          counts={counts}
        />
      </div>

      <DocumentList
        documents={filteredDocs}
        loading={loading}
        error={error}
        onSelect={(id) => navigate(`/documents/${id}`)}
        onRefresh={fetchDocuments}
      />
    </main>
  );
};

export default History;
