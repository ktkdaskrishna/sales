/**
 * Layout Component
 * Swiss-style design with dark sidebar and light content area
 */
import React, { useState, useEffect } from 'react';
import { Link, useLocation, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { configAPI } from '../services/api';
import { cn } from '../lib/utils';
import {
  LayoutDashboard,
  Building2,
  Target,
  BarChart3,
  Mail,
  FileText,
  Settings,
  LogOut,
  Menu,
  X,
  Bell,
  ChevronDown,
  Search,
  Command,
  Sparkles,
  Users,
  User,
  Shield,
  Plug,
  Database,
  Wand2,
  Activity,
  Award,
  Briefcase,
  Rocket,
} from 'lucide-react';

// Icon mapping for dynamic navigation
const ICON_MAP = {
  LayoutDashboard, Building2, Target, BarChart3, Mail, FileText,
  Settings, Users, Shield, Plug, Database, Wand2, Activity, Award,
  Briefcase, Rocket,  // NEW: Portfolio and Initiative icons
};

// Get initials from name
const getInitials = (name) => {
  if (!name) return 'U';
  return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
};

// Get role label
const getRoleLabel = (role) => {
  const labels = {
    super_admin: 'Super Admin',
    ceo: 'CEO',
    sales_director: 'Sales Director',
    account_manager: 'Account Manager',
    presales: 'Pre-Sales',
  };
  return labels[role] || role?.replace(/_/g, ' ') || 'User';
};

// NavLink component
const NavLink = ({ item, pathname, onClick }) => {
  const isActive = pathname === item.path || (item.path !== '/dashboard' && pathname.startsWith(item.path));
  const IconComponent = ICON_MAP[item.icon] || Target;
  
  return (
    <Link
      to={item.path}
      onClick={onClick}
      className={cn(
        "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150",
        isActive
          ? "bg-white/10 text-white"
          : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
      )}
      data-testid={`nav-${item.id}`}
    >
      <IconComponent className="w-5 h-5 flex-shrink-0" />
      <span>{item.label}</span>
    </Link>
  );
};

// Sidebar component
const Sidebar = ({ isOpen, onClose, navigation, user }) => {
  const location = useLocation();
  const mainNavItems = navigation.main_menu?.filter(item => item.enabled) || [];
  const adminNavItems = navigation.admin_menu?.filter(item => item.enabled) || [];

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={cn(
          "fixed lg:sticky top-0 left-0 z-50 w-64 h-screen flex flex-col transform transition-transform duration-200 ease-out",
          "bg-slate-900",
          isOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
        data-testid="sidebar"
      >
        {/* Logo */}
        <div className="flex items-center justify-between h-16 px-5 border-b border-slate-800">
          <Link to="/dashboard" className="flex items-center gap-3">
            <div className="w-9 h-9 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/25">
              <Target className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-lg text-white tracking-tight">
              Securado
            </span>
          </Link>
          <button
            onClick={onClose}
            className="lg:hidden p-1 text-slate-400 hover:text-white rounded-lg hover:bg-white/10"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Search */}
        <div className="px-4 py-4">
          <button className="w-full flex items-center gap-3 px-3 py-2 bg-slate-800/50 hover:bg-slate-800 rounded-lg text-slate-400 text-sm transition-colors">
            <Search className="w-4 h-4" />
            <span>Search...</span>
            <kbd className="ml-auto flex items-center gap-0.5 text-xs text-slate-500 bg-slate-800 px-1.5 py-0.5 rounded">
              <Command className="w-3 h-3" />K
            </kbd>
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 pb-4 space-y-1 overflow-y-auto scrollbar-thin">
          <div className="mb-2">
            <span className="px-3 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
              Main Menu
            </span>
          </div>
          {mainNavItems.map((item) => (
            <NavLink 
              key={item.id} 
              item={item} 
              pathname={location.pathname}
              onClick={onClose}
            />
          ))}

          {adminNavItems.length > 0 && (
            <>
              <div className="pt-6 mb-2">
                <span className="px-3 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
                  Administration
                </span>
              </div>
              {adminNavItems.map((item) => (
                <NavLink 
                  key={item.id}
                  item={item} 
                  pathname={location.pathname}
                  onClick={onClose}
                />
              ))}
            </>
          )}
        </nav>

        {/* User Profile */}
        <div className="p-4 border-t border-slate-800">
          <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-white/5 transition-colors cursor-pointer">
            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-slate-600 to-slate-700 flex items-center justify-center text-white text-sm font-semibold ring-2 ring-slate-700">
              {getInitials(user?.name)}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">
                {user?.name || 'User'}
              </p>
              <p className="text-xs text-slate-500 truncate">
                {getRoleLabel(user?.role)}
              </p>
            </div>
            <ChevronDown className="w-4 h-4 text-slate-500" />
          </div>
        </div>
      </aside>
    </>
  );
};

// Header component
const Header = ({ onMenuClick, user, onLogout }) => {
  const location = useLocation();
  const [showDropdown, setShowDropdown] = useState(false);

  const getPageTitle = () => {
    const path = location.pathname;
    if (path === '/dashboard') return 'Dashboard';
    if (path === '/accounts') return 'Accounts';
    if (path === '/opportunities') return 'Opportunities';
    if (path === '/goals') return 'Goals';
    if (path === '/activity') return 'Activity';
    if (path === '/target-progress') return 'Target Progress Report';
    if (path === '/kpis') return 'KPIs';
    if (path === '/my-outlook') return 'Email & Calendar';
    if (path === '/sales-dashboard') return 'Sales Dashboard';
    if (path === '/admin') return 'System Configuration';
    if (path.startsWith('/integrations')) return 'Integrations';
    if (path === '/data-lake') return 'Data Lake';
    if (path === '/field-mapping') return 'Field Mapping';
    return 'Dashboard';
  };

  return (
    <header className="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between sticky top-0 z-30" data-testid="main-header">
      <div className="flex items-center gap-4">
        <button
          onClick={onMenuClick}
          className="lg:hidden p-2 hover:bg-slate-100 rounded-lg transition-colors"
          data-testid="menu-toggle"
        >
          <Menu className="w-5 h-5 text-slate-600" />
        </button>
        <h1 className="text-lg font-semibold text-slate-900">
          {getPageTitle()}
        </h1>
      </div>

      <div className="flex items-center gap-2">
        <button
          className="p-2.5 hover:bg-slate-100 rounded-lg text-slate-500 hover:text-indigo-600 transition-colors"
          title="AI Insights"
        >
          <Sparkles className="w-5 h-5" />
        </button>

        <button
          className="p-2.5 hover:bg-slate-100 rounded-lg relative transition-colors"
          title="Notifications"
        >
          <Bell className="w-5 h-5 text-slate-500" />
          <span className="absolute top-2 right-2 w-2 h-2 bg-red-500 rounded-full ring-2 ring-white" />
        </button>

        <div className="w-px h-8 bg-slate-200 mx-2" />

        <div className="relative">
          <button
            onClick={() => setShowDropdown(!showDropdown)}
            className="flex items-center gap-3 p-1.5 pr-3 hover:bg-slate-100 rounded-lg transition-colors"
            data-testid="user-dropdown-btn"
          >
            <div className="w-8 h-8 rounded-full bg-slate-900 flex items-center justify-center text-white text-sm font-medium">
              {getInitials(user?.name)}
            </div>
            <span className="text-sm font-medium text-slate-700 hidden sm:block">
              {user?.name?.split(' ')[0]}
            </span>
            <ChevronDown className="w-4 h-4 text-slate-400" />
          </button>

          {showDropdown && (
            <>
              <div 
                className="fixed inset-0 z-40" 
                onClick={() => setShowDropdown(false)} 
              />
              <div className="absolute right-0 top-full mt-2 w-64 bg-white rounded-xl shadow-lg border border-slate-200 py-2 z-50">
                {/* User Info Header */}
                <div className="px-4 py-3 border-b border-slate-100">
                  <p className="font-medium text-slate-900">{user?.name}</p>
                  <p className="text-sm text-slate-500 truncate">{user?.email}</p>
                  {user?.role && (
                    <span className="inline-block mt-1 px-2 py-0.5 rounded text-xs bg-blue-50 text-blue-700 border border-blue-200">
                      {user.role.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </span>
                  )}
                  {user?.odoo_department_name && (
                    <p className="text-xs text-slate-400 mt-1">Dept: {user.odoo_department_name}</p>
                  )}
                </div>
                
                {/* Menu Items */}
                <div className="py-1">
                  <Link
                    to="/profile"
                    className="flex items-center gap-3 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
                    onClick={() => setShowDropdown(false)}
                  >
                    <User className="w-4 h-4" />
                    My Profile
                  </Link>
                  
                  {/* System Config for privileged users */}
                  {(user?.is_super_admin || user?.permissions?.includes?.('system.config.view')) && (
                    <Link
                      to="/system-config"
                      className="flex items-center gap-3 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
                      onClick={() => setShowDropdown(false)}
                    >
                      <Settings className="w-4 h-4" />
                      System Config
                    </Link>
                  )}
                  
                  {user?.is_super_admin && (
                    <Link
                      to="/admin-dashboard"
                      className="flex items-center gap-3 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
                      onClick={() => setShowDropdown(false)}
                    >
                      <Database className="w-4 h-4" />
                      System Health
                    </Link>
                  )}
                </div>
                
                {/* Sign Out */}
                <div className="border-t border-slate-100 pt-1">
                  <button
                    onClick={() => { onLogout(); setShowDropdown(false); }}
                    className="w-full flex items-center gap-3 px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
                    data-testid="logout-btn"
                  >
                    <LogOut className="w-4 h-4" />
                    Sign out
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  );
};

// Main Layout
const Layout = () => {
  const { user, logout, token } = useAuth();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [navigation, setNavigation] = useState({ main_menu: [], admin_menu: [] });

  // Fetch navigation
  useEffect(() => {
    const fetchNavigation = async () => {
      if (!token) return;
      
      try {
        const response = await configAPI.getUserNavigation();
        setNavigation(response.data);
      } catch (err) {
        console.error('Failed to fetch navigation:', err);
        // Fallback navigation
        setNavigation({
          main_menu: [
            { id: 'dashboard', label: 'Dashboard', icon: 'LayoutDashboard', path: '/dashboard', enabled: true },
            { id: 'accounts', label: 'Accounts', icon: 'Building2', path: '/accounts', enabled: true },
            { id: 'opportunities', label: 'Opportunities', icon: 'Target', path: '/opportunities', enabled: true },
            { id: 'goals', label: 'Goals', icon: 'Award', path: '/goals', enabled: true },
            { id: 'activity', label: 'Activity', icon: 'Activity', path: '/activity', enabled: true },
            { id: 'target-progress', label: 'Target Report', icon: 'BarChart3', path: '/target-progress', enabled: true },
            { id: 'invoices', label: 'Invoices', icon: 'FileText', path: '/invoices', enabled: true },
            { id: 'kpis', label: 'KPIs', icon: 'BarChart3', path: '/kpis', enabled: true },
            { id: 'email', label: 'Email & Calendar', icon: 'Mail', path: '/my-outlook', enabled: true },
          ],
          admin_menu: user?.is_super_admin ? [
            { id: 'system-config', label: 'System Config', icon: 'Settings', path: '/admin', enabled: true },
            { id: 'integrations', label: 'Integrations', icon: 'Plug', path: '/integrations', enabled: true },
            { id: 'data-lake', label: 'Data Lake', icon: 'Database', path: '/data-lake', enabled: true },
          ] : []
        });
      }
    };

    fetchNavigation();
  }, [token, user]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="flex min-h-screen bg-slate-50">
      <Sidebar 
        isOpen={sidebarOpen} 
        onClose={() => setSidebarOpen(false)} 
        navigation={navigation}
        user={user}
      />
      <div className="flex-1 flex flex-col min-w-0">
        <Header 
          onMenuClick={() => setSidebarOpen(true)} 
          user={user}
          onLogout={handleLogout}
        />
        <main className="flex-1 p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default Layout;
