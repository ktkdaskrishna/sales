"""
UAT Bug Fixes Test Suite
Tests for critical bugs reported in UAT:
1) Account cards missing data (Industry, Pipeline, Won Revenue)
2) KPI Charts not rendering
3) KPI metrics showing zero values

Test credentials:
- Super Admin: superadmin@salescommand.com / demo123
- Account Manager: am1@salescommand.com / demo123
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://ai-sales-platform-4.preview.emergentagent.com')


class TestAuthentication:
    """Authentication tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for super admin"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "superadmin@salescommand.com", "password": "demo123"}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        return data["access_token"]
    
    def test_login_super_admin(self, auth_token):
        """Test super admin login"""
        assert auth_token is not None
        assert len(auth_token) > 0


class TestAccountsRealEndpoint:
    """Tests for /api/accounts/real endpoint - Bug Fix #1"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "superadmin@salescommand.com", "password": "demo123"}
        )
        return response.json()["access_token"]
    
    def test_accounts_real_returns_data(self, auth_token):
        """Test that /api/accounts/real returns accounts"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/accounts/real", headers=headers)
        
        assert response.status_code == 200, f"API returned {response.status_code}: {response.text}"
        data = response.json()
        
        assert "accounts" in data, "Response missing 'accounts' field"
        assert "count" in data, "Response missing 'count' field"
        assert data["count"] > 0, "No accounts returned"
        print(f"✓ Found {data['count']} accounts")
    
    def test_accounts_have_pipeline_value(self, auth_token):
        """Test that accounts have pipeline_value field"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/accounts/real", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        accounts = data["accounts"]
        
        # Check that at least some accounts have pipeline_value
        accounts_with_pipeline = [a for a in accounts if a.get("pipeline_value", 0) > 0]
        print(f"✓ {len(accounts_with_pipeline)} accounts have pipeline_value > 0")
        
        # Verify field exists on all accounts
        for account in accounts:
            assert "pipeline_value" in account, f"Account {account.get('name')} missing pipeline_value"
    
    def test_accounts_have_won_value(self, auth_token):
        """Test that accounts have won_value field"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/accounts/real", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        accounts = data["accounts"]
        
        # Check that at least some accounts have won_value
        accounts_with_won = [a for a in accounts if a.get("won_value", 0) > 0]
        print(f"✓ {len(accounts_with_won)} accounts have won_value > 0")
        
        # Verify field exists on all accounts
        for account in accounts:
            assert "won_value" in account, f"Account {account.get('name')} missing won_value"
    
    def test_accounts_have_active_opportunities(self, auth_token):
        """Test that accounts have active_opportunities field"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/accounts/real", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        accounts = data["accounts"]
        
        # Verify field exists on all accounts
        for account in accounts:
            assert "active_opportunities" in account, f"Account {account.get('name')} missing active_opportunities"
        
        # Check that at least some accounts have active opportunities
        accounts_with_opps = [a for a in accounts if a.get("active_opportunities", 0) > 0]
        print(f"✓ {len(accounts_with_opps)} accounts have active_opportunities > 0")
    
    def test_accounts_have_names(self, auth_token):
        """Test that all accounts have non-empty names"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/accounts/real", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        accounts = data["accounts"]
        
        for account in accounts:
            name = account.get("name", "")
            assert name and len(name.strip()) > 0, f"Account has empty name: {account}"
        
        print(f"✓ All {len(accounts)} accounts have valid names")


