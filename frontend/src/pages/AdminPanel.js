/**
 * Admin Panel - System Configuration
 * Full CRUD for Roles, Permissions, Departments, Users, Incentives
 */
import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import RoleConfigurationPanel from '../components/RoleConfigurationPanel';
import IncentiveConfiguration from '../components/IncentiveConfiguration';
import BlueSheetConfiguration from '../components/BlueSheetConfiguration';
import SalesTargetsConfiguration from '../components/SalesTargetsConfiguration';
import { configAPI } from '../services/api';
import {
  Users, Shield, Building2, Settings, ChevronRight,
  Plus, Edit2, Trash2, Check, X, Search, AlertCircle,
  Loader2, Save, Cloud, ChevronDown, ChevronUp, DollarSign, LayoutDashboard, Brain, Target,
  Plug2, Zap, Sparkles
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

const AdminPanel = () => {
  const { user, token } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('users');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Data states
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [permissions, setPermissions] = useState({ permissions: [], grouped: {} });
  const [commissionTemplates, setCommissionTemplates] = useState([]);

  // Modal/Edit states
  const [showRoleModal, setShowRoleModal] = useState(false);
  const [editingRole, setEditingRole] = useState(null);
  const [showPermissionModal, setShowPermissionModal] = useState(false);
  const [showDeptModal, setShowDeptModal] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [syncingAzure, setSyncingAzure] = useState(false);
  const [expandedRole, setExpandedRole] = useState(null);
  
  // Webhook & Sync states
  const [webhookStatus, setWebhookStatus] = useState(null);
  const [syncConfig, setSyncConfig] = useState(null);
  const [syncing, setSyncing] = useState(false);
  
  // LLM Configuration states
  const [llmConfig, setLlmConfig] = useState(null);
  const [loadingLlm, setLoadingLlm] = useState(false);
  const [testingLlm, setTestingLlm] = useState(false);
  
  // Integrations sub-tab
  const [integrationsSubTab, setIntegrationsSubTab] = useState('odoo');

  // Check super admin access
  useEffect(() => {
    if (user && !user.is_super_admin) {
      navigate('/dashboard');
    }
  }, [user, navigate]);

  // Fetch all data
  const fetchData = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError('');

    try {
      const headers = { 'Authorization': `Bearer ${token}` };
      const [usersRes, rolesRes, deptsRes, permsRes, templatesRes] = await Promise.all([
        fetch(`${API_URL}/api/admin/users`, { headers }),
        fetch(`${API_URL}/api/admin/roles`, { headers }),
        fetch(`${API_URL}/api/admin/departments`, { headers }),
        fetch(`${API_URL}/api/admin/permissions`, { headers }),
        fetch(`${API_URL}/api/sales/commission-templates`, { headers })
      ]);

      if (usersRes.ok) setUsers((await usersRes.json()).users || []);
      if (rolesRes.ok) setRoles((await rolesRes.json()).roles || []);
      if (deptsRes.ok) setDepartments((await deptsRes.json()).departments || []);
      if (permsRes.ok) setPermissions(await permsRes.json());
      if (templatesRes.ok) {
        const data = await templatesRes.json();
        setCommissionTemplates(data.templates || []);
      }
    } catch (err) {
      setError('Failed to load data');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchData();
    if (activeTab === 'ai-llm') {
      fetchLlmConfig();
    }
  }, [fetchData, activeTab]);

  // ===================== LLM CONFIG =====================
  const fetchLlmConfig = async () => {
    if (!token) return;
    setLoadingLlm(true);
    try {
      const res = await fetch(`${API_URL}/api/admin/llm/config`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setLlmConfig(data.config || {
          provider: 'openai',
          model: 'gpt-4',
          api_key: '',
          base_url: null,
          temperature: 0.7,
          max_tokens: 1000
        });
      }
    } catch (err) {
      setError('Failed to load LLM configuration');
    } finally {
      setLoadingLlm(false);
    }
  };

  const saveLlmConfig = async () => {
    if (!token || !llmConfig) return;
    setLoadingLlm(true);
    try {
      const res = await fetch(`${API_URL}/api/admin/llm/config`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(llmConfig)
      });
      
      if (res.ok) {
        setSuccess('LLM configuration saved successfully');
      } else {
        const data = await res.json();
        setError(data.detail || 'Failed to save LLM configuration');
      }
    } catch (err) {
      setError('Failed to save LLM configuration');
    } finally {
      setLoadingLlm(false);
    }
  };

  const testLlmConnection = async () => {
    if (!token || !llmConfig) return;
    setTestingLlm(true);
    try {
      const res = await fetch(`${API_URL}/api/admin/llm/test`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(llmConfig)
      });
      
      const data = await res.json();
      if (res.ok) {
        setSuccess('✅ LLM connection successful!');
      } else {
        setError(data.detail || 'LLM connection failed');
      }
    } catch (err) {
      setError('Failed to test LLM connection');
    } finally {
      setTestingLlm(false);
    }
  };

  // ===================== ROLE CRUD =====================
  const saveRole = async (roleData) => {
    try {
      const isEdit = !!roleData.id;
      const url = isEdit 
        ? `${API_URL}/api/admin/roles/${roleData.id}`
        : `${API_URL}/api/admin/roles`;
      
      const res = await fetch(url, {
        method: isEdit ? 'PUT' : 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(roleData)
      });

      const data = await res.json();
      if (res.ok) {
        setSuccess(isEdit ? 'Role updated successfully' : 'Role created successfully');
        setShowRoleModal(false);
        setEditingRole(null);
        fetchData();
      } else {
        setError(data.detail || 'Failed to save role');
      }
    } catch (err) {
      setError('Failed to save role');
    }
  };

  const deleteRole = async (roleId) => {
    if (!confirm('Are you sure you want to delete this role?')) return;
    
    try {
      const res = await fetch(`${API_URL}/api/admin/roles/${roleId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (res.ok) {
        setSuccess('Role deleted');
        fetchData();
      } else {
        const data = await res.json();
        setError(data.detail || 'Failed to delete role');
      }
    } catch (err) {
      setError('Failed to delete role');
    }
  };

  // ===================== PERMISSION CRUD =====================
  const createPermission = async (permData) => {
    try {
      const res = await fetch(`${API_URL}/api/admin/permissions`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(permData)
      });

      if (res.ok) {
        setSuccess('Permission created');
        setShowPermissionModal(false);
        fetchData();
      } else {
        const data = await res.json();
        setError(data.detail || 'Failed to create permission');
      }
    } catch (err) {
      setError('Failed to create permission');
    }
  };

  // ===================== DEPARTMENT CRUD =====================
  const saveDepartment = async (deptData) => {
    try {
      const res = await fetch(`${API_URL}/api/admin/departments`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(deptData)
      });

      if (res.ok) {
        setSuccess('Department created');
        setShowDeptModal(false);
        fetchData();
      } else {
        const data = await res.json();
        setError(data.detail || 'Failed to create department');
      }
    } catch (err) {
      setError('Failed to create department');
    }
  };

  // ===================== USER UPDATE =====================
  const updateUser = async (userId, updates) => {
    try {
      const res = await fetch(`${API_URL}/api/admin/users/${userId}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(updates)
      });

      if (res.ok) {
        setSuccess('User updated');
        setEditingUser(null);
        fetchData();
      } else {
        const data = await res.json();
        setError(data.detail || 'Failed to update user');
      }
    } catch (err) {
      setError('Failed to update user');
    }
  };

  // ===================== ODOO SYNC =====================
  const syncOdooDepartments = async () => {
    setLoading(true);
    setError('');
    
    try {
      const res = await fetch(`${API_URL}/api/admin/sync-odoo-departments`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      const data = await res.json();
      if (res.ok) {
        setSuccess(`Odoo Departments Synced: ${data.created} created, ${data.updated} updated`);
        fetchData();
      } else {
        setError(data.detail || 'Odoo department sync failed');
      }
    } catch (err) {
      setError('Odoo department sync failed');
    } finally {
      setLoading(false);
    }
  };

  const syncOdooUsers = async () => {
    setLoading(true);
    setError('');
    
    try {
      const res = await fetch(`${API_URL}/api/admin/sync-odoo-users`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      const data = await res.json();
      if (res.ok) {
        setSuccess(`Odoo Users Synced: ${data.created} created, ${data.updated} updated. ${data.note}`);
        fetchData();
      } else {
        setError(data.detail || 'Odoo user sync failed');
      }
    } catch (err) {
      setError('Odoo user sync failed');
    } finally {
      setLoading(false);
    }
  };

  // ===================== USER APPROVAL =====================
  const approveUser = async (userId) => {
    try {
      const res = await fetch(`${API_URL}/api/admin/users/${userId}/approve`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      const data = await res.json();
      if (res.ok) {
        setSuccess(`User ${data.user_email} approved`);
        fetchData();
      } else {
        setError(data.detail || 'Failed to approve user');
      }
    } catch (err) {
      setError('Failed to approve user');
    }
  };

  const rejectUser = async (userId) => {
    if (!confirm('Are you sure you want to reject this user?')) return;
    
    try {
      const res = await fetch(`${API_URL}/api/admin/users/${userId}/reject`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      const data = await res.json();
      if (res.ok) {
        setSuccess(`User ${data.user_email} rejected`);
        fetchData();
      } else {
        setError(data.detail || 'Failed to reject user');
      }
    } catch (err) {
      setError('Failed to reject user');
    }
  };

  const deleteUser = async (userId) => {
    if (!confirm('Are you sure you want to PERMANENTLY delete this user? This will allow them to re-register via Microsoft SSO. This action cannot be undone.')) return;
    
    try {
      const res = await fetch(`${API_URL}/api/admin/users/${userId}?permanent=true`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      const data = await res.json();
      if (res.ok) {
        setSuccess('User permanently deleted');
        fetchData();
      } else {
        setError(data.detail || 'Failed to delete user');
      }
    } catch (err) {
      setError('Failed to delete user');
    }
  };

  // ===================== AZURE SYNC =====================
  const syncAzureUsers = async () => {
    setSyncingAzure(true);
    setError('');
    
    try {
      const res = await fetch(`${API_URL}/api/admin/sync-azure-users`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      const data = await res.json();
      if (res.ok) {
        setSuccess(`Azure AD Sync: ${data.created} created, ${data.updated} updated`);
        fetchData();
      } else {
        setError(data.detail || 'Azure AD sync failed');
      }
    } catch (err) {
      setError('Azure AD sync failed');
    } finally {
      setSyncingAzure(false);
    }
  };

  const tabs = [
    { id: 'users', label: 'User Management', icon: Users },
    { id: 'roles', label: 'Roles & Permissions', icon: Shield },
    { id: 'role-config', label: 'Role Configuration', icon: LayoutDashboard },
    { id: 'incentives', label: 'Incentive Config', icon: DollarSign },
    { id: 'targets', label: 'Sales Targets', icon: Target },
    { id: 'bluesheet', label: 'Deal Confidence', icon: Brain },
    { id: 'departments', label: 'Departments', icon: Building2 },
    { id: 'integrations', label: 'Integrations', icon: Plug2 },
    { id: 'ai-llm', label: 'AI & LLM', icon: Sparkles },
    { id: 'permissions', label: 'All Permissions', icon: Settings },
  ];

  const filteredUsers = users.filter(u =>
    u.email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    u.name?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Separate pending users for highlight
  const pendingUsers = filteredUsers.filter(u => u.approval_status === 'pending');
  const approvedUsers = filteredUsers.filter(u => u.approval_status !== 'pending');
  const allFilteredUsers = [...pendingUsers, ...approvedUsers]; // Show pending first

  // Clear messages after 5 seconds
  useEffect(() => {
    if (success || error) {
      const timer = setTimeout(() => {
        setSuccess('');
        setError('');
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [success, error]);

  return (
    <div className="min-h-screen bg-slate-50 flex animate-in" data-testid="admin-panel">
      {/* Sidebar */}
      <div className="w-64 bg-white border-r border-slate-200 p-4 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900 mb-6 flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
            <Settings className="w-4 h-4 text-white" />
          </div>
          System Config
        </h2>

        <nav className="space-y-1">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              data-testid={`admin-tab-${tab.id}`}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                activeTab === tab.id
                  ? 'bg-indigo-50 text-indigo-700 border border-indigo-200'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <tab.icon className={`w-4 h-4 ${activeTab === tab.id ? 'text-indigo-600' : ''}`} />
              {tab.label}
              <ChevronRight className={`w-4 h-4 ml-auto transition-transform ${
                activeTab === tab.id ? 'rotate-90 text-indigo-600' : 'text-slate-400'
              }`} />
            </button>
          ))}
        </nav>
      </div>

      {/* Main Content */}
      <div className="flex-1 p-8 overflow-auto">
        {/* Messages */}
        {error && (
          <div className="mb-4 flex items-center gap-2 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span className="flex-1">{error}</span>
            <button onClick={() => setError('')} className="p-1 hover:bg-red-100 rounded-lg transition-colors"><X className="w-4 h-4" /></button>
          </div>
        )}
        {success && (
          <div className="mb-4 flex items-center gap-2 p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-700">
            <Check className="w-4 h-4 flex-shrink-0" />
            <span>{success}</span>
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <Loader2 className="w-8 h-8 text-indigo-500 animate-spin mx-auto mb-3" />
              <p className="text-slate-500">Loading configuration...</p>
            </div>
          </div>
        ) : (
          <>
            {/* ===================== USERS TAB ===================== */}
            {activeTab === 'users' && (
              <div>
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h1 className="text-2xl font-bold text-slate-900">User Management</h1>
                    {pendingUsers.length > 0 && (
                      <p className="text-sm text-amber-600 mt-1 flex items-center gap-1">
                        <AlertCircle className="w-4 h-4" />
                        {pendingUsers.length} user{pendingUsers.length > 1 ? 's' : ''} pending approval
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <Button
                      onClick={syncAzureUsers}
                      disabled={syncingAzure}
                      className="btn-secondary border-blue-200 text-blue-700 hover:bg-blue-50"
                      data-testid="sync-azure-btn"
                    >
                      {syncingAzure ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Cloud className="w-4 h-4 mr-2" />}
                      Sync Azure AD
                    </Button>
                    <Button
                      onClick={syncOdooUsers}
                      disabled={loading}
                      className="btn-secondary border-emerald-200 text-emerald-700 hover:bg-emerald-50"
                      data-testid="sync-odoo-users-btn"
                    >
                      {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Cloud className="w-4 h-4 mr-2" />}
                      Sync Odoo Users
                    </Button>
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                      <Input
                        placeholder="Search users..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="pl-10 w-64"
                      />
                    </div>
                  </div>
                </div>

                <div className="card overflow-x-auto">
                  <table className="w-full min-w-[900px]">
                    <thead className="bg-slate-50 border-b border-slate-200">
                      <tr>
                        <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider min-w-[200px]">User</th>
                        <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider min-w-[100px]">Role</th>
                        <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider min-w-[120px]">Department</th>
                        <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider min-w-[130px]">Commission</th>
                        <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider min-w-[120px]">Approval Status</th>
                        <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider min-w-[80px]">Status</th>
                        <th className="text-right px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider w-36 min-w-[140px]">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {allFilteredUsers.map(u => (
                        <tr 
                          key={u.id} 
                          className={`border-b border-slate-100 hover:bg-slate-50 transition-colors ${
                            u.approval_status === 'pending' ? 'bg-amber-50/50' : ''
                          }`}
                        >
                          <td className="px-4 py-3">
                            <p className="font-medium text-slate-900">{u.name || 'No name'}</p>
                            <p className="text-slate-500 text-sm">{u.email}</p>
                            {/* Azure AD Details */}
                            {(u.job_title || u.ad_department || u.company_name) && (
                              <div className="mt-1 text-xs text-slate-400">
                                {u.job_title && <span>{u.job_title}</span>}
                                {u.job_title && u.ad_department && <span> • </span>}
                                {u.ad_department && <span>{u.ad_department}</span>}
                                {(u.job_title || u.ad_department) && u.company_name && <span> @ </span>}
                                {u.company_name && <span>{u.company_name}</span>}
                              </div>
                            )}
                          </td>
                          <td className="px-4 py-3">
                            {editingUser?.id === u.id ? (
                              <select
                                value={editingUser.role_id || ''}
                                onChange={(e) => setEditingUser({ ...editingUser, role_id: e.target.value })}
                                className="input text-sm py-1"
                              >
                                <option value="">No Role</option>
                                {roles.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
                              </select>
                            ) : (
                              <span className={`px-2.5 py-1 rounded-full text-xs font-semibold border ${
                                u.is_super_admin ? 'bg-purple-50 text-purple-700 border-purple-200' :
                                u.role_name ? 'bg-indigo-50 text-indigo-700 border-indigo-200' : 'bg-slate-100 text-slate-600 border-slate-200'
                              }`}>
                                {u.is_super_admin ? '👑 Super Admin' : u.role_name || 'No Role'}
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-3">
                            {editingUser?.id === u.id ? (
                              <select
                                value={editingUser.department_id || ''}
                                onChange={(e) => setEditingUser({ ...editingUser, department_id: e.target.value })}
                                className="input text-sm py-1"
                              >
                                <option value="">No Department</option>
                                {departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
                              </select>
                            ) : (
                              <span className="text-slate-600">{u.department_name || '-'}</span>
                            )}
                          </td>
                          <td className="px-4 py-3">
                            {u.approval_status === 'pending' ? (
                              <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                                Pending
                              </span>
                            ) : u.approval_status === 'rejected' ? (
                              <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-red-50 text-red-700 border border-red-200">
                                Rejected
                              </span>
                            ) : (
                              <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                                Approved
                              </span>
                            )}
                            {/* Odoo Match Status */}
                            {u.odoo_matched && (
                              <span className="ml-2 px-2 py-0.5 rounded text-xs bg-blue-50 text-blue-700 border border-blue-200" title={`Odoo: ${u.odoo_department_name || u.odoo_salesperson_name || 'Linked'}`}>
                                🔗 Odoo
                              </span>
                            )}
                            {u.odoo_match_status && !u.odoo_matched && u.approval_status === 'approved' && (
                              <span className="ml-2 px-2 py-0.5 rounded text-xs bg-amber-50 text-amber-600 border border-amber-200" title="User not found in Odoo">
                                ⚠️ No Odoo
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-3">
                            <span className={`px-2.5 py-1 rounded-full text-xs font-semibold border ${
                              u.is_active !== false ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-red-50 text-red-700 border-red-200'
                            }`}>
                              {u.is_active !== false ? 'Active' : 'Inactive'}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right w-32 min-w-[120px]">
                            {u.approval_status === 'pending' ? (
                              <div className="flex justify-end gap-2">
                                <Button 
                                  size="sm" 
                                  onClick={() => approveUser(u.id)}
                                  className="bg-emerald-600 hover:bg-emerald-700 text-white"
                                >
                                  <Check className="w-4 h-4 mr-1" />
                                  Approve
                                </Button>
                                <Button 
                                  size="sm" 
                                  variant="ghost" 
                                  onClick={() => rejectUser(u.id)}
                                  className="text-red-600 hover:text-red-700 hover:bg-red-50"
                                >
                                  <X className="w-4 h-4 mr-1" />
                                  Reject
                                </Button>
                              </div>
                            ) : editingUser?.id === u.id ? (
                              <div className="flex justify-end gap-2">
                                <Button size="sm" onClick={() => updateUser(u.id, editingUser)} className="btn-primary">
                                  <Save className="w-4 h-4" />
                                </Button>
                                <Button size="sm" variant="ghost" onClick={() => setEditingUser(null)}>
                                  <X className="w-4 h-4" />
                                </Button>
                              </div>
                            ) : (
                              <div className="flex justify-end gap-2 flex-nowrap">
                                <Button size="sm" variant="ghost" onClick={() => setEditingUser({ id: u.id, role_id: u.role_id, department_id: u.department_id })} className="text-slate-600 hover:text-slate-900" title="Edit user">
                                  <Edit2 className="w-4 h-4" />
                                </Button>
                                <Button 
                                  size="sm" 
                                  variant="ghost" 
                                  onClick={() => deleteUser(u.id)}
                                  className="text-red-600 hover:text-red-700 hover:bg-red-50"
                                  title="Delete user"
                                >
                                  <Trash2 className="w-4 h-4" />
                                </Button>
                              </div>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* ===================== ROLES TAB ===================== */}
            {activeTab === 'roles' && (
              <div>
                <div className="flex items-center justify-between mb-6">
                  <h1 className="text-2xl font-bold text-slate-900">Roles & Permissions</h1>
                  <Button onClick={() => { setEditingRole(null); setShowRoleModal(true); }} className="btn-primary" data-testid="create-role-btn">
                    <Plus className="w-4 h-4 mr-2" /> Create Role
                  </Button>
                </div>

                <div className="space-y-3">
                  {roles.map(role => (
                    <div key={role.id} className="card overflow-hidden">
                      {/* Role Header */}
                      <div
                        className="p-4 flex items-center justify-between cursor-pointer hover:bg-slate-50 transition-colors"
                        onClick={() => setExpandedRole(expandedRole === role.id ? null : role.id)}
                      >
                        <div className="flex items-center gap-3">
                          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${role.code === 'super_admin' ? 'bg-purple-100' : 'bg-indigo-100'}`}>
                            <Shield className={`w-5 h-5 ${role.code === 'super_admin' ? 'text-purple-600' : 'text-indigo-600'}`} />
                          </div>
                          <div>
                            <h3 className="font-semibold text-slate-900 flex items-center gap-2">
                              {role.name}
                              {role.is_system && <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full border border-slate-200">System</span>}
                            </h3>
                            <p className="text-slate-500 text-sm">{role.description}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${
                            role.data_scope === 'all' ? 'bg-purple-50 text-purple-700 border-purple-200' :
                            role.data_scope === 'team' ? 'bg-blue-50 text-blue-700 border-blue-200' :
                            role.data_scope === 'department' ? 'bg-amber-50 text-amber-700 border-amber-200' :
                            'bg-slate-100 text-slate-600 border-slate-200'
                          }`}>
                            {role.data_scope}
                          </span>
                          <span className="text-slate-500 text-sm">{role.permissions?.length || 0} permissions</span>
                          {!role.is_system && (
                            <>
                              <Button size="sm" variant="ghost" onClick={(e) => { e.stopPropagation(); setEditingRole(role); setShowRoleModal(true); }} className="text-slate-600 hover:text-slate-900">
                                <Edit2 className="w-4 h-4" />
                              </Button>
                              <Button size="sm" variant="ghost" className="text-red-600 hover:text-red-700 hover:bg-red-50" onClick={(e) => { e.stopPropagation(); deleteRole(role.id); }}>
                                <Trash2 className="w-4 h-4" />
                              </Button>
                            </>
                          )}
                          {expandedRole === role.id ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                        </div>
                      </div>

                      {/* Expanded Permissions */}
                      {expandedRole === role.id && (
                        <div className="border-t border-slate-200 p-4 bg-slate-50">
                          <p className="text-xs text-slate-500 mb-3 font-medium uppercase tracking-wider">Assigned Permissions:</p>
                          <div className="flex flex-wrap gap-2">
                            {role.permissions?.map(perm => (
                              <span key={perm} className="px-2.5 py-1 bg-white rounded-full text-xs text-slate-700 border border-slate-200">
                                {perm === '*' ? '✓ All Permissions' : perm}
                              </span>
                            ))}
                            {(!role.permissions || role.permissions.length === 0) && (
                              <span className="text-slate-500 text-sm">No permissions assigned</span>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* ===================== DEPARTMENTS TAB ===================== */}
            {activeTab === 'departments' && (
              <div>
                <div className="flex items-center justify-between mb-6">
                  <h1 className="text-2xl font-bold text-slate-900">Departments</h1>
                  <div className="flex items-center gap-3">
                    <Button
                      onClick={syncOdooDepartments}
                      disabled={loading}
                      className="btn-secondary border-emerald-200 text-emerald-700 hover:bg-emerald-50"
                      data-testid="sync-odoo-depts-btn"
                    >
                      {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Cloud className="w-4 h-4 mr-2" />}
                      Sync from Odoo
                    </Button>
                    <Button onClick={() => setShowDeptModal(true)} className="btn-primary" data-testid="create-dept-btn">
                      <Plus className="w-4 h-4 mr-2" /> Create Department
                    </Button>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  {departments.map(dept => (
                    <div key={dept.id} className="card p-5 hover:shadow-lg transition-all">
                      <div className="flex items-center gap-3">
                        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-100 to-purple-100 flex items-center justify-center">
                          <Building2 className="w-6 h-6 text-indigo-600" />
                        </div>
                        <div>
                          <h3 className="font-semibold text-slate-900">{dept.name}</h3>
                          <p className="text-slate-500 text-sm font-mono">{dept.code}</p>
                        </div>
                      </div>
                      {dept.description && <p className="text-slate-600 text-sm mt-3">{dept.description}</p>}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* ===================== ROLE CONFIGURATION TAB ===================== */}
            {activeTab === 'role-config' && (
              <RoleConfigTab 
                roles={roles}
                onRoleUpdated={fetchData}
              />
            )}

            {/* ===================== INCENTIVES TAB ===================== */}
            {activeTab === 'incentives' && (
              <IncentiveConfiguration />
            )}

            {/* ===================== BLUE SHEET CONFIG TAB ===================== */}
            {activeTab === 'bluesheet' && (
              <BlueSheetConfiguration />
            )}

            {/* ===================== SALES TARGETS TAB ===================== */}
            {activeTab === 'targets' && (
              <SalesTargetsConfiguration />
            )}

            {/* ===================== PERMISSIONS TAB ===================== */}


            {/* Webhooks & Sync Tab */}
            {activeTab === 'webhooks' && (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-2xl font-bold text-slate-900">Webhooks & Sync Configuration</h2>
                    <p className="text-slate-600 mt-1">Configure real-time webhooks and auto-sync settings</p>
                  </div>
                  <Button
                    onClick={async () => {
                      setSyncing(true);
                      try {
                        const res = await fetch(`${API_URL}/api/admin/sync/trigger`, {
                          method: 'POST',
                          headers: { 'Authorization': `Bearer ${token}` }
                        });
                        if (res.ok) {
                          setSuccess('Sync triggered successfully!');
                        }
                      } catch (err) {
                        setError('Failed to trigger sync');
                      } finally {
                        setSyncing(false);
                      }
                    }}
                    disabled={syncing}
                  >
                    {syncing ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Cloud className="w-4 h-4 mr-2" />}
                    Sync Now
                  </Button>
                </div>

                {/* Webhook Status */}
                <div className="card p-6">
                  <h3 className="text-lg font-bold text-slate-900 mb-4">Webhook Configuration</h3>
                  <p className="text-sm text-slate-600 mb-4">
                    Configure Odoo to send real-time webhooks for instant updates (sub-second latency)
                  </p>
                  
                  <div className="space-y-4">
                    <div>
                      <Label>Webhook URL</Label>
                      <div className="flex gap-2">
                        <Input
                          value="https://ai-sales-platform-4.preview.emergentagent.com/api/webhooks/odoo"
                          readOnly
                          className="font-mono text-sm"
                        />
                        <Button
                          size="sm"
                          onClick={() => {
                            navigator.clipboard.writeText('https://ai-sales-platform-4.preview.emergentagent.com/api/webhooks/odoo');
                            setSuccess('Webhook URL copied!');
                          }}
                        >
                          Copy
                        </Button>
                      </div>
                      <p className="text-xs text-slate-500 mt-1">Use this URL in Odoo automated actions</p>
                    </div>

                    <div>
                      <Label>Webhook Secret Header</Label>
                      <code className="block bg-slate-50 p-3 rounded text-sm">
                        X-Odoo-Webhook-Secret: your-odoo-api-key
                      </code>
                      <p className="text-xs text-slate-500 mt-1">Include this header in webhook requests</p>
                    </div>

                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                      <h4 className="font-semibold text-blue-900 mb-2">📋 Setup in Odoo:</h4>
                      <ol className="text-sm text-blue-800 space-y-1 list-decimal list-inside">
                        <li>Go to Settings → Technical → Automation</li>
                        <li>Create Automated Action for &quot;Account&quot; (res.partner)</li>
                        <li>Trigger: Before → Delete</li>
                        <li>Action: Execute Python Code</li>
                        <li>Paste the code below</li>
                      </ol>
                    </div>

                    <div>
                      <Label>Sample Python Code for Odoo</Label>
                      <pre className="bg-slate-900 text-slate-100 p-4 rounded text-xs overflow-x-auto">
{`import requests
requests.post(
    'https://ai-sales-platform-4.preview.emergentagent.com/api/webhooks/odoo',
    json={
        'model': 'res.partner',
        'action': 'unlink',
        'record_ids': record.ids
    },
    headers={'X-Odoo-Webhook-Secret': 'your-odoo-api-key'},
    timeout=5
)`}
                      </pre>
                    </div>
                  </div>
                </div>

                {/* Auto-Sync Configuration */}
                <div className="card p-6">
                  <h3 className="text-lg font-bold text-slate-900 mb-4">Auto-Sync Configuration</h3>
                  <p className="text-sm text-slate-600 mb-4">
                    Configure automatic background sync with Odoo (backup to webhooks)
                  </p>
                  
                  <div className="space-y-4">
                    <div className="flex items-center gap-3 p-4 bg-slate-50 rounded-lg">
                      <input
                        type="checkbox"
                        checked={true}
                        className="w-4 h-4"
                        readOnly
                      />
                      <div>
                        <p className="font-medium text-slate-900">Enable Auto-Sync</p>
                        <p className="text-xs text-slate-500">Background sync runs automatically</p>
                      </div>
                    </div>

                    <div>
                      <Label>Sync Interval</Label>
                      <select className="input w-full">
                        <option value={1}>1 minute (Real-time, high load)</option>
                        <option value={5} selected>5 minutes (Default, balanced)</option>
                        <option value={15}>15 minutes (Low priority)</option>
                        <option value={30}>30 minutes (Minimal load)</option>
                        <option value={60}>60 minutes (Hourly)</option>
                      </select>
                      <p className="text-xs text-slate-500 mt-1">
                        Lower intervals increase server load but provide fresher data
                      </p>
                    </div>

                    <div className="grid grid-cols-2 gap-4 p-4 bg-slate-50 rounded-lg">
                      <div>
                        <p className="text-xs text-slate-500">Last Sync</p>
                        <p className="font-medium text-slate-900">2 minutes ago</p>
                      </div>
                      <div>
                        <p className="text-xs text-slate-500">Next Sync</p>
                        <p className="font-medium text-slate-900">In ~3 minutes</p>
                      </div>
                    </div>

                    <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                      <p className="text-sm text-amber-800">
                        <strong>⚡ Production Tip:</strong> Use webhooks for real-time updates (&lt;1 sec) 
                        and set auto-sync to 15-30 minutes as a backup.
                      </p>
                    </div>

                    <Button className="w-full" disabled>
                      Save Sync Configuration
                    </Button>
                    <p className="text-xs text-center text-slate-500">
                      Note: Changing sync interval requires backend restart
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* ===================== INTEGRATIONS TAB ===================== */}
            {activeTab === 'integrations' && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-2xl font-bold text-slate-900">Integrations</h2>
                  <p className="text-slate-600 mt-1">Manage third-party integrations and data sources</p>
                </div>

                {/* Sub-tabs for different integrations */}
                <div className="flex gap-2 border-b border-slate-200">
                  <button
                    onClick={() => setIntegrationsSubTab('odoo')}
                    className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 ${
                      integrationsSubTab === 'odoo'
                        ? 'border-indigo-600 text-indigo-600'
                        : 'border-transparent text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    <Plug2 className="w-4 h-4 inline mr-2" />
                    Odoo ERP
                  </button>
                  <button
                    onClick={() => setIntegrationsSubTab('marketplace')}
                    className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 ${
                      integrationsSubTab === 'marketplace'
                        ? 'border-indigo-600 text-indigo-600'
                        : 'border-transparent text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    <Plus className="w-4 h-4 inline mr-2" />
                    Add Integration
                  </button>
                </div>

                {/* Odoo Integration Sub-section */}
                {integrationsSubTab === 'odoo' && (
                  <div className="space-y-6">
                    {/* Webhook Configuration */}
                    <div className="card p-6">
                      <h3 className="text-lg font-bold text-slate-900 mb-4 flex items-center gap-2">
                        <Zap className="w-5 h-5 text-indigo-600" />
                        Webhook Configuration
                      </h3>
                      <p className="text-sm text-slate-600 mb-4">
                        Configure Odoo to send real-time webhooks for instant updates (sub-second latency)
                      </p>
                      
                      <div className="space-y-4">
                        <div>
                          <Label>Webhook URL</Label>
                          <div className="flex gap-2">
                            <Input
                              value="https://ai-sales-platform-4.preview.emergentagent.com/api/webhooks/odoo"
                              readOnly
                              className="font-mono text-sm"
                            />
                            <Button
                              size="sm"
                              onClick={() => {
                                navigator.clipboard.writeText('https://ai-sales-platform-4.preview.emergentagent.com/api/webhooks/odoo');
                                setSuccess('Webhook URL copied!');
                              }}
                            >
                              Copy
                            </Button>
                          </div>
                          <p className="text-xs text-slate-500 mt-1">Use this URL in Odoo automated actions</p>
                        </div>

                        <div>
                          <Label>Webhook Secret Header</Label>
                          <code className="block bg-slate-50 p-3 rounded text-sm">
                            X-Odoo-Webhook-Secret: your-odoo-api-key
                          </code>
                          <p className="text-xs text-slate-500 mt-1">Include this header in webhook requests</p>
                        </div>

                        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                          <h4 className="font-semibold text-blue-900 mb-2">📋 Setup in Odoo:</h4>
                          <ol className="text-sm text-blue-800 space-y-1 list-decimal list-inside">
                            <li>Go to Settings → Technical → Automation</li>
                            <li>Create Automated Action for &quot;Account&quot; (res.partner)</li>
                            <li>Trigger: Before → Delete</li>
                            <li>Action: Execute Python Code</li>
                            <li>Paste the code below</li>
                          </ol>
                        </div>

                        <div>
                          <Label>Sample Python Code for Odoo</Label>
                          <pre className="bg-slate-900 text-slate-100 p-4 rounded text-xs overflow-x-auto">
{`import requests
requests.post(
    'https://ai-sales-platform-4.preview.emergentagent.com/api/webhooks/odoo',
    json={
        'model': 'res.partner',
        'action': 'unlink',
        'record_ids': record.ids
    },
    headers={'X-Odoo-Webhook-Secret': 'your-odoo-api-key'},
    timeout=5
)`}
                          </pre>
                        </div>
                      </div>
                    </div>

                    {/* Auto-Sync Configuration */}
                    <div className="card p-6">
                      <h3 className="text-lg font-bold text-slate-900 mb-4 flex items-center gap-2">
                        <Cloud className="w-5 h-5 text-indigo-600" />
                        Auto-Sync Configuration
                      </h3>
                      <p className="text-sm text-slate-600 mb-4">
                        Configure automatic background sync with Odoo (backup to webhooks)
                      </p>
                      
                      <div className="space-y-4">
                        <div className="flex items-center gap-3 p-4 bg-slate-50 rounded-lg">
                          <input
                            type="checkbox"
                            checked={true}
                            className="w-4 h-4"
                            readOnly
                          />
                          <div>
                            <p className="font-medium text-slate-900">Enable Auto-Sync</p>
                            <p className="text-xs text-slate-500">Background sync runs automatically</p>
                          </div>
                        </div>

                        <div>
                          <Label>Sync Interval</Label>
                          <select className="input w-full">
                            <option value={1}>1 minute (Real-time, high load)</option>
                            <option value={5}>5 minutes (Default, balanced)</option>
                            <option value={15}>15 minutes (Low priority)</option>
                            <option value={30}>30 minutes (Minimal load)</option>
                            <option value={60}>60 minutes (Hourly)</option>
                          </select>
                          <p className="text-xs text-slate-500 mt-1">
                            Lower intervals increase server load but provide fresher data
                          </p>
                        </div>

                        <Button
                          onClick={async () => {
                            setSyncing(true);
                            try {
                              const res = await fetch(`${API_URL}/api/admin/sync/trigger`, {
                                method: 'POST',
                                headers: { 'Authorization': `Bearer ${token}` }
                              });
                              if (res.ok) {
                                setSuccess('Sync triggered successfully!');
                              }
                            } catch (err) {
                              setError('Failed to trigger sync');
                            } finally {
                              setSyncing(false);
                            }
                          }}
                          disabled={syncing}
                          className="w-full"
                        >
                          {syncing ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Cloud className="w-4 h-4 mr-2" />}
                          Sync Now
                        </Button>
                      </div>
                    </div>

                    {/* API Configuration - Placeholder for future */}
                    <div className="card p-6 border-dashed">
                      <h3 className="text-lg font-bold text-slate-900 mb-2 flex items-center gap-2">
                        <Settings className="w-5 h-5 text-slate-400" />
                        API Configuration
                      </h3>
                      <p className="text-sm text-slate-500 mb-4">
                        Configure Odoo API connection settings (URL, database, credentials)
                      </p>
                      <p className="text-xs text-slate-400 italic">
                        Coming soon - Full API configuration UI
                      </p>
                    </div>

                    {/* Field Mapping - Placeholder for future */}
                    <div className="card p-6 border-dashed">
                      <h3 className="text-lg font-bold text-slate-900 mb-2 flex items-center gap-2">
                        <Settings className="w-5 h-5 text-slate-400" />
                        Field Mapping
                      </h3>
                      <p className="text-sm text-slate-500 mb-4">
                        Configure field mappings between Odoo and your system
                      </p>
                      <p className="text-xs text-slate-400 italic">
                        Coming soon - Field mapping configuration UI
                      </p>
                    </div>
                  </div>
                )}

                {/* Marketplace Sub-section */}
                {integrationsSubTab === 'marketplace' && (
                  <div className="card p-8 text-center">
                    <Plus className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                    <h3 className="text-lg font-bold text-slate-900 mb-2">Integration Marketplace</h3>
                    <p className="text-slate-600 mb-4">
                      Browse and install new integrations for your platform
                    </p>
                    <p className="text-xs text-slate-400 italic">
                      Coming soon - Browse Salesforce, HubSpot, and more integrations
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* ===================== AI & LLM TAB ===================== */}
            {activeTab === 'ai-llm' && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
                    <Sparkles className="w-6 h-6 text-indigo-600" />
                    AI & LLM Configuration
                  </h2>
                  <p className="text-slate-600 mt-1">Configure AI providers and models for all AI features</p>
                </div>

                {loadingLlm ? (
                  <div className="flex items-center justify-center h-64">
                    <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
                  </div>
                ) : (
                  <div className="card p-6">
                    <div className="space-y-6">
                      {/* Provider Selection */}
                      <div>
                        <Label>Provider</Label>
                        <select
                          value={llmConfig?.provider || 'openai'}
                          onChange={(e) => setLlmConfig({ ...llmConfig, provider: e.target.value })}
                          className="input w-full"
                        >
                          <option value="openai">OpenAI</option>
                          <option value="anthropic">Anthropic (Claude)</option>
                          <option value="google">Google (Gemini)</option>
                          <option value="azure">Azure OpenAI</option>
                        </select>
                        <p className="text-xs text-slate-500 mt-1">
                          Select your preferred LLM provider
                        </p>
                      </div>

                      {/* Model Selection */}
                      <div>
                        <Label>Model</Label>
                        <Input
                          value={llmConfig?.model || ''}
                          onChange={(e) => setLlmConfig({ ...llmConfig, model: e.target.value })}
                          placeholder="e.g., gpt-4, claude-3-sonnet, gemini-pro"
                          className="w-full"
                        />
                        <p className="text-xs text-slate-500 mt-1">
                          Specify the model to use for AI features
                        </p>
                      </div>

                      {/* API Key */}
                      <div>
                        <Label>API Key</Label>
                        <Input
                          type="password"
                          value={llmConfig?.api_key || ''}
                          onChange={(e) => setLlmConfig({ ...llmConfig, api_key: e.target.value })}
                          placeholder="sk-..."
                          className="w-full font-mono text-sm"
                        />
                        <p className="text-xs text-slate-500 mt-1">
                          Your API key for the selected provider
                        </p>
                      </div>

                      {/* Base URL (Optional) */}
                      <div>
                        <Label>Base URL (Optional)</Label>
                        <Input
                          value={llmConfig?.base_url || ''}
                          onChange={(e) => setLlmConfig({ ...llmConfig, base_url: e.target.value })}
                          placeholder="https://api.openai.com/v1"
                          className="w-full font-mono text-sm"
                        />
                        <p className="text-xs text-slate-500 mt-1">
                          Custom base URL (leave empty for default)
                        </p>
                      </div>

                      {/* Advanced Settings */}
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <Label>Temperature</Label>
                          <Input
                            type="number"
                            step="0.1"
                            min="0"
                            max="2"
                            value={llmConfig?.temperature || 0.7}
                            onChange={(e) => setLlmConfig({ ...llmConfig, temperature: parseFloat(e.target.value) })}
                            className="w-full"
                          />
                          <p className="text-xs text-slate-500 mt-1">0 = deterministic, 2 = creative</p>
                        </div>
                        <div>
                          <Label>Max Tokens</Label>
                          <Input
                            type="number"
                            value={llmConfig?.max_tokens || 1000}
                            onChange={(e) => setLlmConfig({ ...llmConfig, max_tokens: parseInt(e.target.value) })}
                            className="w-full"
                          />
                          <p className="text-xs text-slate-500 mt-1">Maximum response length</p>
                        </div>
                      </div>

                      {/* Feature Usage Info */}
                      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                        <h4 className="font-semibold text-blue-900 mb-2">🤖 AI Features Using This Config:</h4>
                        <ul className="text-sm text-blue-800 space-y-1 list-disc list-inside">
                          <li>Deal Confidence Analysis</li>
                          <li>Field Mapping (Coming Soon)</li>
                          <li>AI Chat Assistant (Coming Soon)</li>
                          <li>Data Quality Checks (Coming Soon)</li>
                        </ul>
                      </div>

                      {/* Action Buttons */}
                      <div className="flex gap-3">
                        <Button
                          onClick={testLlmConnection}
                          disabled={testingLlm || !llmConfig?.api_key}
                          variant="outline"
                          className="flex-1"
                        >
                          {testingLlm ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Zap className="w-4 h-4 mr-2" />}
                          Test Connection
                        </Button>
                        <Button
                          onClick={saveLlmConfig}
                          disabled={loadingLlm || !llmConfig?.api_key}
                          className="flex-1"
                        >
                          {loadingLlm ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                          Save Configuration
                        </Button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'permissions' && (
              <div>
                <div className="flex items-center justify-between mb-6">
                  <h1 className="text-2xl font-bold text-slate-900">All Permissions</h1>
                  <Button onClick={() => setShowPermissionModal(true)} className="btn-primary" data-testid="create-perm-btn">
                    <Plus className="w-4 h-4 mr-2" /> Create Permission
                  </Button>
                </div>

                <div className="space-y-4">
                  {Object.entries(permissions.grouped || {}).map(([module, perms]) => (
                    <div key={module} className="card p-5">
                      <h3 className="text-lg font-semibold text-slate-900 mb-4 capitalize flex items-center gap-2">
                        <div className="w-8 h-8 rounded-lg bg-indigo-100 flex items-center justify-center">
                          <Settings className="w-4 h-4 text-indigo-600" />
                        </div>
                        {module}
                        <span className="text-slate-500 text-sm font-normal">({perms.length})</span>
                      </h3>
                      <div className="grid grid-cols-2 gap-2">
                        {perms.map(perm => (
                          <div key={perm.code} className="flex items-center gap-2 p-3 bg-slate-50 rounded-lg border border-slate-100">
                            <Check className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                            <span className="text-sm text-slate-700">{perm.name}</span>
                            <span className="text-xs text-slate-400 ml-auto font-mono">{perm.code}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* ===================== ROLE MODAL ===================== */}
      {showRoleModal && (
        <RoleModal
          role={editingRole}
          permissions={permissions.grouped || {}}
          onSave={saveRole}
          onClose={() => { setShowRoleModal(false); setEditingRole(null); }}
        />
      )}

      {/* ===================== PERMISSION MODAL ===================== */}
      {showPermissionModal && (
        <PermissionModal
          onSave={createPermission}
          onClose={() => setShowPermissionModal(false)}
        />
      )}

      {/* ===================== DEPARTMENT MODAL ===================== */}
      {showDeptModal && (
        <DepartmentModal
          onSave={saveDepartment}
          onClose={() => setShowDeptModal(false)}
        />
      )}
    </div>
  );
};

// ===================== ROLE MODAL COMPONENT =====================
const RoleModal = ({ role, permissions, onSave, onClose }) => {
  const [formData, setFormData] = useState({
    id: role?.id || null,
    code: role?.code || '',
    name: role?.name || '',
    description: role?.description || '',
    data_scope: role?.data_scope || 'own',
    permissions: role?.permissions || []
  });

  const handlePermissionToggle = (permCode) => {
    setFormData(prev => ({
      ...prev,
      permissions: prev.permissions.includes(permCode)
        ? prev.permissions.filter(p => p !== permCode)
        : [...prev.permissions, permCode]
    }));
  };

  const handleSelectAll = (module, perms) => {
    const permCodes = perms.map(p => p.code);
    const allSelected = permCodes.every(c => formData.permissions.includes(c));
    
    setFormData(prev => ({
      ...prev,
      permissions: allSelected
        ? prev.permissions.filter(p => !permCodes.includes(p))
        : [...new Set([...prev.permissions, ...permCodes])]
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave(formData);
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white border border-slate-200 rounded-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col shadow-2xl animate-scale-in">
        <div className="p-6 border-b border-slate-200 flex items-center justify-between">
          <h2 className="text-xl font-bold text-slate-900">{role ? 'Edit Role' : 'Create Role'}</h2>
          <button onClick={onClose} className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"><X className="w-5 h-5" /></button>
        </div>

        <form onSubmit={handleSubmit} className="flex-1 overflow-auto p-6">
          {/* Basic Info */}
          <div className="grid grid-cols-2 gap-4 mb-6">
            <div>
              <Label className="text-slate-700 mb-2 block font-medium">Role Code</Label>
              <Input
                value={formData.code}
                onChange={(e) => setFormData({ ...formData, code: e.target.value.toLowerCase().replace(/\s/g, '_') })}
                placeholder="e.g., sales_manager"
                required
                disabled={role?.is_system}
              />
            </div>
            <div>
              <Label className="text-slate-700 mb-2 block font-medium">Role Name</Label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="e.g., Sales Manager"
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 mb-6">
            <div>
              <Label className="text-slate-700 mb-2 block font-medium">Description</Label>
              <Input
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Brief description"
              />
            </div>
            <div>
              <Label className="text-slate-700 mb-2 block font-medium">Data Scope</Label>
              <select
                value={formData.data_scope}
                onChange={(e) => setFormData({ ...formData, data_scope: e.target.value })}
                className="input"
              >
                <option value="own">Own - Only assigned records</option>
                <option value="team">Team - Team members&apos; records</option>
                <option value="department">Department - Department records</option>
                <option value="all">All - Full access to all records</option>
              </select>
            </div>
          </div>

          {/* Permissions Matrix */}
          <div className="mb-4">
            <Label className="text-slate-900 mb-3 block text-lg font-semibold">Permissions</Label>
            <p className="text-slate-500 text-sm mb-4">Select the permissions for this role:</p>
          </div>

          <div className="space-y-4">
            {Object.entries(permissions).map(([module, perms]) => (
              <div key={module} className="bg-slate-50 rounded-xl p-4 border border-slate-200">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="font-semibold text-slate-900 capitalize">{module}</h4>
                  <button
                    type="button"
                    onClick={() => handleSelectAll(module, perms)}
                    className="text-xs text-indigo-600 hover:text-indigo-700 font-medium"
                  >
                    {perms.every(p => formData.permissions.includes(p.code)) ? 'Deselect All' : 'Select All'}
                  </button>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                  {perms.map(perm => (
                    <label
                      key={perm.code}
                      className={`flex items-center gap-2 p-3 rounded-lg cursor-pointer transition-all ${
                        formData.permissions.includes(perm.code)
                          ? 'bg-indigo-50 border-2 border-indigo-300'
                          : 'bg-white border border-slate-200 hover:border-slate-300'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={formData.permissions.includes(perm.code)}
                        onChange={() => handlePermissionToggle(perm.code)}
                        className="sr-only"
                      />
                      <div className={`w-5 h-5 rounded flex items-center justify-center flex-shrink-0 ${
                        formData.permissions.includes(perm.code) ? 'bg-indigo-600' : 'bg-slate-200'
                      }`}>
                        {formData.permissions.includes(perm.code) && <Check className="w-3 h-3 text-white" />}
                      </div>
                      <span className="text-sm text-slate-700">{perm.name}</span>
                    </label>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </form>

        <div className="p-6 border-t border-slate-200 flex justify-end gap-3 bg-slate-50">
          <Button variant="ghost" onClick={onClose} className="btn-secondary">Cancel</Button>
          <Button onClick={handleSubmit} className="btn-primary">
            <Save className="w-4 h-4 mr-2" /> {role ? 'Update Role' : 'Create Role'}
          </Button>
        </div>
      </div>
    </div>
  );
};

// ===================== PERMISSION MODAL =====================
const PermissionModal = ({ onSave, onClose }) => {
  const [formData, setFormData] = useState({
    code: '',
    name: '',
    module: '',
    resource: '',
    action: 'view',
    description: ''
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    const code = formData.code || `${formData.module}.${formData.resource}.${formData.action}`;
    onSave({ ...formData, code });
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white border border-slate-200 rounded-2xl w-full max-w-md shadow-2xl animate-scale-in">
        <div className="p-6 border-b border-slate-200 flex items-center justify-between">
          <h2 className="text-xl font-bold text-slate-900">Create Permission</h2>
          <button onClick={onClose} className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"><X className="w-5 h-5" /></button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <Label className="text-slate-700 mb-2 block font-medium">Permission Name</Label>
            <Input
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="e.g., View Reports"
              required
            />
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <Label className="text-slate-700 mb-2 block font-medium">Module</Label>
              <Input
                value={formData.module}
                onChange={(e) => setFormData({ ...formData, module: e.target.value.toLowerCase() })}
                placeholder="crm"
                required
              />
            </div>
            <div>
              <Label className="text-slate-700 mb-2 block font-medium">Resource</Label>
              <Input
                value={formData.resource}
                onChange={(e) => setFormData({ ...formData, resource: e.target.value.toLowerCase() })}
                placeholder="reports"
                required
              />
            </div>
            <div>
              <Label className="text-slate-700 mb-2 block font-medium">Action</Label>
              <select
                value={formData.action}
                onChange={(e) => setFormData({ ...formData, action: e.target.value })}
                className="input"
              >
                <option value="view">View</option>
                <option value="create">Create</option>
                <option value="edit">Edit</option>
                <option value="delete">Delete</option>
                <option value="export">Export</option>
                <option value="manage">Manage</option>
              </select>
            </div>
          </div>

          <div>
            <Label className="text-slate-700 mb-2 block font-medium">Code (auto-generated)</Label>
            <Input
              value={formData.code || `${formData.module}.${formData.resource}.${formData.action}`}
              onChange={(e) => setFormData({ ...formData, code: e.target.value })}
              className="font-mono text-sm"
              placeholder="module.resource.action"
            />
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <Button type="button" variant="ghost" onClick={onClose} className="btn-secondary">Cancel</Button>
            <Button type="submit" className="btn-primary">
              <Plus className="w-4 h-4 mr-2" /> Create
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

// ===================== DEPARTMENT MODAL =====================
const DepartmentModal = ({ onSave, onClose }) => {
  const [formData, setFormData] = useState({
    code: '',
    name: '',
    description: ''
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave(formData);
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white border border-slate-200 rounded-2xl w-full max-w-md shadow-2xl animate-scale-in">
        <div className="p-6 border-b border-slate-200 flex items-center justify-between">
          <h2 className="text-xl font-bold text-slate-900">Create Department</h2>
          <button onClick={onClose} className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"><X className="w-5 h-5" /></button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <Label className="text-slate-700 mb-2 block font-medium">Department Name</Label>
            <Input
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="e.g., Engineering"
              required
            />
          </div>

          <div>
            <Label className="text-slate-700 mb-2 block font-medium">Code</Label>
            <Input
              value={formData.code}
              onChange={(e) => setFormData({ ...formData, code: e.target.value.toLowerCase().replace(/\s/g, '_') })}
              placeholder="e.g., engineering"
              required
            />
          </div>

          <div>
            <Label className="text-slate-700 mb-2 block font-medium">Description</Label>
            <Input
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Optional description"
            />
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <Button type="button" variant="ghost" onClick={onClose} className="btn-secondary">Cancel</Button>
            <Button type="submit" className="btn-primary">
              <Plus className="w-4 h-4 mr-2" /> Create
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

// ===================== ROLE CONFIG TAB COMPONENT =====================
const RoleConfigTab = ({ roles, onRoleUpdated }) => {
  const [showConfigPanel, setShowConfigPanel] = useState(false);
  const [selectedRole, setSelectedRole] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleEditRole = (role) => {
    setSelectedRole(role);
    setShowConfigPanel(true);
  };

  const handleCreateRole = () => {
    setSelectedRole(null);
    setShowConfigPanel(true);
  };

  const handleSaveRole = async (formData) => {
    setLoading(true);
    setError('');
    try {
      if (selectedRole) {
        await configAPI.updateRole(selectedRole.id, formData);
      } else {
        await configAPI.createRole({
          code: formData.name.toLowerCase().replace(/\s/g, '_'),
          ...formData
        });
      }
      setShowConfigPanel(false);
      setSelectedRole(null);
      if (onRoleUpdated) onRoleUpdated();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save role');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Role Configuration</h1>
          <p className="text-sm text-slate-500 mt-1">Configure navigation, dashboard, and incentives for each role</p>
        </div>
        <Button onClick={handleCreateRole} className="btn-primary">
          <Plus className="w-4 h-4 mr-2" /> New Role
        </Button>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Role Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {roles.map(role => (
          <div
            key={role.id}
            className="card p-5 hover:shadow-lg hover:border-slate-300 transition-all cursor-pointer group"
            onClick={() => handleEditRole(role)}
          >
            <div className="flex items-start justify-between mb-3">
              <div>
                <h3 className="font-semibold text-slate-900 group-hover:text-indigo-600 transition-colors">{role.name}</h3>
                <p className="text-xs text-slate-500 font-mono">{role.code}</p>
              </div>
              {role.is_system && (
                <span className="px-2 py-0.5 bg-amber-50 text-amber-700 text-xs rounded-full border border-amber-200 font-medium">System</span>
              )}
            </div>
            
            <p className="text-sm text-slate-600 mb-3 line-clamp-2">{role.description || 'No description'}</p>
            
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <span className="px-2 py-1 bg-slate-100 rounded-full border border-slate-200">Scope: {role.data_scope}</span>
              <span className="px-2 py-1 bg-slate-100 rounded-full border border-slate-200">
                {role.permissions?.length === 1 && role.permissions[0] === '*' 
                  ? 'All permissions' 
                  : `${role.permissions?.length || 0} permissions`}
              </span>
            </div>
            
            {/* Navigation preview */}
            {role.navigation?.main_menu && (
              <div className="mt-3 pt-3 border-t border-slate-100">
                <span className="text-xs text-slate-500 font-medium">Navigation:</span>
                <div className="flex flex-wrap gap-1 mt-1.5">
                  {role.navigation.main_menu.filter(i => i.enabled).slice(0, 4).map(item => (
                    <span key={item.id} className="px-2 py-0.5 bg-indigo-50 text-indigo-700 text-xs rounded-full border border-indigo-200">
                      {item.label}
                    </span>
                  ))}
                  {role.navigation.main_menu.filter(i => i.enabled).length > 4 && (
                    <span className="text-xs text-slate-500">+{role.navigation.main_menu.filter(i => i.enabled).length - 4} more</span>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Role Configuration Panel (Modal) */}
      {showConfigPanel && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="w-full max-w-4xl">
            <RoleConfigurationPanel
              role={selectedRole}
              onSave={handleSaveRole}
              onCancel={() => { setShowConfigPanel(false); setSelectedRole(null); }}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminPanel;
