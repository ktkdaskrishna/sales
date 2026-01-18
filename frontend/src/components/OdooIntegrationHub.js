import React, { useState, useEffect, useCallback } from "react";
import api from "../services/api";
import { cn } from "../lib/utils";
import { toast } from "sonner";
import {
  Database,
  RefreshCw,
  Check,
  X,
  AlertCircle,
  Play,
  Link2,
  ArrowRight,
  Loader2,
  Save,
  Eye,
  Clock,
  CheckCircle,
  XCircle,
  ChevronRight,
  ChevronDown,
  Building2,
  Calendar,
  Zap,
  TestTube,
  History,
  Search,
  Globe,
  User,
  Key,
  Server,
  Shield,
  ArrowLeftRight,
  Sparkles,
  Info,
  ExternalLink,
  Plus,
  Trash2,
  Edit3,
  ToggleLeft,
  ToggleRight,
  GripVertical,
  Layers,
  Webhook,
  Copy,
} from "lucide-react";

// ===================== MAIN INTEGRATION HUB =====================

const OdooIntegrationHub = () => {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("api");
  const [testingConnection, setTestingConnection] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState(null);
  const [dataLakeStats, setDataLakeStats] = useState({
    raw: 0,
    canonical: 0,
    serving: 0,
    entityCounts: {},
    groups: [],
  });

  useEffect(() => {
    fetchConfig();
    fetchDataLakeStats();
  }, []);

  const fetchConfig = async () => {
    try {
      const response = await api.get("/odoo/config");
      setConfig(response.data);
      if (response.data.connection?.is_connected) {
        setConnectionStatus({ 
          success: true, 
          message: `Connected to Odoo ${response.data.connection.odoo_version}` 
        });
      }
    } catch (error) {
      console.error("Failed to fetch Odoo config:", error);
      toast.error("Failed to load Odoo configuration");
    } finally {
      setLoading(false);
    }
  };

  const handleTestConnection = async () => {
    setTestingConnection(true);
    setConnectionStatus(null);
    try {
      const response = await api.post("/odoo/test-connection");
      setConnectionStatus(response.data);
      if (response.data.success) {
        toast.success("Connection successful!");
        fetchConfig();
      } else {
        toast.error(response.data.message);
      }
    } catch (error) {
      setConnectionStatus({ 
        success: false, 
        message: error.response?.data?.detail || "Connection failed" 
      });
      toast.error("Connection test failed");
    } finally {
      setTestingConnection(false);
    }
  };

  const handleUpdateConnection = async (connectionData) => {
    try {
      await api.put("/odoo/config/connection", connectionData);
      toast.success("Connection settings saved");
      fetchConfig();
      return true;
    } catch (error) {
      toast.error("Failed to save connection settings");
      return false;
    }
  };

  const fetchDataLakeStats = async () => {
    try {
      const response = await api.get("/odoo/data-lake-stats");
      setDataLakeStats({
        raw: response.data?.raw_zone?.total_records || 0,
        canonical: response.data?.canonical_zone?.total_records || 0,
        serving: response.data?.serving_zone?.total_records || 0,
        entityCounts: response.data?.entity_counts || {},
        groups: response.data?.groups || [],
      });
    } catch (error) {
      console.error("Failed to fetch Odoo data lake stats:", error);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <Loader2 className="w-10 h-10 animate-spin text-purple-500 mx-auto mb-4" />
          <p className="text-slate-500">Loading Odoo Integration...</p>
        </div>
      </div>
    );
  }

  const tabs = [
    { id: "api", label: "API Config", icon: Globe },
    { id: "webhooks", label: "Webhooks", icon: Webhook },
    { id: "mappings", label: "Field Mapping", icon: ArrowLeftRight },
    { id: "datalake", label: "Data Lake", icon: Layers },
    { id: "sync", label: "Sync Data", icon: RefreshCw },
    { id: "logs", label: "History", icon: History },
  ];

  return (
    <div className="h-full flex flex-col bg-slate-50" data-testid="odoo-integration-hub">
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-white/20 backdrop-blur flex items-center justify-center">
              <Database className="w-7 h-7 text-white" />
            </div>
            <div>
              <h2 className="text-2xl font-bold">Odoo Integration Hub</h2>
              <p className="text-purple-100 mt-1">
                Connect your Odoo ERP to sync Contacts, Opportunities & Activities
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {config?.connection?.is_connected ? (
              <div className="flex items-center gap-2 px-4 py-2 bg-green-500/20 backdrop-blur border border-green-400/30 rounded-full">
                <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                <span className="font-medium">Connected</span>
                <span className="text-green-200">v{config.connection.odoo_version}</span>
              </div>
            ) : (
              <div className="flex items-center gap-2 px-4 py-2 bg-amber-500/20 backdrop-blur border border-amber-400/30 rounded-full">
                <AlertCircle className="w-4 h-4 text-amber-300" />
                <span className="font-medium">Not Connected</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white border-b shadow-sm">
        <div className="flex">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            const isDisabled = !["api", "webhooks"].includes(tab.id) && !config?.connection?.is_connected;
            
            return (
              <button
                key={tab.id}
                onClick={() => !isDisabled && setActiveTab(tab.id)}
                disabled={isDisabled}
                className={cn(
                  "flex-1 px-6 py-4 text-sm font-medium flex flex-col items-center gap-1 border-b-2 transition-all",
                  isActive
                    ? "border-purple-600 text-purple-600 bg-purple-50/50"
                    : isDisabled
                    ? "border-transparent text-slate-300 cursor-not-allowed"
                    : "border-transparent text-slate-500 hover:text-slate-700 hover:bg-slate-50"
                )}
                data-testid={`tab-${tab.id}`}
              >
                <Icon className={cn("w-5 h-5", isDisabled && "opacity-40")} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {activeTab === "api" && (
          <ConnectionTab
            config={config}
            onUpdate={handleUpdateConnection}
            onTest={handleTestConnection}
            testing={testingConnection}
            status={connectionStatus}
          />
        )}
        {activeTab === "webhooks" && (
          <WebhookTab config={config} />
        )}
        {activeTab === "mappings" && (
          <SimpleFieldMappingTab config={config} onRefresh={fetchConfig} />
        )}
        {activeTab === "datalake" && (
          <OdooDataLakeTab stats={dataLakeStats} />
        )}
        {activeTab === "sync" && (
          <SyncTab config={config} onRefresh={fetchConfig} />
        )}
        {activeTab === "logs" && (
          <SyncLogsTab />
        )}
      </div>
    </div>
  );
};

// ===================== CONNECTION TAB =====================

const ConnectionTab = ({ config, onUpdate, onTest, testing, status }) => {
  const [formData, setFormData] = useState({
    url: config?.connection?.url || "",
    database: config?.connection?.database || "",
    username: config?.connection?.username || "",
    api_key: "",
  });
  const [showApiKey, setShowApiKey] = useState(false);
  const [saving, setSaving] = useState(false);

  const normalizeUrl = (url) => {
    let normalized = url.trim();
    normalized = normalized.replace(/\/(odoo|web|jsonrpc)\/?$/i, "");
    normalized = normalized.replace(/\/+$/, "");
    return normalized;
  };

  const handleSave = async () => {
    if (!formData.url || !formData.database || !formData.username) {
      toast.error("Please fill in URL, Database, and Username");
      return;
    }
    
    setSaving(true);
    const normalizedData = {
      ...formData,
      url: normalizeUrl(formData.url),
    };
    
    if (!formData.api_key && config?.connection?.api_key) {
      delete normalizedData.api_key;
    }
    
    const success = await onUpdate(normalizedData);
    setSaving(false);
    
    if (success) {
      onTest();
    }
  };

  const handleQuickFill = () => {
    setFormData({
      url: "https://securadotest.odoo.com",
      database: "securadotest",
      username: "krishna@securado.net",
      api_key: "",
    });
    toast.info("Credentials pre-filled. Enter your API key to connect.");
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="bg-white rounded-2xl shadow-sm border p-6 space-y-6">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
              <Shield className="w-5 h-5 text-purple-600" />
              Odoo API Configuration
            </h3>
            <p className="text-sm text-slate-500 mt-1">
              Connect to Odoo 17, 18, or 19 using secure JSON-RPC API
            </p>
          </div>
          {!config?.connection?.is_connected && (
            <button
              onClick={handleQuickFill}
              className="text-xs bg-purple-50 text-purple-600 px-3 py-1.5 rounded-full hover:bg-purple-100 transition flex items-center gap-1"
            >
              <Sparkles className="w-3 h-3" />
              Quick Fill Demo
            </button>
          )}
        </div>

        <div className="grid gap-5">
          <div>
            <label className="flex items-center gap-2 text-sm font-medium text-slate-700 mb-2">
              <Globe className="w-4 h-4 text-slate-400" />
              Odoo Instance URL
            </label>
            <input
              type="url"
              value={formData.url}
              onChange={(e) => setFormData({ ...formData, url: e.target.value })}
              className="input w-full"
              placeholder="https://your-company.odoo.com"
              data-testid="odoo-url-input"
            />
          </div>

          <div>
            <label className="flex items-center gap-2 text-sm font-medium text-slate-700 mb-2">
              <Server className="w-4 h-4 text-slate-400" />
              Database Name
            </label>
            <input
              type="text"
              value={formData.database}
              onChange={(e) => setFormData({ ...formData, database: e.target.value })}
              className="input w-full"
              placeholder="your_database_name"
              data-testid="odoo-database-input"
            />
          </div>

          <div>
            <label className="flex items-center gap-2 text-sm font-medium text-slate-700 mb-2">
              <User className="w-4 h-4 text-slate-400" />
              Username (Email)
            </label>
            <input
              type="email"
              value={formData.username}
              onChange={(e) => setFormData({ ...formData, username: e.target.value })}
              className="input w-full"
              placeholder="admin@your-company.com"
              data-testid="odoo-username-input"
            />
          </div>

          <div>
            <label className="flex items-center gap-2 text-sm font-medium text-slate-700 mb-2">
              <Key className="w-4 h-4 text-slate-400" />
              API Key
              {config?.connection?.api_key && (
                <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
                  Saved
                </span>
              )}
            </label>
            <div className="relative">
              <input
                type={showApiKey ? "text" : "password"}
                value={formData.api_key}
                onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                className="input w-full pr-20"
                placeholder={config?.connection?.api_key ? "••••••••••••" : "Enter your Odoo API key"}
                data-testid="odoo-apikey-input"
              />
              <button
                type="button"
                onClick={() => setShowApiKey(!showApiKey)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 text-xs"
              >
                {showApiKey ? "Hide" : "Show"}
              </button>
            </div>
          </div>
        </div>

        {status && (
          <div className={cn(
            "p-4 rounded-xl flex items-start gap-3",
            status.success 
              ? "bg-green-50 border border-green-200" 
              : "bg-red-50 border border-red-200"
          )}>
            {status.success ? (
              <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0" />
            ) : (
              <XCircle className="w-5 h-5 text-red-600 flex-shrink-0" />
            )}
            <div>
              <p className={cn("font-semibold", status.success ? "text-green-800" : "text-red-800")}>
                {status.success ? "Connection Successful!" : "Connection Failed"}
              </p>
              <p className={cn("text-sm mt-0.5", status.success ? "text-green-600" : "text-red-600")}>
                {status.message}
              </p>
            </div>
          </div>
        )}

        <div className="flex gap-3 pt-2">
          <button
            onClick={handleSave}
            disabled={saving || testing}
            className="btn-primary flex-1 flex items-center justify-center gap-2 py-3"
            data-testid="save-connection-btn"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Save & Connect
          </button>
          <button
            onClick={onTest}
            disabled={testing || saving}
            className="btn-secondary flex items-center gap-2 px-6"
            data-testid="test-connection-btn"
          >
            {testing ? <Loader2 className="w-4 h-4 animate-spin" /> : <TestTube className="w-4 h-4" />}
            Test
          </button>
        </div>
      </div>

      <div className="bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200 rounded-2xl p-5">
        <h4 className="font-semibold text-blue-900 flex items-center gap-2 mb-3">
          <Key className="w-4 h-4" />
          How to Get Your Odoo API Key
        </h4>
        <ol className="text-sm text-blue-700 space-y-2">
          <li className="flex items-start gap-2">
            <span className="w-5 h-5 rounded-full bg-blue-200 text-blue-800 text-xs flex items-center justify-center flex-shrink-0 mt-0.5">1</span>
            Log in to your Odoo instance as Administrator
          </li>
          <li className="flex items-start gap-2">
            <span className="w-5 h-5 rounded-full bg-blue-200 text-blue-800 text-xs flex items-center justify-center flex-shrink-0 mt-0.5">2</span>
            Go to <strong>Settings → Users & Companies → Users</strong>
          </li>
          <li className="flex items-start gap-2">
            <span className="w-5 h-5 rounded-full bg-blue-200 text-blue-800 text-xs flex items-center justify-center flex-shrink-0 mt-0.5">3</span>
            Select your user and click <strong>Account Security</strong> tab
          </li>
          <li className="flex items-start gap-2">
            <span className="w-5 h-5 rounded-full bg-blue-200 text-blue-800 text-xs flex items-center justify-center flex-shrink-0 mt-0.5">4</span>
            Click <strong>New API Key</strong> and copy the generated key
          </li>
        </ol>
      </div>
    </div>
  );
};

// ===================== SIMPLE FIELD MAPPING TAB (USER-FRIENDLY) =====================

const SimpleFieldMappingTab = ({ config, onRefresh }) => {
  const [selectedEntity, setSelectedEntity] = useState(null);
  const [mappings, setMappings] = useState([]);
  const [saving, setSaving] = useState(false);
  const [aiMapping, setAiMapping] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingField, setEditingField] = useState(null);

  const entities = config?.entity_mappings || [];

  const entityConfig = {
    "res.partner": { icon: Building2, color: "purple", label: "Contacts & Companies" },
    "crm.lead": { icon: Zap, color: "blue", label: "Opportunities" },
    "mail.activity": { icon: Calendar, color: "amber", label: "Activities" },
  };

  useEffect(() => {
    if (selectedEntity) {
      setMappings(selectedEntity.field_mappings || []);
    }
  }, [selectedEntity]);

  const handleSelectEntity = (entity) => {
    setSelectedEntity(entity);
    setMappings(entity.field_mappings || []);
  };

  const handleToggleField = (fieldId) => {
    setMappings(mappings.map(m => 
      m.id === fieldId ? { ...m, enabled: !m.enabled } : m
    ));
  };

  const handleDeleteField = (fieldId) => {
    const field = mappings.find(m => m.id === fieldId);
    if (field?.is_system) {
      toast.error("Cannot delete system fields. You can disable them instead.");
      return;
    }
    setMappings(mappings.filter(m => m.id !== fieldId));
    toast.success("Field mapping removed");
  };

  const handleAddField = (newField) => {
    setMappings([...mappings, {
      id: `custom_${Date.now()}`,
      ...newField,
      enabled: true,
      is_system: false,
    }]);
    setShowAddModal(false);
    toast.success("Field mapping added");
  };

  const handleSave = async () => {
    if (!selectedEntity) return;
    setSaving(true);
    try {
      await api.put(`/odoo/mappings/${selectedEntity.id}/fields`, mappings);
      toast.success("Field mappings saved!");
      onRefresh();
    } catch (error) {
      toast.error("Failed to save mappings");
    } finally {
      setSaving(false);
    }
  };

  const handleAiAutoMap = async () => {
    if (!selectedEntity) return;
    setAiMapping(true);
    
    try {
      // Get entity type for API
      let entityType = "contacts";
      if (selectedEntity.local_collection?.includes("account")) entityType = "accounts";
      else if (selectedEntity.local_collection?.includes("opportunit")) entityType = "opportunities";
      else if (selectedEntity.local_collection?.includes("activit")) entityType = "activities";

      // Build source fields from current mappings
      const sourceFields = mappings.map(m => ({
        name: m.source_field,
        type: m.source_field_type || "string",
      }));

      const response = await api.post("/ai-mapping/suggest", {
        source_name: "Odoo",
        entity_type: entityType,
        source_fields: sourceFields
      });

      if (response.data.suggestions?.length > 0) {
        // Show suggestions to user
        const confirmed = window.confirm(
          `AI found ${response.data.suggestions.length} mapping suggestions:\n\n` +
          response.data.suggestions.slice(0, 5).map(s => 
            `• ${s.source_field} → ${s.target_field} (${Math.round(s.confidence * 100)}%)`
          ).join('\n') +
          (response.data.suggestions.length > 5 ? `\n... and ${response.data.suggestions.length - 5} more` : '') +
          '\n\nApply these suggestions?'
        );

        if (confirmed) {
          const updatedMappings = [...mappings];
          response.data.suggestions.forEach(suggestion => {
            const existingIdx = updatedMappings.findIndex(m => m.source_field === suggestion.source_field);
            if (existingIdx >= 0) {
              updatedMappings[existingIdx] = {
                ...updatedMappings[existingIdx],
                target_field: suggestion.target_field,
                enabled: true,
              };
            }
          });
          setMappings(updatedMappings);
          toast.success(`Applied ${response.data.suggestions.length} AI suggestions!`);
        }
      } else {
        toast.info("No new mapping suggestions found");
      }
    } catch (error) {
      console.error("AI mapping error:", error);
      toast.error("AI mapping failed");
    } finally {
      setAiMapping(false);
    }
  };

  const enabledCount = mappings.filter(m => m.enabled).length;

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Entity Selection Cards */}
      <div className="grid grid-cols-3 gap-4">
        {entities.map((entity) => {
          const cfg = entityConfig[entity.odoo_model] || { icon: Database, color: "slate", label: entity.name };
          const Icon = cfg.icon;
          const isSelected = selectedEntity?.id === entity.id;
          
          return (
            <button
              key={entity.id}
              onClick={() => handleSelectEntity(entity)}
              className={cn(
                "p-5 rounded-xl border-2 text-left transition-all hover:shadow-md",
                isSelected
                  ? "border-purple-500 bg-purple-50 shadow-md"
                  : "border-slate-200 bg-white hover:border-purple-300"
              )}
              data-testid={`entity-${entity.id}`}
            >
              <div className="flex items-start gap-3">
                <div className={cn(
                  "w-12 h-12 rounded-xl flex items-center justify-center",
                  isSelected ? "bg-purple-500 text-white" : "bg-slate-100 text-slate-500"
                )}>
                  <Icon className="w-6 h-6" />
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="font-semibold text-slate-900">{entity.name}</h4>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {entity.odoo_model} → {entity.local_collection}
                  </p>
                  <div className="flex items-center gap-2 mt-2">
                    <span className={cn(
                      "text-xs px-2 py-0.5 rounded-full",
                      entity.sync_enabled ? "bg-green-100 text-green-700" : "bg-slate-100 text-slate-500"
                    )}>
                      {entity.sync_enabled ? "Active" : "Disabled"}
                    </span>
                    <span className="text-xs text-slate-400">
                      {entity.field_mappings?.length || 0} fields
                    </span>
                  </div>
                </div>
                {isSelected && (
                  <CheckCircle className="w-5 h-5 text-purple-500 flex-shrink-0" />
                )}
              </div>
            </button>
          );
        })}
      </div>

      {/* Field Mappings Table */}
      {selectedEntity ? (
        <div className="bg-white rounded-2xl shadow-sm border overflow-hidden">
          {/* Header */}
          <div className="p-4 border-b bg-slate-50 flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-slate-900 flex items-center gap-2">
                <ArrowLeftRight className="w-5 h-5 text-purple-600" />
                {selectedEntity.name} - Field Mappings
              </h3>
              <p className="text-sm text-slate-500 mt-0.5">
                {enabledCount} of {mappings.length} fields enabled
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleAiAutoMap}
                disabled={aiMapping}
                className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 hover:from-purple-700 hover:to-indigo-700 disabled:opacity-50"
                data-testid="ai-auto-map-btn"
              >
                {aiMapping ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                AI Auto-Map
              </button>
              <button
                onClick={() => setShowAddModal(true)}
                className="btn-secondary flex items-center gap-2"
              >
                <Plus className="w-4 h-4" />
                Add Field
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="btn-primary flex items-center gap-2"
                data-testid="save-mappings-btn"
              >
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                Save
              </button>
            </div>
          </div>

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full" data-testid="field-mappings-table">
              <thead className="bg-slate-50 border-b">
                <tr>
                  <th className="text-left p-4 text-xs font-semibold text-slate-600 w-12">Enable</th>
                  <th className="text-left p-4 text-xs font-semibold text-slate-600">Odoo Field</th>
                  <th className="text-center p-4 text-xs font-semibold text-slate-600 w-16"></th>
                  <th className="text-left p-4 text-xs font-semibold text-slate-600">Local Field</th>
                  <th className="text-left p-4 text-xs font-semibold text-slate-600">Type</th>
                  <th className="text-left p-4 text-xs font-semibold text-slate-600">Transform</th>
                  <th className="text-left p-4 text-xs font-semibold text-slate-600 w-20">Flags</th>
                  <th className="text-right p-4 text-xs font-semibold text-slate-600 w-20">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {mappings.map((field) => (
                  <tr 
                    key={field.id} 
                    className={cn(
                      "hover:bg-slate-50 transition-colors",
                      !field.enabled && "opacity-50 bg-slate-50"
                    )}
                    data-testid={`field-row-${field.id}`}
                  >
                    <td className="p-4">
                      <button
                        onClick={() => handleToggleField(field.id)}
                        className={cn(
                          "w-10 h-6 rounded-full relative transition-colors",
                          field.enabled ? "bg-green-500" : "bg-slate-300"
                        )}
                        data-testid={`toggle-${field.id}`}
                      >
                        <div className={cn(
                          "w-5 h-5 bg-white rounded-full absolute top-0.5 transition-transform shadow-sm",
                          field.enabled ? "translate-x-4" : "translate-x-0.5"
                        )} />
                      </button>
                    </td>
                    <td className="p-4">
                      <div className="flex items-center gap-2">
                        <code className="text-sm font-medium text-purple-700 bg-purple-50 px-2 py-1 rounded">
                          {field.source_field}
                        </code>
                        <span className="text-xs text-slate-400">({field.source_field_type})</span>
                      </div>
                    </td>
                    <td className="p-4 text-center">
                      <ArrowRight className="w-5 h-5 text-slate-400 mx-auto" />
                    </td>
                    <td className="p-4">
                      <code className="text-sm font-medium text-blue-700 bg-blue-50 px-2 py-1 rounded">
                        {field.target_field}
                      </code>
                    </td>
                    <td className="p-4">
                      <span className="text-xs bg-slate-100 text-slate-600 px-2 py-1 rounded">
                        {field.target_field_type}
                      </span>
                    </td>
                    <td className="p-4">
                      <span className="text-xs text-slate-500">
                        {field.transform_type === "direct" ? "Direct" : field.transform_type}
                      </span>
                    </td>
                    <td className="p-4">
                      <div className="flex items-center gap-1">
                        {field.is_key_field && (
                          <span className="text-xs bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded font-medium">
                            KEY
                          </span>
                        )}
                        {field.is_required && (
                          <span className="text-xs bg-red-100 text-red-700 px-1.5 py-0.5 rounded font-medium">
                            REQ
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="p-4 text-right">
                      {!field.is_system && (
                        <button
                          onClick={() => handleDeleteField(field.id)}
                          className="p-1.5 hover:bg-red-50 rounded text-slate-400 hover:text-red-500 transition-colors"
                          title="Delete mapping"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {mappings.length === 0 && (
            <div className="p-12 text-center">
              <ArrowLeftRight className="w-12 h-12 text-slate-300 mx-auto mb-3" />
              <h4 className="font-medium text-slate-700">No Field Mappings</h4>
              <p className="text-sm text-slate-500 mt-1">
                Click &quot;Add Field&quot; or use &quot;AI Auto-Map&quot; to create mappings
              </p>
            </div>
          )}
        </div>
      ) : (
        <div className="bg-white rounded-2xl shadow-sm border p-12 text-center">
          <Database className="w-16 h-16 text-slate-300 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-slate-700">Select an Entity</h3>
          <p className="text-sm text-slate-500 mt-1">
            Choose an entity above to view and edit field mappings
          </p>
        </div>
      )}

      {/* Add Field Modal */}
      {showAddModal && (
        <AddFieldModal
          onAdd={handleAddField}
          onClose={() => setShowAddModal(false)}
        />
      )}
    </div>
  );
};

// ===================== ADD FIELD MODAL =====================

const AddFieldModal = ({ onAdd, onClose }) => {
  const [formData, setFormData] = useState({
    source_field: "",
    source_field_type: "char",
    target_field: "",
    target_field_type: "text",
    transform_type: "direct",
    is_required: false,
    is_key_field: false,
  });

  const fieldTypes = [
    { id: "text", label: "Text" },
    { id: "email", label: "Email" },
    { id: "phone", label: "Phone" },
    { id: "url", label: "URL" },
    { id: "number", label: "Number" },
    { id: "currency", label: "Currency" },
    { id: "date", label: "Date" },
    { id: "textarea", label: "Text Area" },
    { id: "dropdown", label: "Dropdown" },
  ];

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!formData.source_field || !formData.target_field) {
      toast.error("Please fill in both source and target field names");
      return;
    }
    onAdd(formData);
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-md shadow-2xl">
        <div className="p-5 border-b flex items-center justify-between">
          <h3 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
            <Plus className="w-5 h-5 text-purple-600" />
            Add Field Mapping
          </h3>
          <button onClick={onClose} className="p-1 hover:bg-slate-100 rounded-lg">
            <X className="w-5 h-5 text-slate-400" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div>
            <label className="text-sm font-medium text-slate-700">Odoo Field Name</label>
            <input
              type="text"
              value={formData.source_field}
              onChange={(e) => setFormData({ ...formData, source_field: e.target.value })}
              className="input w-full mt-1"
              placeholder="e.g., partner_name, email"
              required
            />
          </div>

          <div>
            <label className="text-sm font-medium text-slate-700">Odoo Field Type</label>
            <select
              value={formData.source_field_type}
              onChange={(e) => setFormData({ ...formData, source_field_type: e.target.value })}
              className="input w-full mt-1"
            >
              <option value="char">Character (char)</option>
              <option value="text">Text (text)</option>
              <option value="integer">Integer</option>
              <option value="float">Float</option>
              <option value="boolean">Boolean</option>
              <option value="date">Date</option>
              <option value="datetime">DateTime</option>
              <option value="many2one">Many2One (Relation)</option>
            </select>
          </div>

          <div>
            <label className="text-sm font-medium text-slate-700">Local Field Name</label>
            <input
              type="text"
              value={formData.target_field}
              onChange={(e) => setFormData({ ...formData, target_field: e.target.value })}
              className="input w-full mt-1"
              placeholder="e.g., name, email_address"
              required
            />
          </div>

          <div>
            <label className="text-sm font-medium text-slate-700">Local Field Type</label>
            <select
              value={formData.target_field_type}
              onChange={(e) => setFormData({ ...formData, target_field_type: e.target.value })}
              className="input w-full mt-1"
            >
              {fieldTypes.map(t => (
                <option key={t.id} value={t.id}>{t.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-sm font-medium text-slate-700">Transform</label>
            <select
              value={formData.transform_type}
              onChange={(e) => setFormData({ ...formData, transform_type: e.target.value })}
              className="input w-full mt-1"
            >
              <option value="direct">Direct Copy</option>
              <option value="lookup">Lookup (for relations)</option>
              <option value="format">Format/Clean</option>
            </select>
          </div>

          <div className="flex items-center gap-4 pt-2">
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={formData.is_required}
                onChange={(e) => setFormData({ ...formData, is_required: e.target.checked })}
                className="rounded border-slate-300 text-purple-600"
              />
              Required
            </label>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={formData.is_key_field}
                onChange={(e) => setFormData({ ...formData, is_key_field: e.target.checked })}
                className="rounded border-slate-300 text-purple-600"
              />
              Key Field
            </label>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t">
            <button type="button" onClick={onClose} className="btn-secondary">
              Cancel
            </button>
            <button type="submit" className="btn-primary">
              Add Mapping
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// ===================== SYNC TAB =====================

const SyncTab = ({ config, onRefresh }) => {
  const [syncing, setSyncing] = useState({});
  const [previewing, setPreviewing] = useState({});
  const [previewData, setPreviewData] = useState({});

  const handleSync = async (mappingId) => {
    setSyncing({ ...syncing, [mappingId]: true });
    try {
      const response = await api.post(`/odoo/sync/${mappingId}`);
      const result = response.data;
      toast.success(
        `Sync complete: ${result.created} created, ${result.updated} updated` +
        (result.failed > 0 ? `, ${result.failed} failed` : "")
      );
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Sync failed");
    } finally {
      setSyncing({ ...syncing, [mappingId]: false });
    }
  };

  const handleSyncAll = async () => {
    setSyncing({ all: true });
    try {
      // Use the correct sync endpoint
      const response = await api.post("/integrations/sync/odoo", {
        entity_types: ["account", "opportunity", "contact", "order", "invoice"]
      });
      if (response.data.job_id) {
        toast.success(`Sync job started! Job ID: ${response.data.job_id}`);
        // Wait for sync to complete
        setTimeout(() => {
          onRefresh();
        }, 5000);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || "Sync failed");
    } finally {
      setSyncing({ all: false });
    }
  };

  const handlePreview = async (mappingId) => {
    setPreviewing({ ...previewing, [mappingId]: true });
    try {
      const response = await api.get(`/odoo/preview/${mappingId}?limit=3`);
      setPreviewData({ ...previewData, [mappingId]: response.data });
    } catch (error) {
      toast.error(error.response?.data?.detail || "Preview failed");
    } finally {
      setPreviewing({ ...previewing, [mappingId]: false });
    }
  };

  const mappings = config?.entity_mappings || [];
  const entityIcons = {
    "res.partner": Building2,
    "crm.lead": Zap,
    "mail.activity": Calendar,
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Sync All Card */}
      <div className="bg-gradient-to-r from-purple-600 to-indigo-600 rounded-2xl p-6 text-white">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xl font-bold flex items-center gap-2">
              <RefreshCw className="w-5 h-5" />
              Full Synchronization
            </h3>
            <p className="text-purple-100 mt-1">
              Sync all enabled entities from Odoo to your local database
            </p>
          </div>
          <button
            onClick={handleSyncAll}
            disabled={syncing.all || !config?.connection?.is_connected}
            className="bg-white text-purple-600 hover:bg-purple-50 px-6 py-3 rounded-xl font-semibold flex items-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            data-testid="sync-all-btn"
          >
            {syncing.all ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Play className="w-5 h-5" />
            )}
            Sync All Now
          </button>
        </div>
      </div>

      {/* Individual Entity Sync Cards */}
      {mappings.map((mapping) => {
        const Icon = entityIcons[mapping.odoo_model] || Database;
        const preview = previewData[mapping.id];
        
        return (
          <div key={mapping.id} className="bg-white rounded-2xl shadow-sm border overflow-hidden">
            <div className="p-5 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className={cn(
                  "w-12 h-12 rounded-xl flex items-center justify-center",
                  mapping.sync_enabled ? "bg-purple-100" : "bg-slate-100"
                )}>
                  <Icon className={cn(
                    "w-6 h-6",
                    mapping.sync_enabled ? "text-purple-600" : "text-slate-400"
                  )} />
                </div>
                <div>
                  <h4 className="font-semibold text-slate-900">{mapping.name}</h4>
                  <p className="text-sm text-slate-500">
                    {mapping.odoo_model} → {mapping.local_collection}
                  </p>
                  {mapping.last_sync_at && (
                    <p className="text-xs text-slate-400 flex items-center gap-1 mt-1">
                      <Clock className="w-3 h-3" />
                      Last sync: {new Date(mapping.last_sync_at).toLocaleString()}
                    </p>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => handlePreview(mapping.id)}
                  disabled={previewing[mapping.id] || !config?.connection?.is_connected}
                  className="btn-secondary flex items-center gap-2"
                  data-testid={`preview-btn-${mapping.id}`}
                >
                  {previewing[mapping.id] ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Eye className="w-4 h-4" />
                  )}
                  Preview
                </button>
                <button
                  onClick={() => handleSync(mapping.id)}
                  disabled={syncing[mapping.id] || !mapping.sync_enabled || !config?.connection?.is_connected}
                  className="btn-primary flex items-center gap-2"
                  data-testid={`sync-btn-${mapping.id}`}
                >
                  {syncing[mapping.id] ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Play className="w-4 h-4" />
                  )}
                  Sync Now
                </button>
              </div>
            </div>

            {/* Preview Data */}
            {preview && (
              <div className="border-t bg-slate-50 p-5">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <Eye className="w-4 h-4 text-slate-500" />
                    <span className="font-medium text-slate-700">Preview Data</span>
                    <span className="text-sm text-slate-500">
                      ({preview.total_in_odoo} total records)
                    </span>
                  </div>
                  <button 
                    onClick={() => setPreviewData({ ...previewData, [mapping.id]: null })} 
                    className="text-slate-400 hover:text-slate-600 p-1"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
                <div className="space-y-3">
                  {preview.preview?.map((item, idx) => (
                    <div key={idx} className="bg-white p-4 rounded-xl border">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <p className="text-xs font-semibold text-purple-700 mb-2">Odoo Data</p>
                          <pre className="text-xs text-slate-600 bg-purple-50 p-2 rounded overflow-x-auto max-h-32">
                            {JSON.stringify(item.odoo, null, 2)}
                          </pre>
                        </div>
                        <div>
                          <p className="text-xs font-semibold text-blue-700 mb-2">Mapped Data</p>
                          <pre className="text-xs text-slate-600 bg-blue-50 p-2 rounded overflow-x-auto max-h-32">
                            {JSON.stringify(item.mapped, null, 2)}
                          </pre>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

// ===================== SYNC LOGS TAB =====================

const SyncLogsTab = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchLogs();
  }, []);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const response = await api.get("/odoo/sync-logs?limit=50");
      setLogs(response.data);
    } catch (error) {
      toast.error("Failed to load sync logs");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-purple-400" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white rounded-2xl shadow-sm border overflow-hidden">
        <div className="p-4 border-b flex items-center justify-between bg-slate-50">
          <h3 className="font-semibold text-slate-900 flex items-center gap-2">
            <History className="w-4 h-4 text-slate-500" />
            Sync History
          </h3>
          <button onClick={fetchLogs} className="btn-secondary text-sm flex items-center gap-1.5">
            <RefreshCw className="w-4 h-4" /> Refresh
          </button>
        </div>
        <div className="divide-y">
          {logs.length === 0 ? (
            <div className="p-12 text-center">
              <History className="w-12 h-12 text-slate-300 mx-auto mb-3" />
              <h4 className="font-medium text-slate-700">No Sync History</h4>
              <p className="text-sm text-slate-500 mt-1">
                Logs will appear here after syncing
              </p>
            </div>
          ) : (
            logs.map((log) => (
              <div key={log.id} className="p-4 hover:bg-slate-50">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={cn(
                      "w-10 h-10 rounded-full flex items-center justify-center",
                      log.status === "success" ? "bg-green-100" : log.status === "failed" ? "bg-red-100" : "bg-amber-100"
                    )}>
                      {log.status === "success" ? (
                        <CheckCircle className="w-5 h-5 text-green-600" />
                      ) : log.status === "failed" ? (
                        <XCircle className="w-5 h-5 text-red-600" />
                      ) : (
                        <AlertCircle className="w-5 h-5 text-amber-600" />
                      )}
                    </div>
                    <div>
                      <p className="font-medium text-slate-900">{log.entity_mapping_id}</p>
                      <p className="text-xs text-slate-500">
                        {new Date(log.started_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="flex items-center gap-3 text-sm">
                      <span className="text-green-600 font-medium">+{log.records_created}</span>
                      <span className="text-blue-600 font-medium">~{log.records_updated}</span>
                      {log.records_failed > 0 && (
                        <span className="text-red-600 font-medium">!{log.records_failed}</span>
                      )}
                    </div>
                    <p className="text-xs text-slate-400">{log.records_processed} processed</p>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default OdooIntegrationHub;
