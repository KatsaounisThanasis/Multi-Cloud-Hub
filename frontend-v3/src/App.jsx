import { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useNavigate } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Deploy from './pages/Deploy';
import DeploymentDetails from './pages/DeploymentDetails';
import KeyboardShortcutsModal from './components/KeyboardShortcutsModal';
import useKeyboardShortcuts from './hooks/useKeyboardShortcuts';

function AppContent() {
  useKeyboardShortcuts();
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [showSearchResults, setShowSearchResults] = useState(false);

  const handleSearch = (e) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      // Navigate to dashboard with search query
      navigate(`/?search=${encodeURIComponent(searchQuery)}`);
      setShowSearchResults(false);
      setSearchQuery('');
    }
  };

  return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 via-blue-50 to-purple-50">
        {/* Navigation - Modern Glass */}
        <nav className="bg-white/80 backdrop-blur-xl shadow-lg border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16">
              <div className="flex">
                <div className="flex-shrink-0 flex items-center">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-purple-600 rounded-xl flex items-center justify-center shadow-lg">
                      <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
                      </svg>
                    </div>
                    <div>
                      <h1 className="text-xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                        Multi-Cloud Manager
                      </h1>
                      <p className="text-xs text-gray-500 font-medium">v3.0</p>
                    </div>
                  </div>
                </div>
                <div className="hidden sm:ml-8 sm:flex sm:space-x-4">
                  <Link
                    to="/"
                    className="group border-transparent text-gray-600 hover:text-blue-600 inline-flex items-center px-3 pt-1 border-b-2 text-sm font-semibold transition-all hover:border-blue-600"
                  >
                    <svg className="w-5 h-5 mr-2 group-hover:scale-110 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
                    </svg>
                    Dashboard
                  </Link>
                  <Link
                    to="/deploy"
                    className="group border-transparent text-gray-600 hover:text-purple-600 inline-flex items-center px-3 pt-1 border-b-2 text-sm font-semibold transition-all hover:border-purple-600"
                  >
                    <svg className="w-5 h-5 mr-2 group-hover:scale-110 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                    </svg>
                    New Deployment
                  </Link>
                </div>
              </div>

              {/* Global Search Bar */}
              <div className="hidden md:flex md:items-center md:ml-6">
                <form onSubmit={handleSearch} className="relative">
                  <div className="relative">
                    <input
                      type="text"
                      id="global-search"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="Search deployments... (Press / to focus)"
                      className="block w-64 rounded-lg border border-gray-300 bg-white py-2 pl-10 pr-3 text-sm placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    />
                    <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                      <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                      </svg>
                    </div>
                    {searchQuery && (
                      <button
                        type="button"
                        onClick={() => setSearchQuery('')}
                        className="absolute inset-y-0 right-0 flex items-center pr-3"
                      >
                        <svg className="h-4 w-4 text-gray-400 hover:text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    )}
                  </div>
                </form>
              </div>
            </div>
          </div>
        </nav>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/deploy" element={<Deploy />} />
            <Route path="/deployments/:id" element={<DeploymentDetails />} />
          </Routes>
        </main>

        {/* Keyboard Shortcuts Modal */}
        <KeyboardShortcutsModal />
      </div>
  );
}

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}

export default App;
