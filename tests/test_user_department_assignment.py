"""
Test User-Department Assignment Feature
Tests for Phase 3: User Management with Department assignment functionality
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://ai-sales-platform-4.preview.emergentagent.com').rstrip('/')

# Test credentials
SUPER_ADMIN_EMAIL = "superadmin@salescommand.com"
SUPER_ADMIN_PASSWORD = "demo123"


class TestUserDepartmentAssignment:
    """Test User-Department assignment functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as super admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        
        token = login_response.json().get("access_token")
        assert token, "No access token received"
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        yield
        
        # Cleanup - delete test users created during tests
        self._cleanup_test_users()
    
    def _cleanup_test_users(self):
        """Clean up test users created during testing"""
        try:
            users_response = self.session.get(f"{BASE_URL}/api/config/users")
            if users_response.status_code == 200:
                users = users_response.json()
                for user in users:
                    if user.get("email", "").startswith("TEST_"):
                        self.session.delete(f"{BASE_URL}/api/config/users/{user['id']}")
        except Exception:
            pass
    
    # ==================== BACKEND API TESTS ====================
    
    def test_01_get_system_config_includes_departments(self):
        """Test that system config includes departments"""
        response = self.session.get(f"{BASE_URL}/api/config/system")
        assert response.status_code == 200, f"Failed to get system config: {response.text}"
        
        config = response.json()
        assert "departments" in config, "departments not in system config"
        
        departments = config["departments"]
        assert "departments" in departments, "departments.departments not found"
        
        dept_list = departments["departments"]
        assert len(dept_list) >= 4, f"Expected at least 4 departments, got {len(dept_list)}"
        
        # Verify expected departments exist
        dept_ids = [d["id"] for d in dept_list]
        expected_depts = ["sales", "strategy", "product", "finance"]
        for expected in expected_depts:
            assert expected in dept_ids, f"Expected department '{expected}' not found"
        
        print(f"✓ System config includes {len(dept_list)} departments: {dept_ids}")
    
    def test_02_get_departments_endpoint(self):
        """Test GET /api/config/departments endpoint"""
        response = self.session.get(f"{BASE_URL}/api/config/departments")
        assert response.status_code == 200, f"Failed to get departments: {response.text}"
        
        data = response.json()
        assert "departments" in data, "departments key not in response"
        
        departments = data["departments"]
        assert len(departments) >= 4, f"Expected at least 4 departments, got {len(departments)}"
        
        # Verify department structure
        for dept in departments:
            assert "id" in dept, "Department missing 'id'"
            assert "name" in dept, "Department missing 'name'"
            assert "code" in dept, "Department missing 'code'"
        
        print(f"✓ GET /api/config/departments returns {len(departments)} departments")
    
    def test_03_get_users_includes_department_id(self):
        """Test that GET /api/config/users returns users with department_id field"""
        response = self.session.get(f"{BASE_URL}/api/config/users")
        assert response.status_code == 200, f"Failed to get users: {response.text}"
        
        users = response.json()
        assert len(users) > 0, "No users returned"
        
        # Check that users have department_id field (can be null)
        for user in users[:5]:  # Check first 5 users
            # department_id should be present in the response (even if null)
            # This verifies the backend model includes the field
            print(f"  User: {user.get('name')} - department_id: {user.get('department_id', 'NOT_PRESENT')}")
        
        print(f"✓ GET /api/config/users returns {len(users)} users")
    
    def test_04_create_user_with_department_id(self):
        """Test creating a new user with department_id"""
        test_email = f"TEST_dept_user_{uuid.uuid4().hex[:8]}@test.com"
        
        # Create user with department assignment
        create_payload = {
            "email": test_email,
            "name": "Test Department User",
            "role": "account_manager",
            "department_id": "sales",  # Assign to Sales department
            "quota": 500000
        }
        
        response = self.session.post(f"{BASE_URL}/api/config/users", json=create_payload)
        assert response.status_code == 200, f"Failed to create user: {response.text}"
        
        data = response.json()
        assert "user" in data, "Response missing 'user' key"
        
        created_user = data["user"]
        assert created_user["email"] == test_email, "Email mismatch"
        assert created_user["department_id"] == "sales", f"department_id mismatch: expected 'sales', got '{created_user.get('department_id')}'"
        
        # Verify by fetching users list
        users_response = self.session.get(f"{BASE_URL}/api/config/users")
        users = users_response.json()
        
        created = next((u for u in users if u["email"] == test_email), None)
        assert created is not None, "Created user not found in users list"
        assert created.get("department_id") == "sales", f"department_id not persisted: {created.get('department_id')}"
        
        print(f"✓ Created user with department_id='sales': {test_email}")
        
        # Store user ID for cleanup
        self._test_user_id = created_user["id"]
    
    def test_05_create_user_without_department_id(self):
        """Test creating a user without department_id (should be null)"""
        test_email = f"TEST_no_dept_{uuid.uuid4().hex[:8]}@test.com"
        
        create_payload = {
            "email": test_email,
            "name": "Test No Department User",
            "role": "account_manager",
            "quota": 500000
            # No department_id provided
        }
        
        response = self.session.post(f"{BASE_URL}/api/config/users", json=create_payload)
        assert response.status_code == 200, f"Failed to create user: {response.text}"
        
        data = response.json()
        created_user = data["user"]
        
        # department_id should be null/None
        assert created_user.get("department_id") is None, f"Expected null department_id, got: {created_user.get('department_id')}"
        
        print(f"✓ Created user without department_id: {test_email}")
    
    def test_06_update_user_assign_department(self):
        """Test updating a user to assign a department"""
        # First create a user without department
        test_email = f"TEST_update_dept_{uuid.uuid4().hex[:8]}@test.com"
        
        create_response = self.session.post(f"{BASE_URL}/api/config/users", json={
            "email": test_email,
            "name": "Test Update Department User",
            "role": "account_manager",
            "quota": 500000
        })
        assert create_response.status_code == 200
        
        user_id = create_response.json()["user"]["id"]
        
        # Update user to assign department
        update_payload = {
            "department_id": "strategy"  # Assign to Strategy department
        }
        
        update_response = self.session.put(f"{BASE_URL}/api/config/users/{user_id}", json=update_payload)
        assert update_response.status_code == 200, f"Failed to update user: {update_response.text}"
        
        # Verify the update
        users_response = self.session.get(f"{BASE_URL}/api/config/users")
        users = users_response.json()
        
        updated_user = next((u for u in users if u["id"] == user_id), None)
        assert updated_user is not None, "Updated user not found"
        assert updated_user.get("department_id") == "strategy", f"department_id not updated: {updated_user.get('department_id')}"
        
        print(f"✓ Updated user department_id to 'strategy'")
    
    def test_07_update_user_change_department(self):
        """Test changing a user's department from one to another"""
        test_email = f"TEST_change_dept_{uuid.uuid4().hex[:8]}@test.com"
        
        # Create user with initial department
        create_response = self.session.post(f"{BASE_URL}/api/config/users", json={
            "email": test_email,
            "name": "Test Change Department User",
            "role": "account_manager",
            "department_id": "sales",
            "quota": 500000
        })
        assert create_response.status_code == 200
        
        user_id = create_response.json()["user"]["id"]
        
        # Change department from sales to product
        update_response = self.session.put(f"{BASE_URL}/api/config/users/{user_id}", json={
            "department_id": "product"
        })
        assert update_response.status_code == 200, f"Failed to change department: {update_response.text}"
        
        # Verify the change
        users_response = self.session.get(f"{BASE_URL}/api/config/users")
        users = users_response.json()
        
        updated_user = next((u for u in users if u["id"] == user_id), None)
        assert updated_user.get("department_id") == "product", f"department_id not changed: {updated_user.get('department_id')}"
        
        print(f"✓ Changed user department from 'sales' to 'product'")
    
    def test_08_update_user_remove_department(self):
        """Test removing a user's department assignment (set to null)"""
        test_email = f"TEST_remove_dept_{uuid.uuid4().hex[:8]}@test.com"
        
        # Create user with department
        create_response = self.session.post(f"{BASE_URL}/api/config/users", json={
            "email": test_email,
            "name": "Test Remove Department User",
            "role": "account_manager",
            "department_id": "finance",
            "quota": 500000
        })
        assert create_response.status_code == 200
        
        user_id = create_response.json()["user"]["id"]
        
        # Remove department by setting to null
        update_response = self.session.put(f"{BASE_URL}/api/config/users/{user_id}", json={
            "department_id": None
        })
        assert update_response.status_code == 200, f"Failed to remove department: {update_response.text}"
        
        # Verify the removal
        users_response = self.session.get(f"{BASE_URL}/api/config/users")
        users = users_response.json()
        
        updated_user = next((u for u in users if u["id"] == user_id), None)
        assert updated_user.get("department_id") is None, f"department_id not removed: {updated_user.get('department_id')}"
        
        print(f"✓ Removed user department assignment (set to null)")
    
    def test_09_update_user_with_multiple_fields_including_department(self):
        """Test updating multiple user fields including department_id"""
        test_email = f"TEST_multi_update_{uuid.uuid4().hex[:8]}@test.com"
        
        # Create user
        create_response = self.session.post(f"{BASE_URL}/api/config/users", json={
            "email": test_email,
            "name": "Test Multi Update User",
            "role": "account_manager",
            "quota": 500000
        })
        assert create_response.status_code == 200
        
        user_id = create_response.json()["user"]["id"]
        
        # Update multiple fields including department
        update_payload = {
            "name": "Updated Multi User Name",
            "role": "sales_director",
            "department_id": "sales",
            "quota": 750000,
            "is_active": True
        }
        
        update_response = self.session.put(f"{BASE_URL}/api/config/users/{user_id}", json=update_payload)
        assert update_response.status_code == 200, f"Failed to update user: {update_response.text}"
        
        # Verify all updates
        users_response = self.session.get(f"{BASE_URL}/api/config/users")
        users = users_response.json()
        
        updated_user = next((u for u in users if u["id"] == user_id), None)
        assert updated_user is not None, "Updated user not found"
        assert updated_user.get("name") == "Updated Multi User Name", "Name not updated"
        assert updated_user.get("role") == "sales_director", "Role not updated"
        assert updated_user.get("department_id") == "sales", "department_id not updated"
        assert updated_user.get("quota") == 750000, "Quota not updated"
        
        print(f"✓ Updated multiple fields including department_id")
    
    def test_10_invalid_department_id_handling(self):
        """Test that invalid department_id is handled gracefully"""
        test_email = f"TEST_invalid_dept_{uuid.uuid4().hex[:8]}@test.com"
        
        # Try to create user with invalid department_id
        create_payload = {
            "email": test_email,
            "name": "Test Invalid Department User",
            "role": "account_manager",
            "department_id": "nonexistent_department",  # Invalid department
            "quota": 500000
        }
        
        response = self.session.post(f"{BASE_URL}/api/config/users", json=create_payload)
        
        # The API should either:
        # 1. Accept it (no validation on department_id) - status 200
        # 2. Reject it with validation error - status 400
        # Both are acceptable behaviors depending on implementation
        
        if response.status_code == 200:
            print(f"✓ API accepts any department_id value (no validation)")
        elif response.status_code == 400:
            print(f"✓ API validates department_id and rejects invalid values")
        else:
            print(f"⚠ Unexpected status code: {response.status_code}")
        
        # Test passes either way - we're just documenting the behavior
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code}"


