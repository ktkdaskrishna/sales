# 🏗️ Unified Admin Architecture - Enterprise Integration Platform

**Version:** 2.0  
**Date:** January 18, 2026  
**Status:** Architecture Design  
**Scope:** 2-3 Week Implementation

---

## 🎯 EXECUTIVE SUMMARY

Transform the Sales Intelligence Platform into a **Unified Enterprise Integration Platform** with:
- XSOAR-style integration marketplace
- Centralized LLM and AI configuration
- Per-person incentives and targets
- Single admin console for all configuration
- Production-grade webhook handling

**Timeline:** 2-3 weeks  
**Estimated Effort:** 80-120 hours  
**Impact:** High - Foundation for enterprise scalability

---

## 🏛️ TARGET ARCHITECTURE

### **Unified Admin Console (Single Source of Truth)**

```
┌─────────────────────────────────────────────────────────────┐
│              SUPER ADMIN CONSOLE (/admin)                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  [Users] [Roles] [Integrations] [AI & LLM] [Incentives]    │
│  [Targets] [Webhooks] [Marketplace] [System Config]         │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ INTEGRATIONS SECTION                                │   │
│  │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │   │
│  │ │ Odoo        │ │ Salesforce  │ │ + Install   │   │   │
│  │ │ Connected   │ │ Available   │ │ Integration │   │   │
│  │ │ • API Sync  │ │             │ │             │   │   │
│  │ │ • Webhooks  │ │             │ │             │   │   │
│  │ │ • Mapping   │ │             │ │             │   │   │
│  │ └─────────────┘ └─────────────┘ └─────────────┘   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ AI & LLM CONFIGURATION                              │   │
│  │ Provider: OpenAI | Model: gpt-4 | API Key: ****    │   │
│  │ Features: Deal Confidence, Field Mapping, Chat      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ INCENTIVES & TARGETS                                │   │
│  │ Default Base Rate: 1%                               │   │
│  │ Per-User Overrides: Enabled                         │   │
│  │ Target Assignment: Per-Person (Manager Delegated)   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 📐 DETAILED ARCHITECTURE

### **1. Integration Module (Unified)**

**Location:** `backend/integrations/`

**Structure:**
```
backend/integrations/
├── base/
│   ├── __init__.py
│   ├── integration.py          # Base Integration class
│   ├── connector.py            # Base Connector interface
│   └── mapper.py               # Base Mapper interface
├── registry/
│   ├── __init__.py
│   ├── registry.py             # Integration Registry
│   └── marketplace.py          # Marketplace loader
├── odoo/
│   ├── __init__.py
│   ├── integration.py          # OdooIntegration (extends BaseIntegration)
│   ├── connector.py            # OdooConnector (API client)
│   ├── webhook.py              # Webhook handler
│   ├── mapper.py               # Field mapper
│   └── manifest.json           # Integration metadata
└── templates/
    └── integration_template/   # Starter template for new integrations
```

**BaseIntegration Interface:**
```python
class BaseIntegration:
    \"\"\"Base class for all integrations\"\"\"
    
    def __init__(self, config: Dict):
        self.config = config
        self.connector = None
        self.mapper = None
    
    async def connect(self) -> bool:
        \"\"\"Establish connection to external system\"\"\"
        raise NotImplementedError
    
    async def fetch_records(self, entity_type: str) -> List[Dict]:
        \"\"\"Fetch records from external system\"\"\"
        raise NotImplementedError
    
    async def webhook_handler(self, payload: Dict) -> Dict:
        \"\"\"Handle incoming webhook\"\"\"
        raise NotImplementedError
    
    def map_to_canonical(self, record: Dict, entity_type: str) -> Dict:
        \"\"\"Map to canonical format\"\"\"
        raise NotImplementedError
    
    def get_manifest(self) -> Dict:
        \"\"\"Return integration metadata\"\"\"
        raise NotImplementedError
