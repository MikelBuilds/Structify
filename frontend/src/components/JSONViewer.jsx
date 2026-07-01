import { useState } from 'react';

// ── Helpers ────────────────────────────────────────────────────

const getType = (value) => {
  if (value === null) return 'null';
  if (Array.isArray(value)) return 'array';
  return typeof value;
};

const getValueClass = (type) => {
  switch (type) {
    case 'string':  return 'json-entry__value--string';
    case 'number':  return 'json-entry__value--number';
    case 'boolean': return 'json-entry__value--boolean';
    case 'null':    return 'json-entry__value--null';
    default:        return '';
  }
};

const formatScalar = (value, type) => {
  if (type === 'null')    return 'null';
  if (type === 'string')  return `"${value}"`;
  return String(value);
};

// ── Recursive JSON Entry ───────────────────────────────────────

const JSONEntry = ({ keyName, value, depth = 0 }) => {
  const [open, setOpen] = useState(depth < 2);
  const type = getType(value);
  const isComplex = type === 'object' || type === 'array';

  const entries = isComplex
    ? (type === 'array' ? value.map((v, i) => [String(i), v]) : Object.entries(value ?? {}))
    : [];

  return (
    <div className="json-entry" style={{ marginLeft: depth > 0 ? 12 : 0 }}>
      <div
        className="json-entry__header"
        onClick={() => isComplex && setOpen((o) => !o)}
        style={{ cursor: isComplex ? 'pointer' : 'default' }}
      >
        <span className="json-entry__key">{keyName}</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="json-entry__type">
            {type === 'array' ? `array[${value.length}]` : type}
          </span>
          {isComplex && (
            <span className={`json-entry__expand-icon ${open ? 'open' : ''}`}>▶</span>
          )}
        </div>
      </div>

      {!isComplex && (
        <div className={`json-entry__value-inline ${getValueClass(type)}`}>
          {formatScalar(value, type)}
        </div>
      )}

      {isComplex && open && (
        <div className="json-entry__nested">
          {entries.length === 0 ? (
            <span className="text-xs text-muted">(empty)</span>
          ) : (
            entries.map(([k, v]) => (
              <JSONEntry key={k} keyName={k} value={v} depth={depth + 1} />
            ))
          )}
        </div>
      )}
    </div>
  );
};

// ── JSONViewer ─────────────────────────────────────────────────

/**
 * JSONViewer
 * Renders structured JSON as expandable key-value cards instead of raw text.
 *
 * Props:
 *  - data  : any JSON-compatible value
 *  - title : optional header label
 */
const JSONViewer = ({ data, title = 'Extracted Data' }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(data, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (_) { /* ignore */ }
  };

  if (!data) {
    return (
      <div className="json-viewer">
        <div className="json-viewer__header">
          <span className="json-viewer__title">🗂 {title}</span>
        </div>
        <div className="json-viewer__body">
          <span className="text-sm text-muted">No data available.</span>
        </div>
      </div>
    );
  }

  const entries =
    typeof data === 'object' && !Array.isArray(data)
      ? Object.entries(data)
      : [['root', data]];

  return (
    <div className="json-viewer animate-scale-in">
      <div className="json-viewer__header">
        <span className="json-viewer__title">🗂 {title}</span>
        <button className="json-viewer__copy-btn" onClick={handleCopy}>
          {copied ? '✓ Copied' : '⎘ Copy JSON'}
        </button>
      </div>
      <div className="json-viewer__body">
        {entries.map(([key, val]) => (
          <JSONEntry key={key} keyName={key} value={val} depth={0} />
        ))}
      </div>
    </div>
  );
};

export default JSONViewer;
