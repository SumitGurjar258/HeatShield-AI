import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from database import get_connection
from services.hospital_service import HospitalService

class AmbulanceService:
    """Ambulance-to-Hospital Coordination & Dispatch Decision-Support Service.
    
    Provides clinical criteria matching, travel-time estimation, incoming alert generation,
    and arrival status tracking. Strictly adheres to decision-support safety boundaries.
    """
    
    CAPABILITY_OPTIONS = [
        "Heat Stroke Resuscitation",
        "Burns/Cooling Unit",
        "ICU",
        "Renal Dialysis",
        "Pediatric Emergency",
        "Adult Emergency",
        "Cardiology",
        "Cooling Therapy"
    ]
    
    URGENCY_LEVELS = [
        "Red (Immediate - Category 1 Life Threat)",
        "Amber (Urgent - Category 2 Serious Condition)",
        "Green (Standard - Category 3/4 Non-Immediate)"
    ]

    @classmethod
    def match_candidate_hospitals(
        cls,
        patient_lat: float,
        patient_lon: float,
        required_capabilities: List[str],
        urgency: str
    ) -> Dict[str, Any]:
        """Filter and rank candidate receiving hospitals based on capabilities, distance, and capacity.
        
        Never silently directs an ambulance to an unverified or incapable facility.
        """
        all_resources = HospitalService.get_hospital_resources()
        candidate_list = []
        ineligible_list = []
        
        for r in all_resources:
            caps = r.get("capabilities", [])
            avail_beds = r.get("available_staffed_beds")
            dist_km = HospitalService.haversine_distance_km(patient_lat, patient_lon, r["latitude"], r["longitude"])
            eta_mins = HospitalService.estimate_travel_time_minutes(dist_km)
            
            # Check capability match
            missing_caps = [c for c in required_capabilities if c not in caps]
            has_all_caps = len(missing_caps) == 0
            
            # Check bed availability
            is_beds_known = avail_beds != "Unknown" and avail_beds is not None
            has_capacity = is_beds_known and int(avail_beds) > 0
            
            # Freshness check
            is_stale = r.get("freshness", "").startswith("Stale")
            
            candidate_item = {
                "hospital_id": r["hospital_id"],
                "hospital_name": r["hospital_name"],
                "latitude": r["latitude"],
                "longitude": r["longitude"],
                "distance_km": dist_km,
                "eta_minutes": eta_mins,
                "available_staffed_beds": avail_beds,
                "total_beds": r["total_beds"],
                "specialist_availability": r["specialist_availability"],
                "supplies_status": r["supplies_status"],
                "nursing_staff_status": r["nursing_staff_status"],
                "capabilities": caps,
                "missing_capabilities": missing_caps,
                "freshness": r["freshness"],
                "is_stale": is_stale,
                "verification_status": r["verification_status"],
                "suitability": "Candidate" if has_all_caps and has_capacity and not is_stale else "Constrained"
            }
            
            if has_all_caps:
                candidate_list.append(candidate_item)
            else:
                ineligible_list.append(candidate_item)
                
        # Sort candidates: prioritize Available Staffed Beds > ETA
        # High bed count and lower ETA gets best score
        def score_candidate(c):
            beds = c["available_staffed_beds"]
            bed_score = int(beds) if isinstance(beds, (int, float)) else 0
            return (bed_score > 0, -c["eta_minutes"], bed_score)
            
        candidate_list.sort(key=score_candidate, reverse=True)
        
        warning_message = None
        if not candidate_list:
            warning_message = (
                "CRITICAL WARNING: No hospital meets all selected capability requirements within regional network. "
                "Do NOT divert to an unverified location without consulting Central Emergency Ambulance Dispatch."
            )
        elif all(c["is_stale"] for c in candidate_list):
            warning_message = (
                "DATA FRESHNESS WARNING: All matching hospitals report stale telemetry (>24h old). "
                "Voice verification with hospital triage via radio/phone is mandatory before departure."
            )

        return {
            "candidates": candidate_list,
            "ineligible": ineligible_list,
            "warning": warning_message,
            "required_capabilities": required_capabilities
        }

    @staticmethod
    def create_dispatch_request(
        patient_urgency: str,
        condition_summary: str,
        required_capabilities: List[str],
        origin_lat: float,
        origin_lon: float,
        destination_hospital_id: str,
        eta_minutes: int
    ) -> Dict[str, Any]:
        """Create an ambulance dispatch record and generate an incoming patient alert for hospital staff."""
        conn = get_connection()
        cursor = conn.cursor()
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        req_id = f"AMB-{datetime.now().strftime('%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        
        # 1. Insert ambulance request
        cursor.execute("""
        INSERT INTO ambulance_requests (
            request_id, patient_urgency, condition_summary, required_capabilities,
            origin_lat, origin_lon, destination_hospital_id, status,
            eta_minutes, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            req_id,
            patient_urgency,
            condition_summary,
            json.dumps(required_capabilities),
            origin_lat,
            origin_lon,
            destination_hospital_id,
            "En Route",
            eta_minutes,
            now_str,
            now_str
        ))
        
        # 2. Insert incoming patient alert for hospital dashboard
        cursor.execute("""
        INSERT INTO incoming_patient_alerts (
            request_id, hospital_id, patient_urgency, care_requirements,
            eta_minutes, alert_status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            req_id,
            destination_hospital_id,
            patient_urgency,
            f"{condition_summary} | Required: {', '.join(required_capabilities)}",
            eta_minutes,
            "Pending",
            now_str
        ))
        
        conn.commit()
        conn.close()
        
        return {
            "request_id": req_id,
            "hospital_id": destination_hospital_id,
            "patient_urgency": patient_urgency,
            "eta_minutes": eta_minutes,
            "status": "En Route",
            "alert_status": "Pending",
            "created_at": now_str
        }

    @staticmethod
    def get_incoming_alerts(hospital_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve incoming patient alerts for hospital clinical team."""
        conn = get_connection()
        cursor = conn.cursor()
        
        query = """
        SELECT a.*, h.name as hospital_name
        FROM incoming_patient_alerts a
        JOIN hospitals h ON a.hospital_id = h.id
        """
        params = []
        if hospital_id:
            query += " WHERE a.hospital_id = ?"
            params.append(hospital_id)
            
        query += " ORDER BY CASE a.alert_status WHEN 'Pending' THEN 1 WHEN 'Acknowledged' THEN 2 WHEN 'Prepared' THEN 3 ELSE 4 END, a.id DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        alerts = [dict(r) for r in rows]
        conn.close()
        return alerts

    @staticmethod
    def update_alert_status(
        alert_id: int,
        new_status: str,
        acknowledged_by: str,
        role: str,
        notes: Optional[str] = None
    ) -> bool:
        """Update alert status (e.g. Acknowledge, Prepare Resources, Mark Arrived)."""
        conn = get_connection()
        cursor = conn.cursor()
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
        UPDATE incoming_patient_alerts
        SET alert_status = ?, acknowledged_at = ?, acknowledged_by = ?
        WHERE id = ?
        """, (new_status, now_str, f"{acknowledged_by} ({role})", alert_id))
        
        # Log acknowledgement in history
        cursor.execute("""
        INSERT INTO alert_acknowledgements (
            alert_type, alert_id, user_role, acknowledged_by, notes, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            "incoming_patient",
            alert_id,
            role,
            acknowledged_by,
            notes or f"Updated status to {new_status}",
            now_str
        ))
        
        conn.commit()
        conn.close()
        return True
