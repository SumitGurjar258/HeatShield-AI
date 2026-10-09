from typing import Dict, Any, List, Optional
from config import Config
from services.hospital_service import HospitalService

class ResourceShortfallEngine:
    """Resource Shortfall & Capacity Risk Calculation Engine.
    
    Evaluates real-time and projected hospital capacity against forecasted demand
    to identify bottlenecks, calculate bed deficits, and determine risk severity.
    """
    
    @staticmethod
    def calculate_hospital_capacity_risk(
        hospital_resource: Dict[str, Any],
        expected_demand_admissions: float,
        safety_buffer_pct: float = 10.0
    ) -> Dict[str, Any]:
        """Calculate capacity shortfall and operational risk profile for a single hospital.
        
        Args:
            hospital_resource: Dict containing current hospital resources
            expected_demand_admissions: Projected emergency admissions requiring staffed beds
            safety_buffer_pct: Required reserve capacity buffer (default 10%)
            
        Returns:
            Dict containing shortfall numbers, bottleneck diagnostics, and severity tier.
        """
        available_beds = hospital_resource.get("available_staffed_beds")
        total_beds = hospital_resource.get("total_beds")
        meds_status = hospital_resource.get("critical_medicines_status", "Unknown")
        supplies_status = hospital_resource.get("supplies_status", "Unknown")
        nursing_status = hospital_resource.get("nursing_staff_status", "Unknown")
        freshness = hospital_resource.get("freshness", "Current")
        
        # Check for unknown bed counts
        if available_beds == "Unknown" or available_beds is None:
            return {
                "hospital_id": hospital_resource.get("hospital_id"),
                "hospital_name": hospital_resource.get("hospital_name"),
                "severity": "Unknown",
                "severity_score": 0,
                "color": "#6B7280", # Gray
                "expected_demand": expected_demand_admissions,
                "available_staffed_beds": "Unknown",
                "total_beds": total_beds,
                "projected_bed_shortfall": "Unknown",
                "primary_bottleneck": "Missing Staffed Bed Telemetry",
                "data_freshness": freshness,
                "limitations": "Staffed bed availability is unverified. Cannot calculate definitive capacity risk without live telemetry."
            }
            
        avail_beds_num = float(available_beds)
        # Expected bed requirement with safety reserve buffer
        buffer_multiplier = 1.0 + (safety_buffer_pct / 100.0)
        buffered_requirement = expected_demand_admissions * buffer_multiplier
        
        # Core Formula per specification:
        # Projected bed shortfall = max(0, expected bed requirement - available staffed beds)
        raw_shortfall = max(0.0, round(expected_demand_admissions - avail_beds_num, 1))
        buffered_shortfall = max(0.0, round(buffered_requirement - avail_beds_num, 1))
        
        # Identify Primary Bottlenecks
        bottlenecks = []
        if raw_shortfall > 0:
            bottlenecks.append(f"Staffed Beds Deficit (-{raw_shortfall} beds)")
        if supplies_status in ["Critical", "Low"]:
            bottlenecks.append(f"Cooling Supplies {supplies_status}")
        if meds_status in ["Critical", "Low"]:
            bottlenecks.append(f"Electrolyte/IV Fluids {meds_status}")
        if nursing_status in ["Critical Shortage", "Strained"]:
            bottlenecks.append(f"Nursing Staff {nursing_status}")
            
        primary_bottleneck = ", ".join(bottlenecks) if bottlenecks else "Normal Operating Capacity"
        
        # Documented Risk Classification Tiers
        severity_score = 0
        if raw_shortfall >= 8.0 or supplies_status == "Critical" or meds_status == "Critical" or nursing_status == "Critical Shortage":
            severity = "Critical"
            severity_score = 4
            color = "#DC2626" # Red
        elif raw_shortfall >= 3.0 or buffered_shortfall >= 5.0 or supplies_status == "Low" or meds_status == "Low" or nursing_status == "Strained":
            severity = "High"
            severity_score = 3
            color = "#EA580C" # Amber
        elif raw_shortfall > 0.0 or avail_beds_num <= (expected_demand_admissions + 2):
            severity = "Moderate"
            severity_score = 2
            color = "#D97706" # Yellow
        else:
            severity = "Low"
            severity_score = 1
            color = "#16A34A" # Green
            
        limitations = []
        if freshness.startswith("Stale"):
            limitations.append("Resource telemetry is older than 24 hours.")
        if nursing_status == "Unknown" or meds_status == "Unknown":
            limitations.append("Staffing or pharmacy inventory contains unconfirmed fields.")
        limitation_text = " ".join(limitations) if limitations else "All primary telemetry fields verified."

        return {
            "hospital_id": hospital_resource.get("hospital_id"),
            "hospital_name": hospital_resource.get("hospital_name"),
            "latitude": hospital_resource.get("latitude"),
            "longitude": hospital_resource.get("longitude"),
            "capabilities": hospital_resource.get("capabilities", []),
            "severity": severity,
            "severity_score": severity_score,
            "color": color,
            "expected_demand": round(expected_demand_admissions, 1),
            "available_staffed_beds": int(avail_beds_num),
            "total_beds": total_beds,
            "projected_bed_shortfall": raw_shortfall,
            "buffered_bed_shortfall": buffered_shortfall,
            "primary_bottleneck": primary_bottleneck,
            "data_freshness": freshness,
            "limitations": limitation_text
        }

    @classmethod
    def evaluate_regional_network(
        cls,
        expected_regional_admissions: float,
        safety_buffer_pct: float = 10.0
    ) -> List[Dict[str, Any]]:
        """Evaluate capacity risk across all registered active hospitals."""
        all_resources = HospitalService.get_hospital_resources()
        if not all_resources:
            return []
            
        # Distribute projected regional admissions proportionally across hospitals based on their capacity scale
        total_staffed_network_beds = sum(
            [r["available_staffed_beds"] for r in all_resources if isinstance(r["available_staffed_beds"], (int, float))]
        )
        if total_staffed_network_beds <= 0:
            total_staffed_network_beds = 1.0
            
        evaluations = []
        for r in all_resources:
            avail = r["available_staffed_beds"]
            # Proportional share of regional demand based on hospital size
            if isinstance(avail, (int, float)):
                hospital_share = max(0.1, avail / total_staffed_network_beds)
            else:
                hospital_share = 1.0 / len(all_resources)
                
            hospital_expected_adm = expected_regional_admissions * hospital_share
            
            risk_eval = cls.calculate_hospital_capacity_risk(
                hospital_resource=r,
                expected_demand_admissions=hospital_expected_adm,
                safety_buffer_pct=safety_buffer_pct
            )
            evaluations.append(risk_eval)
            
        # Sort by severity score descending (Highest risk first)
        evaluations.sort(key=lambda x: x["severity_score"], reverse=True)
        return evaluations
