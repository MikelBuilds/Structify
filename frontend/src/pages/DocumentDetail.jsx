import { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useDocuments } from '../hooks/useDocuments';
import StatusBadge    from '../components/StatusBadge';
import JSONViewer     from '../components/JSONViewer';
import LoadingSpinner from '../components/LoadingSpinner';
import PDFPane        from '../components/PDFPane';

/**
 * DocumentDetail page
 * Route: /documents/:id
 *
 * Layout (completed documents):
 *  Desktop  → 40% PDF | 60% data
 *  Tablet   → 50% / 50%
 *  Mobile   → stacked vertically
 */
const DocumentDetail = () => {
  const { id }   = useParams();
  const navigate = useNavigate();

  const { selectedDoc, loadingDoc, docError, selectDocument } = useDocuments();

  useEffect(() => {
    if (id) selectDocument(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const handleBack = () => navigate(-1);

  // ── Loading ────────────────────────────────────────────────
  if (loadingDoc) {
    return (
      <main className="page-content">
        <LoadingSpinner message="Loading document…" size="lg" />
      </main>
    );
  }

  // ── Error ──────────────────────────────────────────────────
  if (docError || (!loadingDoc && !selectedDoc)) {
    return (
      <main className="page-content">
        <button className="back-btn" onClick={handleBack}>← Back</button>
        <div className="empty-state">
          <div className="empty-state__icon">⚠</div>
          <p className="text-sm" style={{ color: 'var(--status-failed-fg)' }}>
            {docError ?? 'Document not found.'}
          </p>
          <button className="btn btn-ghost" onClick={handleBack} style={{ marginTop: 8 }}>
            Go Back
          </button>
        </div>
      </main>
    );
  }

  const doc = selectedDoc;
  const date = doc.created_at
    ? new Date(doc.created_at).toLocaleString('en-IN', {
        weekday: 'short',
        year:    'numeric',
        month:   'long',
        day:     'numeric',
        hour:    '2-digit',
        minute:  '2-digit',
      })
    : '—';

  const fieldCount = doc.structured_data
    ? Object.keys(doc.structured_data).length
    : 0;

  return (
    <main className="page-content">
      {/* Back */}
      <button className="back-btn" onClick={handleBack}>
        ← Back to Documents
      </button>

      {/* Hero Card — always full width */}
      <div className="detail-hero animate-slide-up">
        <div className="detail-hero__top">
          <div className="detail-hero__title-group">
            <div className="detail-hero__file-icon">📄</div>
            <div>
              <h1 className="detail-hero__filename">{doc.filename}</h1>
              <span className="detail-hero__id">Document ID: #{doc.id}</span>
            </div>
          </div>
          <StatusBadge status={doc.status} />
        </div>

        <div className="detail-meta-grid">
          <div className="detail-meta-item">
            <span className="detail-meta-item__label">Created</span>
            <span className="detail-meta-item__value">{date}</span>
          </div>
          <div className="detail-meta-item">
            <span className="detail-meta-item__label">Status</span>
            <span className="detail-meta-item__value" style={{ textTransform: 'capitalize' }}>
              {doc.status}
            </span>
          </div>
          <div className="detail-meta-item">
            <span className="detail-meta-item__label">Fields Extracted</span>
            <span className="detail-meta-item__value">{fieldCount}</span>
          </div>
          <div className="detail-meta-item">
            <span className="detail-meta-item__label">File Name</span>
            <span
              className="detail-meta-item__value"
              style={{ fontSize: '0.8rem', fontFamily: 'var(--font-mono)', wordBreak: 'break-all' }}
            >
              {doc.filename}
            </span>
          </div>
        </div>
      </div>

      {/* Two-column layout for completed documents */}
      {doc.status === 'completed' && (
        <div className="detail-split animate-slide-up" style={{ animationDelay: '80ms' }}>
          {/* LEFT — PDF Preview */}
          <div className="detail-split__pdf">
            <div className="section-header" style={{ marginBottom: 12 }}>
              <h2 className="section-title">PDF Preview</h2>
            </div>
            <PDFPane documentId={doc.id} filename={doc.filename} />
          </div>

          {/* RIGHT — Extracted Data */}
          <div className="detail-split__data">
            <div className="section-header" style={{ marginBottom: 12 }}>
              <h2 className="section-title">Extracted Data</h2>
              <span className="text-xs text-muted">
                {fieldCount} field{fieldCount !== 1 ? 's' : ''}
              </span>
            </div>
            <JSONViewer
              data={doc.structured_data}
              title="Structured Output"
              documentId={doc.id}
            />
          </div>
        </div>
      )}

      {doc.status === 'processing' && (
        <div className="card" style={{ textAlign: 'center', padding: 48 }}>
          <LoadingSpinner dots message="AI is still processing this document…" />
        </div>
      )}

      {doc.status === 'failed' && (
        <div className="card" style={{ textAlign: 'center', padding: 48 }}>
          <p className="text-sm" style={{ color: 'var(--status-failed-fg)' }}>
            {doc.error_message || 'Extraction failed for this document.'}
          </p>
        </div>
      )}
    </main>
  );
};

export default DocumentDetail;
