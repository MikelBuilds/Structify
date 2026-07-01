/**
 * FilterChips
 * Reusable status filter pills.
 *
 * Props:
 *  - active   : 'all' | 'completed' | 'processing' | 'failed'
 *  - onChange : (filter: string) => void
 *  - counts   : { all, completed, processing, failed }
 */
const FILTERS = [
  { key: 'all',        label: 'All' },
  { key: 'completed',  label: 'Completed' },
  { key: 'processing', label: 'Processing' },
  { key: 'failed',     label: 'Failed' },
];

const FilterChips = ({ active = 'all', onChange, counts = {} }) => {
  return (
    <div className="filter-chips" role="group" aria-label="Filter by status">
      {FILTERS.map(({ key, label }) => {
        const isActive = active === key;
        const count = counts[key];
        return (
          <button
            key={key}
            className={`filter-chip ${isActive ? 'filter-chip--active' : ''}`}
            onClick={() => onChange(key)}
            aria-pressed={isActive}
          >
            {label}
            {count !== undefined && (
              <span className="filter-chip__count">{count}</span>
            )}
          </button>
        );
      })}
    </div>
  );
};

export default FilterChips;
