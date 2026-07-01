import DocumentCard from './DocumentCard';
import LoadingSpinner from '../LoadingSpinner';

/**
 * DocumentList
 * Renders the list of documents with loading and empty states.
 *
 * Props:
 *  - documents : array
 *  - loading   : boolean
 *  - error     : string | null
 *  - onSelect  : (id: number) => void
 *  - onRefresh : () => void
 */
const DocumentList = ({ documents, loading, error, onSelect, onRefresh }) => {
  if (loading) {
    return <LoadingSpinner message="Loading documents…" dots />;
  }

  if (error) {
    return (
      <div className="empty-state">
        <div className="empty-state__icon">⚠</div>
        <p className="text-sm" style={{ color: 'var(--status-failed-fg)' }}>{error}</p>
        <button className="btn btn-ghost" onClick={onRefresh} style={{ marginTop: 8 }}>
          Retry
        </button>
      </div>
    );
  }

  if (!documents.length) {
    return (
      <div className="empty-state">
        <div className="empty-state__icon">📂</div>
        <p className="text-sm font-semibold text-primary">No documents yet</p>
        <p className="text-xs text-muted">Upload a PDF to get started</p>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {documents.map((doc, idx) => (
        <DocumentCard
          key={doc.id}
          doc={doc}
          onClick={() => onSelect(doc.id)}
          style={{ animationDelay: `${idx * 60}ms` }}
        />
      ))}
    </div>
  );
};

export default DocumentList;
