import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Sidebar        from './components/Sidebar';
import Navbar         from './components/Navbar';
import Dashboard      from './pages/Dashboard';
import DocumentDetail from './pages/DocumentDetail';
import History        from './pages/History';

const App = () => {
  return (
    <BrowserRouter>
      <div className="app-shell">
        {/* Fixed sidebar */}
        <Sidebar />

        {/* Main content area */}
        <div className="app-main">
          {/* Fixed top navbar */}
          <Navbar />

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