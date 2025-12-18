import { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useNavigate } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Deploy from './pages/Deploy';
import DeploymentDetails from './pages/DeploymentDetails';
import DeploymentHistory from './pages/DeploymentHistory';
import Settings from './pages/Settings';
import AdminPanel from './pages/AdminPanel';
import Login from './pages/Login';
import Register from './pages/Register';
import KeyboardShortcutsModal from './components/KeyboardShortcutsModal';
import ProtectedRoute from './components/ProtectedRoute';
import useKeyboardShortcuts from './hooks/useKeyboardShortcuts';
import { ToastProvider } from './contexts/ToastContext';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import ToastContainer from './components/ToastContainer';

function AppContent() {
  useKeyboardShortcuts();
  const navigate = useNavigate();
  const { user, isAdmin, isAuthenticated, logout } = useAuth();
  const [searchQuery, setSearchQuery] = useState('');
  const [showSearchResults, setShowSearchResults] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showMobileMenu, setShowMobileMenu] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
    setShowUserMenu(false);
  };

  const getUserInitials = () => {
    if (!user?.username) return '?';
    return user.username.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
  };

  const getRoleBadgeColor = () => {
    switch (user?.role) {
      case 'admin': return 'bg-red-100 text-red-700 border-red-200';
      case 'user': return 'bg-blue-100 text-blue-700 border-blue-200';
      case 'viewer': return 'bg-gray-100 text-gray-700 border-gray-200';
      default: return 'bg-gray-100 text-gray-700 border-gray-200';
    }
  };

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
    <div className="min-h-screen">
      {/* Navigation - Modern Glass */}
      <nav className="sticky top-0 z-50 bg-white/70 backdrop-blur-xl shadow-lg shadow-gray-200/50 border-b border-white/20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center">
                <Link to="/" className="flex items-center space-x-3 group">
                  <div className="w-11 h-11 bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 rounded-2xl flex items-center justify-center shadow-lg shadow-purple-500/30 group-hover:shadow-xl group-hover:shadow-purple-500/40 group-hover:scale-105 transition-all duration-300">
                    <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
                    </svg>
                  </div>
                  <div>
                    <h1 className="text-xl font-bold gradient-text">
                      Multi Cloud Hub
                    </h1>
                    <p className="text-[10px] text-gray-400 font-medium tracking-wider uppercase">Infrastructure Platform</p>
                  </div>
                </Link>
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
                  to="/deployments"
                  className="group border-transparent text-gray-600 hover:text-indigo-600 inline-flex items-center px-3 pt-1 border-b-2 text-sm font-semibold transition-all hover:border-indigo-600"
                >
                  <svg className="w-5 h-5 mr-2 group-hover:scale-110 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                  </svg>
                  History
                </Link>
                {isAdmin() && (
                  <Link
                    to="/admin"
                    className="group border-transparent text-gray-600 hover:text-red-600 inline-flex items-center px-3 pt-1 border-b-2 text-sm font-semibold transition-all hover:border-red-600"
                  >
                    <svg className="w-5 h-5 mr-2 group-hover:scale-110 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                    </svg>
                    Admin
                  </Link>
                )}
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
                    placeholder="Search deployments..."
                    className="block w-72 rounded-xl border-0 bg-gray-100/80 py-2.5 pl-10 pr-4 text-sm placeholder-gray-400 focus:bg-white focus:ring-2 focus:ring-indigo-500/20 focus:shadow-lg transition-all duration-200"
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

              {/* User Menu */}
              {isAuthenticated && user && (
                <div className="relative ml-4">
                  <button
                    onClick={() => setShowUserMenu(!showUserMenu)}
                    className="flex items-center space-x-3 p-1.5 rounded-xl hover:bg-gray-100 transition-all duration-200"
                  >
                    <div className="w-9 h-9 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center text-white font-semibold text-sm shadow-md">
                      {getUserInitials()}
                    </div>
                    <svg className={`w-4 h-4 text-gray-400 transition-transform duration-200 ${showUserMenu ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>

                  {/* Dropdown Menu */}
                  {showUserMenu && (
                    <>
                      <div className="fixed inset-0 z-40" onClick={() => setShowUserMenu(false)}></div>
                      <div className="absolute right-0 mt-2 w-64 bg-white rounded-2xl shadow-xl border border-gray-100 py-2 z-50 animate-fade-in">
                        {/* User Info */}
                        <div className="px-4 py-3 border-b border-gray-100">
                          <div className="flex items-center space-x-3">
                            <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center text-white font-semibold">
                              {getUserInitials()}
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-semibold text-gray-900 truncate">{user.username}</p>
                              <p className="text-xs text-gray-500 truncate">{user.email}</p>
                            </div>
                          </div>
                          <div className="mt-2">
                            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${getRoleBadgeColor()}`}>
                              {user.role?.charAt(0).toUpperCase() + user.role?.slice(1)}
                            </span>
                          </div>
                        </div>

                        {/* Menu Items */}
                        <div className="py-1">
                          <Link
                            to="/settings"
                            onClick={() => setShowUserMenu(false)}
                            className="flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                          >
                            <svg className="w-4 h-4 mr-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            </svg>
                            Settings
                          </Link>
                          <button
                            onClick={handleLogout}
                            className="flex items-center w-full px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
                          >
                            <svg className="w-4 h-4 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                            </svg>
                            Sign out
                          </button>
                        </div>
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>

            {/* Mobile menu button */}
            <div className="flex items-center sm:hidden">
              <button
                onClick={() => setShowMobileMenu(!showMobileMenu)}
                className="inline-flex items-center justify-center p-2 rounded-lg text-gray-400 hover:text-gray-500 hover:bg-gray-100 transition-colors"
              >
                <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  {showMobileMenu ? (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  ) : (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                  )}
                </svg>
              </button>
            </div>
          </div>
        </div>

        {/* Mobile Menu */}
        {showMobileMenu && (
          <div className="sm:hidden bg-white/95 backdrop-blur-xl border-t border-gray-100">
            <div className="px-2 pt-2 pb-3 space-y-1">
              <Link
                to="/"
                onClick={() => setShowMobileMenu(false)}
                className="flex items-center px-3 py-2 rounded-lg text-base font-medium text-gray-700 hover:bg-gray-100"
              >
                <svg className="w-5 h-5 mr-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
                </svg>
                Dashboard
              </Link>
              <Link
                to="/deployments"
                onClick={() => setShowMobileMenu(false)}
                className="flex items-center px-3 py-2 rounded-lg text-base font-medium text-gray-700 hover:bg-gray-100"
              >
                <svg className="w-5 h-5 mr-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                </svg>
                History
              </Link>
              {isAdmin() && (
                <Link
                  to="/admin"
                  onClick={() => setShowMobileMenu(false)}
                  className="flex items-center px-3 py-2 rounded-lg text-base font-medium text-gray-700 hover:bg-gray-100"
                >
                  <svg className="w-5 h-5 mr-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                  Admin
                </Link>
              )}
              <Link
                to="/settings"
                onClick={() => setShowMobileMenu(false)}
                className="flex items-center px-3 py-2 rounded-lg text-base font-medium text-gray-700 hover:bg-gray-100"
              >
                <svg className="w-5 h-5 mr-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                Settings
              </Link>
            </div>

            {/* Mobile User Info & Logout */}
            {isAuthenticated && user && (
              <div className="pt-3 pb-3 border-t border-gray-200">
                <div className="flex items-center px-4 py-2">
                  <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center text-white font-semibold">
                    {getUserInitials()}
                  </div>
                  <div className="ml-3">
                    <p className="text-sm font-semibold text-gray-900">{user.username}</p>
                    <p className="text-xs text-gray-500">{user.email}</p>
                  </div>
                </div>
                <button
                  onClick={handleLogout}
                  className="flex items-center w-full px-4 py-2 mt-2 text-base font-medium text-red-600 hover:bg-red-50"
                >
                  <svg className="w-5 h-5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                  </svg>
                  Sign out
                </button>
              </div>
            )}
          </div>
        )}
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <Routes>
          {/* Public Routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          {/* Protected Routes */}
          <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/deploy" element={<ProtectedRoute requiredPermission="write"><Deploy /></ProtectedRoute>} />
          <Route path="/deploy/:provider/:template" element={<ProtectedRoute requiredPermission="write"><Deploy /></ProtectedRoute>} />
          <Route path="/deployments" element={<ProtectedRoute><DeploymentHistory /></ProtectedRoute>} />
          <Route path="/deployments/:id" element={<ProtectedRoute><DeploymentDetails /></ProtectedRoute>} />
          <Route path="/admin" element={<ProtectedRoute requiredPermission="manage_users"><AdminPanel /></ProtectedRoute>} />
          <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
        </Routes>
      </main>

      {/* Keyboard Shortcuts Modal */}
      <KeyboardShortcutsModal />

      {/* Toast Notifications */}
      <ToastContainer />
    </div>
  );
}

function App() {
  return (
    <Router>
      <AuthProvider>
        <ToastProvider>
          <AppContent />
        </ToastProvider>
      </AuthProvider>
    </Router>
  );
}

export default App;
