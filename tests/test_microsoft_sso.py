"""
Microsoft SSO Authentication Tests
Tests for Microsoft 365 SSO integration endpoints
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://ai-sales-platform-4.preview.emergentagent.com').rstrip('/')


class TestMicrosoftSSOConfig:
    """Tests for Microsoft SSO configuration endpoint"""
    
    def test_microsoft_config_endpoint_exists(self):
        """Test that /api/auth/microsoft/config endpoint exists and returns 200"""
        response = requests.get(f"{BASE_URL}/api/auth/microsoft/config")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Microsoft config endpoint exists and returns 200")
    
    def test_microsoft_config_returns_client_id(self):
        """Test that config returns client_id"""
        response = requests.get(f"{BASE_URL}/api/auth/microsoft/config")
        data = response.json()
        
        assert "client_id" in data, "Response should contain client_id"
        assert data["client_id"] is not None, "client_id should not be None"
        assert len(data["client_id"]) > 0, "client_id should not be empty"
        print(f"✓ client_id returned: {data['client_id'][:8]}...")
    
    def test_microsoft_config_returns_tenant_id(self):
        """Test that config returns tenant_id"""
        response = requests.get(f"{BASE_URL}/api/auth/microsoft/config")
        data = response.json()
        
        assert "tenant_id" in data, "Response should contain tenant_id"
        assert data["tenant_id"] is not None, "tenant_id should not be None"
        assert len(data["tenant_id"]) > 0, "tenant_id should not be empty"
        print(f"✓ tenant_id returned: {data['tenant_id'][:8]}...")


class TestMicrosoftSSOComplete:
    """Tests for Microsoft SSO complete endpoint"""
    
    def test_microsoft_complete_endpoint_exists(self):
        """Test that /api/auth/microsoft/complete endpoint exists"""
        response = requests.post(
            f"{BASE_URL}/api/auth/microsoft/complete",
            json={
                "access_token": "invalid_token",
                "account": {"username": "test@example.com", "name": "Test User"}
            }
        )
        # Should return 401 for invalid token, not 404
        assert response.status_code in [401, 400, 500], f"Expected 401/400/500, got {response.status_code}"
        print(f"✓ Microsoft complete endpoint exists (returned {response.status_code} for invalid token)")
    
    def test_microsoft_complete_validates_token(self):
        """Test that endpoint validates access token against Microsoft Graph"""
        response = requests.post(
            f"{BASE_URL}/api/auth/microsoft/complete",
            json={
                "access_token": "fake_token_12345",
                "account": {"username": "test@example.com", "name": "Test User"}
            }
        )
        
        assert response.status_code == 401, f"Expected 401 for invalid token, got {response.status_code}"
        data = response.json()
        assert "detail" in data, "Response should contain error detail"
        assert "Invalid" in data["detail"] or "invalid" in data["detail"].lower(), \
            f"Error should mention invalid token: {data['detail']}"
        print(f"✓ Token validation working: {data['detail']}")
    
    def test_microsoft_complete_requires_access_token(self):
        """Test that endpoint requires access_token field"""
        response = requests.post(
            f"{BASE_URL}/api/auth/microsoft/complete",
            json={
                "account": {"username": "test@example.com", "name": "Test User"}
            }
        )
        
        # Should return 422 for missing required field
        assert response.status_code == 422, f"Expected 422 for missing access_token, got {response.status_code}"
        print("✓ Endpoint correctly requires access_token field")
    
    def test_microsoft_complete_requires_account(self):
        """Test that endpoint requires account field"""
        response = requests.post(
            f"{BASE_URL}/api/auth/microsoft/complete",
            json={
                "access_token": "test_token"
            }
        )
        
        # Should return 422 for missing required field
        assert response.status_code == 422, f"Expected 422 for missing account, got {response.status_code}"
        print("✓ Endpoint correctly requires account field")


class TestEmailPasswordLogin:
    """Tests for traditional email/password login"""
    
    def test_login_with_valid_credentials(self):
        """Test login with superadmin credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": "superadmin@salescommand.com",
                "password": "demo123"
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "access_token" in data, "Response should contain access_token"
        assert "user" in data, "Response should contain user object"
        assert data["user"]["email"] == "superadmin@salescommand.com"
        assert data["user"]["role"] == "super_admin"
        print(f"✓ Login successful for {data['user']['email']}")
    
    def test_login_with_invalid_credentials(self):
        """Test login with wrong password"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": "superadmin@salescommand.com",
                "password": "wrongpassword"
            }
        )
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        data = response.json()
        assert "detail" in data, "Response should contain error detail"
        print(f"✓ Invalid credentials correctly rejected: {data['detail']}")
    
    def test_login_with_nonexistent_user(self):
        """Test login with non-existent email"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "anypassword"
            }
        )
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Non-existent user correctly rejected")


class TestHealthEndpoints:
    """Tests for health check endpoints"""
    
    def test_api_health(self):
        """Test API health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        print(f"✓ API health: {data}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