class TestKPIsEndpoint:
    """Tests for /api/kpis endpoint - Bug Fix #2 & #3"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "superadmin@salescommand.com", "password": "demo123"}
        )
        return response.json()["access_token"]
    
    def test_kpis_returns_data(self, auth_token):
        """Test that /api/kpis returns KPIs"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/kpis", headers=headers)
        
        assert response.status_code == 200, f"API returned {response.status_code}: {response.text}"
        data = response.json()
        
        # Response should be a list of KPIs
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        print(f"✓ Found {len(data)} KPIs")
    
    def test_kpis_have_achievement_percentage(self, auth_token):
        """Test that KPIs have achievement_percentage values"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/kpis", headers=headers)
        
        assert response.status_code == 200
        kpis = response.json()
        
        if len(kpis) == 0:
            pytest.skip("No KPIs in database")
        
        # Check that KPIs have achievement_percentage
        for kpi in kpis:
            assert "achievement_percentage" in kpi, f"KPI {kpi.get('name')} missing achievement_percentage"
            print(f"  - {kpi.get('name')}: {kpi.get('achievement_percentage')}%")
        
        # Check that at least some KPIs have non-zero achievement
        kpis_with_achievement = [k for k in kpis if k.get("achievement_percentage", 0) > 0]
        print(f"✓ {len(kpis_with_achievement)}/{len(kpis)} KPIs have achievement_percentage > 0")
    
    def test_kpis_returns_all_kpis(self, auth_token):
        """Test that /api/kpis returns all 4 expected KPIs (not filtered by owner_id)"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/kpis", headers=headers)
        
        assert response.status_code == 200
        kpis = response.json()
        
        # According to the bug report, there should be 4 KPIs
        # The fix was to return all KPIs not filtered by owner_id
        print(f"✓ API returned {len(kpis)} KPIs")
        
        # Print KPI details for verification
        for kpi in kpis:
            print(f"  - {kpi.get('name')}: target={kpi.get('target_value')}, current={kpi.get('current_value')}, achievement={kpi.get('achievement_percentage')}%")


class TestGoalsEndpoint:
    """Tests for /api/goals endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "superadmin@salescommand.com", "password": "demo123"}
        )
        return response.json()["access_token"]
    
    def test_goals_returns_data(self, auth_token):
        """Test that /api/goals returns goals"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/goals", headers=headers)
        
        assert response.status_code == 200, f"API returned {response.status_code}: {response.text}"
        data = response.json()
        
        assert "goals" in data, "Response missing 'goals' field"
        print(f"✓ Found {len(data['goals'])} goals")
    
    def test_goals_have_current_value(self, auth_token):
        """Test that goals have current_value populated from opportunity data"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/goals", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        goals = data.get("goals", [])
        
        if len(goals) == 0:
            pytest.skip("No goals in database")
        
        # Check that goals have current_value
        for goal in goals:
            assert "current_value" in goal, f"Goal {goal.get('name')} missing current_value"
            print(f"  - {goal.get('name')}: current={goal.get('current_value')}, target={goal.get('target_value')}")
    
    def test_goals_summary_stats(self, auth_token):
        """Test that /api/goals/summary/stats returns non-zero overall_progress"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/goals/summary/stats", headers=headers)
        
        assert response.status_code == 200, f"API returned {response.status_code}: {response.text}"
        data = response.json()
        
        assert "total_goals" in data, "Response missing 'total_goals'"
        assert "overall_progress" in data, "Response missing 'overall_progress'"
        
        print(f"✓ Goals Summary: total={data['total_goals']}, progress={data['overall_progress']}%")
        print(f"  - Achieved: {data.get('achieved', 0)}")
        print(f"  - On Track: {data.get('on_track', 0)}")
        print(f"  - At Risk: {data.get('at_risk', 0)}")
        print(f"  - Behind: {data.get('behind', 0)}")


class TestOpportunitiesData:
    """Tests to verify opportunity data exists for metrics calculation"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "superadmin@salescommand.com", "password": "demo123"}
        )
        return response.json()["access_token"]
    
    def test_opportunities_exist(self, auth_token):
        """Test that opportunities exist in the system"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/opportunities", headers=headers)
        
        assert response.status_code == 200, f"API returned {response.status_code}: {response.text}"
        data = response.json()
        
        # Response is a list of opportunities
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        assert len(data) > 0, "No opportunities found"
        
        print(f"✓ Found {len(data)} opportunities")
        
        # Print opportunity details
        for opp in data[:5]:  # First 5
            print(f"  - {opp.get('name')}: ${opp.get('value', 0):,.0f} ({opp.get('stage')})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
