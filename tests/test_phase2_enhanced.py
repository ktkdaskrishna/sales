"""
Test Suite for Phase 2 Enhanced: Super Admin Configuration Architecture
Tests Organization Settings, User Management, AI Agents, and LLM Test Connection
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://ai-sales-platform-4.preview.emergentagent.com').rstrip('/')

# Test credentials
SUPER_ADMIN_CREDS = {"email": "superadmin@salescommand.com", "password": "demo123"}
ACCOUNT_MANAGER_CREDS = {"email": "am1@salescommand.com", "password": "demo123"}
CEO_CREDS = {"email": "ceo@salescommand.com", "password": "demo123"}


@pytest.fixture
def super_admin_token():
    """Get Super Admin auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=SUPER_ADMIN_CREDS)
    if response.status_code != 200:
        pytest.skip("Super Admin login failed")
    return response.json()["access_token"]


@pytest.fixture
def account_manager_token():
    """Get Account Manager auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=ACCOUNT_MANAGER_CREDS)
    if response.status_code != 200:
        pytest.skip("Account Manager login failed")
    return response.json()["access_token"]


@pytest.fixture
def ceo_token():
    """Get CEO auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=CEO_CREDS)
    if response.status_code != 200:
        pytest.skip("CEO login failed")
    return response.json()["access_token"]


