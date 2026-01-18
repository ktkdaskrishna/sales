#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime, timezone

class UATFixesTester:
    """Test UAT fixes comprehensively"""
    def __init__(self, base_url="https://ai-sales-platform-4.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.user_id = None
        self.user_role = None
        self.user_email = None

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=30)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=test_headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return True, response.json()
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Response: {response.text[:200]}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_seed_data(self):
        """Test seeding demo data"""
        print("\n" + "="*50)
        print("TESTING DEMO DATA SEEDING")
        print("="*50)
        
        success, response = self.run_test(
            "Seed Demo Data",
            "POST",
            "seed",
            200
        )
        return success

    def test_login(self, email="superadmin@salescommand.com", password="demo123"):
        """Test login and get token"""
        print("\n" + "="*50)
        print(f"TESTING AUTHENTICATION - {email}")
        print("="*50)
        
        success, response = self.run_test(
            f"Login as {email}",
            "POST",
            "auth/login",
            200,
            data={"email": email, "password": password}
        )
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.user_id = response['user']['id']
            self.user_role = response['user']['role']
            self.user_email = email
            print(f"   Logged in as: {response['user']['name']} ({response['user']['role']})")
            return True
        return False

    def test_auth_endpoints(self):
        """Test authentication endpoints"""
        # Test get current user
        success, response = self.run_test(
            "Get Current User",
            "GET",
            "auth/me",
            200
        )
        
        # Test get users (admin only)
        if self.user_role in ['ceo', 'admin']:
            success, response = self.run_test(
                "Get All Users",
                "GET",
                "users",
                200
            )

    def test_accounts_endpoints(self):
        """Test accounts CRUD operations"""
        print("\n" + "="*50)
        print("TESTING ACCOUNTS ENDPOINTS")
        print("="*50)
        
        # Get accounts
        success, accounts = self.run_test(
            "Get Accounts",
            "GET",
            "accounts",
            200
        )
        
        # Create account
        account_data = {
            "name": "Test Account API",
            "industry": "Technology",
            "annual_revenue": 1000000,
            "employee_count": 100,
            "relationship_maturity": "new",
            "business_overview": "Test account for API testing"
        }
        
        success, response = self.run_test(
            "Create Account",
            "POST",
            "accounts",
            200,
            data=account_data
        )
        
        if success and 'id' in response:
            account_id = response['id']
            
            # Get specific account
            success, response = self.run_test(
                "Get Specific Account",
                "GET",
                f"accounts/{account_id}",
                200
            )
            
            # Update account
            account_data['name'] = "Updated Test Account"
            success, response = self.run_test(
                "Update Account",
                "PUT",
                f"accounts/{account_id}",
                200,
                data=account_data
            )
            
            return account_id
        
        return None

    def test_opportunities_endpoints(self, account_id=None):
        """Test opportunities CRUD operations"""
        print("\n" + "="*50)
        print("TESTING OPPORTUNITIES ENDPOINTS")
        print("="*50)
        
        # Get opportunities
        success, opportunities = self.run_test(
            "Get Opportunities",
            "GET",
            "opportunities",
            200
        )
        
        if account_id:
            # Create opportunity
            opp_data = {
                "name": "Test Opportunity API",
                "account_id": account_id,
                "value": 50000,
                "stage": "qualification",
                "probability": 25,
                "product_lines": ["MSSP"],
                "description": "Test opportunity for API testing"
            }
            
            success, response = self.run_test(
                "Create Opportunity",
                "POST",
                "opportunities",
                200,
                data=opp_data
            )
            
            if success and 'id' in response:
                opp_id = response['id']
                
                # Get specific opportunity
                success, response = self.run_test(
                    "Get Specific Opportunity",
                    "GET",
                    f"opportunities/{opp_id}",
                    200
                )
                
                # Update opportunity
                opp_data['stage'] = "discovery"
                opp_data['probability'] = 40
                success, response = self.run_test(
                    "Update Opportunity",
                    "PUT",
                    f"opportunities/{opp_id}",
                    200,
                    data=opp_data
                )
                
                return opp_id
        
        return None

    def test_activities_endpoints(self, account_id=None, opp_id=None):
        """Test activities CRUD operations"""
        print("\n" + "="*50)
        print("TESTING ACTIVITIES ENDPOINTS")
        print("="*50)
        
        # Get activities
        success, activities = self.run_test(
            "Get Activities",
            "GET",
            "activities",
            200
        )
        
        # Create activity
        activity_data = {
            "title": "Test Activity API",
            "description": "Test activity for API testing",
            "activity_type": "task",
            "priority": "medium",
            "status": "pending",
            "due_date": datetime.now(timezone.utc).isoformat()
        }
        
        if account_id:
            activity_data["account_id"] = account_id
        if opp_id:
            activity_data["opportunity_id"] = opp_id
        
        success, response = self.run_test(
            "Create Activity",
            "POST",
            "activities",
            200,
            data=activity_data
        )
        
        if success and 'id' in response:
            activity_id = response['id']
            
            # Update activity status
            success, response = self.run_test(
                "Update Activity Status",
                "PATCH",
                f"activities/{activity_id}/status?status=completed",
                200
            )
            
            return activity_id
        
        return None

    def test_kpis_endpoints(self):
        """Test KPIs endpoints"""
        print("\n" + "="*50)
        print("TESTING KPIs ENDPOINTS")
        print("="*50)
        
        # Get KPIs
        success, kpis = self.run_test(
            "Get KPIs",
            "GET",
            "kpis",
            200
        )
        
        # Create KPI (admin only)
        if self.user_role in ['ceo', 'admin']:
            kpi_data = {
                "name": "Test KPI API",
                "target_value": 100000,
                "current_value": 25000,
                "unit": "currency",
                "period": "monthly",
                "category": "sales"
            }
            
            success, response = self.run_test(
                "Create KPI",
                "POST",
                "kpis",
                200,
                data=kpi_data
            )
            
            if success and 'id' in response:
                kpi_id = response['id']
                
                # Update KPI
                kpi_data['current_value'] = 50000
                success, response = self.run_test(
                    "Update KPI",
                    "PUT",
                    f"kpis/{kpi_id}",
                    200,
                    data=kpi_data
                )

    def test_incentives_endpoints(self):
        """Test incentives endpoints"""
        print("\n" + "="*50)
        print("TESTING INCENTIVES ENDPOINTS")
        print("="*50)
        
        # Get incentives
        success, incentives = self.run_test(
            "Get Incentives",
            "GET",
            "incentives",
            200
        )
        
        # Create incentive (admin only)
        if self.user_role in ['ceo', 'admin']:
            incentive_data = {
                "user_id": self.user_id,
                "name": "Test Incentive API",
                "description": "Test incentive for API testing",
                "target_amount": 10000,
                "earned_amount": 2500,
                "period": "quarterly"
            }
            
            success, response = self.run_test(
                "Create Incentive",
                "POST",
                "incentives",
                200,
                data=incentive_data
            )

    def test_integrations_endpoints(self):
        """Test integrations endpoints"""
        print("\n" + "="*50)
        print("TESTING INTEGRATIONS ENDPOINTS")
        print("="*50)
        
        # Get integrations (admin only)
        if self.user_role in ['ceo', 'admin']:
            success, integrations = self.run_test(
                "Get Integrations",
                "GET",
                "integrations",
                200
            )
            
            # Create/Update integration
            integration_data = {
                "integration_type": "odoo",
                "enabled": False,
                "api_url": "https://test-odoo.com",
                "sync_interval_minutes": 60,
                "settings": {}
            }
            
            success, response = self.run_test(
                "Create/Update Integration",
                "POST",
                "integrations",
                200,
                data=integration_data
            )

    def test_dashboard_endpoints(self):
        """Test dashboard endpoints"""
        print("\n" + "="*50)
        print("TESTING DASHBOARD ENDPOINTS")
        print("="*50)
        
        # Get dashboard stats
        success, stats = self.run_test(
            "Get Dashboard Stats",
            "GET",
            "dashboard/stats",
            200
        )
        
        # Get pipeline by stage
        success, pipeline = self.run_test(
            "Get Pipeline by Stage",
            "GET",
            "dashboard/pipeline-by-stage",
            200
        )
        
        # Get activities by status
        success, activities = self.run_test(
            "Get Activities by Status",
            "GET",
            "dashboard/activities-by-status",
            200
        )
        
        # Get revenue trend
        success, revenue = self.run_test(
            "Get Revenue Trend",
            "GET",
            "dashboard/revenue-trend",
            200
        )

    def test_kanban_endpoints(self):
        """Test Kanban board endpoints"""
        print("\n" + "="*50)
        print("TESTING KANBAN BOARD ENDPOINTS")
        print("="*50)
        
        # Get opportunities kanban view
        success, kanban = self.run_test(
            "Get Opportunities Kanban View",
            "GET",
            "opportunities/kanban",
            200
        )
        
        if success:
            print(f"   Kanban data loaded successfully")
            if 'stages' in kanban:
                print(f"   Number of stages: {len(kanban['stages'])}")
            if 'kanban' in kanban:
                print(f"   Kanban columns: {list(kanban['kanban'].keys())}")

    def test_pipeline_stages(self):
        """Test pipeline stages endpoints"""
        print("\n" + "="*50)
        print("TESTING PIPELINE STAGES")
        print("="*50)
        
        # Get pipeline stages
        success, stages = self.run_test(
            "Get Pipeline Stages",
            "GET",
            "pipeline-stages",
            200
        )
        
        if success:
            print(f"   Pipeline stages loaded successfully")
            if isinstance(stages, list):
                print(f"   Number of stages: {len(stages)}")

    def test_commission_templates(self):
        """Test commission templates endpoints"""
        print("\n" + "="*50)
        print("TESTING COMMISSION TEMPLATES")
        print("="*50)
        
        # Get commission templates
        success, templates = self.run_test(
            "Get Commission Templates",
            "GET",
            "commission-templates",
            200
        )
        
        if success:
            print(f"   Commission templates loaded successfully")
            if isinstance(templates, list):
                print(f"   Number of templates: {len(templates)}")

    def test_incentive_calculator(self):
        """Test incentive calculator endpoint"""
        print("\n" + "="*50)
        print("TESTING INCENTIVE CALCULATOR")
        print("="*50)
        
        # Test incentive calculation
        success, result = self.run_test(
            "Calculate Incentive",
            "POST",
            "incentive-calculator?revenue=100000&quota=500000&is_new_logo=true",
            200
        )
        
        if success:
            print(f"   Incentive calculation successful")
            if 'final_commission' in result:
                print(f"   Final commission: ${result['final_commission']}")

    def test_sales_metrics(self):
        """Test sales metrics endpoint"""
        print("\n" + "="*50)
        print("TESTING SALES METRICS")
        print("="*50)
        
        # Get sales metrics for current user
        success, metrics = self.run_test(
            "Get Sales Metrics",
            "GET",
            f"sales-metrics/{self.user_id}",
            200
        )
        
        if success:
            print(f"   Sales metrics loaded successfully")

    def test_blue_sheet_probability(self, opp_id=None):
        """Test Blue Sheet probability calculation"""
        print("\n" + "="*50)
        print("TESTING BLUE SHEET PROBABILITY")
        print("="*50)
        
        if opp_id:
            # Test Blue Sheet probability calculation
            analysis_data = {
                "opportunity_id": opp_id,
                "economic_buyer_identified": True,
                "economic_buyer_favorable": True,
                "user_buyers_favorable": 2,
                "technical_buyers_favorable": 1,
                "coach_identified": True,
                "coach_engaged": True,
                "clear_business_results": True,
                "quantifiable_value": True
            }
            
            success, result = self.run_test(
                "Calculate Blue Sheet Probability",
                "POST",
                f"opportunities/{opp_id}/calculate-probability",
                200,
                data=analysis_data
            )
            
            if success:
                print(f"   Blue Sheet probability calculated successfully")
                if 'calculated_probability' in result:
                    print(f"   Calculated probability: {result['calculated_probability']}%")

    def test_ai_insights(self):
        """Test AI insights endpoint"""
        print("\n" + "="*50)
        print("TESTING AI INSIGHTS")
        print("="*50)
        
        success, insights = self.run_test(
            "Get AI Insights",
            "POST",
            "ai/insights",
            200
        )
        
        if success:
            print(f"   AI Insights generated successfully")
            if 'insights' in insights:
                print(f"   Number of insights: {len(insights['insights'])}")

