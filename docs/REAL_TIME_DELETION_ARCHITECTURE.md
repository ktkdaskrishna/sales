# 🏗️ Real-Time Deletion Architecture - Production Scale Solution

**Date:** January 18, 2026  
**Topic:** Immediate vs Eventual Consistency for Deletions  
**Audience:** Engineering, Product, Executive

---

## 🎯 CURRENT PROBLEM

### **Observed Behavior:**
```
Time 12:49 PM: Delete "TEST" account in Odoo
Time 12:51 PM: "TEST" still visible in app (2 minutes later)
```

### **Current Architecture (Polling-Based):**

```
┌─────────────────────────────────────────┐
│ ODOO ERP                                │
│ User deletes "TEST" account             │
└──────────────┬──────────────────────────┘
               │
               │ No notification!
               │ App doesn't know yet
               ↓
┌─────────────────────────────────────────┐
│ BACKGROUND SYNC (Every 5 minutes)       │
│ - Fetches current accounts              │
│ - Compares with existing                │
│ - Marks missing as is_active=False      │
└──────────────┬──────────────────────────┘
               │
               │ UP TO 5 MINUTE DELAY ⚠️
               ↓
┌─────────────────────────────────────────┐
│ APP (data_lake_serving)                 │
│ "TEST" marked is_active=False           │
└──────────────┬──────────────────────────┘
               │
               │ Deletion sync runs
               ↓
┌─────────────────────────────────────────┐
│ CQRS VIEWS (opportunity_view, etc.)     │
│ Records marked inactive                 │
└──────────────┬──────────────────────────┘
               │
               │ User refreshes browser
               ↓
┌─────────────────────────────────────────┐
│ UI                                      │
│ "TEST" disappears                       │
│ TOTAL DELAY: 5+ minutes                │
└─────────────────────────────────────────┘
```

**Delay Breakdown:**
- Background sync interval: **5 minutes**
- Deletion sync: **~2 seconds**
- Browser cache: **Until refresh**
- **Total worst-case: 5-10 minutes**

---

## ⚠️ PRODUCTION SCALE IMPLICATIONS

### **At Current Scale (10-50 users):**
- ✅ Acceptable: 5-minute delay tolerable
- ✅ Simple: No infrastructure complexity
- ✅ Reliable: Well-tested polling pattern

### **At Production Scale (500+ users, 10K+ records):**
- ❌ **User Confusion:** "I just deleted this, why is it still here?"
- ❌ **Data Integrity:** Users might re-create deleted records
- ❌ **Audit Issues:** Compliance requires immediate deletion visibility
- ❌ **Sync Load:** Full sync every 5 min = heavy DB load
- ❌ **Race Conditions:** Multiple users, concurrent changes

---

## 🏗️ PRODUCTION-READY ARCHITECTURES

### **Option 1: Webhook-Based (Recommended)**

**Architecture:**
```
┌─────────────────────────────────────────┐
│ ODOO ERP                                │
│ User deletes "TEST" account             │
│ ↓                                       │
│ Triggers webhook immediately            │
└──────────────┬──────────────────────────┘
               │
               │ HTTP POST (instant!)
               ↓
┌─────────────────────────────────────────┐
│ OUR APP: /api/webhooks/odoo/deleted     │
│ {                                       │
│   "model": "res.partner",               │
│   "record_id": 10,                      │
│   "action": "delete",                   │
│   "timestamp": "2026-01-18T12:49:00Z"   │
│ }                                       │
└──────────────┬──────────────────────────┘
               │
               │ Process immediately
               ↓
┌─────────────────────────────────────────┐
│ DELETION HANDLER                        │
│ 1. Mark in data_lake_serving            │
│ 2. Update CQRS views                    │
│ 3. Publish SSE event to connected UIs   │
└──────────────┬──────────────────────────┘
               │
               │ Real-time update
               ↓
┌─────────────────────────────────────────┐
│ UI (via WebSocket/SSE)                  │
│ "TEST" disappears immediately           │
│ TOTAL DELAY: < 1 second                │
└─────────────────────────────────────────┘
```

**Implementation:**

**1. Odoo Webhook Configuration:**
```python
# In Odoo (automated action):
Trigger: On Delete of res.partner, crm.lead, account.move
Action: Send POST to https://yourapp.com/api/webhooks/odoo/deleted
Payload: {
    "model": record.model,
    "record_id": record.id,
    "timestamp": now()
}
```