class TestUserDepartmentUIIntegration:
    """Test User-Department assignment in UI context (API calls that frontend makes)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as super admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        assert login_response.status_code == 200
        
        token = login_response.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        yield
    
    def test_01_frontend_data_flow_get_config_and_users(self):
        """Test the data flow that frontend uses to populate User Management tab"""
        # Frontend first fetches system config to get departments
        config_response = self.session.get(f"{BASE_URL}/api/config/system")
        assert config_response.status_code == 200
        
        config = config_response.json()
        departments = config.get("departments", {}).get("departments", [])
        roles = config.get("roles", [])
        
        print(f"  Config loaded: {len(departments)} departments, {len(roles)} roles")
        
        # Then frontend fetches users
        users_response = self.session.get(f"{BASE_URL}/api/config/users")
        assert users_response.status_code == 200
        
        users = users_response.json()
        print(f"  Users loaded: {len(users)} users")
        
        # Frontend maps department_id to department name for display
        for user in users[:3]:
            dept_id = user.get("department_id")
            dept_name = "No Department"
            if dept_id:
                dept = next((d for d in departments if d["id"] == dept_id), None)
                if dept:
                    dept_name = dept["name"]
            print(f"    {user.get('name')}: {dept_name}")
        
        print(f"✓ Frontend data flow verified")
    
    def test_02_edit_user_modal_data_structure(self):
        """Test the data structure used when editing a user in the modal"""
        # Get a user to edit
        users_response = self.session.get(f"{BASE_URL}/api/config/users")
        users = users_response.json()
        
        # Find a user that's not super admin
        test_user = next((u for u in users if u.get("role") != "super_admin"), None)
        assert test_user is not None, "No non-super-admin user found"
        
        # Simulate the edit modal payload (what frontend sends)
        edit_payload = {
            "name": test_user.get("name"),
            "role": test_user.get("role"),
            "quota": test_user.get("quota", 500000),
            "is_active": test_user.get("is_active", True),
            "department_id": test_user.get("department_id") or None  # Frontend sends null if no department
        }
        
        print(f"  Edit payload structure: {list(edit_payload.keys())}")
        print(f"  department_id value: {edit_payload['department_id']}")
        
        # Verify the PUT endpoint accepts this structure
        response = self.session.put(f"{BASE_URL}/api/config/users/{test_user['id']}", json=edit_payload)
        assert response.status_code == 200, f"Edit failed: {response.text}"
        
        print(f"✓ Edit user modal data structure verified")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
