"""
P0 Features Test Suite
Tests for:
1. 360° Account View Panel - API and data structure
2. Expandable Kanban Board - column expand/collapse
3. Enterprise DataTable - sorting, filtering, search
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://ai-sales-platform-4.preview.emergentagent.com').rstrip('/')

class TestAuth:
    """Authentication helper tests"""
    
    @pytest.fixture(scope="class")
    def super_admin_token(self):
        """Get super admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "superadmin@salescommand.com",
            "password": "demo123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def account_manager_token(self):
        """Get account manager token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "am1@salescommand.com",
            "password": "demo123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json()["access_token"]


class Test360AccountViewAPI(TestAuth):
    """Tests for /api/accounts/{id}/360 endpoint"""
    
    def test_360_view_returns_account_data(self, super_admin_token):
        """Test that 360 view returns account information"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        # Test with account ID 16 (TEST account)
        response = requests.get(f"{BASE_URL}/api/accounts/16/360", headers=headers)
        assert response.status_code == 200, f"360 view failed: {response.text}"
        
        data = response.json()
        
        # Verify account structure
        assert "account" in data, "Response should contain 'account' key"
        account = data["account"]
        assert "id" in account, "Account should have 'id'"
        assert "name" in account, "Account should have 'name'"
        assert "source" in account, "Account should have 'source'"
        
    def test_360_view_returns_summary_cards(self, super_admin_token):
        """Test that 360 view returns summary metrics"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/accounts/16/360", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify summary structure
        assert "summary" in data, "Response should contain 'summary' key"
        summary = data["summary"]
        
        expected_fields = [
            "total_opportunities",
            "total_pipeline_value",
            "total_won_value",
            "total_invoiced",
            "total_outstanding",
            "total_activities",
            "pending_activities",
            "total_contacts"
        ]
        
        for field in expected_fields:
            assert field in summary, f"Summary should contain '{field}'"
    
    def test_360_view_returns_collapsible_sections(self, super_admin_token):
        """Test that 360 view returns data for collapsible sections"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/accounts/16/360", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify collapsible sections exist
        assert "opportunities" in data, "Response should contain 'opportunities'"
        assert "invoices" in data, "Response should contain 'invoices'"
        assert "activities" in data, "Response should contain 'activities'"
        assert "contacts" in data, "Response should contain 'contacts'"
        
        # All should be lists
        assert isinstance(data["opportunities"], list)
        assert isinstance(data["invoices"], list)
        assert isinstance(data["activities"], list)
        assert isinstance(data["contacts"], list)
    
    def test_360_view_with_invalid_account_id(self, super_admin_token):
        """Test 360 view with non-existent account ID"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/accounts/nonexistent-id-12345/360", headers=headers)
        assert response.status_code == 404, "Should return 404 for non-existent account"
    
    def test_360_view_with_different_accounts(self, super_admin_token):
        """Test 360 view works with different account IDs"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        # Test with multiple account IDs
        account_ids = ["16", "12", "10", "8", "1"]
        
        for acc_id in account_ids:
            response = requests.get(f"{BASE_URL}/api/accounts/{acc_id}/360", headers=headers)
            assert response.status_code == 200, f"360 view failed for account {acc_id}: {response.text}"
            
            data = response.json()
            assert data["account"]["id"] == acc_id, f"Account ID mismatch for {acc_id}"


class TestOpportunitiesAPI(TestAuth):
    """Tests for opportunities endpoints"""
    
    def test_get_opportunities(self, super_admin_token):
        """Test getting all opportunities"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/opportunities", headers=headers)
        assert response.status_code == 200, f"Get opportunities failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
    
    def test_opportunities_have_required_fields(self, super_admin_token):
        """Test that opportunities have required fields for table/kanban"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/opportunities", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        
        if len(data) > 0:
            opp = data[0]
            required_fields = ["id", "name", "value", "stage", "probability"]
            for field in required_fields:
                assert field in opp, f"Opportunity should have '{field}'"
    
    def test_opportunities_stage_filter(self, super_admin_token):
        """Test filtering opportunities by stage"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        # Test with different stages
        stages = ["lead", "qualification", "discovery", "proposal", "negotiation"]
        
        for stage in stages:
            response = requests.get(f"{BASE_URL}/api/opportunities?stage={stage}", headers=headers)
            assert response.status_code == 200, f"Stage filter failed for {stage}: {response.text}"


class TestAccountsAPI(TestAuth):
    """Tests for accounts endpoints"""
    
    def test_get_real_accounts(self, super_admin_token):
        """Test getting real Odoo accounts"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/accounts/real", headers=headers)
        assert response.status_code == 200, f"Get real accounts failed: {response.text}"
        
        data = response.json()
        assert "accounts" in data, "Response should contain 'accounts'"
        assert isinstance(data["accounts"], list), "Accounts should be a list"
    
    def test_accounts_have_required_fields(self, super_admin_token):
        """Test that accounts have required fields"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/accounts/real", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        
        if len(data["accounts"]) > 0:
            account = data["accounts"][0]
            required_fields = ["id", "name"]
            for field in required_fields:
                assert field in account, f"Account should have '{field}'"


class TestKanbanAPI(TestAuth):
    """Tests for Kanban board API"""
    
    def test_get_kanban_data(self, super_admin_token):
        """Test getting Kanban board data"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/opportunities/kanban", headers=headers)
        assert response.status_code == 200, f"Get kanban failed: {response.text}"
        
        data = response.json()
        assert "stages" in data, "Response should contain 'stages'"
        assert "kanban" in data, "Response should contain 'kanban'"
    
    def test_kanban_stages_structure(self, super_admin_token):
        """Test Kanban stages have correct structure"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/opportunities/kanban", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        stages = data["stages"]
        
        assert len(stages) > 0, "Should have at least one stage"
        
        for stage in stages:
            assert "id" in stage, "Stage should have 'id'"
            assert "name" in stage, "Stage should have 'name'"
            assert "order" in stage, "Stage should have 'order'"


class TestStageTransitions(TestAuth):
    """Tests for stage transition rules"""
    
    def test_get_stage_transition_rules(self, super_admin_token):
        """Test getting stage transition rules"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/stage-transitions", headers=headers)
        assert response.status_code == 200, f"Get stage transitions failed: {response.text}"
        
        data = response.json()
        assert "rules" in data, "Response should contain 'rules'"
        assert "closed_stages" in data, "Response should contain 'closed_stages'"


class TestDashboardAPI(TestAuth):
    """Tests for dashboard endpoints"""
    
    def test_get_dashboard_stats(self, super_admin_token):
        """Test getting dashboard statistics"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=headers)
        assert response.status_code == 200, f"Get dashboard stats failed: {response.text}"
        
        data = response.json()
        expected_fields = [
            "total_pipeline_value",
            "won_revenue",
            "active_opportunities",
            "total_opportunities"
        ]
        
        for field in expected_fields:
            assert field in data, f"Dashboard stats should contain '{field}'"
    
    def test_get_real_dashboard(self, super_admin_token):
        """Test getting real Odoo dashboard data"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/dashboard/real", headers=headers)
        assert response.status_code == 200, f"Get real dashboard failed: {response.text}"
        
        data = response.json()
        assert "source" in data, "Response should contain 'source'"
        assert "metrics" in data, "Response should contain 'metrics'"
        assert "opportunities" in data, "Response should contain 'opportunities'"
        assert "accounts" in data, "Response should contain 'accounts'"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
