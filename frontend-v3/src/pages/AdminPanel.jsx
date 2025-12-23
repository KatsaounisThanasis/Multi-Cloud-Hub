import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import { useNavigate } from 'react-router-dom';
import { authAPI, deploymentAPI, cloudAccountsAPI } from '../api/client';
import axios from 'axios';
import LoadingState from '../components/LoadingState';
import { formatTemplateName, getStatusColor, formatProviderType } from '../utils/formatters';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function AdminPanel() {
  const { user, token, isAdmin } = useAuth();
  const { addToast } = useToast();
  const navigate = useNavigate();

  // Tab state
  const [activeTab, setActiveTab] = useState('overview');

  // Data states
  const [users, setUsers] = useState([]);
  const [deployments, setDeployments] = useState([]);
  const [cloudAccounts, setCloudAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [systemHealth, setSystemHealth] = useState(null);

  // Modal states
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);

  // Cloud Account modal states
  const [showAccountModal, setShowAccountModal] = useState(false);
  const [showPermissionsModal, setShowPermissionsModal] = useState(false);
  const [selectedAccount, setSelectedAccount] = useState(null);
  const [accountPermissions, setAccountPermissions] = useState([]);

  // Form state for new user
  const [newUser, setNewUser] = useState({
    email: '',
    username: '',
    password: '',
    role: 'user'
  });

  // Form state for edit user
  const [editUser, setEditUser] = useState({
    username: '',
    role: ''
  });

  // Form state for cloud account
  const [accountForm, setAccountForm] = useState({
    name: '',
    provider: 'azure',
    subscription_id: '',
    tenant_id: '',
    client_id: '',
    client_secret: '',
    project_id: '',
    region: ''
  });

  // Form state for permission
  const [permissionForm, setPermissionForm] = useState({
    user_email: '',
    can_deploy: true,
    can_view: true
  });

  // Redirect if not admin
  useEffect(() => {
    if (!isAdmin()) {
      addToast('Access denied. Admin privileges required.', 'error', 4000);
      navigate('/');
    }
  }, [isAdmin, navigate]);

  // Fetch all data
  useEffect(() => {
    if (isAdmin()) {
      fetchAllData();
    }
  }, []);

  const fetchAllData = async () => {
    setLoading(true);
    await Promise.all([
      fetchUsers(),
      fetchDeployments(),
      fetchSystemHealth(),
      fetchCloudAccounts()
    ]);
    setLoading(false);
  };

  const fetchUsers = async () => {
    try {
      const response = await authAPI.listUsers();
      if (response.data.success) {
        setUsers(response.data.data.users || []);
      }
    } catch (error) {
      console.error('Failed to fetch users:', error);
    }
  };

  const fetchDeployments = async () => {
    try {
      const response = await deploymentAPI.getAll();
      setDeployments(response.data.data.deployments || []);
    } catch (error) {
      console.error('Failed to fetch deployments:', error);
    }
  };

  const fetchSystemHealth = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/health`);
      setSystemHealth(response.data);
    } catch (error) {
      console.error('Failed to fetch system health:', error);
      setSystemHealth({ status: 'error' });
    }
  };

  const fetchCloudAccounts = async () => {
    try {
      const response = await cloudAccountsAPI.getAll();
      if (response.data.success) {
        setCloudAccounts(response.data.data.accounts || []);
      }
    } catch (error) {
      console.error('Failed to fetch cloud accounts:', error);
    }
  };

  // Cloud account management functions
  const handleSaveAccount = async (e) => {
    e.preventDefault();
    try {
      if (selectedAccount) {
        // Update existing account
        const response = await cloudAccountsAPI.update(selectedAccount.id, accountForm);
        if (response.data.success) {
          addToast('Cloud account updated successfully', 'success', 3000);
        }
      } else {
        // Create new account
        const response = await cloudAccountsAPI.create(accountForm);
        if (response.data.success) {
          addToast('Cloud account created successfully', 'success', 3000);
        }
      }
      setShowAccountModal(false);
      resetAccountForm();
      fetchCloudAccounts();
    } catch (error) {
      addToast(error.response?.data?.detail || 'Failed to save cloud account', 'error', 4000);
    }
  };

  const handleDeleteAccount = async (accountId) => {
    if (!confirm('Are you sure you want to delete this cloud account? All associated permissions will also be deleted.')) return;
    try {
      const response = await cloudAccountsAPI.delete(accountId);
      if (response.data.success) {
        addToast('Cloud account deleted successfully', 'success', 3000);
        fetchCloudAccounts();
      }
    } catch (error) {
      addToast(error.response?.data?.detail || 'Failed to delete cloud account', 'error', 4000);
    }
  };

  const openEditAccount = (account) => {
    setSelectedAccount(account);
    setAccountForm({
      name: account.name,
      provider: account.provider,
      subscription_id: account.subscription_id || '',
      tenant_id: account.tenant_id || '',
      client_id: account.client_id || '',
      client_secret: '',
      project_id: account.project_id || '',
      region: account.region || ''
    });
    setShowAccountModal(true);
  };

  const resetAccountForm = () => {
    setSelectedAccount(null);
    setAccountForm({
      name: '',
      provider: 'azure',
      subscription_id: '',
      tenant_id: '',
      client_id: '',
      client_secret: '',
      project_id: '',
      region: ''
    });
  };

  // Permission management functions
  const openPermissionsModal = async (account) => {
    setSelectedAccount(account);
    try {
      const response = await cloudAccountsAPI.getPermissions(account.id);
      if (response.data.success) {
        setAccountPermissions(response.data.data.permissions || []);
      }
    } catch (error) {
      console.error('Failed to fetch permissions:', error);
      setAccountPermissions([]);
    }
    setShowPermissionsModal(true);
  };

  const handleAddPermission = async (e) => {
    e.preventDefault();
    try {
      const response = await cloudAccountsAPI.assignPermission(selectedAccount.id, permissionForm);
      if (response.data.success) {
        addToast('Permission added successfully', 'success', 3000);
        setPermissionForm({ user_email: '', can_deploy: true, can_view: true });
        // Refresh permissions
        const permResponse = await cloudAccountsAPI.getPermissions(selectedAccount.id);
        if (permResponse.data.success) {
          setAccountPermissions(permResponse.data.data.permissions || []);
        }
      }
    } catch (error) {
      addToast(error.response?.data?.detail || 'Failed to add permission', 'error', 4000);
    }
  };

  const handleRemovePermission = async (userEmail) => {
    if (!confirm(`Remove permission for ${userEmail}?`)) return;
    try {
      const response = await cloudAccountsAPI.removePermission(selectedAccount.id, userEmail);
      if (response.data.success) {
        addToast('Permission removed', 'success', 3000);
        setAccountPermissions(prev => prev.filter(p => p.user_email !== userEmail));
      }
    } catch (error) {
      addToast(error.response?.data?.detail || 'Failed to remove permission', 'error', 4000);
    }
  };

  // User management functions
  const handleAddUser = async (e) => {
    e.preventDefault();
    try {
      const response = await authAPI.register(newUser);
      if (response.data.success) {
        addToast(`User ${newUser.username} created successfully`, 'success', 3000);
        setShowAddModal(false);
        setNewUser({ email: '', username: '', password: '', role: 'user' });
        fetchUsers();
      }
    } catch (error) {
      addToast(error.response?.data?.detail || 'Failed to create user', 'error', 4000);
    }
  };

  const handleUpdateUser = async (e) => {
    e.preventDefault();
    try {
      const response = await authAPI.updateUser(selectedUser.email, editUser);
      if (response.data.success) {
        addToast('User updated successfully', 'success', 3000);
        setShowEditModal(false);
        setSelectedUser(null);
        fetchUsers();
      }
    } catch (error) {
      addToast(error.response?.data?.detail || 'Failed to update user', 'error', 4000);
    }
  };

  const handleDeleteUser = async (userEmail) => {
    if (!confirm(`Are you sure you want to delete user ${userEmail}?`)) return;
    try {
      const response = await authAPI.deleteUser(userEmail);
      if (response.data.success) {
        addToast('User deleted successfully', 'success', 3000);
        fetchUsers();
      }
    } catch (error) {
      addToast(error.response?.data?.detail || 'Failed to delete user', 'error', 4000);
    }
  };

  const openEditModal = (usr) => {
    setSelectedUser(usr);
    setEditUser({ username: usr.username, role: usr.role });
    setShowEditModal(true);
  };

  // Stats calculations
  const stats = {
    totalUsers: users.length,
    adminUsers: users.filter(u => u.role === 'admin').length,
    regularUsers: users.filter(u => u.role === 'user').length,
    viewerUsers: users.filter(u => u.role === 'viewer').length,
    totalDeployments: deployments.length,
    completedDeployments: deployments.filter(d => d.status?.toLowerCase() === 'completed').length,
    runningDeployments: deployments.filter(d => d.status?.toLowerCase() === 'running').length,
    failedDeployments: deployments.filter(d => d.status?.toLowerCase() === 'failed').length,
  };

  const getRoleBadgeColor = (role) => {
    switch (role) {
      case 'admin': return 'bg-red-100 text-red-700 border-red-200';
      case 'user': return 'bg-blue-100 text-blue-700 border-blue-200';
      case 'viewer': return 'bg-gray-100 text-gray-700 border-gray-200';
      default: return 'bg-gray-100 text-gray-700 border-gray-200';
    }
  };

  if (loading) {
    return <LoadingState message="Loading admin panel..." fullPage />;
  }

  const tabs = [
    { id: 'overview', name: 'Overview', icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    )},
    { id: 'users', name: 'Users', icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
      </svg>
    )},
    { id: 'deployments', name: 'All Deployments', icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
      </svg>
    )},
    { id: 'cloudAccounts', name: 'Cloud Accounts', icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
      </svg>
    )},
  ];

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-6">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center space-x-3">
          <div className="w-12 h-12 bg-gradient-to-br from-red-500 to-rose-600 rounded-2xl flex items-center justify-center shadow-lg shadow-red-500/30">
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Admin Panel</h1>
            <p className="text-sm text-gray-500">System administration and user management</p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center space-x-2 py-4 px-1 border-b-2 font-medium text-sm transition-all ${
                activeTab === tab.id
                  ? 'border-red-500 text-red-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.icon}
              <span>{tab.name}</span>
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* System Health */}
          <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">System Health</h3>
            <div className="flex items-center space-x-3">
              <div className={`w-4 h-4 rounded-full ${
                systemHealth?.status === 'healthy' || systemHealth?.data?.status === 'healthy'
                  ? 'bg-green-500 animate-pulse'
                  : 'bg-red-500'
              }`}></div>
              <span className={`font-medium ${
                systemHealth?.status === 'healthy' || systemHealth?.data?.status === 'healthy'
                  ? 'text-green-600'
                  : 'text-red-600'
              }`}>
                {systemHealth?.status === 'healthy' || systemHealth?.data?.status === 'healthy' ? 'All Systems Operational' : 'System Issues Detected'}
              </span>
            </div>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Total Users */}
            <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-2xl p-6 text-white shadow-lg shadow-blue-500/30">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-blue-100 text-sm font-medium">Total Users</p>
                  <p className="text-3xl font-bold mt-1">{stats.totalUsers}</p>
                </div>
                <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                  </svg>
                </div>
              </div>
              <div className="mt-4 flex space-x-4 text-sm">
                <span className="text-blue-100">{stats.adminUsers} admins</span>
                <span className="text-blue-100">{stats.regularUsers} users</span>
                <span className="text-blue-100">{stats.viewerUsers} viewers</span>
              </div>
            </div>

            {/* Total Deployments */}
            <div className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-2xl p-6 text-white shadow-lg shadow-purple-500/30">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-purple-100 text-sm font-medium">Total Deployments</p>
                  <p className="text-3xl font-bold mt-1">{stats.totalDeployments}</p>
                </div>
                <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                  </svg>
                </div>
              </div>
            </div>

            {/* Completed */}
            <div className="bg-gradient-to-br from-emerald-500 to-green-600 rounded-2xl p-6 text-white shadow-lg shadow-emerald-500/30">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-emerald-100 text-sm font-medium">Completed</p>
                  <p className="text-3xl font-bold mt-1">{stats.completedDeployments}</p>
                </div>
                <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
              </div>
            </div>

            {/* Failed */}
            <div className="bg-gradient-to-br from-red-500 to-rose-600 rounded-2xl p-6 text-white shadow-lg shadow-red-500/30">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-red-100 text-sm font-medium">Failed</p>
                  <p className="text-3xl font-bold mt-1">{stats.failedDeployments}</p>
                </div>
                <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
              </div>
            </div>
          </div>

          {/* Recent Activity */}
          <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Deployments</h3>
            <div className="space-y-3">
              {deployments.slice(0, 5).map((deployment) => (
                <div key={deployment.deployment_id} className="flex items-center justify-between p-3 bg-gray-50 rounded-xl">
                  <div className="flex items-center space-x-3">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(deployment.status)}`}>
                      {deployment.status}
                    </span>
                    <span className="font-medium text-gray-900">{formatTemplateName(deployment.template_name)}</span>
                  </div>
                  <div className="text-sm text-gray-500">
                    {new Date(deployment.created_at).toLocaleString()}
                  </div>
                </div>
              ))}
              {deployments.length === 0 && (
                <p className="text-gray-500 text-center py-4">No deployments yet</p>
              )}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'users' && (
        <div>
          {/* Add User Button */}
          <div className="flex justify-end mb-6">
            <button
              onClick={() => setShowAddModal(true)}
              className="inline-flex items-center px-4 py-2 bg-gradient-to-r from-blue-600 to-purple-600 text-white text-sm font-semibold rounded-xl shadow-lg hover:shadow-xl transition-all"
            >
              <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Add User
            </button>
          </div>

          {/* Users Table */}
          <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">User</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Role</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Created</th>
                  <th className="px-6 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {users.map((usr) => (
                  <tr key={usr.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center text-white font-semibold text-sm">
                          {usr.username?.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2) || '?'}
                        </div>
                        <div className="ml-4">
                          <div className="text-sm font-semibold text-gray-900">{usr.username}</div>
                          <div className="text-sm text-gray-500">{usr.email}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getRoleBadgeColor(usr.role)}`}>
                        {usr.role}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(usr.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <button
                        onClick={() => openEditModal(usr)}
                        className="text-blue-600 hover:text-blue-900 mr-4"
                      >
                        Edit
                      </button>
                      {usr.email !== user?.email && (
                        <button
                          onClick={() => handleDeleteUser(usr.email)}
                          className="text-red-600 hover:text-red-900"
                        >
                          Delete
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'deployments' && (
        <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">ID</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Template</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Provider</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Status</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Created</th>
                <th className="px-6 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {deployments.map((deployment) => (
                <tr key={deployment.deployment_id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="font-mono text-sm text-gray-900">{deployment.deployment_id.slice(0, 8)}...</span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm font-medium text-gray-900">{formatTemplateName(deployment.template_name)}</span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm text-gray-500">{formatProviderType(deployment.provider_type)}</span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(deployment.status)}`}>
                      {deployment.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {new Date(deployment.created_at).toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button
                      onClick={() => navigate(`/deployments/${deployment.deployment_id}`)}
                      className="text-blue-600 hover:text-blue-900"
                    >
                      View
                    </button>
                  </td>
                </tr>
              ))}
              {deployments.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-6 py-8 text-center text-gray-500">
                    No deployments found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'cloudAccounts' && (
        <div>
          {/* Add Account Button */}
          <div className="flex justify-end mb-6">
            <button
              onClick={() => { resetAccountForm(); setShowAccountModal(true); }}
              className="inline-flex items-center px-4 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 text-white text-sm font-semibold rounded-xl shadow-lg hover:shadow-xl transition-all"
            >
              <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Add Cloud Account
            </button>
          </div>

          {/* Cloud Accounts Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {cloudAccounts.map((account) => (
              <div key={account.id} className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6 hover:shadow-xl transition-all">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center space-x-3">
                    <div className={`w-12 h-12 rounded-xl flex items-center justify-center shadow-lg ${
                      account.provider === 'azure'
                        ? 'bg-gradient-to-br from-blue-500 to-blue-600 shadow-blue-500/30'
                        : 'bg-gradient-to-br from-red-500 to-orange-500 shadow-red-500/30'
                    }`}>
                      {account.provider === 'azure' ? (
                        <svg className="w-6 h-6 text-white" viewBox="0 0 24 24" fill="currentColor">
                          <path d="M13.05 4.24l-3.04 8.54 6.18 6.98L3.56 19.76h15.88l-6.39-15.52zM3.87 18.92l6.18-7.02-3.04-8.52L3.87 18.92z"/>
                        </svg>
                      ) : (
                        <svg className="w-6 h-6 text-white" viewBox="0 0 24 24" fill="currentColor">
                          <path d="M12 0c-3.87 0-7.5 1.87-9.77 5.02a.75.75 0 00.76 1.15l8.76-1.54a.75.75 0 00.25-.09l.23-.14a.75.75 0 01.54-.15l9.02 1.59a.75.75 0 00.76-1.15A11.99 11.99 0 0012 0z"/>
                          <path d="M22.5 8.5l-9.75 1.71a.75.75 0 00-.63.74v12.3a.75.75 0 001.13.65l9.75-5.71a.75.75 0 00.38-.65V9.25a.75.75 0 00-.88-.75z"/>
                          <path d="M10.5 10.96l-9.12 1.6a.75.75 0 00-.63.74v4.29a.75.75 0 00.38.65l9.75 5.71a.75.75 0 001.12-.65V11.71a.75.75 0 00-.63-.74l-.87-.01z"/>
                        </svg>
                      )}
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900">{account.name}</h3>
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                        account.provider === 'azure'
                          ? 'bg-blue-100 text-blue-700'
                          : 'bg-orange-100 text-orange-700'
                      }`}>
                        {account.provider.toUpperCase()}
                      </span>
                    </div>
                  </div>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    account.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                  }`}>
                    {account.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>

                <div className="space-y-2 text-sm text-gray-600 mb-4">
                  {account.provider === 'azure' ? (
                    <>
                      <div className="flex justify-between">
                        <span className="text-gray-500">Subscription:</span>
                        <span className="font-mono text-xs">{account.subscription_id?.slice(0, 8)}...</span>
                      </div>
                      {account.tenant_id && (
                        <div className="flex justify-between">
                          <span className="text-gray-500">Tenant:</span>
                          <span className="font-mono text-xs">{account.tenant_id?.slice(0, 8)}...</span>
                        </div>
                      )}
                    </>
                  ) : (
                    <>
                      <div className="flex justify-between">
                        <span className="text-gray-500">Project:</span>
                        <span className="font-mono text-xs">{account.project_id}</span>
                      </div>
                      {account.region && (
                        <div className="flex justify-between">
                          <span className="text-gray-500">Region:</span>
                          <span>{account.region}</span>
                        </div>
                      )}
                    </>
                  )}
                </div>

                <div className="flex space-x-2 pt-4 border-t border-gray-100">
                  <button
                    onClick={() => openPermissionsModal(account)}
                    className="flex-1 px-3 py-2 bg-gray-100 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-200 transition-colors"
                  >
                    Permissions
                  </button>
                  <button
                    onClick={() => openEditAccount(account)}
                    className="px-3 py-2 text-blue-600 hover:bg-blue-50 text-sm font-medium rounded-lg transition-colors"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDeleteAccount(account.id)}
                    className="px-3 py-2 text-red-600 hover:bg-red-50 text-sm font-medium rounded-lg transition-colors"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}

            {cloudAccounts.length === 0 && (
              <div className="col-span-full text-center py-12 bg-white rounded-2xl border border-gray-100">
                <svg className="w-16 h-16 mx-auto text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
                </svg>
                <p className="text-gray-500 mb-4">No cloud accounts configured yet</p>
                <button
                  onClick={() => { resetAccountForm(); setShowAccountModal(true); }}
                  className="inline-flex items-center px-4 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 text-white text-sm font-semibold rounded-xl"
                >
                  Add Your First Account
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Cloud Account Modal */}
      {showAccountModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto animate-fade-in">
            <div className="px-6 py-4 border-b border-gray-100">
              <h3 className="text-lg font-semibold text-gray-900">
                {selectedAccount ? 'Edit Cloud Account' : 'Add Cloud Account'}
              </h3>
            </div>
            <form onSubmit={handleSaveAccount} className="px-6 py-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Account Name</label>
                <input
                  type="text"
                  required
                  value={accountForm.name}
                  onChange={(e) => setAccountForm({ ...accountForm, name: e.target.value })}
                  placeholder="e.g., Production Azure, Dev GCP"
                  className="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Cloud Provider</label>
                <select
                  value={accountForm.provider}
                  onChange={(e) => setAccountForm({ ...accountForm, provider: e.target.value })}
                  disabled={!!selectedAccount}
                  className="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100"
                >
                  <option value="azure">Microsoft Azure</option>
                  <option value="gcp">Google Cloud Platform</option>
                </select>
              </div>

              {accountForm.provider === 'azure' ? (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Subscription ID *</label>
                    <input
                      type="text"
                      required
                      value={accountForm.subscription_id}
                      onChange={(e) => setAccountForm({ ...accountForm, subscription_id: e.target.value })}
                      placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                      className="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Tenant ID</label>
                    <input
                      type="text"
                      value={accountForm.tenant_id}
                      onChange={(e) => setAccountForm({ ...accountForm, tenant_id: e.target.value })}
                      placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                      className="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Client ID (App Registration)</label>
                    <input
                      type="text"
                      value={accountForm.client_id}
                      onChange={(e) => setAccountForm({ ...accountForm, client_id: e.target.value })}
                      placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                      className="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Client Secret {selectedAccount && '(leave blank to keep current)'}
                    </label>
                    <input
                      type="password"
                      value={accountForm.client_secret}
                      onChange={(e) => setAccountForm({ ...accountForm, client_secret: e.target.value })}
                      placeholder="••••••••••••••••"
                      className="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                </>
              ) : (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Project ID *</label>
                    <input
                      type="text"
                      required
                      value={accountForm.project_id}
                      onChange={(e) => setAccountForm({ ...accountForm, project_id: e.target.value })}
                      placeholder="my-gcp-project-id"
                      className="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Default Region</label>
                    <input
                      type="text"
                      value={accountForm.region}
                      onChange={(e) => setAccountForm({ ...accountForm, region: e.target.value })}
                      placeholder="us-central1"
                      className="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                </>
              )}

              <div className="flex justify-end space-x-3 pt-4">
                <button
                  type="button"
                  onClick={() => { setShowAccountModal(false); resetAccountForm(); }}
                  className="px-4 py-2 border border-gray-300 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 text-white rounded-xl text-sm font-medium hover:shadow-lg transition-all"
                >
                  {selectedAccount ? 'Update Account' : 'Create Account'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Permissions Modal */}
      {showPermissionsModal && selectedAccount && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto animate-fade-in">
            <div className="px-6 py-4 border-b border-gray-100">
              <h3 className="text-lg font-semibold text-gray-900">User Permissions</h3>
              <p className="text-sm text-gray-500">{selectedAccount.name}</p>
            </div>

            {/* Add Permission Form */}
            <form onSubmit={handleAddPermission} className="px-6 py-4 border-b border-gray-100">
              <div className="flex items-end space-x-3">
                <div className="flex-1">
                  <label className="block text-sm font-medium text-gray-700 mb-1">User Email</label>
                  <select
                    value={permissionForm.user_email}
                    onChange={(e) => setPermissionForm({ ...permissionForm, user_email: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="">Select user...</option>
                    {users
                      .filter(u => !accountPermissions.some(p => p.user_email === u.email))
                      .map(u => (
                        <option key={u.email} value={u.email}>{u.username} ({u.email})</option>
                      ))
                    }
                  </select>
                </div>
                <div className="flex items-center space-x-4">
                  <label className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      checked={permissionForm.can_deploy}
                      onChange={(e) => setPermissionForm({ ...permissionForm, can_deploy: e.target.checked })}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="text-sm text-gray-700">Deploy</span>
                  </label>
                  <label className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      checked={permissionForm.can_view}
                      onChange={(e) => setPermissionForm({ ...permissionForm, can_view: e.target.checked })}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="text-sm text-gray-700">View</span>
                  </label>
                </div>
                <button
                  type="submit"
                  disabled={!permissionForm.user_email}
                  className="px-4 py-2 bg-blue-600 text-white rounded-xl text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Add
                </button>
              </div>
            </form>

            {/* Permissions List */}
            <div className="px-6 py-4">
              <h4 className="text-sm font-medium text-gray-700 mb-3">Current Permissions</h4>
              {accountPermissions.length > 0 ? (
                <div className="space-y-2">
                  {accountPermissions.map((perm) => (
                    <div key={perm.user_email} className="flex items-center justify-between p-3 bg-gray-50 rounded-xl">
                      <div>
                        <span className="font-medium text-gray-900">{perm.user_email}</span>
                        <div className="flex space-x-2 mt-1">
                          {perm.can_deploy && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700">
                              Can Deploy
                            </span>
                          )}
                          {perm.can_view && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-700">
                              Can View
                            </span>
                          )}
                        </div>
                      </div>
                      <button
                        onClick={() => handleRemovePermission(perm.user_email)}
                        className="text-red-600 hover:text-red-800 p-1"
                      >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 text-center py-4">No permissions assigned yet</p>
              )}
            </div>

            <div className="px-6 py-4 border-t border-gray-100">
              <button
                onClick={() => { setShowPermissionsModal(false); setSelectedAccount(null); setAccountPermissions([]); }}
                className="w-full px-4 py-2 border border-gray-300 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add User Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full mx-4 animate-fade-in">
            <div className="px-6 py-4 border-b border-gray-100">
              <h3 className="text-lg font-semibold text-gray-900">Add New User</h3>
            </div>
            <form onSubmit={handleAddUser} className="px-6 py-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                <input
                  type="email"
                  required
                  value={newUser.email}
                  onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
                <input
                  type="text"
                  required
                  value={newUser.username}
                  onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
                <input
                  type="password"
                  required
                  minLength={6}
                  value={newUser.password}
                  onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
                <select
                  value={newUser.role}
                  onChange={(e) => setNewUser({ ...newUser, role: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="viewer">Viewer (read only)</option>
                  <option value="user">User (read, write)</option>
                  <option value="admin">Admin (full access)</option>
                </select>
              </div>
              <div className="flex justify-end space-x-3 pt-4">
                <button
                  type="button"
                  onClick={() => { setShowAddModal(false); setNewUser({ email: '', username: '', password: '', role: 'user' }); }}
                  className="px-4 py-2 border border-gray-300 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-xl text-sm font-medium hover:shadow-lg transition-all"
                >
                  Create User
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit User Modal */}
      {showEditModal && selectedUser && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full mx-4 animate-fade-in">
            <div className="px-6 py-4 border-b border-gray-100">
              <h3 className="text-lg font-semibold text-gray-900">Edit User</h3>
              <p className="text-sm text-gray-500">{selectedUser.email}</p>
            </div>
            <form onSubmit={handleUpdateUser} className="px-6 py-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
                <input
                  type="text"
                  required
                  value={editUser.username}
                  onChange={(e) => setEditUser({ ...editUser, username: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
                <select
                  value={editUser.role}
                  onChange={(e) => setEditUser({ ...editUser, role: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="viewer">Viewer (read only)</option>
                  <option value="user">User (read, write)</option>
                  <option value="admin">Admin (full access)</option>
                </select>
              </div>
              <div className="flex justify-end space-x-3 pt-4">
                <button
                  type="button"
                  onClick={() => { setShowEditModal(false); setSelectedUser(null); }}
                  className="px-4 py-2 border border-gray-300 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-xl text-sm font-medium hover:shadow-lg transition-all"
                >
                  Update User
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default AdminPanel;
