# 🔗 Odoo 19 Webhook Setup Guide

**Production-Grade Real-Time Integration**  
**Date:** January 18, 2026  
**Version:** 1.0

---

## 🎯 OVERVIEW

This guide configures **Odoo 19** to send real-time webhooks to the Sales Intelligence Platform, enabling:
- **Sub-second deletion propagation** (vs 5-minute polling delay)
- **Instant create/update sync** for critical records
- **Soft-delete audit trail** (preserves data for compliance)
- **CQRS consistency** (immediate dashboard updates)

**Supported Entities:**
- Accounts/Contacts (res.partner)
- Opportunities (crm.lead)
- Invoices (account.move)
- Activities (mail.activity)
- Messages (mail.message)

---

## 📋 PREREQUISITES

**1. Odoo Access:**
- Admin/Settings access
- Technical menu enabled

**2. App Configuration:**
- Webhook endpoint deployed
- Webhook secret configured

**3. Network:**
- Odoo can reach your app URL
- HTTPS enabled (required for security)

---

## 🔧 STEP-BY-STEP CONFIGURATION

### **Step 1: Enable Technical Menu in Odoo**

**Path:** Settings → General Settings

1. Scroll to "Developer Tools"
2. Enable "Developer Mode"
3. Save
4. Verify "Technical" appears in Settings menu

---

### **Step 2: Get Webhook Credentials from App**

**In Your App:**
1. Login as Super Admin
2. Go to `/admin`
3. Click **"Webhooks & Sync"** tab
4. Copy:
   - Webhook URL
   - Webhook Secret

**Example:**
```
Webhook URL: https://your-app.com/api/webhooks/odoo
Webhook Secret: your-odoo-api-key
```

---

### **Step 3: Create Automated Action for Deletions (Critical!)**

**Path:** Settings → Technical → Automation → Automated Actions

#### **3.1: Account Deletion Webhook**

**Click "New"**

**Configuration:**
```
Name: Sales App - Account Delete Webhook
Model: Contact (res.partner)
Trigger: On Deletion
Action To Do: Execute Python Code
```

**Python Code:**
```python
import requests
import json

# Webhook configuration
WEBHOOK_URL = "https://your-app.com/api/webhooks/odoo"
WEBHOOK_SECRET = "your-odoo-api-key"

# Get deleted record IDs from context
record_ids = env.context.get('active_ids', [])

if record_ids:
    try:
        response = requests.post(
            WEBHOOK_URL,
            json={
                'model': 'res.partner',
                'action': 'unlink',
                'record_ids': record_ids,
                'timestamp': fields.Datetime.now().isoformat()
            },
            headers={
                'Content-Type': 'application/json',
                'X-Odoo-Webhook-Secret': WEBHOOK_SECRET
            },
            timeout=5
        )
        
        if response.status_code != 200:
            log('Webhook failed: %s' % response.text, level='warning')
    except Exception as e:
        # Don't block deletion if webhook fails
        log('Webhook error: %s' % str(e), level='warning')
```

**Save and Activate**

---

#### **3.2: Opportunity Deletion Webhook**

**Repeat Step 3.1 with:**
```
Name: Sales App - Opportunity Delete Webhook
Model: Lead/Opportunity (crm.lead)
Python Code: Same as above, change 'res.partner' to 'crm.lead'
```

---

#### **3.3: Invoice Deletion Webhook**

**Repeat Step 3.1 with:**
```
Name: Sales App - Invoice Delete Webhook
Model: Journal Entry (account.move)
Python Code: Same as above, change 'res.partner' to 'account.move'
```

---

### **Step 4: Create Automated Action for Create/Update (Optional)**

**For Real-Time Create/Update (if polling is too slow):**

**Configuration:**
```
Name: Sales App - Account Create/Update Webhook
Model: Contact (res.partner)
Trigger: On Creation and Update
Action To Do: Execute Python Code
```

**Python Code:**
```python
import requests

WEBHOOK_URL = "https://your-app.com/api/webhooks/odoo"
WEBHOOK_SECRET = "your-odoo-api-key"

try:
    # Send create/update webhook
    response = requests.post(
        WEBHOOK_URL,
        json={
            'model': record._name,
            'action': 'create' if record.id not in record.env[record._name].search([]).ids[:-1] else 'write',
            'record_ids': [record.id],
            'data': record.read()[0] if record else None
        },
        headers={
            'Content-Type': 'application/json',
            'X-Odoo-Webhook-Secret': WEBHOOK_SECRET
        },
        timeout=5
    )
except Exception as e:
    log('Webhook error: %s' % str(e), level='warning')
```

**Note:** This is optional. Background polling handles create/update well. Only implement if you need sub-second create/update sync.

---

## 🔒 SECURITY CONFIGURATION

### **Webhook Secret Validation**

**In Your App:**

**Environment Variable (Recommended):**
```bash
# .env
ODOO_WEBHOOK_SECRET=your-secure-secret-key-here
```

**Or use existing ODOO_API_KEY:**
```python
# Backend validates:
expected_secret = settings.ODOO_WEBHOOK_SECRET or settings.ODOO_API_KEY
```

**Odoo Automated Action:**
```python
headers={'X-Odoo-Webhook-Secret': 'your-secure-secret-key-here'}
```

**Security:**
- ✅ Prevents unauthorized webhook calls
- ✅ Validates every request
- ✅ Returns 401 Unauthorized if invalid
- ✅ Logs failed attempts

---