```

---

### **2. Integration Registry**

**Purpose:** Central registry of all integrations

**Storage:** `system_config.integrations`

**Schema:**
```javascript
{
  "_id": ObjectId("..."),
  "integrations": [
    {
      "id": "odoo-v19",
      "name": "Odoo ERP",
      "type": "crm",
      "version": "19.0",
      "status": "active",
      "config": {
        "url": "https://your-odoo.com",
        "api_key": "encrypted",
        "webhook_secret": "encrypted"
      },
      "capabilities": {
        "api_sync": true,
        "webhooks": true,
        "field_mapping": true
      },
      "entities": ["account", "opportunity", "invoice", "activity"],
      "mappings": {
        "opportunity": {
          "partner_id": {"target": "account_id", "transform": "extract_id"},
          "user_id": {"target": "owner_id", "transform": "extract_id"}
        }
      },
      "installed_at": "2026-01-18T...",
      "installed_by": "admin_uuid"
    }
  ]
}
```

**API:**
```
GET /api/integrations/registry
POST /api/integrations/install
PUT /api/integrations/{id}/configure
DELETE /api/integrations/{id}/uninstall
```

---

### **3. LLM Configuration (Centralized)**

**Storage:** `system_config.llm`

**Schema:**
```javascript
{
  "provider": "openai",
  "base_url": "https://api.openai.com/v1",
  "api_key": "encrypted_key",
  "default_model": "gpt-4",
  "features": {
    "deal_confidence": {
      "enabled": true,
      "model": "gpt-4",
      "temperature": 0.7
    },
    "field_mapping": {
      "enabled": true,
      "model": "gpt-4",
      "confidence_threshold": 0.8
    },
    "chat": {
      "enabled": true,
      "model": "gpt-4-turbo",
      "max_tokens": 4000
    }
  },
  "usage_limits": {
    "daily_tokens": 100000,
    "per_user_daily": 1000
  }
}
```

**LLM Service:**
```python
# backend/services/llm_service.py
class LLMService:
    @staticmethod
    async def get_config():
        \"\"\"Get centralized LLM config\"\"\"
        config = await db.system_config.find_one()
        return config.get("llm")
    
    @staticmethod
    async def call_llm(feature: str, prompt: str):
        \"\"\"Call LLM using centralized config\"\"\"
        config = await LLMService.get_config()
        feature_config = config["features"].get(feature)
        
        # Use emergentintegrations or OpenAI SDK
        response = await llm.chat.completions.create(
            model=feature_config["model"],
            messages=[{"role": "user", "content": prompt}]
        )
        return response
```

**Usage in Features:**
```python
# Deal confidence
llm_response = await LLMService.call_llm("deal_confidence", context)

# Field mapping
suggestions = await LLMService.call_llm("field_mapping", fields)

# Chat
answer = await LLMService.call_llm("chat", user_question)
```

---

### **4. Per-Person Incentives (Already 80% Done!)**

**Current State:**
- ✅ 1% base rate set
- ✅ Per-user commission template assignment endpoint
- ✅ Template calculation working

**Remaining (20%):**
- Add UI in Admin panel for assigning templates to users
- Show user's current template in user management
- Add commission preview/calculator

**Implementation:**
```javascript
// In AdminPanel.js - User Management section
<div className="mt-2">
  <Label>Commission Template</Label>
  <select
    value={user.commission_template_id || 'default'}
    onChange={(e) => assignCommissionTemplate(user.id, e.target.value)}
  >
    <option value="default">Default (1%)</option>
    <option value="premium">Premium (8%)</option>
    <option value="custom">Custom Rate</option>
  </select>
</div>
```

---

### **5. Per-Person Targets (Quick Win!)**

**Current State:**
- ✅ Backend supports per-person goals
- ✅ Manager assignment endpoints exist
- ⚠️ UI shows role-based targets

**Implementation (1 hour):**

**Backend (Already Exists):**
```
GET /api/goals/team/subordinates
POST /api/goals/assign-to-team
```

**Frontend Update:**
```javascript
// In Goals.js - Replace role-target UI with person-target UI

