from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from database import get_connection
from services.resource_engine import ResourceShortfallEngine

class AlertService:
    """Geographic Risk & GeoAlerts Management Service.
    
    Monitors regional network capacity, generates documented capacity warnings,
    and maintains alert lifecycles and acknowledgement history.
    """
    
    @classmethod
    def evaluate_and_generate_geo_alerts(
        cls,
        expected_regional_admissions: float,
        safety_buffer_pct: float = 10.0
    ) -> List[Dict[str, Any]]:
        """Evaluate network risk and generate/update active alerts in database."""
        evaluations = ResourceShortfallEngine.evaluate_regional_network(
            expected_regional_admissions=expected_regional_admissions,
            safety_buffer_pct=safety_buffer_pct
        )
        
        conn = get_connection()
        cursor = conn.cursor()
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        
        generated_alerts = []
        for ev in evaluations:
            severity = ev["severity"]
            if severity in ["Moderate", "High", "Critical"]:
                hosp_id = ev["hospital_id"]
                hosp_name = ev["hospital_name"]
                bottleneck = ev["primary_bottleneck"]
                shortfall = ev["projected_bed_shortfall"]
                
                title = f"{severity.upper()} HEAT CAPACITY ALERT: {hosp_name}"
                desc = (
                    f"Projected admissions: {ev['expected_demand']} | Staffed beds: {ev['available_staffed_beds']} | "
                    f"Shortfall: {shortfall} beds. Primary driver: {bottleneck}. "
                    f"Telemetry: {ev['data_freshness']}."
                )
                
                # Check if active alert already exists for hospital
                cursor.execute(
                    "SELECT id, severity FROM geographic_risk_alerts WHERE hospital_id = ? AND status = 'Active'",
                    (hosp_id,)
                )
                existing = cursor.fetchone()
                
                if existing:
                    # Update severity if changed
                    cursor.execute("""
                    UPDATE geographic_risk_alerts
                    SET severity = ?, description = ?, bottleneck_factor = ?, updated_at = ?
                    WHERE id = ?
                    """, (severity, desc, bottleneck, now_str, existing["id"]))
                    alert_id = existing["id"]
                else:
                    cursor.execute("""
                    INSERT INTO geographic_risk_alerts (
                        hospital_id, severity, title, description,
                        bottleneck_factor, status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (hosp_id, severity, title, desc, bottleneck, "Active", now_str, now_str))
                    alert_id = cursor.lastrowid
                    
                generated_alerts.append({
                    "id": alert_id,
                    "hospital_id": hosp_id,
                    "hospital_name": hosp_name,
                    "severity": severity,
                    "title": title,
                    "description": desc,
                    "bottleneck_factor": bottleneck,
                    "status": "Active",
                    "created_at": now_str
                })
                
        conn.commit()
        conn.close()
        return generated_alerts

    @staticmethod
    def get_geo_alerts(status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve geographic risk alerts with optional status filtering."""
        conn = get_connection()
        cursor = conn.cursor()
        
        query = """
        SELECT a.*, h.name as hospital_name, h.latitude, h.longitude
        FROM geographic_risk_alerts a
        JOIN hospitals h ON a.hospital_id = h.id
        """
        params = []
        if status_filter:
            query += " WHERE a.status = ?"
            params.append(status_filter)
            
        query += " ORDER BY CASE a.severity WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 WHEN 'Moderate' THEN 3 ELSE 4 END, a.id DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        alerts = [dict(r) for r in rows]
        conn.close()
        return alerts

    @staticmethod
    def acknowledge_geo_alert(
        alert_id: int,
        user_role: str,
        acknowledged_by: str,
        notes: str = "Capacity mitigation protocol initiated"
    ) -> bool:
        """Acknowledge a geographic capacity alert and record in audit trail."""
        conn = get_connection()
        cursor = conn.cursor()
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
        UPDATE geographic_risk_alerts
        SET status = 'Acknowledged', updated_at = ?
        WHERE id = ?
        """, (now_str, alert_id))
        
        cursor.execute("""
        INSERT INTO alert_acknowledgements (
            alert_type, alert_id, user_role, acknowledged_by, notes, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?)
        """, ("geo_risk", alert_id, user_role, acknowledged_by, notes, now_str))
        
        conn.commit()
        conn.close()
        return True

    @staticmethod
    def resolve_geo_alert(alert_id: int, resolved_by: str, role: str) -> bool:
        """Mark alert as resolved."""
        conn = get_connection()
        cursor = conn.cursor()
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
        UPDATE geographic_risk_alerts
        SET status = 'Resolved', updated_at = ?
        WHERE id = ?
        """, (now_str, alert_id))
        
        cursor.execute("""
        INSERT INTO alert_acknowledgements (
            alert_type, alert_id, user_role, acknowledged_by, notes, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?)
        """, ("geo_risk", alert_id, role, resolved_by, "Alert marked as Resolved", now_str))
        
        conn.commit()
        conn.close()
        return True
