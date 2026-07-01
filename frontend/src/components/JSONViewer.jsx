import { useState } from 'react';
import { formatKey, formatValue, isCurrencyKey, isDateString } from '../utils/formatters';

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

// ── Recursive JSON Entry ───────────────────────────────────────

const JSONEntry = ({ keyName, value, depth = 0 }) => {
  const [open, setOpen] = useState(depth < 2);
  const rawType = getType(value);
  const isComplex = rawType === 'object' || rawType === 'array';

  // Apply formatting for scalar null values
  const displayValue = formatValue(value, keyName);
  const isNullValue  = value === null || value === undefined;

  const entries = isComplex
    ? (rawType === 'array'
        ? value.map((v, i) => [String(i), v])
        : Object.entries(value ?? {}))
    : [];

  // Determine display type label
  const typeLabel = rawType === 'array'
    ? `array[${value.length}]`
    : isNullValue
    ? 'null'
    : rawType;

  // Scalar value class — null gets its own class
  const valueClass = isNullValue
    ? 'json-entry__value--null'
    : isCurrencyKey(keyName) && typeof value === 'number'
    ? 'json-entry__value--number'
    : isDateString(value)
    ? 'json-entry__value--string'
    : getValueClass(rawType);

  return (
    <div className="json-entry" style={{ marginLeft: depth > 0 ? 12 : 0 }}>
      <div
        className="json-entry__header"
        onClick={() => isComplex && setOpen((o) => !o)}
        style={{ cursor: isComplex ? 'pointer' : 'default' }}
      >
        <span className="json-entry__key">{formatKey(keyName)}</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="json-entry__type">{typeLabel}</span>
          {isComplex && (
            <span className={`json-entry__expand-icon ${open ? 'open' : ''}`}>▶</span>
          )}
        </div>
      </div>

      {!isComplex && (
        <div className={`json-entry__value-inline ${valueClass}`}>
          {isNullValue
            ? 'Not Available'
            : typeof displayValue === 'boolean'
            ? (displayValue ? 'Yes' : 'No')
            : String(displayValue)}
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
 * Renders structured JSON as expandable key-value cards.
 *
 * Props:
 *  - data          : any JSON-compatible value
 *  - title         : optional header label
 *  - documentId    : optional — enables Download JSON button
 */
const JSONViewer = ({ data, title = 'Extracted Data', documentId }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(data, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (_) { /* ignore */ }
  };

  const handleDownload = () => {
    if (!data) return;
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = documentId ? `document_${documentId}.json` : 'structured_data.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
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
        <div style={{ display: 'flex', gap: 8 }}>
          {documentId && (
            <button className="json-viewer__copy-btn" onClick={handleDownload}>
              ⬇ Download JSON
            </button>
          )}
          <button className="json-viewer__copy-btn" onClick={handleCopy}>
            {copied ? '✓ Copied' : '⎘ Copy JSON'}
          </button>
        </div>
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
