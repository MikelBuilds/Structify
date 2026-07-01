import { useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Sidebar        from './components/Sidebar';
import Navbar         from './components/Navbar';
import Dashboard      from './pages/Dashboard';
import DocumentDetail from './pages/DocumentDetail';
import History        from './pages/History';

const App = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const closeSidebar = () => setSidebarOpen(false);
  const toggleSidebar = () => setSidebarOpen((o) => !o);

  return (
    <BrowserRouter>
      <div className="app-shell">
        {/* Mobile overlay — closes sidebar on tap */}
        {sidebarOpen && (
          <div
            className="sidebar-overlay"
            onClick={closeSidebar}
            aria-hidden="true"
          />
        )}

        {/* Fixed sidebar */}
        <Sidebar isOpen={sidebarOpen} onClose={closeSidebar} />

        {/* Main content area */}
        <div className="app-main">
          {/* Fixed top navbar */}
          <Navbar onMenuToggle={toggleSidebar} />

          {/* Page routes */}
          <Routes>
            <Route path="/"              element={<Dashboard />} />
            <Route path="/history"       element={<History />} />
            <Route path="/documents/:id" element={<DocumentDetail />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  );
};

export default App;