import StatusBadge from '../StatusBadge';

/**
 * DocumentCard
 * A clickable row card for a document in the list.
 *
 * Props:
 *  - doc     : { id, filename, status, created_at }
 *  - onClick : () => void
 *  - style   : optional inline style (for staggered animation delay)
 */
const DocumentCard = ({ doc, onClick, style }) => {
  const date = doc.created_at
    ? new Date(doc.created_at).toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    : '—';

  return (
    <div className="doc-card" onClick={onClick} style={style} role="button" tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onClick()}
    >
      <div className="doc-card__icon">📄</div>

      <div className="doc-card__info">
        <div className="doc-card__name" title={doc.filename}>
          {doc.filename}
        </div>
        <div className="doc-card__meta">ID #{doc.id} · {date}</div>
      </div>

      <div className="doc-card__right">
        <StatusBadge status={doc.status} />
        <span className="doc-card__arrow">›</span>
      </div>
    </div>
  );
};

export default DocumentCard;