**2. Webhook Endpoint:**
```python
# backend/routes/webhooks.py
@router.post("/odoo/deleted")
async def handle_odoo_deletion(webhook_data: dict):
    """Process deletion webhook from Odoo"""
    model = webhook_data["model"]
    record_id = webhook_data["record_id"]
    
    # Map Odoo model to entity type
    entity_type = {
        "res.partner": "account",
        "crm.lead": "opportunity",
        "account.move": "invoice"
    }.get(model)
    
    if not entity_type:
        return {"status": "ignored"}
    
    # Mark as deleted
    await db.data_lake_serving.update_one(
        {"entity_type": entity_type, "data.id": record_id},
        {"$set": {"is_active": False, "deleted_at": datetime.now()}}
    )
    
    # Update CQRS views
    if entity_type == "opportunity":
        await db.opportunity_view.update_one(
            {"odoo_id": record_id},
            {"$set": {"is_active": False}}
        )
    
    # Broadcast to connected clients (SSE/WebSocket)
    await broadcast_deletion(entity_type, record_id)
    
    return {"status": "processed", "entity": entity_type}
```

**3. Real-time UI Updates (Server-Sent Events):**
```javascript
// frontend/src/services/realtimeSync.js
const eventSource = new EventSource('/api/events/deletions');

eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === 'account_deleted') {
        // Remove from local state immediately
        setAccounts(prev => prev.filter(a => a.id !== data.record_id));
    }
};
```

**Benefits:**
- ✅ Instant deletion (< 1 second)
- ✅ No polling overhead
- ✅ Scales to 10K+ records
- ✅ Real-time user experience

**Challenges:**
- ⚠️ Requires Odoo configuration access
- ⚠️ Additional infrastructure (WebSocket/SSE server)
- ⚠️ Webhook security (HMAC signatures)

---

### **Option 2: Event-Driven with Message Queue (Enterprise)**

**Architecture:**
```
Odoo → Webhook → Kafka/RabbitMQ → Worker → Update DB → Broadcast SSE
```

**Benefits:**
- ✅ Guaranteed delivery
- ✅ Retry logic
- ✅ Horizontal scaling
- ✅ Audit trail

**Challenges:**
- ⚠️ Complex infrastructure
- ⚠️ Higher operational cost
- ⚠️ Kafka/RabbitMQ management

---

### **Option 3: Reduced Polling Interval (Quick Win)**

**Current:** Sync every 5 minutes  
**Proposed:** Sync every 30 seconds

**Code Change:**
```python
# backend/services/sync/background_sync.py
await start_background_sync(interval_minutes=0.5)  # 30 seconds
```

**Benefits:**
- ✅ Simple: No architecture change
- ✅ Faster: 30-second max delay
- ✅ No Odoo changes needed

**Challenges:**
- ⚠️ 10x more API calls to Odoo
- ⚠️ Higher database load
- ⚠️ Still not "instant"

---

### **Option 4: Hybrid Approach (RECOMMENDED)**

**Critical Data (Accounts, Opportunities):** Webhooks  
**Non-Critical (Invoices, Activities):** Polling (5 min)

**Architecture:**
```
HIGH PRIORITY (Instant):
- Account deletion → Webhook → Immediate update
- Opportunity deletion → Webhook → Immediate update

LOW PRIORITY (Eventual):
- Invoice sync → Poll every 5 min
- Activity sync → Poll every 5 min
- User sync → Poll every 15 min
```

**Benefits:**
- ✅ Best of both worlds
- ✅ Instant for critical data
- ✅ Low overhead for non-critical
- ✅ Gradual migration path

---

## 🚀 RECOMMENDED IMPLEMENTATION PLAN

### **Phase 1 (Immediate - 1 week):**

**Quick Wins:**

1. **Reduce Sync Interval to 1 minute:**
```python
# Change from 5 min to 1 min
await start_background_sync(interval_minutes=1)
```

2. **Add Manual Sync Button:**
```javascript
// In dashboard
<Button onClick={triggerManualSync}>
  Sync Now
</Button>
```

3. **Add "Last Synced" Indicator:**
```javascript
<span className="text-xs text-slate-500">
  Last synced: {formatTimeAgo(lastSyncTime)}
</span>
```

**Estimated Effort:** 2-3 hours  
**Delay Reduction:** 5 min → 1 min (80% improvement)

---

### **Phase 2 (Short-term - 2-3 weeks):**

**Implement Odoo Webhooks:**

1. **Configure Odoo Automated Actions:**
   - Trigger on delete of res.partner, crm.lead
   - Send webhook to our app
   - Include model, record_id, timestamp

2. **Create Webhook Endpoints:**
   - POST /api/webhooks/odoo/deleted
   - Verify webhook signature (security)
   - Process deletion immediately

3. **Update CQRS Views:**
   - Instant propagation to opportunity_view
   - No polling delay

