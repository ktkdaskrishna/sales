"""
Test Suite for Phase 2: Super Admin Configuration Architecture
Tests configuration endpoints for roles, blue sheet, LLM, UI, and integrations
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://ai-sales-platform-4.preview.emergentagent.com').rstrip('/')

# Test credentials
SUPER_ADMIN_CREDS = {"email": "superadmin@salescommand.com", "password": "demo123"}
ACCOUNT_MANAGER_CREDS = {"email": "am1@salescommand.com", "password": "demo123"}
CEO_CREDS = {"email": "ceo@salescommand.com", "password": "demo123"}


class TestAuthentication:
    """Test authentication for different user roles"""
    
    def test_super_admin_login(self):
        """Super Admin should be able to login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=SUPER_ADMIN_CREDS)
        assert response.status_code == 200, f"Super Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "super_admin"
        assert data["user"]["email"] == "superadmin@salescommand.com"
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


class TestSystemConfigEndpoint:
    """Test /api/config/system endpoint"""
    
    def test_super_admin_can_access_system_config(self, super_admin_token):
        """Super Admin should access full system configuration"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        response = requests.get(f"{BASE_URL}/api/config/system", headers=headers)
        assert response.status_code == 200, f"Failed to get system config: {response.text}"
        
        data = response.json()
        # Verify all expected sections exist
        assert "modules" in data, "Missing modules in system config"
        assert "roles" in data, "Missing roles in system config"
        assert "blue_sheet" in data, "Missing blue_sheet in system config"
        assert "llm" in data, "Missing llm in system config"
        assert "ui" in data, "Missing ui in system config"
        
        print(f"✓ System config retrieved - Modules: {len(data.get('modules', []))}, Roles: {len(data.get('roles', []))}")
    
    def test_account_manager_cannot_access_system_config(self, account_manager_token):
        """Account Manager should NOT access system configuration"""
        headers = {"Authorization": f"Bearer {account_manager_token}"}
        response = requests.get(f"{BASE_URL}/api/config/system", headers=headers)
        assert response.status_code == 403, f"Expected 403 Forbidden, got {response.status_code}"
        print("✓ Account Manager correctly denied access to system config")
    
    def test_ceo_cannot_access_system_config(self, ceo_token):
        """CEO should NOT access full system configuration (only Super Admin)"""
        headers = {"Authorization": f"Bearer {ceo_token}"}
        response = requests.get(f"{BASE_URL}/api/config/system", headers=headers)
        assert response.status_code == 403, f"Expected 403 Forbidden, got {response.status_code}"
        print("✓ CEO correctly denied access to system config")


class TestRolesEndpoint:
    """Test /api/config/roles endpoint"""
    
    def test_get_all_roles(self, super_admin_token):
        """Super Admin should get all role definitions"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        response = requests.get(f"{BASE_URL}/api/config/roles", headers=headers)
        assert response.status_code == 200, f"Failed to get roles: {response.text}"
        
        roles = response.json()
        assert isinstance(roles, list), "Roles should be a list"
        assert len(roles) >= 8, f"Expected at least 8 roles, got {len(roles)}"
        
        # Verify expected roles exist
        role_ids = [r["id"] for r in roles]
        expected_roles = ["super_admin", "ceo", "sales_director", "finance_manager", 
                         "account_manager", "product_director", "strategy", "referrer"]
        for expected in expected_roles:
            assert expected in role_ids, f"Missing role: {expected}"
        
        # Verify each role has permissions
        for role in roles:
            assert "permissions" in role, f"Role {role['id']} missing permissions"
            assert "name" in role, f"Role {role['id']} missing name"
            print(f"  - {role['name']}: {len(role.get('permissions', []))} permissions")
        
        print(f"✓ Retrieved {len(roles)} roles with permission counts")
    
    def test_ceo_can_view_roles(self, ceo_token):
        """CEO should be able to view roles"""
        headers = {"Authorization": f"Bearer {ceo_token}"}
        response = requests.get(f"{BASE_URL}/api/config/roles", headers=headers)
        assert response.status_code == 200, f"CEO should be able to view roles: {response.text}"
        print("✓ CEO can view roles")


