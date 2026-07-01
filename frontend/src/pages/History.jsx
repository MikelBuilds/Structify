import { useNavigate } from 'react-router-dom';
import { useDocuments } from '../hooks/useDocuments';
import DocumentList     from '../components/documents/DocumentList';

/**
 * History page
 * Route: /history
 * Shows full list of all processed documents.
 */
const History = () => {
  const navigate = useNavigate();

  const {
    documents,
    loading,
    error,
    fetchDocuments,
  } = useDocuments();

  const handleSelect = (id) => {
    navigate(`/documents/${id}`);
  };

  const completed  = documents.filter((d) => d.status === 'completed').length;
  const processing = documents.filter((d) => d.status === 'processing').length;
  const failed     = documents.filter((d) => d.status === 'failed').length;

  return (
    <main className="page-content">
      {/* Header */}
      <div className="section-header" style={{ marginBottom: 24 }}>
        <div>
          <h1 className="section-title" style={{ fontSize: '1.5rem' }}>Document History</h1>
          <p className="section-subtitle">
            {documents.length} total · {completed} completed · {processing} processing · {failed} failed
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

      {/* Filter chips (visual only, can be wired up later) */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
        {['All', 'Completed', 'Processing', 'Failed'].map((label) => (
          <span
            key={label}
            style={{
              padding: '4px 12px',
              borderRadius: 'var(--radius-full)',
              fontSize: '0.75rem',
              fontWeight: 600,
              background: label === 'All' ? 'rgba(99,102,241,0.15)' : 'var(--bg-glass)',
              border: `1px solid ${label === 'All' ? 'rgba(99,102,241,0.4)' : 'var(--border-subtle)'}`,
              color: label === 'All' ? 'var(--accent-hover)' : 'var(--text-secondary)',
              cursor: 'pointer',
            }}
          >
            {label}
          </span>
        ))}
      </div>

      <DocumentList
        documents={documents}
        loading={loading}
        error={error}
        onSelect={handleSelect}
        onRefresh={fetchDocuments}
      />
    </main>
  );
};

export default History;
