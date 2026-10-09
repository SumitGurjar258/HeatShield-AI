import streamlit as st
import folium
from streamlit_folium import folium_static
import plotly.express as px
from datetime import datetime, timezone
from config import Config
from services.hospital_service import HospitalService
from services.resource_engine import ResourceShortfallEngine
from services.alert_service import AlertService
from services.ambulance_service import AmbulanceService
from services.demand_forecasting import DemandForecastingService
from services.weather_service import WeatherService
from ui_components import apply_custom_theme, get_risk_badge_html, get_verification_badge_html

apply_custom_theme()

st.title("🏥 Smart Hospital Resources & Ambulance Coordination")
st.caption("Major Field 2 • Real-time staffed bed telemetry, shortfall calculations, geographic risk maps, GeoAlerts, and ambulance triage dispatch")

# Active Role Banner
user_role = st.session_state.get("user_role", Config.ROLES[0])
st.markdown(
    f"<div style='background: #F1F5F9; border: 1px solid #CBD5E1; border-radius: 8px; padding: 10px 16px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center;'>"
    f"<div>👤 <b>Active Operational Role:</b> <span style='color: #0369A1; font-weight: 600;'>{user_role}</span></div>"
    f"<div><span style='font-size: 0.8rem; color: #64748B;'>Audit trail active for all actions</span></div>"
    f"</div>",
    unsafe_allow_html=True
)

# Connect with weather & demand prediction
if "latest_weather_data" not in st.session_state:
    st.session_state["latest_weather_data"] = WeatherService.fetch_weather_forecast(
        lat=st.session_state.get("selected_lat", Config.DEFAULT_LAT),
        lon=st.session_state.get("selected_lon", Config.DEFAULT_LON),
        location_name=st.session_state.get("selected_region_name", Config.DEFAULT_LOCATION_NAME)
    )

w_data = st.session_state["latest_weather_data"]
forecast_list = w_data.get("forecast", [])

# Demand Estimation for Regional Network
demand_service = DemandForecastingService()
peak_temp = w_data.get("max_forecast_temp", 26.0)
sim_demand = demand_service.simulate_what_if_scenario(
    base_temp_c=25.0,
    temp_delta_c=max(0.0, peak_temp - 25.0),
    heatwave_days=w_data.get("heatwave_duration_days", 1),
    baseline_bed_capacity=80
)
regional_expected_admissions = sim_demand["predicted_emergency_admissions"]

# Sub-tab Navigation inside Major Field 2
tab1, tab2, tab3, tab4 = st.tabs([
    "🗺️ Geographic Risk & GeoAlerts",
    "📊 Capacity Shortfall Engine",
    "🚑 Ambulance Dispatch Coordination",
    "🏥 Hospital Registry & Telemetry Updates"
])

