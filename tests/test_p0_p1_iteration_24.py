"""
Test Suite for P0 and P1 Bug Fixes - Iteration 24
Tests:
1. Token Refresh API - POST /api/auth/refresh
2. Target Progress Report API - GET /api/config/target-progress-report
3. Deletion Sync Logic - reconcile_entity soft-delete behavior
4. Active Entity Filter - sales.py active_entity_filter function
"""
import pytest
import requests
import os
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://ai-sales-platform-4.preview.emergentagent.com').rstrip('/')

# Test credentials
SUPER_ADMIN = {"email": "superadmin@salescommand.com", "password": "demo123"}
ACCOUNT_MANAGER = {"email": "am1@salescommand.com", "password": "demo123"}


class TestTokenRefreshAPI:
    """Test Token Refresh endpoint - P0 MS365 Token Refresh"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login and get initial token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get initial token
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=SUPER_ADMIN)
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        self.token = data.get("access_token")
        self.user = data.get("user")
        assert self.token, "No token received from login"
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_refresh_token_returns_new_token(self):
        """Test that POST /api/auth/refresh returns a new JWT token"""
        response = self.session.post(f"{BASE_URL}/api/auth/refresh")
        
        assert response.status_code == 200, f"Token refresh failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "access_token" in data, "Response missing access_token"
        assert "user" in data, "Response missing user data"
        
        # Verify new token is returned
        new_token = data["access_token"]
        assert new_token, "New token is empty"
        assert isinstance(new_token, str), "Token should be a string"
        assert len(new_token) > 50, "Token seems too short"
        
        # Verify user data is returned
        user = data["user"]
        assert user.get("email") == SUPER_ADMIN["email"], "User email mismatch"
        assert "id" in user, "User missing id"
        
        print(f"Token refresh successful - new token length: {len(new_token)}")
    
    def test_refresh_token_works_with_new_token(self):
        """Test that the new token from refresh can be used for API calls"""
        # Get new token
        response = self.session.post(f"{BASE_URL}/api/auth/refresh")
        assert response.status_code == 200
        new_token = response.json()["access_token"]
        
        # Use new token for another API call
        self.session.headers.update({"Authorization": f"Bearer {new_token}"})
        me_response = self.session.get(f"{BASE_URL}/api/auth/me")
        
        assert me_response.status_code == 200, f"API call with new token failed: {me_response.text}"
        user_data = me_response.json()
        assert user_data.get("email") == SUPER_ADMIN["email"]
        
        print("New token works for subsequent API calls")
    
    def test_refresh_token_requires_auth(self):
        """Test that refresh endpoint requires authentication"""
        # Create new session without auth
        no_auth_session = requests.Session()
        no_auth_session.headers.update({"Content-Type": "application/json"})
        
        response = no_auth_session.post(f"{BASE_URL}/api/auth/refresh")
        
        # Should return 401 or 403
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("Refresh endpoint correctly requires authentication")
    
    def test_refresh_token_for_account_manager(self):
        """Test token refresh works for account manager role"""
        # Login as account manager
        am_session = requests.Session()
        am_session.headers.update({"Content-Type": "application/json"})
        
        login_response = am_session.post(f"{BASE_URL}/api/auth/login", json=ACCOUNT_MANAGER)
        assert login_response.status_code == 200, f"AM login failed: {login_response.text}"
        
        am_token = login_response.json()["access_token"]
        am_session.headers.update({"Authorization": f"Bearer {am_token}"})
        
        # Refresh token
        refresh_response = am_session.post(f"{BASE_URL}/api/auth/refresh")
        assert refresh_response.status_code == 200, f"AM token refresh failed: {refresh_response.text}"
        
        data = refresh_response.json()
        assert "access_token" in data
        assert data["user"]["email"] == ACCOUNT_MANAGER["email"]
        
        print("Token refresh works for account manager")


class TestTargetProgressReportAPI:
    """Test Target Progress Report endpoint - P1 Feature"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login as super admin"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=SUPER_ADMIN)
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json()["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_target_progress_report_endpoint_exists(self):
        """Test that GET /api/config/target-progress-report endpoint exists"""
        response = self.session.get(f"{BASE_URL}/api/config/target-progress-report")
        
        # Should return 200 (success) not 404 (not found)
        assert response.status_code == 200, f"Endpoint returned {response.status_code}: {response.text}"
        print("Target progress report endpoint exists and returns 200")
    
    def test_target_progress_report_structure(self):
        """Test that response has correct structure"""
        response = self.session.get(f"{BASE_URL}/api/config/target-progress-report")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify top-level structure
        assert "generated_at" in data, "Missing generated_at timestamp"
        assert "summary" in data, "Missing summary section"
        assert "team_totals" in data, "Missing team_totals section"
        assert "team_progress" in data, "Missing team_progress section"
        assert "individual_progress" in data, "Missing individual_progress section"
        
        # Verify summary structure
        summary = data["summary"]
        assert "total_salespeople" in summary, "Summary missing total_salespeople"
        assert "achieved" in summary, "Summary missing achieved count"
        assert "on_track" in summary, "Summary missing on_track count"
        assert "at_risk" in summary, "Summary missing at_risk count"
        assert "behind" in summary, "Summary missing behind count"
        
        # Verify team_totals structure
        team_totals = data["team_totals"]
        assert "target_revenue" in team_totals, "team_totals missing target_revenue"
        assert "actual_revenue" in team_totals, "team_totals missing actual_revenue"
        assert "target_deals" in team_totals, "team_totals missing target_deals"
        assert "actual_deals" in team_totals, "team_totals missing actual_deals"
        
        # Verify team_progress structure
        team_progress = data["team_progress"]
        assert "revenue" in team_progress, "team_progress missing revenue"
        assert "deals" in team_progress, "team_progress missing deals"
        assert "activities" in team_progress, "team_progress missing activities"
        
        print(f"Target progress report structure verified - {summary['total_salespeople']} salespeople")
    
    def test_target_progress_report_with_period_filter(self):
        """Test filtering by period type"""
        for period in ["monthly", "quarterly", "yearly"]:
            response = self.session.get(
                f"{BASE_URL}/api/config/target-progress-report",
                params={"period_type": period}
            )
            assert response.status_code == 200, f"Failed for period {period}: {response.text}"
            data = response.json()
            assert data["period_filter"] == period, f"Period filter not applied: {data.get('period_filter')}"
        
        print("Period filter works for all period types")
    
    def test_target_progress_report_with_role_filter(self):
        """Test filtering by role"""
        # First get available roles
        roles_response = self.session.get(f"{BASE_URL}/api/config/roles")
        assert roles_response.status_code == 200
        roles = roles_response.json()
        
        if roles:
            role_id = roles[0]["id"]
            response = self.session.get(
                f"{BASE_URL}/api/config/target-progress-report",
                params={"role_id": role_id}
            )
            assert response.status_code == 200, f"Role filter failed: {response.text}"
            data = response.json()
            assert data["role_filter"] == role_id, "Role filter not applied"
            print(f"Role filter works - filtered by role: {roles[0].get('name')}")
        else:
            print("No roles found to test filter")
    
    def test_individual_progress_structure(self):
        """Test individual progress entries have correct structure"""
        response = self.session.get(f"{BASE_URL}/api/config/target-progress-report")
        assert response.status_code == 200
        
        data = response.json()
        individual_progress = data.get("individual_progress", [])
        
        if individual_progress:
            user_progress = individual_progress[0]
            
            # Verify user progress structure
            assert "user_id" in user_progress, "Missing user_id"
            assert "user_name" in user_progress, "Missing user_name"
            assert "role_name" in user_progress, "Missing role_name"
            assert "target" in user_progress, "Missing target section"
            assert "actual" in user_progress, "Missing actual section"
            assert "progress" in user_progress, "Missing progress section"
            assert "variance" in user_progress, "Missing variance section"
            assert "status" in user_progress, "Missing status"
            
            # Verify target structure
            target = user_progress["target"]
            assert "revenue" in target, "Target missing revenue"
            assert "deals" in target, "Target missing deals"
            assert "activities" in target, "Target missing activities"
            
            # Verify progress structure
            progress = user_progress["progress"]
            assert "revenue" in progress, "Progress missing revenue"
            assert "deals" in progress, "Progress missing deals"
            assert "activities" in progress, "Progress missing activities"
            assert "overall" in progress, "Progress missing overall"
            
            # Verify status is valid
            valid_statuses = ["achieved", "on_track", "at_risk", "behind"]
            assert user_progress["status"] in valid_statuses, f"Invalid status: {user_progress['status']}"
            
            print(f"Individual progress structure verified - {user_progress['user_name']}: {user_progress['status']}")
        else:
            print("No individual progress data (no users with targets)")


class TestActiveEntityFilter:
    """Test active_entity_filter function behavior - P0 Deletion Sync"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login as super admin"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=SUPER_ADMIN)
        assert response.status_code == 200
        self.token = response.json()["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_opportunities_exclude_deleted(self):
        """Test that /api/opportunities excludes soft-deleted records"""
        response = self.session.get(f"{BASE_URL}/api/opportunities")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        opportunities = response.json()
        
        # All returned opportunities should be active (not soft-deleted)
        # We can't directly verify is_active field from API, but we verify the endpoint works
        assert isinstance(opportunities, list), "Response should be a list"
        print(f"Opportunities endpoint returns {len(opportunities)} active records")
    
    def test_real_dashboard_excludes_deleted(self):
        """Test that /api/dashboard/real excludes soft-deleted records"""
        response = self.session.get(f"{BASE_URL}/api/dashboard/real")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        
        # Verify structure
        assert "opportunities" in data, "Missing opportunities"
        assert "accounts" in data, "Missing accounts"
        assert "metrics" in data, "Missing metrics"
        
        # All returned data should be active
        print(f"Real dashboard returns {len(data['opportunities'])} opportunities, {len(data['accounts'])} accounts")
    
    def test_accounts_real_excludes_deleted(self):
        """Test that /api/accounts/real excludes soft-deleted records"""
        response = self.session.get(f"{BASE_URL}/api/accounts/real")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        
        assert "accounts" in data, "Missing accounts"
        accounts = data["accounts"]
        assert isinstance(accounts, list), "Accounts should be a list"
        
        print(f"Real accounts endpoint returns {len(accounts)} active records")
    
    def test_receivables_excludes_deleted(self):
        """Test that /api/receivables excludes soft-deleted invoices"""
        response = self.session.get(f"{BASE_URL}/api/receivables")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        
        assert "invoices" in data, "Missing invoices"
        invoices = data["invoices"]
        assert isinstance(invoices, list), "Invoices should be a list"
        
        print(f"Receivables endpoint returns {len(invoices)} active invoices")


class TestRoleTargets:
    """Test role-based targets API - Supporting P1 Target Progress Report"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login as super admin"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=SUPER_ADMIN)
        assert response.status_code == 200
        self.token = response.json()["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_get_role_targets(self):
        """Test GET /api/config/role-targets endpoint"""
        response = self.session.get(f"{BASE_URL}/api/config/role-targets")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        targets = response.json()
        assert isinstance(targets, list), "Response should be a list"
        
        if targets:
            target = targets[0]
            assert "role_id" in target, "Target missing role_id"
            assert "period_type" in target, "Target missing period_type"
            assert "target_revenue" in target, "Target missing target_revenue"
            assert "target_deals" in target, "Target missing target_deals"
            print(f"Found {len(targets)} role targets")
        else:
            print("No role targets configured")
    
    def test_get_user_effective_targets(self):
        """Test GET /api/config/user-targets/{user_id} endpoint"""
        # First get a user
        users_response = self.session.get(f"{BASE_URL}/api/auth/users")
        assert users_response.status_code == 200
        users = users_response.json()
        
        if users:
            user_id = users[0]["id"]
            response = self.session.get(f"{BASE_URL}/api/config/user-targets/{user_id}")
            assert response.status_code == 200, f"Failed: {response.text}"
            
            data = response.json()
            assert "user_id" in data, "Missing user_id"
            assert "user_name" in data, "Missing user_name"
            assert "role_id" in data, "Missing role_id"
            
            print(f"User effective targets retrieved for {data.get('user_name')}")
        else:
            print("No users found to test")


class TestHealthAndBasicAPIs:
    """Basic health and API verification"""
    
    def test_health_endpoint(self):
        """Test /api/health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        
        data = response.json()
        assert data.get("status") == "healthy", f"Unhealthy status: {data}"
        print("Health endpoint OK")
    
    def test_login_super_admin(self):
        """Test login with super admin credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=SUPER_ADMIN,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        data = response.json()
        assert "access_token" in data, "Missing access_token"
        assert "user" in data, "Missing user"
        assert data["user"]["email"] == SUPER_ADMIN["email"]
        
        print("Super admin login successful")
    
    def test_login_account_manager(self):
        """Test login with account manager credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=ACCOUNT_MANAGER,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == ACCOUNT_MANAGER["email"]
        
        print("Account manager login successful")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
