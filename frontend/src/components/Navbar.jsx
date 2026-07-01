import { useLocation } from 'react-router-dom';

/**
 * Navbar
 * Fixed top bar. Passes onMenuToggle for mobile hamburger.
 *
 * Props:
 *  - onMenuToggle : () => void
 */
const Navbar = ({ onMenuToggle }) => {
  const location = useLocation();

  const pageTitles = {
    '/':        { title: 'Dashboard', sub: 'Upload & monitor documents' },
    '/history': { title: 'History',   sub: 'All processed documents' },
  };

  const current =
    pageTitles[location.pathname] ??
    { title: 'Document Detail', sub: 'Extracted structured data' };

  return (
    <nav className="navbar">
      {/* Hamburger — visible only on mobile */}
      <button
        className="navbar__hamburger"
        onClick={onMenuToggle}
        aria-label="Toggle sidebar"
      >
        <span />
        <span />
        <span />
      </button>

      <div className="navbar__left">
        <span className="navbar__title">{current.title}</span>
        <span className="navbar__subtitle">{current.sub}</span>
      </div>

      <div className="navbar__right">
        <div className="navbar__pill">
          <span className="navbar__dot" />
          API Connected
        </div>
        <div className="navbar__avatar" title="User">US</div>
      </div>
    </nav>
  );
};

export default Navbar;
