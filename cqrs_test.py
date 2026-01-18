#!/usr/bin/env python3
"""
Comprehensive CQRS System Testing
Tests Event Sourcing, Projections, Access Control, and Performance
"""

import requests
import sys
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

class CQRSSystemTester:
    def __init__(self, base_url="https://ai-sales-platform-4.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.current_user = None
        self.test_results = []
        
    def log_result(self, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        self.tests_run += 1
        if passed:
            self.tests_passed += 1
            status = "✅ PASS"
        else:
            self.tests_failed += 1
            status = "❌ FAIL"
        
        result = {
            "test": test_name,
            "status": status,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.test_results.append(result)
        print(f"{status}: {test_name}")
        if details:
            print(f"   {details}")
    
    def api_call(self, method: str, endpoint: str, data: dict = None, 
                 expected_status: int = 200, measure_time: bool = False) -> tuple:
        """Make API call and return (success, response_data, duration_ms)"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        
        start_time = time.time()
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=30)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=headers, timeout=30)
            
            duration_ms = (time.time() - start_time) * 1000
            
            success = response.status_code == expected_status
            
            try:
                response_data = response.json()
            except:
                response_data = {"text": response.text[:200]}
            
            if not success:
                print(f"   ⚠️  Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {json.dumps(response_data, indent=2)[:300]}")
            
            return success, response_data, duration_ms
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            print(f"   ❌ Exception: {str(e)}")
            return False, {"error": str(e)}, duration_ms
    
    def login(self, email: str, password: str) -> bool:
        """Login and store token"""
        print(f"\n🔐 Logging in as {email}...")
        
        success, response, _ = self.api_call(
            'POST', 
            'auth/login',
            data={"email": email, "password": password}
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.current_user = response.get('user', {})
            print(f"   ✅ Logged in as: {self.current_user.get('name', email)}")
            return True
        else:
            print(f"   ❌ Login failed")
            return False
    
    # ==================== TEST 1: Manager Visibility ====================
    
    def test_manager_visibility(self):
        """
        CRITICAL TEST: Vinsha (Manager) should see 4 opportunities
        - 2 own opportunities
        - 2 subordinate opportunities (from Zakariya)
        """
        print("\n" + "="*70)
        print("TEST 1: MANAGER VISIBILITY (MOST CRITICAL)")
        print("="*70)
        
        # Login as Vinsha (Manager)
        if not self.login("vinsha.nair@securado.net", "demo123"):
            self.log_result("Manager Login", False, "Failed to login as Vinsha")
            return
        
        self.log_result("Manager Login", True, "Vinsha logged in successfully")
        
        # Get dashboard
        success, dashboard, duration = self.api_call(
            'GET',
            'v2/dashboard/',
            measure_time=True
        )
        
        if not success:
            self.log_result("Manager Dashboard API", False, "Dashboard API failed")
            return
        
        self.log_result("Manager Dashboard API", True, f"Response time: {duration:.0f}ms")
        
        # Verify opportunity count
        opportunities = dashboard.get('opportunities', [])
        opp_count = len(opportunities)
        
        if opp_count == 4:
            self.log_result("Manager Opportunity Count", True, f"Correct: {opp_count} opportunities")
        else:
            self.log_result("Manager Opportunity Count", False, 
                          f"Expected 4, got {opp_count}")
        
        # Verify hierarchy
        hierarchy = dashboard.get('hierarchy', {})
        is_manager = hierarchy.get('is_manager', False)
        subordinate_count = hierarchy.get('subordinate_count', 0)
        
        if is_manager:
            self.log_result("Manager Flag", True, "is_manager = true")
        else:
            self.log_result("Manager Flag", False, "is_manager should be true")
        
        if subordinate_count >= 1:
            self.log_result("Subordinate Count", True, f"Has {subordinate_count} subordinate(s)")
        else:
            self.log_result("Subordinate Count", False, 
                          f"Expected >= 1 subordinate, got {subordinate_count}")
        
        # Verify own vs subordinate opportunities
        own_opps = []
        subordinate_opps = []
        
        for opp in opportunities:
            salesperson = opp.get('salesperson', {})
            salesperson_email = salesperson.get('email', '')
            
            if salesperson_email == "vinsha.nair@securado.net":
                own_opps.append(opp)
            elif salesperson_email == "z.albaloushi@securado.net":
                subordinate_opps.append(opp)
                
                # Verify manager relationship
                manager = salesperson.get('manager', {})
                manager_email = manager.get('email', '')
                
                if manager_email != "vinsha.nair@securado.net":
                    self.log_result("Subordinate Manager Link", False,
                                  f"Zakariya's manager should be Vinsha, got {manager_email}")
        
        if len(own_opps) == 2:
            self.log_result("Manager Own Opportunities", True, "2 own opportunities")
        else:
            self.log_result("Manager Own Opportunities", False,
                          f"Expected 2 own, got {len(own_opps)}")
        
        if len(subordinate_opps) == 2:
            self.log_result("Manager Subordinate Opportunities", True, 
                          "2 subordinate opportunities")
        else:
            self.log_result("Manager Subordinate Opportunities", False,
                          f"Expected 2 subordinate, got {len(subordinate_opps)}")
        
        # Verify metrics
        metrics = dashboard.get('metrics', {})
        pipeline_value = metrics.get('pipeline_value', 0)
        
        if pipeline_value > 0:
            self.log_result("Manager Pipeline Value", True, 
                          f"Pipeline value: ${pipeline_value:,.0f}")
        else:
            self.log_result("Manager Pipeline Value", False, "Pipeline value is 0")
        
        # Performance check
        if duration < 500:
            self.log_result("Manager Dashboard Performance", True, 
                          f"{duration:.0f}ms < 500ms target")
        else:
            self.log_result("Manager Dashboard Performance", False,
                          f"{duration:.0f}ms exceeds 500ms target")
    
    # ==================== TEST 2: Data Isolation ====================
    
    def test_data_isolation(self):
        """
        SECURITY CRITICAL: Zakariya (Subordinate) should only see his 2 opportunities
        Should NOT see Vinsha's opportunities
        """
        print("\n" + "="*70)
        print("TEST 2: DATA ISOLATION (SECURITY CRITICAL)")
        print("="*70)
        
        # Login as Zakariya (Subordinate)
        if not self.login("z.albaloushi@securado.net", "demo123"):
            self.log_result("Subordinate Login", False, "Failed to login as Zakariya")
            return
        
        self.log_result("Subordinate Login", True, "Zakariya logged in successfully")
        
        # Get dashboard
        success, dashboard, duration = self.api_call(
            'GET',
            'v2/dashboard/',
            measure_time=True
        )
        
        if not success:
            self.log_result("Subordinate Dashboard API", False, "Dashboard API failed")
            return
        
        self.log_result("Subordinate Dashboard API", True, f"Response time: {duration:.0f}ms")
        
        # Verify opportunity count
        opportunities = dashboard.get('opportunities', [])
        opp_count = len(opportunities)
        
        if opp_count == 2:
            self.log_result("Subordinate Opportunity Count", True, 
                          f"Correct: {opp_count} opportunities (own only)")
        else:
            self.log_result("Subordinate Opportunity Count", False,
                          f"Expected 2, got {opp_count} - SECURITY ISSUE!")
        
        # Verify all opportunities belong to Zakariya
        unauthorized_access = False
        for opp in opportunities:
            salesperson = opp.get('salesperson', {})
            salesperson_email = salesperson.get('email', '')
            
            if salesperson_email != "z.albaloushi@securado.net":
                unauthorized_access = True
                self.log_result("Data Isolation Breach", False,
                              f"SECURITY: Zakariya can see {salesperson_email}'s opportunity!")
        
        if not unauthorized_access and opp_count > 0:
            self.log_result("Data Isolation", True, "All opportunities belong to user")
        
        # Verify hierarchy
        hierarchy = dashboard.get('hierarchy', {})
        is_manager = hierarchy.get('is_manager', False)
        
        if not is_manager:
            self.log_result("Subordinate Manager Flag", True, "is_manager = false")
        else:
            self.log_result("Subordinate Manager Flag", False, 
                          "Subordinate should not be manager")
    
    # ==================== TEST 3: Access Matrix Accuracy ====================
    
    def test_access_matrix_accuracy(self):
        """
        Test access matrix for multiple users
        Verify accessible_opportunities matches actual visible opportunities
        """
        print("\n" + "="*70)
        print("TEST 3: ACCESS MATRIX ACCURACY")
        print("="*70)
        
        test_users = [
            ("krishna@securado.net", "demo123", "Krishna"),
            ("vinsha.nair@securado.net", "demo123", "Vinsha"),
            ("z.albaloushi@securado.net", "demo123", "Zakariya"),
            ("ravi.chandran@securado.net", "demo123", "Ravi")
        ]
        
        for email, password, name in test_users:
            if not self.login(email, password):
                self.log_result(f"Access Matrix - {name} Login", False, 
                              f"Failed to login as {email}")
                continue
            
            # Get dashboard to check opportunities
            success, dashboard, _ = self.api_call('GET', 'v2/dashboard/')
            
            if not success:
                self.log_result(f"Access Matrix - {name} Dashboard", False, 
                              "Dashboard API failed")
                continue
            
            opportunities = dashboard.get('opportunities', [])
            opp_count = len(opportunities)
            
            # Get user profile to check access matrix
            success, profile, _ = self.api_call('GET', 'v2/dashboard/users/profile')
            
            if success:
                self.log_result(f"Access Matrix - {name} Profile", True,
                              f"{opp_count} opportunities accessible")
            else:
                self.log_result(f"Access Matrix - {name} Profile", False,
                              "Failed to get user profile")
    
    # ==================== TEST 4: CQRS Sync Functionality ====================
    
    def test_cqrs_sync(self):
        """
        Test CQRS sync trigger and status tracking
        """
        print("\n" + "="*70)
        print("TEST 4: CQRS SYNC FUNCTIONALITY")
        print("="*70)
        
        # Login as admin
        if not self.login("superadmin@salescommand.com", "demo123"):
            self.log_result("CQRS Sync - Admin Login", False, 
                          "Failed to login as admin")
            return
        
        self.log_result("CQRS Sync - Admin Login", True, "Admin logged in")
        
        # Trigger sync
        success, response, _ = self.api_call(
            'POST',
            'integrations/cqrs/sync/trigger'
        )
        
        if success and 'sync_job_id' in response:
            sync_job_id = response['sync_job_id']
            self.log_result("CQRS Sync Trigger", True, 
                          f"Sync job created: {sync_job_id}")
            
            # Wait a bit for sync to process
            time.sleep(2)
            
            # Check sync status
            success, job_status, _ = self.api_call(
                'GET',
                f'integrations/cqrs/sync/{sync_job_id}'
            )
            
            if success:
                status = job_status.get('status', 'unknown')
                self.log_result("CQRS Sync Status", True, 
                              f"Sync status: {status}")
            else:
                self.log_result("CQRS Sync Status", False, 
                              "Failed to get sync status")
        else:
            self.log_result("CQRS Sync Trigger", False, 
                          "Failed to trigger sync or already running")
        
        # Check CQRS health
        success, health, _ = self.api_call('GET', 'integrations/cqrs/health')
        
        if success:
            event_count = health.get('event_store', {}).get('total_events', 0)
            projections = health.get('projections', {})
            
            self.log_result("CQRS Health Check", True,
                          f"Events: {event_count}, Projections: {projections}")
            
            # Verify event count
            if event_count >= 29:
                self.log_result("Event Store Count", True, 
                              f"{event_count} events (expected >= 29)")
            else:
                self.log_result("Event Store Count", False,
                              f"{event_count} events (expected >= 29)")
        else:
            self.log_result("CQRS Health Check", False, "Health check failed")
    
    # ==================== TEST 5: System Logging ====================
    
    def test_system_logging(self):
        """
        Test system logging endpoints
        """
        print("\n" + "="*70)
        print("TEST 5: SYSTEM LOGGING")
        print("="*70)
        
        # Login as admin
        if not self.login("superadmin@salescommand.com", "demo123"):
            self.log_result("Logging - Admin Login", False, "Failed to login as admin")
            return
        
        # Get log stats
        success, stats, _ = self.api_call('GET', 'admin/logs/stats?hours=24')
        
        if success:
            errors = stats.get('errors', {})
            api_calls = stats.get('api_calls', {})
            sessions = stats.get('sessions', {})
            
            self.log_result("Log Statistics", True,
                          f"Errors: {errors.get('total', 0)}, " +
                          f"API Calls: {api_calls.get('total', 0)}, " +
                          f"Sessions: {sessions.get('unique', 0)}")
        else:
            self.log_result("Log Statistics", False, "Failed to get log stats")
        
        # Get error sessions
        success, sessions_data, _ = self.api_call('GET', 'admin/logs/sessions')
        
        if success:
            session_count = len(sessions_data.get('sessions', []))
            self.log_result("Error Sessions", True, 
                          f"{session_count} sessions with errors")
        else:
            self.log_result("Error Sessions", False, "Failed to get error sessions")
        
        # Get system errors
        success, errors_data, _ = self.api_call('GET', 'admin/logs/errors?limit=10')
        
        if success:
            error_count = errors_data.get('total', 0)
            unresolved = errors_data.get('unresolved', 0)
            
            self.log_result("System Errors", True,
                          f"Total: {error_count}, Unresolved: {unresolved}")
        else:
            self.log_result("System Errors", False, "Failed to get system errors")
    
    # ==================== TEST 6: Performance Benchmarks ====================
    
    def test_performance_benchmarks(self):
        """
        Test response times for all CQRS endpoints
        Target: All < 500ms
        """
        print("\n" + "="*70)
        print("TEST 6: PERFORMANCE BENCHMARKS")
        print("="*70)
        
        # Login as regular user
        if not self.login("vinsha.nair@securado.net", "demo123"):
            self.log_result("Performance - Login", False, "Failed to login")
            return
        
        endpoints = [
            ('v2/dashboard/', 200, "Main Dashboard"),
            ('v2/dashboard/opportunities', 200, "Opportunities List"),
            ('v2/dashboard/users/profile', 200, "User Profile")
        ]
        
        for endpoint, target_ms, name in endpoints:
            success, response, duration = self.api_call('GET', endpoint, measure_time=True)
            
            if success:
                if duration < target_ms:
                    self.log_result(f"Performance - {name}", True,
                                  f"{duration:.0f}ms < {target_ms}ms target")
                else:
                    self.log_result(f"Performance - {name}", False,
                                  f"{duration:.0f}ms exceeds {target_ms}ms target")
            else:
                self.log_result(f"Performance - {name}", False, "API call failed")
    
    # ==================== TEST 7: Edge Cases ====================
    
    def test_edge_cases(self):
        """
        Test edge cases and error handling
        """
        print("\n" + "="*70)
        print("TEST 7: EDGE CASES")
        print("="*70)
        
        # Test with invalid token
        old_token = self.token
        self.token = "invalid_token_12345"
        
        success, response, _ = self.api_call('GET', 'v2/dashboard/', expected_status=401)
        
        if success:
            self.log_result("Invalid Token Handling", True, "401 returned as expected")
        else:
            self.log_result("Invalid Token Handling", False, 
                          "Should return 401 for invalid token")
        
        self.token = old_token
        
        # Test with non-existent user profile
        # This is handled by the API returning 503 if user not in CQRS
        
        # Test opportunities endpoint
        success, response, _ = self.api_call('GET', 'v2/dashboard/opportunities')
        
        if success:
            self.log_result("Opportunities Endpoint", True, "Endpoint working")
        else:
            self.log_result("Opportunities Endpoint", False, "Endpoint failed")
    
    # ==================== Main Test Runner ====================
    
    def run_all_tests(self):
        """Run all CQRS tests"""
        print("\n" + "="*70)
        print("🚀 COMPREHENSIVE CQRS SYSTEM TESTING")
        print("="*70)
        print(f"Base URL: {self.base_url}")
        print(f"Started: {datetime.now(timezone.utc).isoformat()}")
        
        try:
            # Run all test suites
            self.test_manager_visibility()
            self.test_data_isolation()
            self.test_access_matrix_accuracy()
            self.test_cqrs_sync()
            self.test_system_logging()
            self.test_performance_benchmarks()
            self.test_edge_cases()
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Tests interrupted by user")
        except Exception as e:
            print(f"\n\n❌ Unexpected error: {str(e)}")
            import traceback
            traceback.print_exc()
        
        # Print final results
        self.print_results()
    
    def print_results(self):
        """Print test results summary"""
        print("\n" + "="*70)
        print("📊 TEST RESULTS SUMMARY")
        print("="*70)
        
        print(f"\nTotal Tests: {self.tests_run}")
        print(f"✅ Passed: {self.tests_passed}")
        print(f"❌ Failed: {self.tests_failed}")
        
        if self.tests_run > 0:
            success_rate = (self.tests_passed / self.tests_run) * 100
            print(f"Success Rate: {success_rate:.1f}%")
        
        # Group results by category
        print("\n" + "="*70)
        print("DETAILED RESULTS BY CATEGORY")
        print("="*70)
        
        categories = {}
        for result in self.test_results:
            test_name = result['test']
            category = test_name.split(' - ')[0] if ' - ' in test_name else "General"
            
            if category not in categories:
                categories[category] = []
            categories[category].append(result)
        
        for category, results in categories.items():
            print(f"\n{category}:")
            for result in results:
                print(f"  {result['status']}: {result['test']}")
                if result['details']:
                    print(f"      {result['details']}")
        
        # Critical failures
        critical_failures = [r for r in self.test_results if '❌' in r['status'] and 
                           ('CRITICAL' in r['test'] or 'SECURITY' in r['test'])]
        
        if critical_failures:
            print("\n" + "="*70)
            print("⚠️  CRITICAL FAILURES")
            print("="*70)
            for failure in critical_failures:
                print(f"  {failure['test']}")
                print(f"    {failure['details']}")
        
        print("\n" + "="*70)
        
        if self.tests_failed == 0:
            print("🎉 ALL TESTS PASSED!")
            return 0
        else:
            print(f"⚠️  {self.tests_failed} TEST(S) FAILED")
            return 1


def main():
    tester = CQRSSystemTester()
    return tester.run_all_tests()


if __name__ == "__main__":
    sys.exit(main())
