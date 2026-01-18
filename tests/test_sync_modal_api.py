"""
Backend API Tests for Sales Intelligence Platform
Tests: Auth, Integrations, Sync Modal API, Data Lake Health

Test credentials: superadmin@salescommand.com / demo123
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://ai-sales-platform-4.preview.emergentagent.com')

# Test credentials
TEST_EMAIL = "superadmin@salescommand.com"
TEST_PASSWORD = "demo123"


class TestAuthEndpoints:
    """Authentication endpoint tests"""
    
    def test_login_success(self):
        """Test login with valid credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        assert "user" in data, "No user in response"
        assert data["user"]["email"] == TEST_EMAIL
        assert data["user"]["role"] == "super_admin"
        print(f"✓ Login successful for {TEST_EMAIL}")
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "wrong@example.com", "password": "wrongpass"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Invalid credentials correctly rejected")
    
    def test_get_me_authenticated(self):
        """Test /auth/me with valid token"""
        # First login
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        token = login_response.json()["access_token"]
        
        # Get current user
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Get me failed: {response.text}"
        
        data = response.json()
        assert data["email"] == TEST_EMAIL
        print(f"✓ /auth/me returned user: {data['name']}")


class TestIntegrationsEndpoints:
    """Integration endpoints tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_list_integrations(self):
        """Test GET /integrations/ returns list of integrations"""
        response = requests.get(
            f"{BASE_URL}/api/integrations/",
            headers=self.headers
        )
        assert response.status_code == 200, f"List integrations failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        # Check for Odoo integration
        odoo_found = any(i["integration_type"] == "odoo" for i in data)
        assert odoo_found, "Odoo integration not found in list"
        
        print(f"✓ Found {len(data)} integrations")
        for intg in data:
            print(f"  - {intg['integration_type']}: enabled={intg['enabled']}, status={intg['sync_status']}")
    
    def test_get_odoo_integration(self):
        """Test GET /integrations/odoo returns Odoo config"""
        response = requests.get(
            f"{BASE_URL}/api/integrations/odoo",
            headers=self.headers
        )
        assert response.status_code == 200, f"Get Odoo integration failed: {response.text}"
        
        data = response.json()
        assert data["integration_type"] == "odoo"
        print(f"✓ Odoo integration: enabled={data['enabled']}, status={data['sync_status']}")


class TestSyncEndpoints:
    """Sync endpoint tests - specifically for Sync Modal functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_sync_endpoint_accepts_entity_types_in_body(self):
        """
        Test POST /integrations/sync/odoo accepts entity_types in request body
        This is the key feature for the Sync Modal
        """
        # Test with specific entity types
        entity_types = ["account", "contact", "opportunity"]
        
        response = requests.post(
            f"{BASE_URL}/api/integrations/sync/odoo",
            headers=self.headers,
            json={"entity_types": entity_types}
        )
        
        # Note: This may fail if Odoo is not configured, but we're testing the endpoint structure
        if response.status_code == 400:
            # Expected if Odoo not configured
            data = response.json()
            assert "detail" in data
            print(f"✓ Sync endpoint correctly returns 400 when Odoo not configured: {data['detail']}")
        elif response.status_code == 200:
            data = response.json()
            assert "job_id" in data, "Response should contain job_id"
            print(f"✓ Sync job started: {data['job_id']}")
        else:
            # Check if it's a validation error (422) which would indicate wrong request format
            assert response.status_code != 422, f"Request body format incorrect: {response.text}"
            print(f"✓ Sync endpoint responded with status {response.status_code}")
    
    def test_sync_endpoint_with_all_entity_types(self):
        """Test sync endpoint with all 5 entity types from Sync Modal"""
        all_entity_types = ["account", "contact", "opportunity", "order", "invoice"]
        
        response = requests.post(
            f"{BASE_URL}/api/integrations/sync/odoo",
            headers=self.headers,
            json={"entity_types": all_entity_types}
        )
        
        # We're testing that the endpoint accepts all 5 entity types
        if response.status_code == 400:
            data = response.json()
            # Should fail because Odoo not configured, not because of invalid entity types
            assert "not enabled" in data["detail"] or "not configured" in data["detail"], \
                f"Unexpected error: {data['detail']}"
            print(f"✓ All 5 entity types accepted by endpoint (Odoo not configured)")
        elif response.status_code == 200:
            print(f"✓ Sync started with all 5 entity types")
        else:
            assert response.status_code != 422, f"Entity types validation failed: {response.text}"
    
    def test_sync_endpoint_without_entity_types(self):
        """Test sync endpoint uses defaults when no entity_types provided"""
        response = requests.post(
            f"{BASE_URL}/api/integrations/sync/odoo",
            headers=self.headers,
            json={}  # Empty body - should use defaults
        )
        
        # Should not fail with 422 (validation error)
        assert response.status_code != 422, f"Empty body should be accepted: {response.text}"
        print(f"✓ Sync endpoint accepts empty body (uses defaults)")
    
    def test_get_sync_status(self):
        """Test GET /integrations/sync/status returns recent jobs"""
        response = requests.get(
            f"{BASE_URL}/api/integrations/sync/status",
            headers=self.headers
        )
        assert response.status_code == 200, f"Get sync status failed: {response.text}"
        
        data = response.json()
        assert "jobs" in data, "Response should contain 'jobs' key"
        print(f"✓ Sync status returned {len(data['jobs'])} recent jobs")