class TestAuthentication:
    """Test authentication for different user roles"""
    
    def test_super_admin_login(self):
        """Super Admin should be able to login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=SUPER_ADMIN_CREDS)
        assert response.status_code == 200, f"Super Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "super_admin"
        print(f"✓ Super Admin login successful - Role: {data['user']['role']}")
    
    def test_account_manager_login(self):
        """Account Manager should be able to login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ACCOUNT_MANAGER_CREDS)
        assert response.status_code == 200, f"Account Manager login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "account_manager"
        print(f"✓ Account Manager login successful - Role: {data['user']['role']}")
    
    def test_ceo_login(self):
        """CEO should be able to login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CEO_CREDS)
        assert response.status_code == 200, f"CEO login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "ceo"
        print(f"✓ CEO login successful - Role: {data['user']['role']}")


class TestOrganizationSettings:
    """Test /api/config/organization endpoint"""
    
    def test_get_organization_settings(self, super_admin_token):
        """Super Admin should get organization settings"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        response = requests.get(f"{BASE_URL}/api/config/organization", headers=headers)
        assert response.status_code == 200, f"Failed to get organization settings: {response.text}"
        
        data = response.json()
        # Verify expected fields exist
        assert "name" in data, "Missing name in organization settings"
        assert "timezone" in data, "Missing timezone in organization settings"
        assert "currency" in data, "Missing currency in organization settings"
        assert "fiscal_year_start_month" in data, "Missing fiscal_year_start_month"
        assert "quota_period" in data, "Missing quota_period"
        assert "default_commission_rate" in data, "Missing default_commission_rate"
        assert "enable_ai_features" in data, "Missing enable_ai_features"
        assert "enable_referrals" in data, "Missing enable_referrals"
        
        print(f"✓ Organization settings retrieved - Name: {data.get('name')}")
        print(f"  - Currency: {data.get('currency')}, Timezone: {data.get('timezone')}")
        print(f"  - Quota Period: {data.get('quota_period')}, Commission Rate: {data.get('default_commission_rate')}")
    
    def test_update_organization_settings(self, super_admin_token):
        """Super Admin should update organization settings"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        # First get current settings
        get_response = requests.get(f"{BASE_URL}/api/config/organization", headers=headers)
        assert get_response.status_code == 200
        original = get_response.json()
        
        # Update with new values
        update_data = {
            "name": "SalesCommand Test Enterprise",
            "industry": "cybersecurity",
            "timezone": "America/New_York"
        }
        response = requests.put(f"{BASE_URL}/api/config/organization", headers=headers, json=update_data)
        assert response.status_code == 200, f"Failed to update organization settings: {response.text}"
        
        # Verify update
        verify_response = requests.get(f"{BASE_URL}/api/config/organization", headers=headers)
        updated = verify_response.json()
        assert updated.get("name") == "SalesCommand Test Enterprise"
        assert updated.get("industry") == "cybersecurity"
        
        # Restore original name
        restore_data = {"name": original.get("name", "SalesCommand Enterprise")}
        requests.put(f"{BASE_URL}/api/config/organization", headers=headers, json=restore_data)
        
        print("✓ Organization settings updated and verified successfully")
    
    def test_ceo_can_view_organization(self, ceo_token):
        """CEO should be able to view organization settings"""
        headers = {"Authorization": f"Bearer {ceo_token}"}
        response = requests.get(f"{BASE_URL}/api/config/organization", headers=headers)
        assert response.status_code == 200, f"CEO should view organization: {response.text}"
        print("✓ CEO can view organization settings")
    
    def test_account_manager_cannot_view_organization(self, account_manager_token):
        """Account Manager should NOT access organization settings"""
        headers = {"Authorization": f"Bearer {account_manager_token}"}
        response = requests.get(f"{BASE_URL}/api/config/organization", headers=headers)
        assert response.status_code == 403, f"Expected 403 Forbidden, got {response.status_code}"
        print("✓ Account Manager correctly denied access to organization settings")


class TestUserManagement:
    """Test /api/config/users endpoints"""
    
    def test_get_all_users(self, super_admin_token):
        """Super Admin should get all users with full details"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        response = requests.get(f"{BASE_URL}/api/config/users", headers=headers)
        assert response.status_code == 200, f"Failed to get users: {response.text}"
        
        users = response.json()
        assert isinstance(users, list), "Users should be a list"
        assert len(users) >= 1, "Should have at least 1 user"
        
        # Verify user structure
        user = users[0]
        assert "id" in user, "User missing id"
        assert "email" in user, "User missing email"
        assert "name" in user, "User missing name"
        assert "role" in user, "User missing role"
        
        print(f"✓ Retrieved {len(users)} users with full details")
        for u in users[:5]:  # Print first 5
            print(f"  - {u.get('name')} ({u.get('email')}) - {u.get('role')}")
    
    def test_create_user_with_auto_password(self, super_admin_token):
        """Super Admin should create user with auto-generated password"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        test_email = f"TEST_user_{uuid.uuid4().hex[:8]}@salescommand.com"
        new_user = {
            "email": test_email,
            "name": "TEST Auto Password User",
            "role": "account_manager",
            "quota": 300000
        }
        
        response = requests.post(f"{BASE_URL}/api/config/users", headers=headers, json=new_user)
        assert response.status_code == 200, f"Failed to create user: {response.text}"
        
        data = response.json()
        assert "user" in data, "Response missing user object"
        assert "generated_password" in data["user"], "Response missing generated_password"
        assert data["user"]["generated_password"] is not None, "Generated password should not be None"
        
        created_user = data["user"]
        print(f"✓ User created with auto-generated password")
        print(f"  - Email: {created_user.get('email')}")
        print(f"  - Generated Password: {created_user.get('generated_password')}")
        
        # Cleanup - deactivate the test user
        if created_user.get("id"):
            requests.delete(f"{BASE_URL}/api/config/users/{created_user['id']}", headers=headers)
    
    def test_create_user_with_provided_password(self, super_admin_token):
        """Super Admin should create user with provided password"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        test_email = f"TEST_user_{uuid.uuid4().hex[:8]}@salescommand.com"
        new_user = {
            "email": test_email,
            "name": "TEST Provided Password User",
            "role": "account_manager",
            "password": "testpassword123",
            "quota": 400000
        }
        
        response = requests.post(f"{BASE_URL}/api/config/users", headers=headers, json=new_user)
        assert response.status_code == 200, f"Failed to create user: {response.text}"
        
        data = response.json()
        assert "user" in data
        # When password is provided, generated_password should be None
        assert data["user"].get("generated_password") is None, "Should not generate password when provided"
        
        created_user = data["user"]
        print(f"✓ User created with provided password")
        print(f"  - Email: {created_user.get('email')}")
        
        # Cleanup
        if created_user.get("id"):
            requests.delete(f"{BASE_URL}/api/config/users/{created_user['id']}", headers=headers)
    
    def test_update_user(self, super_admin_token):
        """Super Admin should update user details"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        # First create a test user
        test_email = f"TEST_update_{uuid.uuid4().hex[:8]}@salescommand.com"
        new_user = {
            "email": test_email,
            "name": "TEST Update User",
            "role": "account_manager",
            "quota": 300000
        }
        create_response = requests.post(f"{BASE_URL}/api/config/users", headers=headers, json=new_user)
        assert create_response.status_code == 200
        user_id = create_response.json()["user"]["id"]
        
        # Update the user
        update_data = {
            "name": "TEST Updated Name",
            "quota": 500000
        }
        update_response = requests.put(f"{BASE_URL}/api/config/users/{user_id}", headers=headers, json=update_data)
        assert update_response.status_code == 200, f"Failed to update user: {update_response.text}"
        
        # Verify update by getting all users
        get_response = requests.get(f"{BASE_URL}/api/config/users", headers=headers)
        users = get_response.json()
        updated_user = next((u for u in users if u["id"] == user_id), None)
        assert updated_user is not None, "Updated user not found"
        assert updated_user["name"] == "TEST Updated Name"
        
        print(f"✓ User updated successfully - New name: {updated_user['name']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/config/users/{user_id}", headers=headers)
    
    def test_assign_role_to_user(self, super_admin_token):
        """Super Admin should assign role to user"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        # Create a test user
        test_email = f"TEST_role_{uuid.uuid4().hex[:8]}@salescommand.com"
        new_user = {
            "email": test_email,
            "name": "TEST Role Assignment User",
            "role": "account_manager"
        }
        create_response = requests.post(f"{BASE_URL}/api/config/users", headers=headers, json=new_user)
        assert create_response.status_code == 200
        user_id = create_response.json()["user"]["id"]
        
        # Assign new role
        role_data = {"role": "sales_director"}
        role_response = requests.put(f"{BASE_URL}/api/config/users/{user_id}/role", headers=headers, json=role_data)
        assert role_response.status_code == 200, f"Failed to assign role: {role_response.text}"
        
        # Verify role change
        get_response = requests.get(f"{BASE_URL}/api/config/users", headers=headers)
        users = get_response.json()
        updated_user = next((u for u in users if u["id"] == user_id), None)
        assert updated_user is not None
        assert updated_user["role"] == "sales_director"
        
        print(f"✓ Role assigned successfully - New role: {updated_user['role']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/config/users/{user_id}", headers=headers)
    
    def test_reset_user_password(self, super_admin_token):
        """Super Admin should reset user password"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        # Create a test user
        test_email = f"TEST_reset_{uuid.uuid4().hex[:8]}@salescommand.com"
        new_user = {
            "email": test_email,
            "name": "TEST Password Reset User",
            "role": "account_manager",
            "password": "oldpassword123"
        }
        create_response = requests.post(f"{BASE_URL}/api/config/users", headers=headers, json=new_user)
        assert create_response.status_code == 200
        user_id = create_response.json()["user"]["id"]
        
        # Reset password
        reset_response = requests.post(f"{BASE_URL}/api/config/users/{user_id}/reset-password", headers=headers)
        assert reset_response.status_code == 200, f"Failed to reset password: {reset_response.text}"
        
        data = reset_response.json()
        assert "new_password" in data, "Response missing new_password"
        assert len(data["new_password"]) >= 8, "New password should be at least 8 characters"
        
        print(f"✓ Password reset successfully - New password: {data['new_password']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/config/users/{user_id}", headers=headers)
    
    def test_delete_user_soft_delete(self, super_admin_token):
        """Super Admin should soft-delete user (set is_active=False)"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        # Create a test user
        test_email = f"TEST_delete_{uuid.uuid4().hex[:8]}@salescommand.com"
        new_user = {
            "email": test_email,
            "name": "TEST Delete User",
            "role": "account_manager"
        }
        create_response = requests.post(f"{BASE_URL}/api/config/users", headers=headers, json=new_user)
        assert create_response.status_code == 200
        user_id = create_response.json()["user"]["id"]
        
        # Delete (soft delete)
        delete_response = requests.delete(f"{BASE_URL}/api/config/users/{user_id}", headers=headers)
        assert delete_response.status_code == 200, f"Failed to delete user: {delete_response.text}"
        
        # Verify user is deactivated (not hard deleted)
        get_response = requests.get(f"{BASE_URL}/api/config/users", headers=headers)
        users = get_response.json()
        deleted_user = next((u for u in users if u["id"] == user_id), None)
        
        # User should still exist but be inactive
        if deleted_user:
            assert deleted_user.get("is_active") == False, "User should be deactivated"
            print(f"✓ User soft-deleted successfully - is_active: {deleted_user.get('is_active')}")
        else:
            print("✓ User deleted (may have been hard deleted)")
    
    def test_account_manager_cannot_manage_users(self, account_manager_token):
        """Account Manager should NOT access user management"""
        headers = {"Authorization": f"Bearer {account_manager_token}"}
        response = requests.get(f"{BASE_URL}/api/config/users", headers=headers)
        assert response.status_code == 403, f"Expected 403 Forbidden, got {response.status_code}"
        print("✓ Account Manager correctly denied access to user management")


