import { useNavigate } from 'react-router-dom';
import { useUpload }     from '../hooks/useUpload';
import { useDocuments }  from '../hooks/useDocuments';
import UploadCard        from '../components/upload/UploadCard';
import DocumentList      from '../components/documents/DocumentList';

// ── Stat Card helper ───────────────────────────────────────────
const StatCard = ({ icon, value, label }) => (
  <div className="stat-card">
    <span className="stat-card__icon">{icon}</span>
    <div className="stat-card__value">{value}</div>
    <div className="stat-card__label">{label}</div>
  </div>
);

// ── Dashboard ─────────────────────────────────────────────────

const Dashboard = () => {
  const navigate = useNavigate();

  const {
    uploadState,
    uploadProgress,
    result,
    error,
    handleUpload,
    reset,
  } = useUpload();

  const {
    documents,
    loading,
    error: listError,
    fetchDocuments,
    selectDocument,
  } = useDocuments();

  // After a successful upload, refresh the list and navigate to detail
  const handleViewResult = async (id) => {
    await fetchDocuments();
    navigate(`/documents/${id}`);
  };

  // Clicking a document in the list navigates to its detail page
  const handleSelectDocument = (id) => {
    navigate(`/documents/${id}`);
  };

  // Stats derived from documents list
  const total      = documents.length;
  const completed  = documents.filter((d) => d.status === 'completed').length;
  const processing = documents.filter((d) => d.status === 'processing').length;

  return (
    <main className="page-content">
      {/* Stats Row */}
      <div className="stats-grid">
        <StatCard icon="📁" value={total}      label="Total Documents" />
        <StatCard icon="✓"  value={completed}  label="Completed" />
        <StatCard icon="⚙"  value={processing} label="Processing" />
      </div>

      {/* Upload Card */}
      <div style={{ marginBottom: 32 }}>
        <UploadCard
          onUpload={handleUpload}
          uploadState={uploadState}
          uploadProgress={uploadProgress}
          result={result}
          error={error}
          onReset={reset}
          onViewResult={handleViewResult}
        />
      </div>

      {/* Recent Documents */}
      <div>
        <div className="section-header">
          <div>
            <h2 className="section-title">Recent Documents</h2>
            <p className="section-subtitle">
              {total} document{total !== 1 ? 's' : ''} processed
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

        <DocumentList
          documents={documents.slice(0, 8)}
          loading={loading}
          error={listError}
          onSelect={handleSelectDocument}
          onRefresh={fetchDocuments}
        />
      </div>
    </main>
  );
};

export default Dashboard;
