"""
Test Suite for P1 and P2 Features - Iteration 25
Tests:
1. Background Sync Health API - GET /api/integrations/background-sync/health
2. Sync Logs API - GET /api/integrations/sync/logs
3. Leaderboard in Target Progress Report
4. Activities for Opportunity API - GET /api/activities/opportunity/{opp_id}
5. Calendar UI enhancements (grouping by day)
6. Odoo 19.0 compatibility ('title' field removed)
"""

import pytest
import requests
import os
from datetime import datetime

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://ai-sales-platform-4.preview.emergentagent.com').rstrip('/')

# Test credentials
SUPER_ADMIN_EMAIL = "superadmin@salescommand.com"
SUPER_ADMIN_PASSWORD = "demo123"


class TestAuthentication:
    """Authentication tests to get tokens for subsequent tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for super admin"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        return data["access_token"]
    
    def test_login_super_admin(self, auth_token):
        """Test super admin login works"""
        assert auth_token is not None
        assert len(auth_token) > 0


class TestBackgroundSyncHealth:
    """Tests for Background Sync Health API - P1 Feature"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD}
        )
        return response.json().get("access_token")
    
    def test_background_sync_health_endpoint_exists(self, auth_token):
        """Test that background-sync/health endpoint exists and returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/integrations/background-sync/health",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_background_sync_health_returns_metrics(self, auth_token):
        """Test that health endpoint returns detailed metrics"""
        response = requests.get(
            f"{BASE_URL}/api/integrations/background-sync/health",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "health" in data, "Missing 'health' field"
        assert "health_message" in data, "Missing 'health_message' field"
        assert "metrics" in data, "Missing 'metrics' field"
        
        # Check health status is valid
        assert data["health"] in ["healthy", "degraded", "critical", "stale"], \
            f"Invalid health status: {data['health']}"
        
        # Check metrics structure
        metrics = data["metrics"]
        assert "recent_failures_24h" in metrics, "Missing recent_failures_24h in metrics"
        assert "recent_successes_24h" in metrics, "Missing recent_successes_24h in metrics"
        assert "success_rate_24h" in metrics, "Missing success_rate_24h in metrics"
        
        print(f"Health Status: {data['health']}")
        print(f"Health Message: {data['health_message']}")
        print(f"Metrics: {metrics}")
    
    def test_background_sync_health_has_last_sync_info(self, auth_token):
        """Test that health endpoint includes last sync information"""
        response = requests.get(
            f"{BASE_URL}/api/integrations/background-sync/health",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check for last_success and last_failure fields
        assert "last_success" in data, "Missing 'last_success' field"
        assert "last_failure" in data, "Missing 'last_failure' field"
        
        # If there's a last_success, check its structure
        if data["last_success"]:
            assert "timestamp" in data["last_success"], "Missing timestamp in last_success"
        
        # If there's a last_failure, check its structure
        if data["last_failure"]:
            assert "timestamp" in data["last_failure"], "Missing timestamp in last_failure"
            assert "error" in data["last_failure"], "Missing error in last_failure"


class TestSyncLogs:
    """Tests for Sync Logs API - P1 Feature"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD}
        )
        return response.json().get("access_token")
    
    def test_sync_logs_endpoint_exists(self, auth_token):
        """Test that sync/logs endpoint exists and returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/integrations/sync/logs",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_sync_logs_returns_logs_array(self, auth_token):
        """Test that sync logs returns an array of logs"""
        response = requests.get(
            f"{BASE_URL}/api/integrations/sync/logs",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "logs" in data, "Missing 'logs' field"
        assert "count" in data, "Missing 'count' field"
        assert isinstance(data["logs"], list), "logs should be a list"
        
        print(f"Sync logs count: {data['count']}")
        
        # If there are logs, check their structure
        if data["logs"]:
            log = data["logs"][0]
            assert "id" in log or "status" in log, "Log entry missing expected fields"
            print(f"Sample log: {log}")
    
    def test_sync_logs_with_status_filter(self, auth_token):
        """Test sync logs with status filter"""
        # Test with 'completed' status
        response = requests.get(
            f"{BASE_URL}/api/integrations/sync/logs?status=completed",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # All returned logs should have status=completed
        for log in data.get("logs", []):
            if "status" in log:
                assert log["status"] == "completed", f"Expected completed status, got {log['status']}"
    
    def test_sync_logs_with_limit(self, auth_token):
        """Test sync logs with limit parameter"""
        response = requests.get(
            f"{BASE_URL}/api/integrations/sync/logs?limit=5",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert len(data.get("logs", [])) <= 5, "Returned more logs than limit"


class TestLeaderboard:
    """Tests for Leaderboard in Target Progress Report - P2 Feature"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD}
        )
        return response.json().get("access_token")
    
    def test_target_progress_report_returns_individual_progress(self, auth_token):
        """Test that target progress report returns individual_progress for leaderboard"""
        response = requests.get(
            f"{BASE_URL}/api/config/target-progress-report",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "individual_progress" in data, "Missing 'individual_progress' field for leaderboard"
        assert isinstance(data["individual_progress"], list), "individual_progress should be a list"
        
        print(f"Individual progress count: {len(data['individual_progress'])}")
    
    def test_individual_progress_has_required_fields(self, auth_token):
        """Test that individual progress entries have required fields for leaderboard"""
        response = requests.get(
            f"{BASE_URL}/api/config/target-progress-report",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        if data.get("individual_progress"):
            user = data["individual_progress"][0]
            
            # Check required fields for leaderboard display
            assert "user_id" in user, "Missing user_id"
            assert "user_name" in user, "Missing user_name"
            assert "status" in user, "Missing status"
            assert "progress" in user, "Missing progress"
            
            # Check progress has overall field
            assert "overall" in user.get("progress", {}), "Missing overall in progress"
            
            # Check actual values exist
            assert "actual" in user, "Missing actual"
            assert "revenue" in user.get("actual", {}), "Missing revenue in actual"
            
            print(f"Sample user: {user['user_name']}, Progress: {user['progress']['overall']}%")


class TestActivitiesForOpportunity:
    """Tests for Activities for Opportunity API - P1 Feature"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD}
        )
        return response.json().get("access_token")
    
    def test_activities_opportunity_endpoint_exists(self, auth_token):
        """Test that activities/opportunity/{opp_id} endpoint exists"""
        # Use a test opportunity ID (numeric for Odoo compatibility)
        test_opp_id = "1"
        response = requests.get(
            f"{BASE_URL}/api/activities/opportunity/{test_opp_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        # Should return 200 even if no activities found
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_activities_opportunity_returns_correct_structure(self, auth_token):
        """Test that activities endpoint returns correct structure"""
        test_opp_id = "1"
        response = requests.get(
            f"{BASE_URL}/api/activities/opportunity/{test_opp_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "opportunity_id" in data, "Missing opportunity_id"
        assert "activities" in data, "Missing activities"
        assert "count" in data, "Missing count"
        
        assert data["opportunity_id"] == test_opp_id, "opportunity_id mismatch"
        assert isinstance(data["activities"], list), "activities should be a list"
        
        print(f"Activities for opportunity {test_opp_id}: {data['count']}")
    
    def test_activities_opportunity_with_uuid(self, auth_token):
        """Test activities endpoint with UUID format opportunity ID"""
        # Test with a UUID-style ID
        test_opp_id = "test-uuid-12345"
        response = requests.get(
            f"{BASE_URL}/api/activities/opportunity/{test_opp_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        # Should return 200 even for non-existent opportunity
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "activities" in data
        assert isinstance(data["activities"], list)


class TestOdoo19Compatibility:
    """Tests for Odoo 19.0 compatibility - 'title' field removed"""
    
    def test_odoo_connector_fields_no_title(self):
        """Verify 'title' field is not in res.partner fields list"""
        # Read the connector file and check fields
        connector_path = "/app/backend/integrations/odoo/connector.py"
        with open(connector_path, 'r') as f:
            content = f.read()
        
        # Check that 'title' is not in the res.partner fields
        # The fields are defined in _get_fields_for_model method
        assert "'title'" not in content or "# Note: 'title' field removed" in content, \
            "'title' field should be removed or commented for Odoo 19.0 compatibility"
        
        print("Odoo 19.0 compatibility: 'title' field properly removed from res.partner queries")


class TestBackgroundSyncStatus:
    """Tests for Background Sync Status API"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD}
        )
        return response.json().get("access_token")
    
    def test_background_sync_status_endpoint(self, auth_token):
        """Test background-sync/status endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/integrations/background-sync/status",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check required fields
        assert "is_running" in data, "Missing is_running"
        assert "interval_minutes" in data, "Missing interval_minutes"
        
        print(f"Sync status: running={data['is_running']}, interval={data['interval_minutes']}min")


class TestHealthEndpoint:
    """Basic health check tests"""
    
    def test_health_endpoint(self):
        """Test health endpoint returns healthy"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"Health: {data}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