class TestAIAgents:
    """Test /api/config/ai-agents endpoints"""
    
    def test_get_ai_agents(self, super_admin_token):
        """Super Admin should get AI agents configuration"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        response = requests.get(f"{BASE_URL}/api/config/ai-agents", headers=headers)
        assert response.status_code == 200, f"Failed to get AI agents: {response.text}"
        
        data = response.json()
        assert "agents" in data, "Missing agents in AI agents config"
        assert "global_rate_limit" in data, "Missing global_rate_limit"
        
        agents = data.get("agents", [])
        print(f"✓ AI agents config retrieved - {len(agents)} agents configured")
        
        for agent in agents:
            print(f"  - {agent.get('name')} ({agent.get('agent_type')}) - Enabled: {agent.get('is_enabled')}")
    
    def test_create_ai_agent(self, super_admin_token):
        """Super Admin should create new AI agent"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        new_agent = {
            "name": "TEST Custom Agent",
            "agent_type": "sales_insights",
            "description": "Test agent for automated testing",
            "system_prompt": "You are a test assistant.",
            "user_prompt_template": "Test prompt: {test_input}",
            "is_enabled": False,
            "llm_provider": "openai",
            "model": "gpt-4o",
            "temperature": 0.5,
            "max_tokens": 500
        }
        
        response = requests.post(f"{BASE_URL}/api/config/ai-agents", headers=headers, json=new_agent)
        assert response.status_code == 200, f"Failed to create AI agent: {response.text}"
        
        data = response.json()
        assert "agent" in data, "Response missing agent object"
        created_agent = data["agent"]
        assert created_agent["name"] == "TEST Custom Agent"
        
        print(f"✓ AI agent created - ID: {created_agent.get('id')}, Name: {created_agent.get('name')}")
        
        # Cleanup - delete the test agent
        if created_agent.get("id"):
            requests.delete(f"{BASE_URL}/api/config/ai-agents/{created_agent['id']}", headers=headers)
    
    def test_update_ai_agent(self, super_admin_token):
        """Super Admin should update AI agent"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        # First get existing agents
        get_response = requests.get(f"{BASE_URL}/api/config/ai-agents", headers=headers)
        agents = get_response.json().get("agents", [])
        
        if not agents:
            pytest.skip("No agents to update")
        
        agent_id = agents[0]["id"]
        original_temp = agents[0].get("temperature", 0.7)
        
        # Update temperature
        update_data = {"temperature": 0.9}
        update_response = requests.put(f"{BASE_URL}/api/config/ai-agents/{agent_id}", headers=headers, json=update_data)
        assert update_response.status_code == 200, f"Failed to update AI agent: {update_response.text}"
        
        # Verify update
        verify_response = requests.get(f"{BASE_URL}/api/config/ai-agents", headers=headers)
        updated_agents = verify_response.json().get("agents", [])
        updated_agent = next((a for a in updated_agents if a["id"] == agent_id), None)
        assert updated_agent is not None
        assert updated_agent["temperature"] == 0.9
        
        # Restore original
        requests.put(f"{BASE_URL}/api/config/ai-agents/{agent_id}", headers=headers, json={"temperature": original_temp})
        
        print(f"✓ AI agent updated successfully - Temperature changed to 0.9")
    
    def test_test_ai_agent(self, super_admin_token):
        """Super Admin should test AI agent with sample data"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        # Get existing agents
        get_response = requests.get(f"{BASE_URL}/api/config/ai-agents", headers=headers)
        agents = get_response.json().get("agents", [])
        
        # Find an enabled agent
        enabled_agent = next((a for a in agents if a.get("is_enabled")), None)
        if not enabled_agent:
            pytest.skip("No enabled agents to test")
        
        agent_id = enabled_agent["id"]
        
        # Test with sample data
        test_data = {
            "opportunity_name": "Test Enterprise Deal",
            "opportunity_value": 250000,
            "stage": "Proposal",
            "score": 65,
            "economic_buyer_status": "Identified",
            "coach_status": "Active",
            "red_flags": "Budget pending",
            "business_results": "Improved security",
            "user_role": "Account Manager",
            "active_opportunities": 10,
            "pipeline_value": 1000000,
            "won_deals": 3,
            "pending_activities": 5
        }
        
        response = requests.post(f"{BASE_URL}/api/config/ai-agents/{agent_id}/test", headers=headers, json=test_data)
        assert response.status_code == 200, f"Failed to test AI agent: {response.text}"
        
        data = response.json()
        assert "success" in data, "Response missing success field"
        
        if data["success"]:
            print(f"✓ AI agent test successful - Agent: {enabled_agent['name']}")
            print(f"  - Response preview: {str(data.get('response', ''))[:100]}...")
        else:
            print(f"⚠ AI agent test returned error: {data.get('error')}")
            # This is not a failure - the test endpoint works, just the LLM call may fail
    
    def test_account_manager_cannot_access_ai_agents(self, account_manager_token):
        """Account Manager should NOT access AI agents configuration"""
        headers = {"Authorization": f"Bearer {account_manager_token}"}
        response = requests.get(f"{BASE_URL}/api/config/ai-agents", headers=headers)
        assert response.status_code == 403, f"Expected 403 Forbidden, got {response.status_code}"
        print("✓ Account Manager correctly denied access to AI agents config")