# -------------------------------------------------------------
# TAB 1: GEOGRAPHIC RISK MAP & GEOALERTS
# -------------------------------------------------------------
with tab1:
    st.markdown("<div class='section-title'>🗺️ Interactive Hospital Capacity Risk Map</div>", unsafe_allow_html=True)
    
    # Run evaluation across regional network
    evaluations = ResourceShortfallEngine.evaluate_regional_network(
        expected_regional_admissions=regional_expected_admissions,
        safety_buffer_pct=Config.BED_SAFETY_BUFFER_PCT
    )
    
    # Generate / sync GeoAlerts
    AlertService.evaluate_and_generate_geo_alerts(
        expected_regional_admissions=regional_expected_admissions,
        safety_buffer_pct=Config.BED_SAFETY_BUFFER_PCT
    )
    
    # Active GeoAlerts count
    active_alerts = AlertService.get_geo_alerts(status_filter="Active")
    
    c_map, c_alerts = st.columns([3, 2])
    
    with c_map:
        # Create Folium Map
        center_lat = st.session_state.get("selected_lat", Config.DEFAULT_LAT)
        center_lon = st.session_state.get("selected_lon", Config.DEFAULT_LON)
        
        hosp_map = folium.Map(location=[center_lat, center_lon], zoom_start=11, tiles="CartoDB positron")
        
        for ev in evaluations:
            sev = ev["severity"]
            marker_color = "red" if sev == "Critical" else ("orange" if sev == "High" else ("beige" if sev == "Moderate" else "green"))
            
            popup_html = f"""
            <div style='font-family: sans-serif; min-width: 200px;'>
                <h4 style='margin: 0 0 6px 0; color: #1E293B;'>{ev['hospital_name']}</h4>
                <b>Risk Tier:</b> <span style='color: {ev['color']}; font-weight: bold;'>{sev}</span><br>
                <b>Available Staffed Beds:</b> {ev['available_staffed_beds']}<br>
                <b>Projected Shortfall:</b> {ev['projected_bed_shortfall']} beds<br>
                <b>Bottleneck:</b> {ev['primary_bottleneck']}<br>
                <small>Freshness: {ev['data_freshness']}</small>
            </div>
            """
            
            folium.Marker(
                location=[ev["latitude"], ev["longitude"]],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"{ev['hospital_name']} ({sev} Risk - Shortfall: {ev['projected_bed_shortfall']})",
                icon=folium.Icon(color=marker_color, icon="plus-sign")
            ).add_to(hosp_map)
            
        folium_static(hosp_map, width=540, height=440)
        
    with c_alerts:
        st.markdown(f"**Active Regional GeoAlerts ({len(active_alerts)})**")
        if not active_alerts:
            st.success("✅ No critical capacity shortfalls currently active across the regional network.")
        else:
            for al in active_alerts:
                sev_color = "#DC2626" if al["severity"] == "Critical" else ("#EA580C" if al["severity"] == "High" else "#D97706")
                st.markdown(
                    f"<div style='border-left: 5px solid {sev_color}; background: #FFFFFF; border-top: 1px solid #E2E8F0; border-right: 1px solid #E2E8F0; border-bottom: 1px solid #E2E8F0; border-radius: 6px; padding: 10px 14px; margin-bottom: 10px;'>"
                    f"<div style='font-weight: 700; color: {sev_color}; font-size: 0.9rem;'>{al['title']}</div>"
                    f"<div style='font-size: 0.8rem; color: #334155; margin-top: 4px;'>{al['description']}</div>"
                    f"<div style='font-size: 0.75rem; color: #64748B; margin-top: 6px;'>Created: {al['created_at']}</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )
                
                # Acknowledge button if authorized
                btn_key = f"ack_alert_{al['id']}"
                if st.button(f"Acknowledge Alert #{al['id']}", key=btn_key):
                    AlertService.acknowledge_geo_alert(
                        alert_id=al["id"],
                        user_role=user_role,
                        acknowledged_by="Authorized Officer",
                        notes=f"Acknowledged by {user_role} under heatwave surge response protocol"
                    )
                    st.success(f"Alert #{al['id']} acknowledged and logged to audit trail.")
                    st.rerun()

# -------------------------------------------------------------
# TAB 2: RESOURCE SHORTFALL ENGINE
# -------------------------------------------------------------
with tab2:
    st.markdown("<div class='section-title'>📊 Capacity Shortfall Calculations & Bottleneck Analysis</div>", unsafe_allow_html=True)
    st.info(
        "💡 **Shortfall Formula:** `Projected Bed Shortfall = max(0, Expected Bed Requirement - Available Staffed Beds)`. "
        "Total registered beds are never conflated with staffed, ready-to-admit beds."
    )
    
    # Regional summary metrics
    total_avail_beds = sum([ev["available_staffed_beds"] for ev in evaluations if isinstance(ev["available_staffed_beds"], (int, float))])
    total_shortfall = sum([ev["projected_bed_shortfall"] for ev in evaluations if isinstance(ev["projected_bed_shortfall"], (int, float))])
    critical_hospitals = len([ev for ev in evaluations if ev["severity"] == "Critical"])
    
    sm1, sm2, sm3, sm4 = st.columns(4)
    with sm1:
        st.markdown(
            f"<div class='metric-card'>"
            f"<div class='metric-title'>Projected Network Admissions</div>"
            f"<div class='metric-val'>{round(regional_expected_admissions, 1)}</div>"
            f"<div class='metric-sub'>Based on heatwave model</div>"
            f"</div>",
            unsafe_allow_html=True
        )
    with sm2:
        st.markdown(
            f"<div class='metric-card'>"
            f"<div class='metric-title'>Available Staffed Beds</div>"
            f"<div class='metric-val'>{total_avail_beds}</div>"
            f"<div class='metric-sub'>Verified network capacity</div>"
            f"</div>",
            unsafe_allow_html=True
        )
    with sm3:
        sh_color = "#DC2626" if total_shortfall > 0 else "#16A34A"
        st.markdown(
            f"<div class='metric-card'>"
            f"<div class='metric-title'>Net Bed Shortfall</div>"
            f"<div class='metric-val' style='color: {sh_color};'>{round(total_shortfall, 1)}</div>"
            f"<div class='metric-sub'>Regional deficit</div>"
            f"</div>",
            unsafe_allow_html=True
        )
    with sm4:
        st.markdown(
            f"<div class='metric-card'>"
            f"<div class='metric-title'>Hospitals in Critical Risk</div>"
            f"<div class='metric-val' style='color: #DC2626;'>{critical_hospitals}</div>"
            f"<div class='metric-sub'>Requiring immediate diversion</div>"
            f"</div>",
            unsafe_allow_html=True
        )
        
    # Table of evaluations
    table_rows = []
    for ev in evaluations:
        table_rows.append({
            "Hospital Name": ev["hospital_name"],
            "Severity Risk": ev["severity"],
            "Staffed Beds": ev["available_staffed_beds"],
            "Total Beds": ev["total_beds"],
            "Expected Admissions": ev["expected_demand"],
            "Bed Shortfall": ev["projected_bed_shortfall"],
            "Primary Bottleneck": ev["primary_bottleneck"],
            "Telemetry Freshness": ev["data_freshness"],
            "Limitations": ev["limitations"]
        })
    st.dataframe(table_rows, use_container_width=True)

# -------------------------------------------------------------
# TAB 3: AMBULANCE DISPATCH & INCOMING ALERTS
# -------------------------------------------------------------
with tab3:
    st.markdown("<div class='section-title'>🚑 Ambulance Triage Matching & Hospital Notification</div>", unsafe_allow_html=True)
    st.warning("⚠️ **Notice:** This decision-support tool does not replace clinical triage, paramedic judgement, or emergency dispatch protocols.")
    
    col_triage, col_dest = st.columns([1, 1])
    
    with col_triage:
        st.markdown("#### Step 1: Clinical Triage Input")
        urgency = st.selectbox(
            "Patient Urgency Classification:",
            options=AmbulanceService.URGENCY_LEVELS,
            index=0
        )
        
        condition = st.text_area(
            "Condition Summary & Heat Impact:",
            value="Heat stroke with hyperthermia (temp 40.8°C), confusion, dehydration shock, tachycardia.",
            height=85
        )
        
        req_caps = st.multiselect(
            "Mandatory Hospital Capabilities Required:",
            options=AmbulanceService.CAPABILITY_OPTIONS,
            default=["Heat Stroke Resuscitation", "Burns/Cooling Unit"]
        )
        
        # Origin coordinates (simulated paramedic GPS)
        c_lat, c_lon = st.columns(2)
        with c_lat:
            origin_lat = st.number_input("Incident Latitude", value=51.5050, format="%.4f")
        with c_lon:
            origin_lon = st.number_input("Incident Longitude", value=-0.1150, format="%.4f")
            
    with col_dest:
        st.markdown("#### Step 2: Destination Matching & Capacity Evaluation")
        
        matching = AmbulanceService.match_candidate_hospitals(
            patient_lat=origin_lat,
            patient_lon=origin_lon,
            required_capabilities=req_caps,
            urgency=urgency
        )
        
        if matching.get("warning"):
            st.error(matching["warning"])
            
        candidates = matching["candidates"]
        if not candidates:
            st.info("No candidates match all criteria. Select fewer capability restrictions or refer to Central Emergency Dispatch.")
        else:
            candidate_options = {
                f"{c['hospital_name']} (ETA: {c['eta_minutes']}m | Staffed Beds: {c['available_staffed_beds']})": c["hospital_id"]
                for c in candidates
            }
            
            selected_label = st.selectbox("Select Verified Receiving Facility:", options=list(candidate_options.keys()))
            selected_hosp_id = candidate_options[selected_label]
            
            # Show selected hospital telemetry details
            chosen_c = [c for c in candidates if c["hospital_id"] == selected_hosp_id][0]
            st.markdown(
                f"<div style='background: #F8FAFC; border: 1px solid #E2E8F0; padding: 12px; border-radius: 8px; margin: 10px 0;'>"
                f"<b>Distance:</b> {chosen_c['distance_km']} km &nbsp;|&nbsp; <b>ETA:</b> {chosen_c['eta_minutes']} mins<br>"
                f"<b>Staffed Beds:</b> {chosen_c['available_staffed_beds']} &nbsp;|&nbsp; <b>Supplies:</b> {chosen_c['supplies_status']}<br>"
                f"<b>Specialists:</b> {chosen_c['specialist_availability']}"
                f"</div>",
                unsafe_allow_html=True
            )
            
            if st.button("🚨 Confirm Destination & Transmit Incoming Alert", type="primary"):
                dispatch_res = AmbulanceService.create_dispatch_request(
                    patient_urgency=urgency,
                    condition_summary=condition,
                    required_capabilities=req_caps,
                    origin_lat=origin_lat,
                    origin_lon=origin_lon,
                    destination_hospital_id=selected_hosp_id,
                    eta_minutes=chosen_c["eta_minutes"]
                )
                st.success(f"Incoming Patient Alert Transmitted! Request ID: `{dispatch_res['request_id']}`. Hospital receiving ward notified.")
                st.rerun()

    st.divider()
    # Hospital Receiving Screen / Alert Inbox
    st.markdown("#### 📥 Receiving Hospital Dashboard: Incoming Ambulance Alerts")
    
    # Hospital filter for receiving clinician view
    all_hospitals = HospitalService.get_all_hospitals()
    hosp_filter_names = {h["name"]: h["id"] for h in all_hospitals}
    selected_view_hosp = st.selectbox(
        "View Alert Queue for Hospital:",
        options=["All Hospitals"] + list(hosp_filter_names.keys())
    )
    
    filter_id = hosp_filter_names.get(selected_view_hosp) if selected_view_hosp != "All Hospitals" else None
    incoming_alerts = AmbulanceService.get_incoming_alerts(hospital_id=filter_id)
    
    if not incoming_alerts:
        st.info("No incoming ambulance alerts in queue.")
    else:
        for alert in incoming_alerts:
            status = alert["alert_status"]
            status_color = "#EA580C" if status == "Pending" else ("#0284C7" if status == "Acknowledged" else "#16A34A")
            
            c_info, c_action = st.columns([3, 1])
            with c_info:
                st.markdown(
                    f"<div style='border: 1px solid #E2E8F0; border-radius: 6px; padding: 10px 14px; background: #FFFFFF;'>"
                    f"<div style='display: flex; justify-content: space-between;'>"
                    f"<b>{alert['request_id']}</b> &nbsp;•&nbsp; <span>{alert['hospital_name']}</span>"
                    f"<span style='color: {status_color}; font-weight: bold;'>[{status.upper()}]</span>"
                    f"</div>"
                    f"<div style='margin-top: 4px; font-size: 0.85rem; color: #1E293B;'>"
                    f"<b>Urgency:</b> {alert['patient_urgency']} &nbsp;|&nbsp; <b>ETA:</b> ~{alert['eta_minutes']} mins<br>"
                    f"<b>Care Requirements:</b> {alert['care_requirements']}"
                    f"</div>"
                    f"<div style='font-size: 0.75rem; color: #64748B; margin-top: 4px;'>Created: {alert['created_at']} | Ack: {alert['acknowledged_by'] or 'Unacknowledged'}</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )
            with c_action:
                if status == "Pending":
                    if st.button("Acknowledge Alert", key=f"btn_ack_inc_{alert['id']}"):
                        AmbulanceService.update_alert_status(
                            alert_id=alert["id"],
                            new_status="Acknowledged",
                            acknowledged_by="Charge Nurse",
                            role=user_role,
                            notes="Resuscitation bay assigned and team alerted"
                        )
                        st.rerun()
                elif status == "Acknowledged":
                    if st.button("Mark Prepared", key=f"btn_prep_inc_{alert['id']}"):
                        AmbulanceService.update_alert_status(
                            alert_id=alert["id"],
                            new_status="Prepared",
                            acknowledged_by="Charge Nurse",
                            role=user_role,
                            notes="Cooling immersion and fluids ready"
                        )
                        st.rerun()
                elif status == "Prepared":
                    if st.button("Mark Arrived", key=f"btn_arr_inc_{alert['id']}"):
                        AmbulanceService.update_alert_status(
                            alert_id=alert["id"],
                            new_status="Completed",
                            acknowledged_by="Triage Team",
                            role=user_role,
                            notes="Patient safely received into emergency bay"
                        )
                        st.rerun()

# -------------------------------------------------------------
# TAB 4: HOSPITAL REGISTRY & TELEMETRY UPDATES
# -------------------------------------------------------------
with tab4:
    st.markdown("<div class='section-title'>🏥 Registered Hospital Telemetry & Authorized Updates</div>", unsafe_allow_html=True)
    
    col_update_form, col_audit_log = st.columns([1, 1])
    
    with col_update_form:
        st.markdown("#### Update Hospital Capacity Telemetry")
        st.caption(f"Changes will be logged in the audit ledger under role: `{user_role}`")
        
        up_hosp_name = st.selectbox("Select Hospital:", options=list(hosp_filter_names.keys()))
        up_hosp_id = hosp_filter_names[up_hosp_name]
        
        # Current data for hospital
        curr_res = HospitalService.get_hospital_resources(hospital_id=up_hosp_id)
        curr_obj = curr_res[0] if curr_res else {}
        
        with st.form("hospital_resource_update_form"):
            total_b = st.number_input("Total Registered Beds", value=int(curr_obj.get("total_beds", 300) if isinstance(curr_obj.get("total_beds"), (int, float)) else 300))
            occupied_b = st.number_input("Occupied Beds", value=int(curr_obj.get("occupied_beds", 270) if isinstance(curr_obj.get("occupied_beds"), (int, float)) else 270))
            staffed_b = st.number_input(
                "Available Staffed Beds (Ready to Admit)",
                value=int(curr_obj.get("available_staffed_beds", 10) if isinstance(curr_obj.get("available_staffed_beds"), (int, float)) else 10),
                help="Crucial: This is the staffed, available capacity, not total beds."
            )
            
            nursing_st = st.selectbox("Nursing Staff Status:", ["Adequate", "Strained", "Critical Shortage", "Unknown"])
            meds_st = st.selectbox("Critical Medicines / IV Fluids:", ["Adequate", "Low", "Critical", "Unknown"])
            supplies_st = st.selectbox("Cooling Equipment & Supplies:", ["Adequate", "Low", "Critical", "Unknown"])
            reason = st.text_input("Operational Update Reason:", value="Daily heatwave shift bed-census update")
            
            submit_update = st.form_submit_button("Submit Telemetry Update", type="primary")
            if submit_update:
                HospitalService.update_hospital_resource(
                    hospital_id=up_hosp_id,
                    available_staffed_beds=staffed_b,
                    occupied_beds=occupied_b,
                    total_beds=total_b,
                    nursing_staff_status=nursing_st,
                    critical_medicines_status=meds_st,
                    supplies_status=supplies_st,
                    updated_by="Authorised Clinician",
                    role=user_role,
                    reason=reason
                )
                st.success("Resource telemetry updated and logged to audit trail!")
                st.rerun()

    with col_audit_log:
        st.markdown("#### 📜 Resource Audit Trail Ledger")
        st.caption("Immutable record of capacity adjustments and operational updates.")
        history = HospitalService.get_resource_audit_history(limit=15)
        
        if not history:
            st.info("No audit entries recorded yet.")
        else:
            for h in history:
                st.markdown(
                    f"<div style='font-size: 0.8rem; background: #FFFFFF; border: 1px solid #E2E8F0; padding: 8px 12px; border-radius: 6px; margin-bottom: 8px;'>"
                    f"<b>{h['hospital_name']}</b> • <code>{h['timestamp']}</code><br>"
                    f"<span style='color: #475569;'>Role:</span> {h['role']} ({h['updated_by']})<br>"
                    f"<span style='color: #475569;'>Change:</span> {h['new_value']}<br>"
                    f"<span style='color: #64748B;'>Reason:</span> <i>{h['reason']}</i>"
                    f"</div>",
                    unsafe_allow_html=True
                )
