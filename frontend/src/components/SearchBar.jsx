/**
 * SearchBar
 * Reusable instant search input.
 *
 * Props:
 *  - value       : string
 *  - onChange    : (value: string) => void
 *  - placeholder : string
 */
const SearchBar = ({ value, onChange, placeholder = 'Search documents…' }) => {
  return (
    <div className="search-bar">
      <span className="search-bar__icon">⌕</span>
      <input
        id="doc-search"
        className="search-bar__input"
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        autoComplete="off"
        spellCheck={false}
        aria-label={placeholder}
      />
      {value && (
        <button
          className="search-bar__clear"
          onClick={() => onChange('')}
          aria-label="Clear search"
        >
          ✕
        </button>
      )}
    </div>
  );
};

export default SearchBar;