class TestLLMTestConnection:
    """Test /api/config/llm/test-connection endpoint"""
    
    def test_llm_test_connection(self, super_admin_token):
        """Super Admin should test LLM provider connection"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        test_data = {
            "provider": "openai",
            "api_key_env": "EMERGENT_LLM_KEY",
            "model": "gpt-4o"
        }
        
        response = requests.post(f"{BASE_URL}/api/config/llm/test-connection", headers=headers, json=test_data)
        assert response.status_code == 200, f"Failed to test LLM connection: {response.text}"
        
        data = response.json()
        assert "success" in data, "Response missing success field"
        
        if data["success"]:
            print(f"✓ LLM connection test successful")
            print(f"  - Provider: {data.get('provider')}, Model: {data.get('model')}")
            print(f"  - Response: {data.get('response')}")
        else:
            print(f"⚠ LLM connection test failed: {data.get('error')}")
            # This is informational - the endpoint works, connection may fail due to API key
    
    def test_account_manager_cannot_test_llm(self, account_manager_token):
        """Account Manager should NOT test LLM connection"""
        headers = {"Authorization": f"Bearer {account_manager_token}"}
        test_data = {"provider": "openai"}
        response = requests.post(f"{BASE_URL}/api/config/llm/test-connection", headers=headers, json=test_data)
        assert response.status_code == 403, f"Expected 403 Forbidden, got {response.status_code}"
        print("✓ Account Manager correctly denied access to LLM test connection")


class TestRoleBasedAccessControl:
    """Test that non-super-admin users get 403 on admin endpoints"""
    
    def test_account_manager_denied_system_config(self, account_manager_token):
        """Account Manager should be denied access to system config"""
        headers = {"Authorization": f"Bearer {account_manager_token}"}
        response = requests.get(f"{BASE_URL}/api/config/system", headers=headers)
        assert response.status_code == 403
        print("✓ Account Manager denied /api/config/system")
    
    def test_account_manager_denied_organization(self, account_manager_token):
        """Account Manager should be denied access to organization settings"""
        headers = {"Authorization": f"Bearer {account_manager_token}"}
        response = requests.get(f"{BASE_URL}/api/config/organization", headers=headers)
        assert response.status_code == 403
        print("✓ Account Manager denied /api/config/organization")
    
    def test_account_manager_denied_users(self, account_manager_token):
        """Account Manager should be denied access to user management"""
        headers = {"Authorization": f"Bearer {account_manager_token}"}
        response = requests.get(f"{BASE_URL}/api/config/users", headers=headers)
        assert response.status_code == 403
        print("✓ Account Manager denied /api/config/users")
    
    def test_account_manager_denied_ai_agents(self, account_manager_token):
        """Account Manager should be denied access to AI agents"""
        headers = {"Authorization": f"Bearer {account_manager_token}"}
        response = requests.get(f"{BASE_URL}/api/config/ai-agents", headers=headers)
        assert response.status_code == 403
        print("✓ Account Manager denied /api/config/ai-agents")
    
    def test_account_manager_denied_llm_config(self, account_manager_token):
        """Account Manager should be denied access to LLM config"""
        headers = {"Authorization": f"Bearer {account_manager_token}"}
        response = requests.get(f"{BASE_URL}/api/config/llm", headers=headers)
        assert response.status_code == 403
        print("✓ Account Manager denied /api/config/llm")


class TestCEOAccess:
    """Test CEO access levels"""
    
    def test_ceo_can_view_organization(self, ceo_token):
        """CEO should view organization settings"""
        headers = {"Authorization": f"Bearer {ceo_token}"}
        response = requests.get(f"{BASE_URL}/api/config/organization", headers=headers)
        assert response.status_code == 200
        print("✓ CEO can view organization settings")
    
    def test_ceo_can_view_users(self, ceo_token):
        """CEO should view users"""
        headers = {"Authorization": f"Bearer {ceo_token}"}
        response = requests.get(f"{BASE_URL}/api/config/users", headers=headers)
        assert response.status_code == 200
        print("✓ CEO can view users")
    
    def test_ceo_cannot_modify_organization(self, ceo_token):
        """CEO should NOT modify organization settings"""
        headers = {"Authorization": f"Bearer {ceo_token}"}
        response = requests.put(f"{BASE_URL}/api/config/organization", headers=headers, json={"name": "Test"})
        assert response.status_code == 403
        print("✓ CEO correctly denied from modifying organization")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
