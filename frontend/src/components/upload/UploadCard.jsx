import { useRef, useState, useCallback } from 'react';
import LoadingSpinner from '../LoadingSpinner';

// ── Stage tracker ──────────────────────────────────────────────
const STAGES = [
  { key: 'uploading',   label: 'Uploading',   icon: '↑' },
  { key: 'processing',  label: 'Processing',  icon: '⚙' },
  { key: 'completed',   label: 'Complete',    icon: '✓' },
];

const stageIndex = { uploading: 0, processing: 1, completed: 2, failed: 2 };

const ProgressStages = ({ uploadState }) => {
  const current = stageIndex[uploadState] ?? 0;

  return (
    <div className="upload-progress__stages">
      {STAGES.map((stage, idx) => {
        const isDone   = idx < current || (uploadState === 'completed' && idx === 2);
        const isActive = idx === current && uploadState !== 'completed';
        const isFailed = uploadState === 'failed' && idx === 2;

        return (
          <div
            key={stage.key}
            className={`stage ${isDone ? 'done' : ''} ${isActive ? 'active' : ''}`}
          >
            <div className="stage__dot">
              {isDone && !isFailed && '✓'}
              {isFailed && '✕'}
              {isActive && <LoadingSpinner size="sm" />}
              {!isDone && !isActive && !isFailed && idx + 1}
            </div>
            <span className="stage__label">{stage.label}</span>
          </div>
        );
      })}
    </div>
  );
};

const progressPercent = { idle: 0, uploading: 33, processing: 66, completed: 100, failed: 100 };

// ── UploadCard ─────────────────────────────────────────────────

/**
 * UploadCard
 * Drag & drop / browse upload zone with live progress UI.
 *
 * Props:
 *  - onUpload       : (file: File) => void
 *  - uploadState    : 'idle' | 'uploading' | 'processing' | 'completed' | 'failed'
 *  - uploadProgress : 0-100 (HTTP progress percent)
 *  - result         : completed result object | null
 *  - error          : error string | null
 *  - onReset        : () => void
 *  - onViewResult   : (id) => void
 */
const UploadCard = ({
  onUpload,
  uploadState,
  uploadProgress,
  result,
  error,
  onReset,
  onViewResult,
}) => {
  const inputRef  = useRef(null);
  const [dragging, setDragging] = useState(false);

  // ── Drag handlers ────────────────────────────────────────────
  const handleDragOver  = useCallback((e) => { e.preventDefault(); setDragging(true); },  []);
  const handleDragLeave = useCallback((e) => { e.preventDefault(); setDragging(false); }, []);
  const handleDrop      = useCallback(
    (e) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files?.[0];
      if (file && file.type === 'application/pdf') onUpload(file);
    },
    [onUpload]
  );

  const handleFileChange = useCallback(
    (e) => {
      const file = e.target.files?.[0];
      if (file) onUpload(file);
    },
    [onUpload]
  );

  const isActive = uploadState !== 'idle';
  const barWidth =
    uploadState === 'uploading'
      ? `${uploadProgress}%`
      : `${progressPercent[uploadState] ?? 0}%`;

  return (
    <div className="upload-card">
      <div className="section-header" style={{ marginBottom: 20 }}>
        <div>
          <h2 className="section-title">Upload Document</h2>
          <p className="section-subtitle">
            Extract structured data from any PDF using AI
          </p>
        </div>
        {isActive && uploadState !== 'completed' && (
          <button className="btn btn-ghost" onClick={onReset} style={{ fontSize: '0.8rem' }}>
            Cancel
          </button>
        )}
      </div>

      {/* Drop Zone */}
      {!isActive && (
        <div
          className={`upload-zone ${dragging ? 'dragging' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          role="button"
          tabIndex={0}
          aria-label="Upload PDF"
          onKeyDown={(e) => e.key === 'Enter' && inputRef.current?.click()}
        >
          <input
            ref={inputRef}
            type="file"
            accept="application/pdf"
            onChange={handleFileChange}
            id="file-input"
          />
          <div className="upload-zone__icon">📄</div>
          <div>
            <p className="upload-zone__title">
              Drop your PDF here, or{' '}
              <span className="upload-zone__browse">browse</span>
            </p>
            <p className="upload-zone__subtitle" style={{ marginTop: 4 }}>
              Drag & drop to upload instantly
            </p>
          </div>
          <div className="upload-zone__meta">
            <span>📎 PDF only</span>
            <span>•</span>
            <span>Max 50 MB</span>
          </div>
        </div>
      )}

      {/* Progress UI */}
      {isActive && (
        <div className="upload-progress">
          <div className="upload-progress__header">
            <span className="upload-progress__filename">
              📄{' '}
              {uploadState === 'completed'
                ? result?.filename ?? 'File'
                : 'Processing…'}
            </span>
            {uploadState === 'uploading' && (
              <span className="text-sm text-muted">{uploadProgress}%</span>
            )}
          </div>

          <ProgressStages uploadState={uploadState} />

          <div className="upload-progress__bar-wrap">
            <div
              className="upload-progress__bar"
              style={{
                width: barWidth,
                background:
                  uploadState === 'failed'
                    ? 'linear-gradient(90deg,#ef4444,#f87171)'
                    : undefined,
              }}
            />
          </div>

          {/* Status messages */}
          <div style={{ marginTop: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            {uploadState === 'uploading' && (
              <p className="text-sm text-muted">Uploading file to server…</p>
            )}
            {uploadState === 'processing' && (
              <p className="text-sm text-muted animate-pulse">
                AI is extracting structured data — this may take a moment…
              </p>
            )}
            {uploadState === 'completed' && (
              <p className="text-sm" style={{ color: 'var(--status-completed-fg)' }}>
                ✓ Extraction complete!
              </p>
            )}
            {uploadState === 'failed' && (
              <p className="text-sm" style={{ color: 'var(--status-failed-fg)' }}>
                {error ?? 'Something went wrong. Please try again.'}
              </p>
            )}

            <div style={{ display: 'flex', gap: 8 }}>
              {uploadState === 'completed' && result && (
                <button
                  className="btn btn-primary"
                  onClick={() => onViewResult(result.id)}
                  style={{ padding: '8px 16px', fontSize: '0.8125rem' }}
                >
                  View Results →
                </button>
              )}
              {(uploadState === 'completed' || uploadState === 'failed') && (
                <button
                  className="btn btn-ghost"
                  onClick={onReset}
                  style={{ padding: '8px 16px', fontSize: '0.8125rem' }}
                >
                  Upload Another
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UploadCard;
