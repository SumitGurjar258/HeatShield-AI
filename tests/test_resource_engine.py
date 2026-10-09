import pytest
from services.resource_engine import ResourceShortfallEngine

def test_bed_shortfall_calculation():
    # Case 1: Demand exceeds available staffed beds
    resource = {
        "hospital_id": "HOSP-01",
        "hospital_name": "Test Hospital",
        "total_beds": 300,
        "occupied_beds": 290,
        "available_staffed_beds": 10,
        "critical_medicines_status": "Adequate",
        "supplies_status": "Adequate",
        "nursing_staff_status": "Adequate",
        "freshness": "Current"
    }
    
    # Expected demand is 18 admissions
    eval_result = ResourceShortfallEngine.calculate_hospital_capacity_risk(
        hospital_resource=resource,
        expected_demand_admissions=18.0,
        safety_buffer_pct=10.0
    )
    
    # Shortfall must be max(0, 18 - 10) = 8.0
    assert eval_result["projected_bed_shortfall"] == 8.0
    assert eval_result["severity"] in ["High", "Critical"]
    assert "Staffed Beds Deficit (-8.0 beds)" in eval_result["primary_bottleneck"]

def test_bed_surplus_zero_shortfall():
    # Case 2: Available staffed beds exceed demand
    resource = {
        "hospital_id": "HOSP-02",
        "hospital_name": "Surplus Hospital",
        "total_beds": 300,
        "available_staffed_beds": 35,
        "critical_medicines_status": "Adequate",
        "supplies_status": "Adequate",
        "nursing_staff_status": "Adequate",
        "freshness": "Current"
    }
    
    eval_result = ResourceShortfallEngine.calculate_hospital_capacity_risk(
        hospital_resource=resource,
        expected_demand_admissions=12.0
    )
    
    # Shortfall must be max(0, 12 - 35) = 0.0
    assert eval_result["projected_bed_shortfall"] == 0.0
    assert eval_result["severity"] == "Low"

def test_unknown_beds_handling():
    # Case 3: Unavailable information represented as Unknown
    resource = {
        "hospital_id": "HOSP-03",
        "hospital_name": "Unreported Hospital",
        "total_beds": 150,
        "available_staffed_beds": "Unknown",
        "critical_medicines_status": "Unknown",
        "supplies_status": "Unknown",
        "nursing_staff_status": "Unknown",
        "freshness": "Stale (>24h)"
    }
    
    eval_result = ResourceShortfallEngine.calculate_hospital_capacity_risk(
        hospital_resource=resource,
        expected_demand_admissions=10.0
    )
    
    assert eval_result["available_staffed_beds"] == "Unknown"
    assert eval_result["projected_bed_shortfall"] == "Unknown"
    assert eval_result["severity"] == "Unknown"
    assert "Missing Staffed Bed Telemetry" in eval_result["primary_bottleneck"]
