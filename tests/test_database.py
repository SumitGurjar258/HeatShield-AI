import os
import pytest
from database import init_db, seed_demo_data, get_connection

@pytest.fixture
def temp_db(tmp_path):
    db_file = str(tmp_path / "test_heatshield.db")
    init_db(db_file)
    seed_demo_data(db_file, force=True)
    yield db_file

def test_database_initialization(temp_db):
    conn = get_connection(temp_db)
    cursor = conn.cursor()
    
    # Check tables exist
    tables = [
        "hospitals", "hospital_resources", "resource_inventory",
        "staff_availability", "weather_observations", "weather_forecasts",
        "demand_forecasts", "ambulance_requests", "incoming_patient_alerts",
        "geographic_risk_alerts", "alert_acknowledgements", "resource_update_history"
    ]
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        assert cursor.fetchone() is not None
    conn.close()

def test_hospitals_seeded_properly(temp_db):
    conn = get_connection(temp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM hospitals")
    hosp_count = cursor.fetchone()[0]
    assert hosp_count >= 5
    
    cursor.execute("SELECT total_beds, available_staffed_beds FROM hospital_resources")
    resources = cursor.fetchall()
    assert len(resources) >= 5
    
    # Verify that total_beds != available_staffed_beds
    for r in resources:
        assert r["total_beds"] > r["available_staffed_beds"]
    conn.close()
