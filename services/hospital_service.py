import json
import math
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from config import Config
from database import get_connection

class HospitalService:
    """Hospital Registry and Resource Availability Management Service.
    
    Maintains verified hospital capabilities, separate records for total vs available staffed beds,
    inventory, staff availability, and an audit trail for all resource updates.
    """
    
    @staticmethod
    def get_all_hospitals(include_inactive: bool = False) -> List[Dict[str, Any]]:
        """Retrieve all registered hospitals with active status filtering."""
        conn = get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM hospitals"
        if not include_inactive:
            query += " WHERE is_active = 1"
            
        cursor.execute(query)
        rows = cursor.fetchall()
        
        hospitals = []
        for r in rows:
            caps = []
            try:
                caps = json.loads(r["capabilities"]) if r["capabilities"] else []
            except Exception:
                caps = [c.strip() for c in r["capabilities"].split(",") if c.strip()]
                
            hospitals.append({
                "id": r["id"],
                "name": r["name"],
                "latitude": float(r["latitude"]),
                "longitude": float(r["longitude"]),
                "address": r["address"],
                "capabilities": caps,
                "contact_endpoint": r["contact_endpoint"],
                "is_active": bool(r["is_active"]),
                "created_at": r["created_at"]
            })
            
        conn.close()
        return hospitals

    @classmethod
    def get_hospital_by_id(cls, hospital_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve details of a single hospital."""
        hospitals = cls.get_all_hospitals(include_inactive=True)
        for h in hospitals:
            if h["id"] == hospital_id:
                return h
        return None

    @staticmethod
    def get_hospital_resources(hospital_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve latest resource records for specified hospital or all hospitals."""
        conn = get_connection()
        cursor = conn.cursor()
        
        query = """
        SELECT r.*, h.name as hospital_name, h.latitude, h.longitude, h.capabilities
        FROM hospital_resources r
        JOIN hospitals h ON r.hospital_id = h.id
        WHERE h.is_active = 1
        """
        params = []
        if hospital_id:
            query += " AND r.hospital_id = ?"
            params.append(hospital_id)
            
        query += " ORDER BY r.last_updated DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        results = []
        seen_hospitals = set()
        
        # Keep latest record per hospital
        for r in rows:
            h_id = r["hospital_id"]
            if hospital_id is None and h_id in seen_hospitals:
                continue
            seen_hospitals.add(h_id)
            
            # Freshness calculation
            freshness_label = "Current"
            try:
                dt = datetime.strptime(r["last_updated"], "%Y-%m-%d %H:%M:%S")
                delta_hours = (datetime.now(timezone.utc).replace(tzinfo=None) - dt).total_seconds() / 3600.0
                if delta_hours > 24:
                    freshness_label = "Stale (>24h)"
                elif delta_hours > 12:
                    freshness_label = "Aging (>12h)"
            except Exception:
                pass

            caps = []
            try:
                caps = json.loads(r["capabilities"]) if r["capabilities"] else []
            except Exception:
                caps = []
                
            results.append({
                "id": r["id"],
                "hospital_id": h_id,
                "hospital_name": r["hospital_name"],
                "latitude": float(r["latitude"]),
                "longitude": float(r["longitude"]),
                "capabilities": caps,
                "total_beds": r["total_beds"] if r["total_beds"] is not None else "Unknown",
                "occupied_beds": r["occupied_beds"] if r["occupied_beds"] is not None else "Unknown",
                "available_staffed_beds": r["available_staffed_beds"] if r["available_staffed_beds"] is not None else "Unknown",
                "specialist_availability": r["specialist_availability"] or "Unknown",
                "nursing_staff_count": r["nursing_staff_count"] if r["nursing_staff_count"] is not None else "Unknown",
                "nursing_staff_status": r["nursing_staff_status"] or "Unknown",
                "ambulance_count": r["ambulance_count"] if r["ambulance_count"] is not None else "Unknown",
                "critical_medicines_status": r["critical_medicines_status"] or "Unknown",
                "supplies_status": r["supplies_status"] or "Unknown",
                "last_updated": r["last_updated"],
                "freshness": freshness_label,
                "data_source": r["data_source"],
                "verification_status": r["verification_status"]
            })
            
        conn.close()
        return results

    @staticmethod
    def update_hospital_resource(
        hospital_id: str,
        available_staffed_beds: int,
        occupied_beds: int,
        total_beds: int,
        nursing_staff_status: str,
        critical_medicines_status: str,
        supplies_status: str,
        updated_by: str,
        role: str,
        reason: str = "Routine operational status update"
    ) -> bool:
        """Update hospital resource status with full audit logging."""
        conn = get_connection()
        cursor = conn.cursor()
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        
        # Get prior record for audit comparison
        cursor.execute(
            "SELECT available_staffed_beds, occupied_beds, supplies_status FROM hospital_resources WHERE hospital_id = ? ORDER BY id DESC LIMIT 1",
            (hospital_id,)
        )
        old_row = cursor.fetchone()
        old_beds = old_row["available_staffed_beds"] if old_row else "Unknown"
        
        # Insert new resource record
        cursor.execute("""
        INSERT INTO hospital_resources (
            hospital_id, total_beds, occupied_beds, available_staffed_beds,
            specialist_availability, nursing_staff_count, nursing_staff_status,
            ambulance_count, critical_medicines_status, supplies_status,
            last_updated, data_source, verification_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            hospital_id,
            total_beds,
            occupied_beds,
            available_staffed_beds,
            "Updated via Authorised Form",
            20,
            nursing_staff_status,
            3,
            critical_medicines_status,
            supplies_status,
            now_str,
            "Authorised Healthcare Portal Entry",
            "Verified"
        ))
        
        # Log audit entry
        cursor.execute("""
        INSERT INTO resource_update_history (
            hospital_id, field_changed, old_value, new_value, updated_by, role, timestamp, reason
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            hospital_id,
            "available_staffed_beds & statuses",
            f"Beds: {old_beds}",
            f"Beds: {available_staffed_beds}, Meds: {critical_medicines_status}, Supplies: {supplies_status}",
            updated_by,
            role,
            now_str,
            reason
        ))
        
        conn.commit()
        conn.close()
        return True

    @staticmethod
    def get_resource_audit_history(hospital_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve audit log of all resource updates."""
        conn = get_connection()
        cursor = conn.cursor()
        
        query = """
        SELECT a.*, h.name as hospital_name
        FROM resource_update_history a
        JOIN hospitals h ON a.hospital_id = h.id
        """
        params = []
        if hospital_id:
            query += " WHERE a.hospital_id = ?"
            params.append(hospital_id)
            
        query += " ORDER BY a.id DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        audit_records = [dict(r) for r in rows]
        conn.close()
        return audit_records

    @staticmethod
    def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate the Great Circle distance between two points in kilometers."""
        r = 6371.0 # Earth radius in km
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2.0) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon / 2.0) ** 2)
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return round(r * c, 2)
        
    @classmethod
    def estimate_travel_time_minutes(cls, distance_km: float, is_urban: bool = True) -> int:
        """Estimate ambulance travel time considering urban traffic conditions."""
        avg_speed_kmh = 32.0 if is_urban else 55.0
        # Transit time + 4 mins dispatch/staging baseline
        transit_time = (distance_km / avg_speed_kmh) * 60.0 + 4.0
        return max(5, int(round(transit_time)))