// BEFORE: Role-based
<select>
  <option>Account Manager Role</option>
  <option>Sales Rep Role</option>
</select>

// AFTER: Person-based
<select>
  <option>John Doe</option>
  <option>Jane Smith</option>
  <option>All Team Members</option>
</select>

// Fetch subordinates
const subordinates = await api.get('/goals/team/subordinates');

// Assign goal to person
await api.post('/goals/assign-to-team', {
  goal_id,
  team_member_ids: [selectedUserId]
});
```

---

### **6. Integration Marketplace**

**Manifest Format:**
```yaml
# integrations/salesforce/manifest.yaml
name: Salesforce CRM
version: 1.0.0
type: crm
author: Platform Team
description: Salesforce CRM integration with bi-directional sync

capabilities:
  api_sync: true
  webhooks: true
  field_mapping: true
  realtime: false

entities:
  - account
  - opportunity
  - contact
  - activity

dependencies:
  - simple-salesforce>=1.12.0

configuration:
  - name: instance_url
    type: string
    required: true
  - name: username
    type: string
    required: true
  - name: password
    type: password
    required: true
  - name: security_token
    type: password
    required: true

webhooks:
  endpoint: /api/webhooks/salesforce
  secret_header: X-Salesforce-Signature
```

**Installer:**
```python
# backend/services/integration_installer.py
class IntegrationInstaller:
    async def install(self, package_path: str):
        \"\"\"Install integration from package\"\"\"
        
        # 1. Load manifest
        manifest = load_yaml(f"{package_path}/manifest.yaml")
        
        # 2. Install dependencies
        subprocess.run(["pip", "install", "-r", f"{package_path}/requirements.txt"])
        
        # 3. Register in system_config
        await db.system_config.update_one(
            {},
            {
                "$push": {
                    "integrations": {
                        "id": manifest["name"],
                        "version": manifest["version"],
                        "config": {},
                        "status": "installed"
                    }
                }
            }
        )
        
        # 4. Initialize integration
        integration_class = import_module(f"{package_path}.integration")
        integration = integration_class()
        
        return {"status": "installed", "integration": manifest["name"]}
```

---

## 📊 IMPLEMENTATION PHASES

### **Phase 1: Quick Wins (This Session)**

**1. Per-Person Targets UI (1 hour)**
- Update Goals.js to show individuals instead of roles
- Use existing `/goals/team/subordinates` API
- Manager can assign to team members

**2. Architecture Documentation (Completed)**
- This document serves as blueprint
- Detailed specifications for each component
- Ready for implementation

**Estimated:** 1-2 hours

---

### **Phase 2: LLM & AI Centralization (3-4 days)**

**1. LLM Service (1 day)**
- Create centralized LLM service
- Store config in system_config
- Update all LLM calls to use service

**2. AI Features (2 days)**
- Deal confidence uses central config
- Field mapping uses central config
- Add AI chat feature

**3. Admin UI (1 day)**
- LLM provider configuration
- API key management
- Feature toggles

---

### **Phase 3: Integration Module (5-7 days)**

**1. Base Integration Framework (2 days)**
- BaseIntegration class
- Connector interface
- Mapper interface
- Integration registry

**2. Odoo Migration (2 days)**
- Refactor into new structure
- Merge webhook + API sync
- Remove odoo_routes.py conflicts

**3. Marketplace Foundation (2 days)**
- Manifest parser
- Installer service
- Template generator

**4. Admin UI (1 day)**
- Integration management page
- Install/uninstall workflows
- Configuration forms

---

### **Phase 4: Migration & Testing (3-4 days)**

**1. Data Migration (1 day)**
- Role targets → User targets
- Move LLM config to system_config
- Update integration registry

**2. Testing (2 days)**
- Unit tests for all new modules
- Integration tests
- UI testing

**3. Documentation (1 day)**
- User guides
- Developer SDK docs
- Migration guides

---

## 🎯 DETAILED SPECIFICATIONS

### **Integration SDK Template**

**Developer Experience:**
```python
# my_integration/integration.py
from integrations.base import BaseIntegration

