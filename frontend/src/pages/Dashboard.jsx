import { useState, useMemo } from 'react';
import { useNavigate }  from 'react-router-dom';
import { useUpload }    from '../hooks/useUpload';
import { useDocuments } from '../hooks/useDocuments';
import UploadCard       from '../components/upload/UploadCard';
import DocumentList     from '../components/documents/DocumentList';
import SearchBar        from '../components/SearchBar';
import FilterChips      from '../components/FilterChips';

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

  const [searchQuery, setSearchQuery] = useState('');
  const [activeFilter, setActiveFilter] = useState('all');

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
  } = useDocuments();

  // After a successful upload, refresh the list and navigate to detail
  const handleViewResult = async (id) => {
    await fetchDocuments();
    navigate(`/documents/${id}`);
  };

  // Stats
  const total      = documents.length;
  const completed  = documents.filter((d) => d.status === 'completed').length;
  const processing = documents.filter((d) => d.status === 'processing').length;
  const failed     = documents.filter((d) => d.status === 'failed').length;

  const counts = { all: total, completed, processing, failed };

  // Filtered + searched list (shown max 8 on dashboard)
  const filteredDocs = useMemo(() => {
    const q = searchQuery.toLowerCase().trim();

    return documents
      .filter((doc) => {
        // Filter by status
        if (activeFilter !== 'all' && doc.status !== activeFilter) return false;
        // Filter by search query
        if (q) {
          return (
            doc.filename?.toLowerCase().includes(q) ||
            doc.status?.toLowerCase().includes(q) ||
            String(doc.id).includes(q)
          );
        }
        return true;
      })
      .slice(0, 8);
  }, [documents, searchQuery, activeFilter]);

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
              {filteredDocs.length} of {total} document{total !== 1 ? 's' : ''}
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
        <div style={{ marginBottom: 16 }}>
          <FilterChips
            active={activeFilter}
            onChange={setActiveFilter}
            counts={counts}
          />
        </div>

        <DocumentList
          documents={filteredDocs}
          loading={loading}
          error={listError}
          onSelect={(id) => navigate(`/documents/${id}`)}
          onRefresh={fetchDocuments}
        />
      </div>
    </main>
  );
};

export default Dashboard;