**Estimated Effort:** 1-2 weeks  
**Delay Reduction:** 1 min → < 1 second (99% improvement)

---

### **Phase 3 (Long-term - 1-2 months):**

**Real-Time UI Updates:**

1. **Implement Server-Sent Events (SSE):**
   - Backend broadcasts deletion events
   - Frontend listens and updates in real-time
   - No page refresh needed

2. **Optimistic UI Updates:**
   - When user deletes in Odoo
   - App predicts deletion
   - Updates UI before sync completes

**Estimated Effort:** 3-4 weeks  
**User Experience:** Real-time, no delays

---

## 📊 COMPARISON TABLE

| Approach | Delay | Complexity | Odoo Changes | Cost | Scalability |
|----------|-------|------------|--------------|------|-------------|
| **Current (5 min poll)** | 5 min | Low | None | Low | Poor |
| **1 min poll** | 1 min | Low | None | Low | Fair |
| **30 sec poll** | 30 sec | Low | None | Medium | Fair |
| **Webhooks** | < 1 sec | Medium | Required | Medium | Excellent |
| **Webhooks + SSE** | Real-time | High | Required | High | Excellent |
| **Event Queue** | < 1 sec | Very High | Required | Very High | Excellent |

---

## 🎯 IMMEDIATE RECOMMENDATION

### **For Your Situation:**

**Now (This Week):**
- ✅ Reduce sync interval to **1 minute**
- ✅ Add "Sync Now" button for manual triggers
- ✅ Show "Last synced" timestamp
- ✅ Document the 1-minute delay for users

**Next Sprint (2-3 weeks):**
- ✅ Implement Odoo webhooks for accounts and opportunities
- ✅ Instant deletion propagation
- ✅ Keep polling for non-critical data

**Long-term (1-2 months):**
- ✅ Add SSE for real-time UI updates
- ✅ Eliminate all polling where possible
- ✅ Full event-driven architecture

---

## 💡 IMMEDIATE FIX - MANUAL SYNC TRIGGER

Let me implement a quick "Sync Now" button that users can click:

**Backend Endpoint (Already exists):**
```
POST /api/integrations/odoo/sync-all
```

**Add to Dashboard:**
```javascript
<Button onClick={handleSyncNow}>
  <RefreshCw className="w-4 h-4 mr-2" />
  Sync Now
</Button>
```

**This gives users control while we implement webhooks.**

---

## 🔍 WHY CURRENT APPROACH BREAKS AT SCALE

### **With 10K Accounts:**

**Current Polling:**
```
Every 5 minutes:
  - Fetch 10,000 accounts from Odoo (15 seconds)
  - Compare with 10,000 in database (10 seconds)
  - Mark ~50 as deleted (5 seconds)
  - Update CQRS views (10 seconds)
  
Total: 40 seconds per sync
Load: Constant DB queries
Result: 6-11 minute delay
```

**With Webhooks:**
```
On delete (instant):
  - Receive webhook (< 100ms)
  - Mark 1 record as deleted (< 50ms)
  - Update CQRS view (< 50ms)
  - Broadcast to UI (< 50ms)

Total: < 250ms
Load: Only on changes
Result: Sub-second response
```

---

## 📋 DECISION MATRIX

### **Choose Based On:**

**Stay with Polling IF:**
- ✅ < 100 users
- ✅ < 1,000 records
- ✅ 5-minute delay acceptable
- ✅ No Odoo admin access

**Move to Webhooks IF:**
- ✅ > 100 users
- ✅ > 5,000 records
- ✅ Need instant updates
- ✅ Have Odoo admin access
- ✅ Production deployment

**Your Situation:**
- Moving to production ✅
- Huge data expected ✅
- User experience critical ✅

**Recommendation:** **Implement Webhooks (Option 4 - Hybrid)**

---

## 🎯 IMMEDIATE ACTION ITEMS

**1. Short-term Fix (Today):**
- Reduce sync to 1 minute
- Add "Sync Now" button
- Manual fix: Mark "TEST" as inactive

**2. Medium-term (2 weeks):**
- Implement Odoo webhooks
- Create webhook endpoints
- Test with staging Odoo

**3. Long-term (1-2 months):**
- Add SSE for real-time updates
- Migrate to event-driven
- Remove polling where possible

---

## ✅ WHAT I'LL DO NOW

**Immediate:**
1. Mark "TEST" account as inactive
2. Document the current limitation
3. Recommend webhook implementation timeline

**Next Session:**
- Reduce sync interval to 1 minute
- Add manual sync button
- Prepare webhook endpoint structure

---

**Current approach works for development but needs webhooks for production scale!**

**Recommendation: Plan webhook implementation before production launch!** 🚀

---

**Document End**
