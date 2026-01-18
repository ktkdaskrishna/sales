# Odoo Integration - Production Considerations & Enhancements

**Date**: January 18, 2026  
**Version**: v3.1  
**Status**: Architectural Guidance

---

## 🚨 Critical Issues to Monitor

### 1. ID Type Mismatches (Can Cause Duplicates)

**Problem**:
- Odoo returns IDs as integers (e.g., `123`)
- MongoDB stores IDs as strings (e.g., `"123"`)
- Comparison `123 !== "123"` can create duplicate records

**Current Mitigation**:
- ✅ Webhook path: `str(record_id)` conversion implemented
- ⚠️ Sync pipeline: Verify all `source_id` fields are stringified

**Action Required**:
```python
# In all mappers, ensure:
source_id = str(data.get('id'))  # NOT data.get('id')

# In deduplication logic:
existing = await db.find_one({"source_id": str(odoo_id)})
```

**Files to Review**:
- `/app/backend/integrations/odoo/mapper.py` - All 6 mappers
- `/app/backend/data_lake/canonical_zone.py` - Deduplication logic
- `/app/backend/routes/webhooks.py` - ✅ Already fixed

---

### 2. Missing Field Mappings (Silent Data Loss)

**Problem**:
- Odoo adds new field `customer_credit_limit` to res.partner
- Field mapping doesn't include it
- **Result**: Field never syncs, business logic breaks silently

**Current State**:
- Field mappings are static (configured once)
- No detection of new Odoo fields
- No alerts when unmapped fields exist

**Enhancement Required**: Schema Drift Detection

**Implementation**:
```python
async def detect_schema_drift(odoo_model: str, configured_fields: List[str]):
    """
    Compare Odoo's current schema with configured field mappings.
    Alert admins when new fields are detected.
    """
    # Fetch current fields from Odoo
    actual_fields = await connector.fields_get(odoo_model)
    
    # Compare
    new_fields = set(actual_fields.keys()) - set(configured_fields)
    removed_fields = set(configured_fields) - set(actual_fields.keys())
    
    if new_fields:
        logger.warning(f"Schema drift detected for {odoo_model}:")
        logger.warning(f"  New fields in Odoo: {new_fields}")
        # Send alert to admin panel
    
    if removed_fields:
        logger.error(f"  Removed fields: {removed_fields}")
        # Critical: existing mappings are broken
    
    return {
        "new_fields": list(new_fields),
        "removed_fields": list(removed_fields),
        "drift_detected": len(new_fields) > 0 or len(removed_fields) > 0
    }
```

**Files to Create**:
- `/app/backend/services/odoo/schema_monitor.py`
- Add endpoint: `GET /api/integrations/odoo/schema-drift`
- Add UI alert in Field Mapping tab

---

### 3. Partial Webhook Coverage (Stale Data Risk)

**Problem**:
- Webhooks configured for `delete` events only
- Create/update events not captured
- Batch sync runs every 5 minutes
- **Result**: 5-minute data lag for creates/updates

**Current Webhook Coverage**:
- ✅ Delete events (`unlink` action) - Real-time
- ❌ Create events - Not captured
- ❌ Update events - Not captured

**Enhancement Required**: Full Webhook Coverage

**Implementation**:
```python
# Odoo Automated Actions needed:

# 1. On Create (res.partner, crm.lead, account.move, mail.activity)
Trigger: After → Create
Action: Python Code
requests.post(
    'YOUR_URL/api/webhooks/odoo',
    json={
        'model': record._name,
        'action': 'create',
        'record_ids': record.ids,
        'data': record.read()[0]  # Include data for immediate sync
    },
    headers={'X-Odoo-Webhook-Secret': 'your-key'}
)

# 2. On Update
Trigger: After → Update
Action: Python Code
requests.post(
    'YOUR_URL/api/webhooks/odoo',
    json={
        'model': record._name,
        'action': 'write',
        'record_ids': record.ids,
        'data': record.read()[0]
    },
    headers={'X-Odoo-Webhook-Secret': 'your-key'}
)
```

**Backend Changes**:
```python
# In /app/backend/routes/webhooks.py

if payload.action == "create":
    # Immediate ingestion to Raw zone
    await data_lake.ingest_from_source(...)
    
elif payload.action == "write":
    # Update canonical zone
    await data_lake.canonical.update(...)
```

---

## 🚀 Enhancement Roadmap

### Enhancement 1: Schema Drift Alerts

**Priority**: High  
**Effort**: 2-3 hours  
**Impact**: Prevents silent data loss

**Implementation Steps**:
1. Create `SchemaMonitor` service
2. Add scheduled job (daily) to compare schemas
3. Store drift reports in `schema_drift_log` collection
4. Add UI alert in Field Mapping tab: "⚠️ 3 new fields detected in Odoo"
5. Admin can review and add mappings

**Benefits**:
- Proactive detection of Odoo schema changes
- Prevents missing critical business data
- Audit trail of schema evolution