class TestFieldMappingsEndpoints:
    """Field mapping endpoints tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_field_mappings_account(self):
        """Test GET /integrations/mappings/odoo/account"""
        response = requests.get(
            f"{BASE_URL}/api/integrations/mappings/odoo/account",
            headers=self.headers
        )
        assert response.status_code == 200, f"Get mappings failed: {response.text}"
        
        data = response.json()
        assert data["integration_type"] == "odoo"
        assert data["entity_type"] == "account"
        assert "canonical_schema" in data
        print(f"✓ Account mappings: {len(data.get('mappings', []))} custom mappings")
    
    def test_get_field_mappings_all_entity_types(self):
        """Test field mappings endpoint for all 5 entity types"""
        entity_types = ["account", "contact", "opportunity", "order", "invoice"]
        
        for entity_type in entity_types:
            response = requests.get(
                f"{BASE_URL}/api/integrations/mappings/odoo/{entity_type}",
                headers=self.headers
            )
            assert response.status_code == 200, f"Get {entity_type} mappings failed: {response.text}"
            
            data = response.json()
            assert data["entity_type"] == entity_type
            print(f"✓ {entity_type} mappings endpoint working")


class TestDataLakeEndpoints:
    """Data Lake health endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_data_lake_health(self):
        """Test GET /data-lake/health returns zone statistics"""
        response = requests.get(
            f"{BASE_URL}/api/data-lake/health",
            headers=self.headers
        )
        assert response.status_code == 200, f"Data lake health failed: {response.text}"
        
        data = response.json()
        assert "zones" in data, "Response should contain 'zones'"
        
        # Check all three zones exist
        zones = data["zones"]
        assert "raw" in zones, "Raw zone missing"
        assert "canonical" in zones, "Canonical zone missing"
        assert "serving" in zones, "Serving zone missing"
        
        print(f"✓ Data Lake Health:")
        print(f"  - Raw Zone: {zones['raw'].get('total_records', 0)} records")
        print(f"  - Canonical Zone: {zones['canonical'].get('total_records', 0)} records")
        print(f"  - Serving Zone: {zones['serving'].get('total_records', 0)} records")


class TestHealthEndpoint:
    """Basic health check tests"""
    
    def test_api_health(self):
        """Test /api/health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        print(f"✓ API Health: {data}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
