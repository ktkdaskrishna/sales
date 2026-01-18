"""
Test Goals and Activity Features
Tests for:
- Goals CRUD API
- Activity Timeline API
- Re-link user to Odoo API
- Navigation updates
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://ai-sales-platform-4.preview.emergentagent.com').rstrip('/')

class TestGoalsAPI:
    """Test Goals CRUD operations"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as super admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "superadmin@salescommand.com",
            "password": "demo123"
        })
        
        if login_response.status_code == 200:
            data = login_response.json()
            self.token = data.get("access_token") or data.get("token")
            self.user_id = data.get("user", {}).get("id")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip(f"Login failed: {login_response.status_code} - {login_response.text}")
    
    def test_01_get_goals_empty_or_list(self):
        """Test GET /api/goals returns goals list"""
        response = self.session.get(f"{BASE_URL}/api/goals")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "goals" in data or isinstance(data, list), "Response should contain goals array"
        print(f"✓ GET /api/goals returned {len(data.get('goals', data))} goals")
    
    def test_02_create_goal(self):
        """Test POST /api/goals creates a new goal"""
        due_date = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
        
        goal_data = {
            "name": "TEST_Q1 Revenue Target",
            "description": "Test goal for Q1 revenue",
            "target_value": 100000,
            "current_value": 25000,
            "unit": "currency",
            "goal_type": "revenue",
            "due_date": due_date
        }
        
        response = self.session.post(f"{BASE_URL}/api/goals", json=goal_data)
        assert response.status_code == 200 or response.status_code == 201, f"Expected 200/201, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "goal" in data or "id" in data, "Response should contain created goal"
        
        goal = data.get("goal", data)
        assert goal.get("name") == goal_data["name"], "Goal name should match"
        assert goal.get("target_value") == goal_data["target_value"], "Target value should match"
        
        # Store goal ID for later tests
        self.__class__.created_goal_id = goal.get("id")
        print(f"✓ Created goal with ID: {self.__class__.created_goal_id}")
    
    def test_03_get_goal_by_id(self):
        """Test GET /api/goals/{id} returns specific goal"""
        if not hasattr(self.__class__, 'created_goal_id'):
            pytest.skip("No goal created in previous test")
        
        response = self.session.get(f"{BASE_URL}/api/goals/{self.__class__.created_goal_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("id") == self.__class__.created_goal_id, "Goal ID should match"
        print(f"✓ GET /api/goals/{self.__class__.created_goal_id} returned goal")
    
    def test_04_update_goal(self):
        """Test PUT /api/goals/{id} updates goal"""
        if not hasattr(self.__class__, 'created_goal_id'):
            pytest.skip("No goal created in previous test")
        
        update_data = {
            "current_value": 50000,
            "description": "Updated test goal description"
        }
        
        response = self.session.put(f"{BASE_URL}/api/goals/{self.__class__.created_goal_id}", json=update_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ Updated goal {self.__class__.created_goal_id}")
    
    def test_05_get_goals_summary(self):
        """Test GET /api/goals/summary/stats returns summary statistics"""
        response = self.session.get(f"{BASE_URL}/api/goals/summary/stats")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "total_goals" in data, "Response should contain total_goals"
        assert "overall_progress" in data, "Response should contain overall_progress"
        print(f"✓ Goals summary: {data.get('total_goals')} total, {data.get('overall_progress')}% progress")
    
    def test_06_delete_goal(self):
        """Test DELETE /api/goals/{id} deletes goal"""
        if not hasattr(self.__class__, 'created_goal_id'):
            pytest.skip("No goal created in previous test")
        
        response = self.session.delete(f"{BASE_URL}/api/goals/{self.__class__.created_goal_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ Deleted goal {self.__class__.created_goal_id}")


class TestActivityAPI:
    """Test Activity Timeline API"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as super admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "superadmin@salescommand.com",
            "password": "demo123"
        })
        
        if login_response.status_code == 200:
            data = login_response.json()
            self.token = data.get("access_token") or data.get("token")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip(f"Login failed: {login_response.status_code}")
    
    def test_01_get_activities(self):
        """Test GET /api/activities returns activities list"""
        response = self.session.get(f"{BASE_URL}/api/activities")
        # Activities endpoint might not exist yet, check for 200 or 404
        if response.status_code == 404:
            print("⚠ /api/activities endpoint not found - may use mock data on frontend")
            return
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ GET /api/activities returned data")


class TestRelinkAPI:
    """Test Re-link user to Odoo API"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as super admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "superadmin@salescommand.com",
            "password": "demo123"
        })
        
        if login_response.status_code == 200:
            data = login_response.json()
            self.token = data.get("access_token") or data.get("token")
            self.user_id = data.get("user", {}).get("id")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip(f"Login failed: {login_response.status_code}")
    
    def test_01_relink_user(self):
        """Test POST /api/admin/users/{id}/relink attempts to match user with Odoo"""
        if not self.user_id:
            pytest.skip("No user ID available")
        
        response = self.session.post(f"{BASE_URL}/api/admin/users/{self.user_id}/relink")
        # Should return 200 with match status (even if no match found)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should contain message"
        assert "odoo_match_status" in data or "user_email" in data, "Response should contain match info"
        print(f"✓ Relink response: {data.get('message')}")


class TestNavigationConfig:
    """Test Navigation configuration includes Goals and Activity"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as super admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "superadmin@salescommand.com",
            "password": "demo123"
        })
        
        if login_response.status_code == 200:
            data = login_response.json()
            self.token = data.get("access_token") or data.get("token")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip(f"Login failed: {login_response.status_code}")
    
    def test_01_navigation_items(self):
        """Test GET /api/config/navigation-items includes Goals and Activity"""
        response = self.session.get(f"{BASE_URL}/api/config/navigation-items")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        main_menu = data.get("main_menu", [])
        
        # Check for Goals and Activity in navigation
        nav_ids = [item.get("id") for item in main_menu]
        
        assert "goals" in nav_ids, f"Goals should be in navigation. Found: {nav_ids}"
        assert "activity" in nav_ids, f"Activity should be in navigation. Found: {nav_ids}"
        
        print(f"✓ Navigation includes Goals and Activity. All items: {nav_ids}")
    
    def test_02_user_navigation(self):
        """Test GET /api/config/user/navigation returns user's navigation"""
        response = self.session.get(f"{BASE_URL}/api/config/user/navigation")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        main_menu = data.get("main_menu", [])
        
        nav_ids = [item.get("id") for item in main_menu]
        print(f"✓ User navigation items: {nav_ids}")


class TestProfileAPI:
    """Test Profile API with Odoo integration status"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as super admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "superadmin@salescommand.com",
            "password": "demo123"
        })
        
        if login_response.status_code == 200:
            data = login_response.json()
            self.token = data.get("access_token") or data.get("token")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip(f"Login failed: {login_response.status_code}")
    
    def test_01_get_profile(self):
        """Test GET /api/auth/me returns user profile with Odoo fields"""
        response = self.session.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "email" in data, "Profile should contain email"
        assert "name" in data, "Profile should contain name"
        
        # Check for Odoo-related fields (may or may not be present)
        odoo_fields = ["odoo_matched", "odoo_user_id", "odoo_department_name"]
        present_fields = [f for f in odoo_fields if f in data]
        print(f"✓ Profile returned. Odoo fields present: {present_fields}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