class TestBlueSheetConfigEndpoint:
    """Test /api/config/blue-sheet endpoint"""
    
    def test_get_blue_sheet_config(self, super_admin_token):
        """Should get Blue Sheet configuration"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        response = requests.get(f"{BASE_URL}/api/config/blue-sheet", headers=headers)
        assert response.status_code == 200, f"Failed to get blue sheet config: {response.text}"
        
        data = response.json()
        # Verify structure
        assert "elements" in data, "Missing elements in blue sheet config"
        assert "stages" in data, "Missing stages in blue sheet config"
        
        elements = data.get("elements", [])
        stages = data.get("stages", [])
        
        print(f"✓ Blue Sheet config - Elements: {len(elements)}, Stages: {len(stages)}")
        
        # Verify elements have required fields
        if elements:
            element = elements[0]
            assert "id" in element
            assert "name" in element
            assert "weight" in element
            assert "category" in element
            print(f"  - Sample element: {element['name']} (weight: {element['weight']})")
        
        # Verify stages have required fields
        if stages:
            stage = stages[0]
            assert "id" in stage
            assert "name" in stage
            assert "probability_default" in stage
            print(f"  - Sample stage: {stage['name']} (probability: {stage['probability_default']}%)")
    
    def test_account_manager_can_view_blue_sheet(self, account_manager_token):
        """Account Manager should be able to view Blue Sheet config"""
        headers = {"Authorization": f"Bearer {account_manager_token}"}
        response = requests.get(f"{BASE_URL}/api/config/blue-sheet", headers=headers)
        assert response.status_code == 200, f"Account Manager should view blue sheet: {response.text}"
        print("✓ Account Manager can view Blue Sheet config")


class TestUIConfigEndpoint:
    """Test /api/config/ui endpoint"""
    
    def test_get_ui_config(self, super_admin_token):
        """Should get UI configuration"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        response = requests.get(f"{BASE_URL}/api/config/ui", headers=headers)
        assert response.status_code == 200, f"Failed to get UI config: {response.text}"
        
        data = response.json()
        # Verify structure
        assert "theme_mode" in data, "Missing theme_mode in UI config"
        assert "colors" in data, "Missing colors in UI config"
        assert "typography" in data, "Missing typography in UI config"
        assert "branding" in data, "Missing branding in UI config"
        
        print(f"✓ UI config retrieved - Theme: {data.get('theme_mode')}")
        print(f"  - Branding: {data.get('branding', {}).get('app_name', 'N/A')}")
        print(f"  - Colors: {len(data.get('colors', {}))} defined")
    
    def test_any_user_can_view_ui_config(self, account_manager_token):
        """Any authenticated user should view UI config"""
        headers = {"Authorization": f"Bearer {account_manager_token}"}
        response = requests.get(f"{BASE_URL}/api/config/ui", headers=headers)
        assert response.status_code == 200, f"Any user should view UI config: {response.text}"
        print("✓ Account Manager can view UI config")