class MyIntegration(BaseIntegration):
    def __init__(self, config):
        super().__init__(config)
        self.connector = MyConnector(config)
        self.mapper = MyMapper()
    
    async def fetch_records(self, entity_type):
        # Fetch from external system
        records = await self.connector.get_records(entity_type)
        
        # Map to canonical
        canonical = [self.mapper.map(r) for r in records]
        
        # Write to data lake
        for record in canonical:
            await self.data_lake.ingest_raw(record)
        
        return canonical
    
    async def webhook_handler(self, payload):
        # Handle webhook
        if payload["action"] == "delete":
            await self.soft_delete(payload["record_id"])
        else:
            await self.sync_record(payload["record_id"])
```

**Install:**
```bash
# From marketplace
POST /api/integrations/install
{
  "source": "marketplace",
  "integration_id": "salesforce-crm"
}

# From file
POST /api/integrations/install
{
  "source": "upload",
  "package": "salesforce.zip"
}
```

---

### **Per-Person Targets**

**Data Model:**
```javascript
// User target
{
  "id": "uuid",
  "user_id": "user_uuid",
  "assigned_by": "manager_uuid",
  "target_type": "revenue",
  "target_value": 500000,
  "period": "Q1 2026",
  "current_value": 150000,  // Auto-calculated
  "progress": 30.0,
  "kpi_id": "kpi_uuid",  // Link to KPI
  "created_at": "2026-01-18T..."
}
```

**UI Flow:**
```
Manager View:
1. Click "Assign Targets"
2. Select team member
3. Set target value and KPI
4. Save
5. Team member sees their personal target
6. Progress auto-updates from activities
```

---

### **LLM Config**

**Admin Configuration:**
```javascript
{
  "llm": {
    "provider": "openai",
    "api_key": "sk-...",
    "models": {
      "chat": "gpt-4-turbo",
      "analysis": "gpt-4",
      "embeddings": "text-embedding-3-small"
    },
    "features": {
      "deal_confidence": {
        "enabled": true,
        "model": "gpt-4",
        "prompt_template": "Analyze this opportunity..."
      },
      "field_mapping": {
        "enabled": true,
        "confidence_threshold": 0.8
      },
      "chat": {
        "enabled": true,
        "context_window": 8000
      }
    }
  }
}
```

---

## 📋 IMPLEMENTATION CHECKLIST

### **Phase 1: Quick Wins (This Session)**
- [x] Architecture document
- [ ] Per-person targets UI
- [ ] Test and verify

### **Phase 2: LLM & AI (Next Session)**
- [ ] LLM Service class
- [ ] Update all AI features
- [ ] Admin UI for LLM config
- [ ] Migration script

### **Phase 3: Integration Module (Week 2)**
- [ ] Base integration framework
- [ ] Odoo refactor
- [ ] Marketplace foundation
- [ ] Admin UI updates

### **Phase 4: Testing & Launch (Week 3)**
- [ ] Migration scripts
- [ ] Comprehensive testing
- [ ] Documentation
- [ ] Production deployment

---

## 🎯 SUCCESS METRICS

**Technical:**
- All integrations use data lake pipeline
- Zero hard-deletes
- <1 second webhook propagation
- 99%+ webhook success rate

**Business:**
- Admins can install integrations in <5 minutes
- Targets assigned to individuals
- Commission calculations accurate (1% base)
- AI features operational

**User Experience:**
- Single admin console
- Intuitive configuration
- Real-time data updates
- AI assistance available

---

**Architecture plan complete!**

**Ready for phased implementation!** 📋

**Document End**
