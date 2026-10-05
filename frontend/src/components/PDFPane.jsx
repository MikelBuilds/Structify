import { useState } from 'react';

import { API_BASE_URL } from '../api/documentApi';

/**
 * PDFPane
 * Embeds the original PDF via iframe.
 * Falls back to a Download/Open link if the iframe fails to load.
 *
 * Props:
 *  - documentId : number | string
 *  - filename   : string
 */
const PDFPane = ({ documentId, filename }) => {
  const [loadFailed, setLoadFailed] = useState(false);
  const pdfUrl = `${API_BASE_URL}/pdf/${documentId}`;

  if (loadFailed) {
    return (
      <div className="pdf-pane pdf-pane--fallback">
        <div className="pdf-pane__fallback-icon">📄</div>
        <p className="pdf-pane__fallback-title">PDF Preview Unavailable</p>
        <p className="pdf-pane__fallback-subtitle">
          The file may have been moved or the server is unavailable.
        </p>
        <a
          href={pdfUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="btn btn-primary"
          style={{ marginTop: 16, fontSize: '0.8125rem', padding: '10px 20px' }}
        >
          Open PDF ↗
        </a>
      </div>
    );
  }

  return (
    <div className="pdf-pane">
      <div className="pdf-pane__header">
        <span className="pdf-pane__label">📄 {filename}</span>
        <a
          href={pdfUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="json-viewer__copy-btn"
          title="Open in new tab"
        >
          ↗ Open
        </a>
      </div>
      <iframe
        className="pdf-pane__frame"
        src={pdfUrl}
        title={`PDF Preview — ${filename}`}
        onError={() => setLoadFailed(true)}
        // Some browsers don't fire onError for iframes; we rely on the
        // backend 404 response which still loads the fallback via the UI below.
      />
    </div>
  );
};

export default PDFPane;
