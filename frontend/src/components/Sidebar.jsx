import { NavLink } from 'react-router-dom';

const NAV_ITEMS = [
  { to: '/',        icon: '⊞', label: 'Dashboard' },
  { to: '/history', icon: '◫', label: 'History' },
];

/**
 * Sidebar
 * Fixed left navigation with brand logo and page links.
 */
const Sidebar = () => {
  return (
    <aside className="sidebar">
      {/* Brand */}
      <div className="sidebar__brand">
        <div className="sidebar__logo">S</div>
        <div>
          <div className="sidebar__brand-name">Structify</div>
          <span className="sidebar__brand-tag">AI</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="sidebar__nav">
        <span className="sidebar__section-label">Menu</span>

        {NAV_ITEMS.map(({ to, icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `sidebar__item${isActive ? ' active' : ''}`
            }
          >
            <span className="sidebar__icon">{icon}</span>
            {label}
          </NavLink>
        ))}

        <span className="sidebar__section-label" style={{ marginTop: 8 }}>
          System
        </span>

        <div className="sidebar__item" style={{ cursor: 'default', opacity: 0.5 }}>
          <span className="sidebar__icon">⚙</span>
          Settings
        </div>
      </nav>

      {/* Footer */}
      <div className="sidebar__footer">
        <span className="sidebar__version">Structify v1.0 · Powered by AI</span>
      </div>
    </aside>
  );
};

export default Sidebar;