---

### Enhancement 2: Sync Health Metrics

**Priority**: Medium  
**Effort**: 1-2 hours  
**Impact**: Visibility into sync freshness

**Implementation**:
```python
# Add to each entity in system_config
{
    "odoo_model": "crm.lead",
    "health_metrics": {
        "last_webhook_received": "2026-01-18T12:30:45Z",
        "last_batch_sync": "2026-01-18T12:25:00Z",
        "last_successful_sync": "2026-01-18T12:30:45Z",
        "total_records": 21,
        "sync_lag_seconds": 15,
        "health_status": "healthy"  # healthy|warning|critical
    }
}
```

**UI Display**:
- Data Lake tab: Show health status per entity
- Green: Last sync < 5 min
- Yellow: Last sync 5-15 min  
- Red: Last sync > 15 min

**Benefits**:
- Real-time visibility into sync freshness
- Early warning for webhook failures
- SLA monitoring

---

### Enhancement 3: Automated Backfill After Mapping Changes

**Priority**: High  
**Effort**: 2 hours  
**Impact**: Eliminates manual sync after config changes

**Current Flow**:
```
Admin adds new field mapping (customer_credit_limit)
  ↓
Field saved to config
  ↓
❌ Existing records still have null for this field
  ↓
Admin must manually click "Sync Now"
```

**Enhanced Flow**:
```
Admin adds new field mapping
  ↓
Field saved to config
  ↓
System detects new mapping
  ↓
Background job: Backfill existing records
  ↓
Fetch updated data from Odoo for all records
  ↓
Update only the new field in Canonical + Serving zones
  ↓
✅ All records now have customer_credit_limit populated
```

**Implementation**:
```python
@router.put("/odoo/mappings/{mapping_id}/fields")
async def update_field_mappings(...):
    # ... save mappings ...
    
    # Detect new fields
    old_fields = set(old_mapping['field_mappings'].keys())
    new_fields = set(updated_mappings.keys()) - old_fields
    
    if new_fields:
        # Trigger backfill job
        background_tasks.add_task(
            backfill_new_fields,
            entity_type=mapping['odoo_model'],
            new_fields=list(new_fields),
            mapping_id=mapping_id
        )
        
        return {
            "message": "Field mappings updated",
            "backfill_triggered": True,
            "new_fields": list(new_fields)
        }
```

**Benefits**:
- Zero manual intervention
- Immediate data consistency
- Better UX (admin doesn't need to remember to sync)

---

## 📋 Implementation Priority

**Phase 1 (Critical - Now)**:
- [x] ID type standardization (str conversion)
- [x] Real-time field mapping auto-save
- [ ] Automated backfill after mapping changes

**Phase 2 (Important - This Week)**:
- [ ] Full webhook coverage (create/update events)
- [ ] Sync health metrics dashboard
- [ ] Schema drift detection (daily job)

**Phase 3 (Nice to Have - Next Sprint)**:
- [ ] Field-level sync history
- [ ] Conflict resolution UI
- [ ] Performance metrics (sync duration tracking)

---

## 🔧 Quick Wins (Can Implement Now)

### 1. Add ID Standardization Check

```python
# Add to all mappers in mapper.py
def _ensure_string_id(self, value: Any) -> str:
    """Ensure ID is always string for MongoDB consistency"""
    if value is None:
        return ""
    return str(value)

# Use in all source_id assignments:
source_id = self._ensure_string_id(data.get('id'))
```

### 2. Add Sync Lag Indicator

```python
# In Data Lake tab, add per-entity freshness:
{
    "entity": "Opportunities",
    "last_sync": "2 minutes ago",
    "status": "🟢 Fresh"  # or "🟡 Stale" if > 10 min
}
```

### 3. Add "Backfill Now" Button

```python
# In Field Mapping tab after save:
<button onClick={triggerBackfill}>
    🔄 Backfill Existing Records
</button>
```

---

## 📚 Related Documentation

- `/app/docs/REAL_TIME_DELETION_ARCHITECTURE.md` - Webhook deletion sync
- `/app/docs/UNIFIED_ADMIN_ARCHITECTURE.md` - Integration architecture
- `/app/docs/ODOO_WEBHOOK_SETUP.md` - Webhook configuration guide

---

## ✅ Current System Strengths

**What's Working Well**:
- ✅ Real-time deletions via webhooks (sub-second)
- ✅ 3-zone data lake (audit trail + reprocessing)
- ✅ Configurable field mappings per entity
- ✅ Automated 5-minute batch sync (fallback)
- ✅ v3.1 pipeline (proper Raw → Canonical → Serving)

**What Needs Attention**:
- ⚠️ ID type consistency across all code paths
- ⚠️ Schema drift detection
- ⚠️ Create/update webhook coverage
- ⚠️ Automated backfill after mapping changes

---

**Next Steps**: Prioritize Phase 1 enhancements for production hardening.
