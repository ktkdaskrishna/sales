/**
 * Integrations Page
 * Manage all ERP integrations (Odoo, Salesforce, etc.)
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { integrationsAPI } from '../services/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import {
  Plug2,
  Settings,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Play,
  AlertCircle,
  Wand2,
  Save,
  ChevronRight,
  Webhook,
  Clock,
  Database,
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '../components/ui/dialog';

// Entity types available for Odoo sync
const ODOO_ENTITY_TYPES = [
  { id: 'account', label: 'Accounts', description: 'Companies/Organizations' },
  { id: 'contact', label: 'Contacts', description: 'People/Individuals' },
  { id: 'opportunity', label: 'Opportunities', description: 'CRM Leads/Deals' },
  { id: 'order', label: 'Orders', description: 'Sales Orders' },
  { id: 'invoice', label: 'Invoices', description: 'Customer Invoices' },
];

// Entity types available for O365 sync
const O365_ENTITY_TYPES = [
  { id: 'email', label: 'Emails', description: 'Outlook inbox/sent emails' },
  { id: 'calendar', label: 'Calendar Events', description: 'Meetings & appointments' },
  { id: 'outlook_contact', label: 'Outlook Contacts', description: 'Address book contacts' },
  { id: 'onedrive', label: 'OneDrive Files', description: 'Documents & attachments' },
];

const Integrations = () => {
  const navigate = useNavigate();
  
  // Redirect to Admin Panel - this page is deprecated
  useEffect(() => {
    const timer = setTimeout(() => {
      navigate('/admin?tab=integrations');
    }, 5000);
    return () => clearTimeout(timer);
  }, [navigate]);

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-8">
      <div className="max-w-2xl w-full bg-white rounded-2xl shadow-xl border border-slate-200 p-8 text-center">
        <div className="w-16 h-16 rounded-full bg-amber-100 flex items-center justify-center mx-auto mb-4">
          <AlertCircle className="w-8 h-8 text-amber-600" />
        </div>
        <h2 className="text-2xl font-bold text-slate-900 mb-3">Page Moved</h2>
        <p className="text-slate-600 mb-6">
          Integrations management has been moved to the Admin Panel for better organization.
        </p>
        <p className="text-sm text-slate-500 mb-6">
          You will be redirected automatically in 5 seconds...
        </p>
        <Button 
          onClick={() => navigate('/admin?tab=integrations')}
          className="btn-primary"
        >
          <ChevronRight className="w-4 h-4 mr-2" />
          Go to Admin Panel → Integrations
        </Button>
      </div>
    </div>
  );
};

const IntegrationsOLD = () => {
  const navigate = useNavigate();
  const [integrations, setIntegrations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedIntegration, setSelectedIntegration] = useState(null);
  const [configModal, setConfigModal] = useState(false);
  const [syncModal, setSyncModal] = useState(false);
  const [webhookModal, setWebhookModal] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [saving, setSaving] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncIntegrationType, setSyncIntegrationType] = useState(null);
  
  // Selected entities for sync
  const [selectedEntities, setSelectedEntities] = useState(['account', 'opportunity']);

  // Odoo config form
  const [odooConfig, setOdooConfig] = useState({
    url: '',
    database: '',
    username: '',
    api_key: '',
  });

  // O365 config form
  const [o365Config, setO365Config] = useState({
    client_id: '',
    tenant_id: '',
    client_secret: '',
  });
  const [o365ConfigModal, setO365ConfigModal] = useState(false);

  useEffect(() => {
    fetchIntegrations();
  }, []);

  const fetchIntegrations = async () => {
    setLoading(true);
    try {
      const response = await integrationsAPI.list();
      setIntegrations(response.data);
    } catch (error) {
      console.error('Failed to fetch integrations:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleConfigureOdoo = () => {
    setSelectedIntegration('odoo');
    setConfigModal(true);
    setTestResult(null);
  };

  const handleConfigureO365 = () => {
    setSelectedIntegration('ms365');
    setO365ConfigModal(true);
    setTestResult(null);
  };

  // Helper function to extract error message from API response
  const getErrorMessage = (error, defaultMsg = 'An error occurred') => {
    const detail = error.response?.data?.detail;
    if (!detail) return defaultMsg;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      // Pydantic validation errors
      return detail.map(e => e.msg || e.message || JSON.stringify(e)).join(', ');
    }
    if (typeof detail === 'object') {
      return detail.msg || detail.message || JSON.stringify(detail);
    }
    return defaultMsg;
  };

  const handleTestO365Connection = async () => {
    setTestResult({ testing: true });
    try {
      const response = await integrationsAPI.testO365(o365Config);
      setTestResult(response.data);
    } catch (error) {
      setTestResult({
        success: false,
        message: getErrorMessage(error, 'Connection test failed'),
      });
    }
  };

  const handleSaveO365Config = async () => {
    setSaving(true);
    try {
      await integrationsAPI.configureO365(o365Config);
      toast.success('Microsoft 365 configured successfully!');
      setO365ConfigModal(false);
      setTestResult(null);
      await fetchIntegrations();
    } catch (error) {
      console.error('Failed to save O365 config:', error);
      toast.error(getErrorMessage(error, 'Failed to save configuration'));
    } finally {
      setSaving(false);
    }
  };

  const handleTestConnection = async () => {
    setTestResult({ testing: true });
    try {
      const response = await integrationsAPI.testOdoo(odooConfig);
      setTestResult(response.data);
    } catch (error) {
      setTestResult({
        success: false,
        message: getErrorMessage(error, 'Connection test failed'),
      });
    }
  };

  const handleSaveConfig = async () => {
    setSaving(true);
    try {
      await integrationsAPI.configureOdoo({
        ...odooConfig,
        enabled_entities: selectedEntities,
      });
      toast.success('Odoo integration configured successfully!');
      setConfigModal(false);
      setTestResult(null);
      // Refresh integrations list
      await fetchIntegrations();
    } catch (error) {
      console.error('Failed to save config:', error);
      toast.error(getErrorMessage(error, 'Failed to save configuration'));
    } finally {
      setSaving(false);
    }
  };

  const handleOpenSyncModal = (integrationType) => {
    setSyncIntegrationType(integrationType);
    // Set default selected entities based on integration type
    if (integrationType === 'odoo') {
      setSelectedEntities(['account', 'opportunity']);
    } else if (integrationType === 'ms365') {
      setSelectedEntities(['email', 'calendar']);
    }
    setSyncModal(true);
  };

  const handleTriggerSync = async () => {
    if (selectedEntities.length === 0) {
      toast.error('Please select at least one entity type to sync');
      return;
    }
    
    setSyncing(true);
    try {
      const intType = syncIntegrationType || 'odoo';
      toast.info(`Starting ${intType} sync for ${selectedEntities.length} entity types...`);
      const response = await integrationsAPI.triggerSync(
        intType,
        selectedEntities
      );
      toast.success(`Sync job started: ${response.data.job_id}`);
      setSyncModal(false);
      // Refresh to show updated status
      await fetchIntegrations();
    } catch (error) {
      console.error('Failed to trigger sync:', error);
      toast.error(getErrorMessage(error, 'Failed to start sync'));
    } finally {
      setSyncing(false);
    }
  };

  const toggleEntity = (entityId) => {
    setSelectedEntities(prev => 
      prev.includes(entityId)
        ? prev.filter(e => e !== entityId)
        : [...prev, entityId]
    );
  };

  const getIntegrationDetails = (type) => {
    const details = {
      odoo: {
        name: 'Odoo ERP',
        description: 'Connect to Odoo 16+ for accounts, opportunities, orders, and invoices.',
        color: 'purple',
      },
      salesforce: {
        name: 'Salesforce',
        description: 'Sync with Salesforce CRM for unified sales data.',
        color: 'blue',
      },
      ms365: {
        name: 'Microsoft 365',
        description: 'SSO authentication and calendar integration.',
        color: 'cyan',
      },
      hubspot: {
        name: 'HubSpot',
        description: 'Marketing and sales automation integration.',
        color: 'orange',
      },
    };
    return details[type] || { name: type, description: '', color: 'zinc' };
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Integrations</h1>
          <p className="text-zinc-400 mt-1">Connect and manage your ERP systems</p>
        </div>
        <Button
          onClick={fetchIntegrations}
          variant="outline"
          className="border-zinc-700 text-zinc-300 hover:bg-zinc-800"
        >
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="w-8 h-8 text-zinc-500 animate-spin" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {integrations.map((integration) => {
            const details = getIntegrationDetails(integration.integration_type);
            return (
              <div
                key={integration.id}
                className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-6"
                data-testid={`integration-panel-${integration.integration_type}`}
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className={`p-3 rounded-xl bg-${details.color}-500/10`}>
                      <Plug2 className={`w-6 h-6 text-${details.color}-500`} />
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-white">{details.name}</h3>
                      <p className="text-zinc-500 text-sm">{details.description}</p>
                    </div>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                    integration.enabled 
                      ? 'bg-emerald-500/10 text-emerald-400' 
                      : 'bg-zinc-500/10 text-zinc-400'
                  }`}>
                    {integration.enabled ? 'Connected' : 'Not Connected'}
                  </span>
                </div>

                {/* Status Info */}
                <div className="bg-zinc-800/50 rounded-lg p-4 mb-4">
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-zinc-500">Status</p>
                      <p className="text-white capitalize">{integration.sync_status}</p>
                    </div>
                    <div>
                      <p className="text-zinc-500">Last Sync</p>
                      <p className="text-white">
                        {integration.last_sync 
                          ? new Date(integration.last_sync).toLocaleString()
                          : 'Never'
                        }
                      </p>
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex gap-3">
                  {integration.integration_type === 'odoo' && (
                    <>
                      <Button
                        onClick={handleConfigureOdoo}
                        className="flex-1 bg-purple-600 hover:bg-purple-500"
                        data-testid="configure-odoo-btn"
                      >
                        <Settings className="w-4 h-4 mr-2" />
                        Configure
                      </Button>
                      <Button
                        onClick={() => navigate('/field-mapping')}
                        variant="outline"
                        className="border-zinc-700 text-zinc-300 hover:bg-zinc-800"
                        data-testid="field-mapping-btn"
                      >
                        <Wand2 className="w-4 h-4 mr-2" />
                        Mapping
                      </Button>
                    </>
                  )}
                  {integration.integration_type === 'ms365' && (
                    <Button
                      onClick={handleConfigureO365}
                      className="flex-1 bg-cyan-600 hover:bg-cyan-500"
                      data-testid="configure-o365-btn"
                    >
                      <Settings className="w-4 h-4 mr-2" />
                      Configure
                    </Button>
                  )}
                  {integration.enabled && (
                    <Button
                      onClick={() => handleOpenSyncModal(integration.integration_type)}
                      variant="outline"
                      className="border-emerald-700 text-emerald-400 hover:bg-emerald-900/30"
                      data-testid={`sync-${integration.integration_type}-btn`}
                    >
                      <Play className="w-4 h-4 mr-2" />
                      Sync Now
                    </Button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Odoo Configuration Modal */}
      <Dialog open={configModal} onOpenChange={setConfigModal}>
        <DialogContent className="bg-zinc-900 border-zinc-800 max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-white">Configure Odoo Integration</DialogTitle>
            <DialogDescription className="text-zinc-400">
              Connect to your Odoo instance using REST API credentials
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 mt-2">
            <div className="space-y-2">
              <Label className="text-zinc-300">Odoo URL</Label>
              <Input
                value={odooConfig.url}
                onChange={(e) => setOdooConfig({ ...odooConfig, url: e.target.value })}
                placeholder="https://yourcompany.odoo.com"
                className="bg-zinc-800 border-zinc-700 text-white"
                data-testid="odoo-url-input"
              />
              <p className="text-xs text-zinc-500">Base URL only. No /web or /odoo suffix needed.</p>
            </div>

            <div className="space-y-2">
              <Label className="text-zinc-300">Database Name</Label>
              <Input
                value={odooConfig.database}
                onChange={(e) => setOdooConfig({ ...odooConfig, database: e.target.value })}
                placeholder="yourcompany"
                className="bg-zinc-800 border-zinc-700 text-white"
                data-testid="odoo-database-input"
              />
              <p className="text-xs text-zinc-500">Usually your subdomain (e.g., &quot;securadotest&quot;)</p>
            </div>

            <div className="space-y-2">
              <Label className="text-zinc-300">Username / Email</Label>
              <Input
                value={odooConfig.username}
                onChange={(e) => setOdooConfig({ ...odooConfig, username: e.target.value })}
                placeholder="admin@yourcompany.com"
                className="bg-zinc-800 border-zinc-700 text-white"
                data-testid="odoo-username-input"
              />
            </div>

            <div className="space-y-2">
              <Label className="text-zinc-300">API Key</Label>
              <Input
                type="password"
                value={odooConfig.api_key}
                onChange={(e) => setOdooConfig({ ...odooConfig, api_key: e.target.value })}
                placeholder="••••••••••••••••"
                className="bg-zinc-800 border-zinc-700 text-white"
                data-testid="odoo-apikey-input"
              />
              <p className="text-xs text-zinc-500">Generate in Odoo: Settings → Users → API Keys</p>
            </div>

            {/* Test Result */}
            {testResult && (
              <div className={`p-3 rounded-lg ${
                testResult.testing 
                  ? 'bg-zinc-800 border border-zinc-700'
                  : testResult.success 
                    ? 'bg-emerald-500/10 border border-emerald-500/20'
                    : 'bg-red-500/10 border border-red-500/20'
              }`}>
                {testResult.testing ? (
                  <div className="flex items-center gap-2 text-zinc-400 text-sm">
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Testing connection...
                  </div>
                ) : testResult.success ? (
                  <div className="flex items-center gap-2 text-emerald-400 text-sm">
                    <CheckCircle2 className="w-4 h-4" />
                    {testResult.message}
                  </div>
                ) : (
                  <div className="flex items-start gap-2 text-red-400 text-sm">
                    <XCircle className="w-4 h-4 mt-0.5 shrink-0" />
                    <span>{testResult.message}</span>
                  </div>
                )}
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-3 pt-2">
              <Button
                onClick={handleTestConnection}
                variant="outline"
                className="flex-1 border-zinc-700 text-zinc-300 hover:bg-zinc-800"
                data-testid="test-odoo-connection-btn"
              >
                <AlertCircle className="w-4 h-4 mr-2" />
                Test
              </Button>
              <Button
                onClick={handleSaveConfig}
                disabled={saving || !testResult?.success}
                className="flex-1 bg-emerald-600 hover:bg-emerald-500 disabled:bg-zinc-700 disabled:text-zinc-500"
                data-testid="save-odoo-config-btn"
              >
                {saving ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                Save
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Sync Entity Selection Modal */}
      <Dialog open={syncModal} onOpenChange={setSyncModal}>
        <DialogContent className="bg-zinc-900 border-zinc-800 max-w-md">
          <DialogHeader>
            <DialogTitle className="text-white flex items-center gap-2">
              <Database className={`w-5 h-5 ${syncIntegrationType === 'ms365' ? 'text-cyan-500' : 'text-emerald-500'}`} />
              {syncIntegrationType === 'ms365' ? 'Select O365 Data to Sync' : 'Select Entities to Sync'}
            </DialogTitle>
            <DialogDescription className="text-zinc-400">
              {syncIntegrationType === 'ms365' 
                ? 'Choose which Microsoft 365 data to synchronize with your CRM'
                : 'Choose which Odoo objects to synchronize with your Data Lake'}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 mt-4">
            {(syncIntegrationType === 'ms365' ? O365_ENTITY_TYPES : ODOO_ENTITY_TYPES).map((entity) => (
              <div
                key={entity.id}
                onClick={() => toggleEntity(entity.id)}
                className={`p-3 rounded-lg border cursor-pointer transition-all ${
                  selectedEntities.includes(entity.id)
                    ? syncIntegrationType === 'ms365' 
                      ? 'bg-cyan-500/10 border-cyan-500/30'
                      : 'bg-emerald-500/10 border-emerald-500/30'
                    : 'bg-zinc-800/50 border-zinc-700 hover:border-zinc-600'
                }`}
                data-testid={`entity-toggle-${entity.id}`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className={`font-medium ${
                      selectedEntities.includes(entity.id) 
                        ? syncIntegrationType === 'ms365' ? 'text-cyan-400' : 'text-emerald-400' 
                        : 'text-white'
                    }`}>
                      {entity.label}
                    </p>
                    <p className="text-xs text-zinc-500">{entity.description}</p>
                  </div>
                  <div className={`w-5 h-5 rounded-md border-2 flex items-center justify-center ${
                    selectedEntities.includes(entity.id)
                      ? syncIntegrationType === 'ms365' 
                        ? 'bg-cyan-500 border-cyan-500'
                        : 'bg-emerald-500 border-emerald-500'
                      : 'border-zinc-600'
                  }`}>
                    {selectedEntities.includes(entity.id) && (
                      <CheckCircle2 className="w-3 h-3 text-white" />
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {syncIntegrationType === 'ms365' && (
            <div className="bg-cyan-500/10 border border-cyan-500/20 rounded-lg p-3 mt-4">
              <p className="text-xs text-cyan-400">
                Note: O365 sync requires user to be logged in with Microsoft SSO to access their data.
              </p>
            </div>
          )}

          <div className="flex gap-3 mt-4 pt-4 border-t border-zinc-800">
            <Button
              onClick={() => setSyncModal(false)}
              variant="outline"
              className="flex-1 border-zinc-700 text-zinc-300 hover:bg-zinc-800"
            >
              Cancel
            </Button>
            <Button
              onClick={handleTriggerSync}
              disabled={syncing || selectedEntities.length === 0}
              className={`flex-1 disabled:bg-zinc-700 disabled:text-zinc-500 ${
                syncIntegrationType === 'ms365' 
                  ? 'bg-cyan-600 hover:bg-cyan-500'
                  : 'bg-emerald-600 hover:bg-emerald-500'
              }`}
              data-testid="start-sync-btn"
            >
              {syncing ? (
                <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Play className="w-4 h-4 mr-2" />
              )}
              Start Sync ({selectedEntities.length})
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Microsoft 365 Configuration Modal */}
      <Dialog open={o365ConfigModal} onOpenChange={setO365ConfigModal}>
        <DialogContent className="bg-zinc-900 border-zinc-800 max-w-lg max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-white flex items-center gap-2">
              <Settings className="w-5 h-5 text-cyan-500" />
              Microsoft 365 Configuration
            </DialogTitle>
            <DialogDescription className="text-zinc-400">
              Enter your Azure AD app credentials for SSO, Email, and Calendar integration
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 mt-4">
            {/* Client ID */}
            <div className="space-y-2">
              <Label htmlFor="client_id" className="text-zinc-300">Application (Client) ID *</Label>
              <Input
                id="client_id"
                value={o365Config.client_id}
                onChange={(e) => setO365Config({ ...o365Config, client_id: e.target.value })}
                placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                className="bg-zinc-800 border-zinc-700 text-white font-mono text-sm"
                data-testid="o365-clientid-input"
              />
              <p className="text-xs text-zinc-500">Found on Azure Portal → App registrations → Overview</p>
            </div>

            {/* Tenant ID */}
            <div className="space-y-2">
              <Label htmlFor="tenant_id" className="text-zinc-300">Directory (Tenant) ID *</Label>
              <Input
                id="tenant_id"
                value={o365Config.tenant_id}
                onChange={(e) => setO365Config({ ...o365Config, tenant_id: e.target.value })}
                placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                className="bg-zinc-800 border-zinc-700 text-white font-mono text-sm"
                data-testid="o365-tenantid-input"
              />
              <p className="text-xs text-zinc-500">Found on Azure Portal → App registrations → Overview</p>
            </div>

            {/* Client Secret */}
            <div className="space-y-2">
              <Label htmlFor="client_secret" className="text-zinc-300">Client Secret *</Label>
              <Input
                id="client_secret"
                type="password"
                value={o365Config.client_secret}
                onChange={(e) => setO365Config({ ...o365Config, client_secret: e.target.value })}
                placeholder="••••••••••••••••"
                className="bg-zinc-800 border-zinc-700 text-white"
                data-testid="o365-secret-input"
              />
              <p className="text-xs text-zinc-500">Found on Azure Portal → Certificates & secrets</p>
            </div>

            {/* Features Info */}
            <div className="bg-cyan-500/10 border border-cyan-500/20 rounded-lg p-4">
              <h4 className="text-cyan-400 font-medium mb-2">Features Enabled</h4>
              <ul className="text-sm text-zinc-400 space-y-1">
                <li>✓ Single Sign-On (SSO) with Microsoft Account</li>
                <li>✓ Email sync from Outlook to CRM</li>
                <li>✓ Calendar event synchronization</li>
                <li>✓ OneDrive document attachments</li>
              </ul>
            </div>

            {/* Test Result */}
            {testResult && (
              <div className={`p-3 rounded-lg ${
                testResult.testing 
                  ? 'bg-zinc-800 border border-zinc-700'
                  : testResult.success 
                    ? 'bg-emerald-500/10 border border-emerald-500/20'
                    : 'bg-red-500/10 border border-red-500/20'
              }`}>
                {testResult.testing ? (
                  <div className="flex items-center gap-2 text-zinc-400 text-sm">
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Testing connection...
                  </div>
                ) : testResult.success ? (
                  <div className="flex items-center gap-2 text-emerald-400 text-sm">
                    <CheckCircle2 className="w-4 h-4" />
                    {testResult.message}
                  </div>
                ) : (
                  <div className="flex items-start gap-2 text-red-400 text-sm">
                    <XCircle className="w-4 h-4 mt-0.5 shrink-0" />
                    <span>{testResult.message}</span>
                  </div>
                )}
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-3 pt-2">
              <Button
                onClick={handleTestO365Connection}
                variant="outline"
                className="flex-1 border-zinc-700 text-zinc-300 hover:bg-zinc-800"
                disabled={!o365Config.client_id || !o365Config.tenant_id || !o365Config.client_secret}
                data-testid="test-o365-connection-btn"
              >
                <AlertCircle className="w-4 h-4 mr-2" />
                Test
              </Button>
              <Button
                onClick={handleSaveO365Config}
                disabled={saving || !testResult?.success}
                className="flex-1 bg-cyan-600 hover:bg-cyan-500 disabled:bg-zinc-700 disabled:text-zinc-500"
                data-testid="save-o365-config-btn"
              >
                {saving ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                Save
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Integrations;