class TestLLMConfigEndpoint:
    """Test /api/config/llm endpoint"""
    
    def test_get_llm_config(self, super_admin_token):
        """Super Admin should get LLM configuration"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        response = requests.get(f"{BASE_URL}/api/config/llm", headers=headers)
        assert response.status_code == 200, f"Failed to get LLM config: {response.text}"
        
        data = response.json()
        # Verify structure
        assert "providers" in data, "Missing providers in LLM config"
        assert "prompt_templates" in data, "Missing prompt_templates in LLM config"
        
        providers = data.get("providers", [])
        templates = data.get("prompt_templates", [])
        
        print(f"✓ LLM config - Providers: {len(providers)}, Templates: {len(templates)}")
        
        # Verify provider structure
        if providers:
            provider = providers[0]
            assert "provider" in provider
            assert "model" in provider
            print(f"  - Provider: {provider.get('provider')} / {provider.get('model')}")
        
        # Verify template structure
        if templates:
            template = templates[0]
            assert "id" in template
            assert "name" in template
            assert "system_prompt" in template
            print(f"  - Template: {template.get('name')}")
    
    def test_account_manager_cannot_access_llm_config(self, account_manager_token):
        """Account Manager should NOT access LLM configuration"""
        headers = {"Authorization": f"Bearer {account_manager_token}"}
        response = requests.get(f"{BASE_URL}/api/config/llm", headers=headers)
        assert response.status_code == 403, f"Expected 403 Forbidden, got {response.status_code}"
        print("✓ Account Manager correctly denied access to LLM config")


class TestIntegrationsConfigEndpoint:
    """Test /api/config/integrations endpoint"""
    
    def test_get_integrations_config(self, super_admin_token):
        """Super Admin should get integrations configuration"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        response = requests.get(f"{BASE_URL}/api/config/integrations", headers=headers)
        assert response.status_code == 200, f"Failed to get integrations config: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Integrations should be a list"
        print(f"✓ Integrations config - {len(data)} integrations configured")
        
        for intg in data:
            print(f"  - {intg.get('name', intg.get('id', 'Unknown'))}: {intg.get('is_enabled', False)}")


class TestUserPermissionsEndpoint:
    """Test /api/config/user-permissions endpoint"""
    
    def test_get_user_permissions(self, account_manager_token):
        """Any user should get their own permissions"""
        headers = {"Authorization": f"Bearer {account_manager_token}"}
        response = requests.get(f"{BASE_URL}/api/config/user-permissions", headers=headers)
        assert response.status_code == 200, f"Failed to get user permissions: {response.text}"
        
        data = response.json()
        assert "modules" in data, "Missing modules in permissions"
        assert "features" in data, "Missing features in permissions"
        assert "actions" in data, "Missing actions in permissions"
        
        print(f"✓ User permissions - Modules: {len(data.get('modules', {}))}, Actions: {len(data.get('actions', []))}")


class TestUserConfigEndpoint:
    """Test /api/config/user-config endpoint"""
    
    def test_get_user_config(self, account_manager_token):
        """Any user should get their filtered configuration"""
        headers = {"Authorization": f"Bearer {account_manager_token}"}
        response = requests.get(f"{BASE_URL}/api/config/user-config", headers=headers)
        assert response.status_code == 200, f"Failed to get user config: {response.text}"
        
        data = response.json()
        assert "modules" in data, "Missing modules in user config"
        assert "ui" in data, "Missing ui in user config"
        assert "permissions" in data, "Missing permissions in user config"
        
        print(f"✓ User config - Visible modules: {len(data.get('modules', []))}")


class TestDashboardStillWorks:
    """Verify Account Manager dashboard still works after Phase 2 changes"""
    
    def test_dashboard_stats(self, account_manager_token):
        """Dashboard stats should still work"""
        headers = {"Authorization": f"Bearer {account_manager_token}"}
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=headers)
        assert response.status_code == 200, f"Dashboard stats failed: {response.text}"
        
        data = response.json()
        assert "total_pipeline_value" in data
        assert "active_opportunities" in data
        print(f"✓ Dashboard stats working - Pipeline: ${data.get('total_pipeline_value', 0):,.0f}")
    
    def test_opportunities_kanban(self, account_manager_token):
        """Kanban view should still work"""
        headers = {"Authorization": f"Bearer {account_manager_token}"}
        response = requests.get(f"{BASE_URL}/api/opportunities/kanban", headers=headers)
        assert response.status_code == 200, f"Kanban view failed: {response.text}"
        
        data = response.json()
        assert "stages" in data
        assert "kanban" in data
        print(f"✓ Kanban view working - {len(data.get('stages', []))} stages")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
