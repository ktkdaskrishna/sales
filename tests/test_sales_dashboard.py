"""
Sales Dashboard & Blue Sheet API Tests
Tests for Account Manager Dashboard, Kanban Pipeline, Blue Sheet Probability Calculator,
Incentive Calculator, and Global Search features.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://ai-sales-platform-4.preview.emergentagent.com')

class TestSalesDashboardAPIs:
    """Sales Dashboard API tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as superadmin
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "superadmin@salescommand.com", "password": "demo123"}
        )
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        token = login_response.json()["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        self.user_id = login_response.json()["user"]["id"]
    
    # ==================== DASHBOARD STATS ====================
    
    def test_dashboard_stats_returns_kpi_data(self):
        """Test dashboard stats endpoint returns KPI data"""
        response = self.session.get(f"{BASE_URL}/api/dashboard/stats")
        assert response.status_code == 200
        
        data = response.json()
        # Verify all expected KPI fields exist
        assert "total_pipeline_value" in data
        assert "won_revenue" in data
        assert "active_opportunities" in data
        assert "total_opportunities" in data
        assert "activity_completion_rate" in data
        
        # Verify data types
        assert isinstance(data["total_pipeline_value"], (int, float))
        assert isinstance(data["won_revenue"], (int, float))
        assert isinstance(data["active_opportunities"], int)
        
        # Verify expected values based on test data
        assert data["total_pipeline_value"] >= 1000000, "Pipeline value should be ~$1.25M"
        assert data["won_revenue"] >= 100000, "Won revenue should be ~$170K"
        assert data["active_opportunities"] >= 5, "Should have 6+ active opportunities"
        print(f"Dashboard Stats: Pipeline=${data['total_pipeline_value']:,}, Won=${data['won_revenue']:,}, Active={data['active_opportunities']}")
    
    # ==================== KANBAN BOARD ====================
    
    def test_kanban_board_returns_stages_and_opportunities(self):
        """Test Kanban board endpoint returns stages and opportunities"""
        response = self.session.get(f"{BASE_URL}/api/opportunities/kanban")
        assert response.status_code == 200
        
        data = response.json()
        assert "stages" in data
        assert "kanban" in data
        
        # Verify 7 stages exist
        assert len(data["stages"]) == 7, f"Expected 7 stages, got {len(data['stages'])}"
        
        # Verify stage structure
        stage_ids = [s["id"] for s in data["stages"]]
        expected_stages = ["lead", "qualification", "discovery", "proposal", "negotiation", "closed_won", "closed_lost"]
        for stage_id in expected_stages:
            assert stage_id in stage_ids, f"Missing stage: {stage_id}"
        
        # Verify kanban data structure
        for stage_id in stage_ids:
            assert stage_id in data["kanban"], f"Kanban missing stage: {stage_id}"
            assert "opportunities" in data["kanban"][stage_id]
        
        print(f"Kanban Board: {len(data['stages'])} stages loaded")
    
    def test_kanban_stage_has_correct_properties(self):
        """Test each Kanban stage has required properties"""
        response = self.session.get(f"{BASE_URL}/api/opportunities/kanban")
        assert response.status_code == 200
        
        data = response.json()
        for stage in data["stages"]:
            assert "id" in stage
            assert "name" in stage
            assert "color" in stage
            assert "order" in stage
            print(f"Stage: {stage['name']} (order={stage['order']}, color={stage['color']})")
    
    # ==================== OPPORTUNITIES ====================
    
    def test_get_all_opportunities(self):
        """Test getting all opportunities"""
        response = self.session.get(f"{BASE_URL}/api/opportunities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 6, f"Expected 6+ opportunities, got {len(data)}"
        
        # Verify opportunity structure
        if len(data) > 0:
            opp = data[0]
            assert "id" in opp
            assert "name" in opp
            assert "value" in opp
            assert "stage" in opp
            assert "probability" in opp
        
        print(f"Opportunities: {len(data)} total")
    
    def test_update_opportunity_stage_drag_drop(self):
        """Test updating opportunity stage (drag-drop simulation)"""
        # Get first opportunity
        opps_response = self.session.get(f"{BASE_URL}/api/opportunities")
        assert opps_response.status_code == 200
        opps = opps_response.json()
        assert len(opps) > 0
        
        opp_id = opps[0]["id"]
        original_stage = opps[0]["stage"]
        
        # Move to a different stage
        new_stage = "proposal" if original_stage != "proposal" else "discovery"
        response = self.session.patch(f"{BASE_URL}/api/opportunities/{opp_id}/stage?new_stage={new_stage}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["stage"] == new_stage
        assert "probability" in data
        
        # Restore original stage
        self.session.patch(f"{BASE_URL}/api/opportunities/{opp_id}/stage?new_stage={original_stage}")
        print(f"Stage update: {original_stage} -> {new_stage} -> {original_stage}")
    
    # ==================== BLUE SHEET PROBABILITY ====================
    
    def test_blue_sheet_probability_calculation(self):
        """Test Blue Sheet probability calculation with AI recommendations"""
        # Get first opportunity
        opps_response = self.session.get(f"{BASE_URL}/api/opportunities")
        assert opps_response.status_code == 200
        opps = opps_response.json()
        assert len(opps) > 0
        
        opp_id = opps[0]["id"]
        
        # Calculate probability with Blue Sheet analysis
        analysis_data = {
            "opportunity_id": opp_id,
            "economic_buyer_identified": True,
            "economic_buyer_favorable": True,
            "user_buyers_identified": 2,
            "user_buyers_favorable": 2,
            "technical_buyers_identified": 1,
            "technical_buyers_favorable": 1,
            "coach_identified": True,
            "coach_engaged": True,
            "no_access_to_economic_buyer": False,
            "reorganization_pending": False,
            "budget_not_confirmed": False,
            "competition_preferred": False,
            "timeline_unclear": False,
            "clear_business_results": True,
            "quantifiable_value": True,
            "next_steps_defined": True,
            "mutual_action_plan": True
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/opportunities/{opp_id}/calculate-probability",
            json=analysis_data
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "calculated_probability" in data
        assert "confidence_level" in data
        assert "analysis_summary" in data
        assert "recommendations" in data
        assert "score_breakdown" in data
        
        # Verify probability is reasonable
        assert 0 <= data["calculated_probability"] <= 100
        assert data["confidence_level"] in ["low", "medium", "high"]
        
        # Verify AI recommendations exist (may be fallback if LLM fails)
        assert isinstance(data["recommendations"], list)
        
        print(f"Blue Sheet: Probability={data['calculated_probability']}%, Confidence={data['confidence_level']}")
        print(f"Recommendations: {len(data['recommendations'])} generated")
    
    def test_blue_sheet_with_red_flags(self):
        """Test Blue Sheet calculation with red flags reduces probability"""
        opps_response = self.session.get(f"{BASE_URL}/api/opportunities")
        opps = opps_response.json()
        opp_id = opps[0]["id"]
        
        # Analysis with red flags
        analysis_data = {
            "opportunity_id": opp_id,
            "economic_buyer_identified": False,
            "economic_buyer_favorable": False,
            "no_access_to_economic_buyer": True,
            "budget_not_confirmed": True,
            "competition_preferred": True,
            "timeline_unclear": True
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/opportunities/{opp_id}/calculate-probability",
            json=analysis_data
        )
        assert response.status_code == 200
        
        data = response.json()
        # With red flags, probability should be low
        assert data["calculated_probability"] < 50, "Red flags should reduce probability"
        assert data["score_breakdown"]["red_flags"] < 0, "Red flags should have negative score"
        
        print(f"Blue Sheet with Red Flags: Probability={data['calculated_probability']}%")
    
    # ==================== INCENTIVE CALCULATOR ====================
    
    def test_incentive_calculator_basic(self):
        """Test basic incentive calculation"""
        response = self.session.post(
            f"{BASE_URL}/api/incentive-calculator?revenue=100000&quota=500000&is_new_logo=false"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "revenue" in data
        assert "quota" in data
        assert "attainment" in data
        assert "base_commission" in data
        assert "final_commission" in data
        
        # Verify calculations
        assert data["revenue"] == 100000
        assert data["quota"] == 500000
        assert data["attainment"] == 20  # 100000/500000 * 100
        assert data["base_commission"] == 5000  # 100000 * 0.05
        
        print(f"Incentive Calculator: Revenue=${data['revenue']:,}, Commission=${data['final_commission']:,}")
    
    def test_incentive_calculator_with_new_logo(self):
        """Test incentive calculation with new logo multiplier"""
        response = self.session.post(
            f"{BASE_URL}/api/incentive-calculator?revenue=100000&quota=500000&is_new_logo=true"
        )
        assert response.status_code == 200
        
        data = response.json()
        # New logo should apply 1.5x multiplier
        assert data["final_commission"] > data["base_commission"]
        
        # Check multiplier was applied
        new_logo_mult = next((m for m in data["multipliers_applied"] if m["type"] == "new_logo"), None)
        assert new_logo_mult is not None
        assert new_logo_mult["value"] == 1.5
        
        print(f"New Logo Commission: ${data['final_commission']:,} (1.5x multiplier)")
    
    def test_incentive_calculator_with_product_line(self):
        """Test incentive calculation with product line weight"""
        response = self.session.post(
            f"{BASE_URL}/api/incentive-calculator?revenue=100000&quota=500000&is_new_logo=false&product_line=MSSP"
        )
        assert response.status_code == 200
        
        data = response.json()
        # MSSP has 1.2x weight
        assert data["final_commission"] > data["base_commission"]
        
        print(f"MSSP Product Line Commission: ${data['final_commission']:,}")
    
    def test_commission_templates_list(self):
        """Test getting commission templates"""
        response = self.session.get(f"{BASE_URL}/api/commission-templates")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2, "Should have at least 2 default templates"
        
        # Verify template structure
        if len(data) > 0:
            template = data[0]
            assert "id" in template
            assert "name" in template
            assert "template_type" in template
            assert "base_rate" in template
        
        print(f"Commission Templates: {len(data)} available")
    
    # ==================== GLOBAL SEARCH ====================
    
    def test_global_search_accounts(self):
        """Test global search finds accounts"""
        response = self.session.get(f"{BASE_URL}/api/search?q=tech")
        assert response.status_code == 200
        
        data = response.json()
        assert "results" in data
        assert "query" in data
        assert data["query"] == "tech"
        
        # Should find accounts with "tech" in name
        account_results = [r for r in data["results"] if r["type"] == "account"]
        print(f"Search 'tech': {len(data['results'])} results, {len(account_results)} accounts")
    
    def test_global_search_opportunities(self):
        """Test global search finds opportunities"""
        response = self.session.get(f"{BASE_URL}/api/search?q=security")
        assert response.status_code == 200
        
        data = response.json()
        opp_results = [r for r in data["results"] if r["type"] == "opportunity"]
        assert len(opp_results) > 0, "Should find opportunities with 'security'"
        
        print(f"Search 'security': {len(opp_results)} opportunities found")
    
    def test_global_search_minimum_length(self):
        """Test global search requires minimum 2 characters"""
        response = self.session.get(f"{BASE_URL}/api/search?q=a")
        # Should return 422 validation error for single character
        assert response.status_code == 422
    
    # ==================== SALES METRICS ====================
    
    def test_sales_metrics_for_user(self):
        """Test getting sales metrics for a user"""
        response = self.session.get(f"{BASE_URL}/api/sales-metrics/{self.user_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert "user_id" in data
        assert "period" in data
        assert "orders_won" in data
        assert "quota" in data
        assert "attainment_percentage" in data
        assert "commission_earned" in data
        
        print(f"Sales Metrics: Won=${data['orders_won']:,}, Attainment={data['attainment_percentage']}%")
    
    def test_sales_metrics_different_periods(self):
        """Test sales metrics for different periods"""
        for period in ["monthly", "quarterly", "ytd"]:
            response = self.session.get(f"{BASE_URL}/api/sales-metrics/{self.user_id}?period={period}")
            assert response.status_code == 200
            data = response.json()
            assert data["period"] == period
            print(f"Sales Metrics ({period}): Won=${data['orders_won']:,}")
    
    # ==================== ACTIVITIES ====================
    
    def test_get_activities(self):
        """Test getting activities"""
        response = self.session.get(f"{BASE_URL}/api/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        print(f"Activities: {len(data)} total")
    
    def test_get_pending_activities(self):
        """Test getting pending activities"""
        response = self.session.get(f"{BASE_URL}/api/activities?status=pending")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        # All returned activities should be pending
        for activity in data:
            assert activity.get("status") == "pending"
        
        print(f"Pending Activities: {len(data)}")
    
    # ==================== ACCOUNTS ====================
    
    def test_get_accounts(self):
        """Test getting accounts"""
        response = self.session.get(f"{BASE_URL}/api/accounts")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0, "Should have test accounts"
        
        # Verify account structure
        account = data[0]
        assert "id" in account
        assert "name" in account
        
        print(f"Accounts: {len(data)} total")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
