/**
 * StatusBadge
 * Displays a colored pill badge for document processing status.
 *
 * Props:
 *  - status: 'processing' | 'completed' | 'failed'
 */
const StatusBadge = ({ status }) => {
  const icons = {
    processing: '⏳',
    completed:  '✓',
    failed:     '✕',
  };

  return (
    <span className={`status-badge status-badge--${status ?? 'processing'}`}>
      <span className="status-badge__dot" />
      {icons[status] ? `${icons[status]} ` : ''}
      {status ?? 'unknown'}
    </span>
  );
};

export default StatusBadge;