def main():
    print("🚀 Starting UAT Fixes Comprehensive Testing")
    print("=" * 60)
    
    tester = UATFixesTester()
    
    # Test credentials
    test_users = [
        ("superadmin@salescommand.com", "demo123", "Super Admin"),
        ("vinsha.nair@securado.net", "demo123", "Manager"),
        ("z.albaloushi@securado.net", "demo123", "Sales Rep")
    ]
    
    all_results = {}
    
    for email, password, role_name in test_users:
        print(f"\n{'='*60}")
        print(f"TESTING AS: {role_name} ({email})")
        print(f"{'='*60}")
        
        # Login
        if not tester.test_login(email, password):
            print(f"❌ Login failed for {email}, skipping tests")
            continue
        
        # Test 1: Activity API Endpoints
        print("\n" + "="*50)
        print("TEST 1: ACTIVITY API ENDPOINTS")
        print("="*50)
        
        # GET /api/activities
        success, activities_response = tester.run_test(
            "GET /api/activities",
            "GET",
            "activities",
            200
        )
        
        if success:
            if isinstance(activities_response, list):
                print(f"   ✅ Activities returned as array: {len(activities_response)} activities")
                all_results[f"{role_name}_activities_array"] = "PASS"
            else:
                print(f"   ❌ Activities should be array, got: {type(activities_response)}")
                all_results[f"{role_name}_activities_array"] = "FAIL"
        
        # GET /api/activities/stats
        success, stats_response = tester.run_test(
            "GET /api/activities/stats",
            "GET",
            "activities/stats",
            200
        )
        
        if success:
            required_fields = ["total", "business_activities", "system_events", "by_type"]
            missing = [f for f in required_fields if f not in stats_response]
            if not missing:
                print(f"   ✅ Stats response has all required fields")
                print(f"      Total: {stats_response.get('total')}, Business: {stats_response.get('business_activities')}")
                all_results[f"{role_name}_activities_stats"] = "PASS"
            else:
                print(f"   ❌ Stats response missing fields: {missing}")
                all_results[f"{role_name}_activities_stats"] = "FAIL"
        
        # Test 2: Sync Integrity (Soft Deletes) - Only for admin
        if email == "superadmin@salescommand.com":
            print("\n" + "="*50)
            print("TEST 2: SYNC INTEGRITY (SOFT DELETES)")
            print("="*50)
            
            success, sync_response = tester.run_test(
                "POST /api/integrations/odoo/sync-all",
                "POST",
                "integrations/odoo/sync-all",
                200
            )
            
            if success:
                if "synced_entities" in sync_response:
                    print(f"   ✅ Sync response includes synced_entities")
                    print(f"      Synced entities: {sync_response.get('synced_entities')}")
                    all_results["sync_integrity"] = "PASS"
                else:
                    print(f"   ❌ Sync response missing synced_entities")
                    all_results["sync_integrity"] = "FAIL"
            
            # Check sync logs for soft-delete counts
            success, logs_response = tester.run_test(
                "GET /api/integrations/sync/logs",
                "GET",
                "integrations/sync/logs?limit=5",
                200
            )
            
            if success and "logs" in logs_response:
                logs = logs_response["logs"]
                if logs:
                    latest_log = logs[0]
                    print(f"   Latest sync log status: {latest_log.get('status')}")
                    if "soft_deleted" in str(latest_log):
                        print(f"   ✅ Sync logs track soft-delete counts")
                    else:
                        print(f"   ⚠️  Soft-delete tracking not visible in logs")
        
        # Test 3: Enhanced Receivables
        print("\n" + "="*50)
        print("TEST 3: ENHANCED RECEIVABLES")
        print("="*50)
        
        success, receivables_response = tester.run_test(
            "GET /api/receivables",
            "GET",
            "receivables",
            200
        )
        
        if success:
            if "invoices" in receivables_response:
                invoices = receivables_response["invoices"]
                print(f"   ✅ Receivables returned {len(invoices)} invoices")
                
                if invoices:
                    sample_invoice = invoices[0]
                    has_salesperson = "salesperson" in sample_invoice
                    has_account_id = "account_id" in sample_invoice
                    
                    if has_salesperson and has_account_id:
                        print(f"   ✅ Invoices include salesperson and account_id fields")
                        print(f"      Sample: salesperson='{sample_invoice.get('salesperson')}', account_id={sample_invoice.get('account_id')}")
                        all_results[f"{role_name}_receivables_enhanced"] = "PASS"
                    else:
                        missing = []
                        if not has_salesperson:
                            missing.append("salesperson")
                        if not has_account_id:
                            missing.append("account_id")
                        print(f"   ❌ Invoices missing fields: {missing}")
                        all_results[f"{role_name}_receivables_enhanced"] = "FAIL"
                else:
                    print(f"   ⚠️  No invoices to verify fields")
                    all_results[f"{role_name}_receivables_enhanced"] = "SKIP"
            else:
                print(f"   ❌ Receivables response missing 'invoices' field")
                all_results[f"{role_name}_receivables_enhanced"] = "FAIL"
        
        # Test 4: Account 360° View with Activities
        print("\n" + "="*50)
        print("TEST 4: ACCOUNT 360° VIEW WITH ACTIVITIES")
        print("="*50)
        
        # Use a known valid account ID from data_lake_serving (account ID 12 = VM)
        # This is more reliable than getting from opportunities which may have mismatched IDs
        account_id = "12"  # VM account from Odoo
        
        success, account_360_response = tester.run_test(
            f"GET /api/accounts/{account_id}/360",
            "GET",
            f"accounts/{account_id}/360",
            200
        )
        
        if success:
            has_activities = "activities" in account_360_response
            has_summary = "summary" in account_360_response
            
            if has_activities and has_summary:
                activities = account_360_response["activities"]
                summary = account_360_response["summary"]
                activity_summary = summary.get("activity_summary", {})
                
                # Check if activity_summary exists in summary
                if activity_summary:
                    print(f"   ✅ Account 360° includes activities ({len(activities)}) and activity_summary")
                    print(f"      Activity summary: total={activity_summary.get('total')}, pending={activity_summary.get('pending')}, overdue={activity_summary.get('overdue')}")
                    
                    # Check if activities from both sources (if any exist)
                    if activities:
                        sources = set(a.get("source") for a in activities)
                        print(f"   ✅ Activities from sources: {sources}")
                    else:
                        print(f"   ℹ️  No activities for this account (expected for test data)")
                    
                    all_results[f"{role_name}_account_360"] = "PASS"
                else:
                    print(f"   ❌ Account 360° summary missing activity_summary field")
                    all_results[f"{role_name}_account_360"] = "FAIL"
            else:
                missing = []
                if not has_activities:
                    missing.append("activities")
                if not has_summary:
                    missing.append("summary")
                print(f"   ❌ Account 360° missing fields: {missing}")
                all_results[f"{role_name}_account_360"] = "FAIL"
        else:
            print(f"   ❌ Account 360° endpoint failed")
            all_results[f"{role_name}_account_360"] = "FAIL"
        
        # Test 5: Goals Team Assignment
        print("\n" + "="*50)
        print("TEST 5: GOALS TEAM ASSIGNMENT")
        print("="*50)
        
        success, subordinates_response = tester.run_test(
            "GET /api/goals/team/subordinates",
            "GET",
            "goals/team/subordinates",
            200
        )
        
        if success:
            has_is_manager = "is_manager" in subordinates_response
            has_subordinates = "subordinates" in subordinates_response
            
            if has_is_manager and has_subordinates:
                is_manager = subordinates_response["is_manager"]
                subordinates = subordinates_response["subordinates"]
                
                print(f"   ✅ Team subordinates response includes is_manager and subordinates")
                print(f"      is_manager: {is_manager}, subordinates count: {len(subordinates)}")
                
                if is_manager and subordinates:
                    print(f"      Subordinates: {[s.get('name') for s in subordinates]}")
                
                all_results[f"{role_name}_goals_team"] = "PASS"
            else:
                missing = []
                if not has_is_manager:
                    missing.append("is_manager")
                if not has_subordinates:
                    missing.append("subordinates")
                print(f"   ❌ Team subordinates response missing fields: {missing}")
                all_results[f"{role_name}_goals_team"] = "FAIL"
    
    # Print final summary
    print("\n" + "="*60)
    print("📊 UAT FIXES TEST RESULTS SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in all_results.values() if v == "PASS")
    failed = sum(1 for v in all_results.values() if v == "FAIL")
    skipped = sum(1 for v in all_results.values() if v == "SKIP")
    partial = sum(1 for v in all_results.values() if v == "PARTIAL")
    
    for test_name, result in all_results.items():
        icon = "✅" if result == "PASS" else "❌" if result == "FAIL" else "⚠️" if result == "PARTIAL" else "⏭️"
        print(f"{icon} {test_name}: {result}")
    
    print(f"\n{'='*60}")
    print(f"Total: {len(all_results)} | Passed: {passed} | Failed: {failed} | Partial: {partial} | Skipped: {skipped}")
    print(f"Success rate: {(passed/(len(all_results)-skipped)*100):.1f}%" if (len(all_results)-skipped) > 0 else "N/A")
    print(f"{'='*60}")
    
    if failed > 0:
        print(f"⚠️  {failed} tests failed")
        return 1
    elif partial > 0:
        print(f"⚠️  {partial} tests partially passed")
        return 0
    else:
        print("🎉 All tests passed!")
        return 0

if __name__ == "__main__":
    sys.exit(main())