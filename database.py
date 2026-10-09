import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from config import Config

def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Return a connection to the SQLite database with row factory enabled."""
    path = db_path or Config.DATABASE_PATH
    conn = sqlite3.connect(path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db(db_path: Optional[str] = None) -> None:
    """Initialize database tables and indexes."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    # 1. Hospitals Registry
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hospitals (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        address TEXT,
        capabilities TEXT, -- JSON array of capability tags
        contact_endpoint TEXT,
        is_active INTEGER DEFAULT 1,
        created_at TEXT NOT NULL
    );
    """)

    # 2. Hospital Resources
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hospital_resources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hospital_id TEXT NOT NULL,
        total_beds INTEGER,
        occupied_beds INTEGER,
        available_staffed_beds INTEGER,
        specialist_availability TEXT, -- JSON or string summary
        nursing_staff_count INTEGER,
        nursing_staff_status TEXT, -- 'Adequate', 'Strained', 'Critical Shortage', 'Unknown'
        ambulance_count INTEGER,
        critical_medicines_status TEXT, -- 'Adequate', 'Low', 'Critical', 'Unknown'
        supplies_status TEXT, -- 'Adequate', 'Low', 'Critical', 'Unknown'
        last_updated TEXT NOT NULL,
        data_source TEXT NOT NULL, -- e.g. 'Hospital Electronic Feed', 'Demonstration Record'
        verification_status TEXT NOT NULL, -- 'Verified', 'Pending', 'Stale', 'Simulated'
        FOREIGN KEY (hospital_id) REFERENCES hospitals(id) ON DELETE CASCADE
    );
    """)

    # 3. Resource Inventory Items
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS resource_inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hospital_id TEXT NOT NULL,
        item_type TEXT NOT NULL, -- 'medicine', 'supply', 'equipment'
        item_name TEXT NOT NULL,
        quantity REAL,
        unit TEXT,
        status TEXT NOT NULL, -- 'Adequate', 'Low', 'Critical', 'Unknown'
        last_updated TEXT NOT NULL,
        FOREIGN KEY (hospital_id) REFERENCES hospitals(id) ON DELETE CASCADE
    );
    """)

    # 4. Staff Availability Records
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS staff_availability (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hospital_id TEXT NOT NULL,
        role TEXT NOT NULL,
        staff_name TEXT,
        on_duty_count INTEGER,
        status TEXT NOT NULL, -- 'Available', 'On-Call', 'Unavailable', 'Unknown'
        last_updated TEXT NOT NULL,
        FOREIGN KEY (hospital_id) REFERENCES hospitals(id) ON DELETE CASCADE
    );
    """)

    # 5. Weather Observations
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS weather_observations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        location_name TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        recorded_at TEXT NOT NULL,
        temperature_c REAL NOT NULL,
        humidity_pct REAL NOT NULL,
        heat_index_c REAL,
        heat_risk_level TEXT NOT NULL,
        data_source TEXT NOT NULL
    );
    """)

    # 6. Weather Forecasts
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS weather_forecasts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        location_name TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        forecast_time TEXT NOT NULL,
        temp_max_c REAL NOT NULL,
        temp_min_c REAL NOT NULL,
        humidity_pct REAL NOT NULL,
        heatwave_flag INTEGER DEFAULT 0,
        heat_risk_level TEXT NOT NULL,
        data_source TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)

    # 7. Healthcare Demand Forecasts
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS demand_forecasts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        forecast_date TEXT NOT NULL,
        hospital_id TEXT,
        predicted_ae_attendances REAL NOT NULL,
        predicted_emergency_admissions REAL NOT NULL,
        lower_ci REAL,
        upper_ci REAL,
        model_version TEXT,
        created_at TEXT NOT NULL
    );
    """)

    # 8. Ambulance Requests
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ambulance_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id TEXT UNIQUE NOT NULL,
        patient_urgency TEXT NOT NULL, -- 'Red (Immediate)', 'Amber (Urgent)', 'Green (Standard)'
        condition_summary TEXT NOT NULL,
        required_capabilities TEXT, -- JSON array
        origin_lat REAL,
        origin_lon REAL,
        destination_hospital_id TEXT,
        status TEXT NOT NULL, -- 'Dispatched', 'En Route', 'Arrived', 'Closed'
        eta_minutes INTEGER,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (destination_hospital_id) REFERENCES hospitals(id)
    );
    """)

    # 9. Incoming Patient Alerts
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS incoming_patient_alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id TEXT NOT NULL,
        hospital_id TEXT NOT NULL,
        patient_urgency TEXT NOT NULL,
        care_requirements TEXT,
        eta_minutes INTEGER,
        alert_status TEXT NOT NULL, -- 'Pending', 'Acknowledged', 'Prepared', 'Completed'
        created_at TEXT NOT NULL,
        acknowledged_at TEXT,
        acknowledged_by TEXT,
        FOREIGN KEY (request_id) REFERENCES ambulance_requests(request_id),
        FOREIGN KEY (hospital_id) REFERENCES hospitals(id)
    );
    """)

    # 10. Geographic Risk Alerts
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS geographic_risk_alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hospital_id TEXT NOT NULL,
        severity TEXT NOT NULL, -- 'Low', 'Moderate', 'High', 'Critical'
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        bottleneck_factor TEXT NOT NULL,
        status TEXT NOT NULL, -- 'Active', 'Acknowledged', 'Resolved'
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (hospital_id) REFERENCES hospitals(id)
    );
    """)

    # 11. Alert Acknowledgements
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alert_acknowledgements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        alert_type TEXT NOT NULL, -- 'geo_risk' or 'incoming_patient'
        alert_id INTEGER NOT NULL,
        user_role TEXT NOT NULL,
        acknowledged_by TEXT NOT NULL,
        notes TEXT,
        timestamp TEXT NOT NULL
    );
    """)

    # 12. Resource Update History
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS resource_update_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hospital_id TEXT NOT NULL,
        field_changed TEXT NOT NULL,
        old_value TEXT,
        new_value TEXT,
        updated_by TEXT NOT NULL,
        role TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        reason TEXT,
        FOREIGN KEY (hospital_id) REFERENCES hospitals(id)
    );
    """)

    # Indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_hosp_active ON hospitals(is_active);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_res_hosp ON hospital_resources(hospital_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_geo_alerts_hosp ON geographic_risk_alerts(hospital_id, status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_inc_alerts_hosp ON incoming_patient_alerts(hospital_id, alert_status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_weather_loc ON weather_forecasts(location_name, forecast_time);")

    conn.commit()
    conn.close()

def seed_demo_data(db_path: Optional[str] = None, force: bool = False) -> None:
    """Seed labelled demonstration data for hospitals and initial resources."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    # Check if hospitals already exist
    cursor.execute("SELECT COUNT(*) FROM hospitals")
    count = cursor.fetchone()[0]
    if count > 0 and not force:
        conn.close()
        return

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    # Sample hospitals (e.g. Greater London Healthcare Region network)
    demo_hospitals = [
        (
            "HOSP-LON-01",
            "St Thomas' Heat Emergency Hospital",
            51.4988,
            -0.1186,
            "Westminster Bridge Rd, London SE1 7EH",
            json.dumps(["Heat Stroke Resuscitation", "Burns/Cooling Unit", "ICU", "Renal Dialysis", "Adult Emergency"]),
            "dispatch@stthomas.demo-nhs.net",
            1,
            now_iso
        ),
        (
            "HOSP-LON-02",
            "Royal London Heatwave Trauma Centre",
            51.5190,
            -0.0594,
            "Whitechapel Rd, London E1 1FR",
            json.dumps(["Heat Stroke Resuscitation", "ICU", "Pediatric Emergency", "Cardiology", "Adult Emergency"]),
            "trauma@royallondon.demo-nhs.net",
            1,
            now_iso
        ),
        (
            "HOSP-LON-03",
            "King's College Hospital Emergency Unit",
            51.4682,
            -0.0935,
            "Denmark Hill, Brixton, London SE5 9RS",
            json.dumps(["Heat Stroke Resuscitation", "Burns/Cooling Unit", "Renal Dialysis", "Adult Emergency"]),
            "ops@kings.demo-nhs.net",
            1,
            now_iso
        ),
        (
            "HOSP-LON-04",
            "St Mary's Urgent & Acute Care Pavilion",
            51.5175,
            -0.1746,
            "Praed St, Paddington, London W2 1NY",
            json.dumps(["Pediatric Emergency", "ICU", "Adult Emergency"]),
            "dispatch@stmarys.demo-nhs.net",
            1,
            now_iso
        ),
        (
            "HOSP-LON-05",
            "North Middlesex University Hospital",
            51.6143,
            -0.0766,
            "Sterling Way, London N18 1QX",
            json.dumps(["Adult Emergency", "Renal Dialysis", "Cooling Therapy"]),
            "emergency@northmid.demo-nhs.net",
            1,
            now_iso
        ),
        (
            "HOSP-LON-06",
            "Croydon Health Services Community Hospital",
            51.3887,
            -0.1147,
            "530 London Rd, Thornton Heath, Croydon CR7 7YE",
            json.dumps(["Adult Emergency", "Geriatric Heat Vulnerability"]),
            "ops@croydon.demo-nhs.net",
            1,
            now_iso
        )
    ]

    cursor.executemany("""
    INSERT OR REPLACE INTO hospitals (id, name, latitude, longitude, address, capabilities, contact_endpoint, is_active, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, demo_hospitals)

    # Sample resource levels (clearly showing distinction between total and available staffed beds!)
    demo_resources = [
        # hospital_id, total_beds, occupied_beds, available_staffed_beds, specialist_availability, nursing_count, nursing_status, amb_count, meds_status, supplies_status, last_updated, source, verification
        ("HOSP-LON-01", 380, 342, 14, json.dumps({"Emergency Physicians": 4, "Cooling Specialists": 2, "Intensivists": 2}), 28, "Adequate", 5, "Adequate", "Adequate", now_iso, "Synthetic Demonstration Record", "Simulated"),
        ("HOSP-LON-02", 420, 408, 4, json.dumps({"Emergency Physicians": 2, "Cooling Specialists": 0, "Intensivists": 1}), 14, "Critical Shortage", 2, "Low", "Critical", now_iso, "Synthetic Demonstration Record", "Simulated"),
        ("HOSP-LON-03", 310, 275, 18, json.dumps({"Emergency Physicians": 3, "Cooling Specialists": 1, "Intensivists": 2}), 22, "Adequate", 4, "Adequate", "Adequate", now_iso, "Synthetic Demonstration Record", "Simulated"),
        ("HOSP-LON-04", 290, 282, 3, json.dumps({"Emergency Physicians": 1, "Cooling Specialists": 0, "Intensivists": 1}), 11, "Strained", 1, "Low", "Low", now_iso, "Synthetic Demonstration Record", "Simulated"),
        ("HOSP-LON-05", 260, 220, 25, json.dumps({"Emergency Physicians": 3, "Cooling Specialists": 1, "Intensivists": 1}), 20, "Adequate", 3, "Adequate", "Adequate", now_iso, "Synthetic Demonstration Record", "Simulated"),
        ("HOSP-LON-06", 180, 172, 2, json.dumps({"Emergency Physicians": 1, "Cooling Specialists": 0, "Intensivists": 0}), 8, "Critical Shortage", 1, "Critical", "Low", now_iso, "Synthetic Demonstration Record", "Simulated"),
    ]

    cursor.executemany("""
    INSERT INTO hospital_resources (
        hospital_id, total_beds, occupied_beds, available_staffed_beds,
        specialist_availability, nursing_staff_count, nursing_staff_status,
        ambulance_count, critical_medicines_status, supplies_status,
        last_updated, data_source, verification_status
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, demo_resources)

    # Sample Inventory Items
    inventory_items = [
        ("HOSP-LON-01", "medicine", "IV Saline & Electrolyte Cooling Solutions", 450, "Bags (1L)", "Adequate", now_iso),
        ("HOSP-LON-01", "equipment", "Cold Water Immersion Cooling Tubs", 6, "Units", "Adequate", now_iso),
        ("HOSP-LON-01", "supply", "Body Cooling Evaporative Blankets", 48, "Packs", "Adequate", now_iso),
        ("HOSP-LON-02", "medicine", "IV Saline & Electrolyte Cooling Solutions", 22, "Bags (1L)", "Critical", now_iso),
        ("HOSP-LON-02", "equipment", "Cold Water Immersion Cooling Tubs", 1, "Units", "Low", now_iso),
        ("HOSP-LON-02", "supply", "Body Cooling Evaporative Blankets", 5, "Packs", "Critical", now_iso),
        ("HOSP-LON-03", "medicine", "IV Saline & Electrolyte Cooling Solutions", 310, "Bags (1L)", "Adequate", now_iso),
        ("HOSP-LON-04", "medicine", "IV Saline & Electrolyte Cooling Solutions", 40, "Bags (1L)", "Low", now_iso),
        ("HOSP-LON-06", "medicine", "IV Saline & Electrolyte Cooling Solutions", 12, "Bags (1L)", "Critical", now_iso),
    ]
    cursor.executemany("""
    INSERT INTO resource_inventory (hospital_id, item_type, item_name, quantity, unit, status, last_updated)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, inventory_items)

    # Sample Staff availability
    staff_items = [
        ("HOSP-LON-01", "Emergency Physician", "Dr. Sarah Jenkins", 4, "Available", now_iso),
        ("HOSP-LON-01", "Heat Stroke Specialist", "Dr. Liam Patel", 2, "Available", now_iso),
        ("HOSP-LON-02", "Emergency Physician", "Dr. Tariq Khan", 2, "Available", now_iso),
        ("HOSP-LON-02", "Heat Stroke Specialist", "Unknown", 0, "Unavailable", now_iso),
        ("HOSP-LON-03", "Emergency Physician", "Dr. Emma Watson", 3, "Available", now_iso),
        ("HOSP-LON-04", "Emergency Physician", "Dr. Oliver Smith", 1, "Available", now_iso),
        ("HOSP-LON-06", "Emergency Physician", "Dr. David Bell", 1, "Available", now_iso),
    ]
    cursor.executemany("""
    INSERT INTO staff_availability (hospital_id, role, staff_name, on_duty_count, status, last_updated)
    VALUES (?, ?, ?, ?, ?, ?)
    """, staff_items)

    conn.commit()
    conn.close()
