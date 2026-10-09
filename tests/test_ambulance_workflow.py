import pytest
from database import init_db, seed_demo_data
from services.ambulance_service import AmbulanceService
from services.hospital_service import HospitalService

@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    test_db = str(tmp_path / "test_amb.db")
    monkeypatch.setattr("config.Config.DATABASE_PATH", test_db)
    init_db(test_db)
    seed_demo_data(test_db, force=True)
    yield

def test_haversine_distance():
    # St Thomas' (51.4988, -0.1186) to Royal London (51.5190, -0.0594)
    dist = HospitalService.haversine_distance_km(51.4988, -0.1186, 51.5190, -0.0594)
    assert 4.0 <= dist <= 6.0
    
    eta = HospitalService.estimate_travel_time_minutes(dist)
    assert eta >= 10

def test_candidate_hospital_matching():
    # Match for Heat Stroke Resuscitation + Burns/Cooling Unit
    res = AmbulanceService.match_candidate_hospitals(
        patient_lat=51.5000,
        patient_lon=-0.1200,
        required_capabilities=["Heat Stroke Resuscitation", "Burns/Cooling Unit"],
        urgency="Red (Immediate - Category 1 Life Threat)"
    )
    
    candidates = res["candidates"]
    assert len(candidates) > 0
    
    # Check that all candidates have both capabilities
    for c in candidates:
        assert "Heat Stroke Resuscitation" in c["capabilities"]
        assert "Burns/Cooling Unit" in c["capabilities"]

def test_dispatch_and_alert_lifecycle():
    dispatch_info = AmbulanceService.create_dispatch_request(
        patient_urgency="Red (Immediate)",
        condition_summary="Core temperature 40.5C, obtunded",
        required_capabilities=["Heat Stroke Resuscitation"],
        origin_lat=51.505,
        origin_lon=-0.110,
        destination_hospital_id="HOSP-LON-01",
        eta_minutes=14
    )
    
    req_id = dispatch_info["request_id"]
    assert req_id.startswith("AMB-")
    assert dispatch_info["status"] == "En Route"
    
    # Verify incoming alerts in hospital dashboard
    alerts = AmbulanceService.get_incoming_alerts(hospital_id="HOSP-LON-01")
    assert len(alerts) >= 1
    found = [a for a in alerts if a["request_id"] == req_id]
    assert len(found) == 1
    alert_item = found[0]
    assert alert_item["alert_status"] == "Pending"
    
    # Hospital nurse acknowledges alert
    ack_res = AmbulanceService.update_alert_status(
        alert_id=alert_item["id"],
        new_status="Acknowledged",
        acknowledged_by="Nurse Williams",
        role="Hospital Charge Nurse",
        notes="Cooling tub prepared"
    )
    assert ack_res is True
    
    # Check updated alert status
    updated_alerts = AmbulanceService.get_incoming_alerts(hospital_id="HOSP-LON-01")
    updated_found = [a for a in updated_alerts if a["request_id"] == req_id][0]
    assert updated_found["alert_status"] == "Acknowledged"