## 🧪 TESTING WEBHOOKS

### **Test Deletion Webhook:**

**1. In Odoo:**
- Go to Contacts
- Find a test contact (e.g., "Webhook Test Contact")
- Click "Delete"
- Confirm deletion

**2. In Your App (within 1 second):**
- Check logs: `grep "Webhook DELETE" /var/log/supervisor/backend.err.log`
- Expected: `Webhook DELETE complete | Entity: account | Records: [123] | Latency: 0.123s`

**3. Verify in UI:**
- Refresh accounts page
- Deleted contact should disappear immediately
- No 5-minute wait!

---

### **Test Create/Update Webhook (if configured):**

**1. In Odoo:**
- Create new contact "Webhook Test 2"
- Or update existing contact

**2. In Your App:**
- Check logs: `grep "Webhook" /var/log/supervisor/backend.err.log`
- Verify record appears in data_lake_serving
- Refresh UI to see new/updated record

---

## 📊 MONITORING WEBHOOKS

### **View Webhook Events:**

**In Admin Panel:**
1. Go to `/admin`
2. Click "Webhooks & Sync" tab
3. See:
   - Recent webhook events (last 10)
   - Success/failure statistics
   - Processing latency
   - Error messages (if any)

**Via API:**
```bash
GET /api/admin/webhooks/status
```

**Response:**
```json
{
  "recent_events": [
    {
      "event_type": "odoo_delete",
      "model": "res.partner",
      "record_ids": [123],
      "processing_time_seconds": 0.123,
      "status": "success",
      "timestamp": "2026-01-18T..."
    }
  ],
  "statistics": {
    "total_recent": 10,
    "successful": 9,
    "failed": 1
  }
}
```

---

## 🔍 TROUBLESHOOTING

### **Issue: Webhook Returns 401 Unauthorized**

**Cause:** Invalid or missing X-Odoo-Webhook-Secret header

**Fix:**
1. Check webhook secret in Odoo automated action code
2. Verify it matches app configuration
3. Check logs: `grep "Invalid webhook secret" backend.err.log`

---

### **Issue: Deletions Still Show in App**

**Cause:** Webhook not configured or failing

**Check:**
1. Verify automated action is active in Odoo
2. Check webhook event logs in admin panel
3. Verify network connectivity (Odoo → App)
4. Test with manual sync: Click "Sync Now" in admin

---

### **Issue: Webhook Timeout**

**Cause:** Slow network or app response

**Fix:**
1. Increase timeout in Odoo code (from 5 to 10 seconds)
2. Check app backend health: `curl https://your-app.com/api/health`
3. Verify database performance

---

## ⚡ PERFORMANCE EXPECTATIONS

**With Webhooks Configured:**

| Action | Without Webhooks | With Webhooks |
|--------|------------------|---------------|
| Delete in Odoo | Visible for 5 min | Hidden in < 1 sec |
| Create in Odoo | Appears in 5 min | Appears in 5 min* |
| Update in Odoo | Updates in 5 min | Updates in 5 min* |

*Create/update webhooks are optional. Background polling handles these well.

**Critical Path: DELETIONS** 
- Webhooks provide 300x faster deletion propagation
- Sub-second vs 5-minute delay
- Essential for production user experience

---

## 📋 CONFIGURATION CHECKLIST

**Before Production:**
- [ ] Webhook secret configured in environment
- [ ] HTTPS enabled on app
- [ ] Automated actions created for:
  - [ ] res.partner (Delete)
  - [ ] crm.lead (Delete)
  - [ ] account.move (Delete)
- [ ] Test deletion in Odoo staging
- [ ] Verify < 1 second propagation
- [ ] Monitor webhook events for 1 week
- [ ] Set up alerts for webhook failures

**After Deployment:**
- [ ] Monitor webhook success rate (target: >99%)
- [ ] Set up Sentry/error tracking
- [ ] Configure webhook retry in Odoo (if available)
- [ ] Document runbook for webhook failures

---

## 🎯 RECOMMENDED PRODUCTION SETUP

**Deletion Handling:**
- ✅ Webhooks: PRIMARY (accounts, opportunities, invoices)
- ✅ Polling: BACKUP (every 15 minutes)

**Create/Update Handling:**
- ✅ Polling: PRIMARY (every 5 minutes, sufficient)
- ⚠️ Webhooks: OPTIONAL (only if needed for specific use cases)

**Why:**
- Deletions need instant visibility (user expectation)
- Create/update can tolerate 5-minute delay
- Reduces webhook volume by 90%
- Balances performance and complexity

---

## 📚 ADDITIONAL RESOURCES

**Odoo Documentation:**
- Automated Actions: https://www.odoo.com/documentation/19.0/developer/reference/backend/actions.html
- Python Code Actions: https://www.odoo.com/documentation/19.0/developer/reference/backend/actions.html#python-code

**App Documentation:**
- `/app/docs/REAL_TIME_DELETION_ARCHITECTURE.md` - Architecture overview
- `/app/docs/ODOO_DATA_EXTRACTION_GUIDE.md` - Data flow details

**Support:**
- Check webhook logs: `/admin` → "Webhooks & Sync" tab
- Manual sync: Click "Sync Now" button
- Test endpoint: `POST /api/webhooks/odoo` (with proper headers)

---

**Document End**

**Estimated Setup Time:** 30 minutes  
**Expected Performance:** <1 second deletion propagation  
**Maintenance:** Monitor webhook events weekly
