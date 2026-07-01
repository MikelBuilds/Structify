/**
 * LoadingSpinner
 *
 * Props:
 *  - size   : 'sm' | 'md' | 'lg'  (default 'md')
 *  - message: optional label beneath spinner
 *  - dots   : boolean  – use dot-bounce style instead of ring
 */
const LoadingSpinner = ({ size = 'md', message, dots = false }) => {
  if (dots) {
    return (
      <div className="spinner-wrap">
        <div className="spinner-dots">
          <div className="spinner-dot" />
          <div className="spinner-dot" />
          <div className="spinner-dot" />
        </div>
        {message && (
          <span className="text-sm text-muted">{message}</span>
        )}
      </div>
    );
  }

  return (
    <div className="spinner-wrap">
      <div className={`spinner spinner--${size}`} />
      {message && (
        <span className="text-sm text-muted">{message}</span>
      )}
    </div>
  );
};

export default LoadingSpinner;
