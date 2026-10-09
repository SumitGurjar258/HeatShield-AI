import streamlit as st
import plotly.graph_objects as go
from datetime import datetime
import folium
from streamlit_folium import folium_static
from config import Config
from services.weather_service import WeatherService
from ui_components import apply_custom_theme, get_risk_badge_html, get_verification_badge_html

# Page styling
apply_custom_theme()

st.title("☀️ Weather Forecast & Heatwave Intelligence")
st.caption("Major Field 1 • Real-time meteorological intelligence, apparent heat index, and early-warning heat-health alerts")

# Initialize session state defaults if not set
if "selected_lat" not in st.session_state:
    st.session_state["selected_lat"] = Config.DEFAULT_LAT
if "selected_lon" not in st.session_state:
    st.session_state["selected_lon"] = Config.DEFAULT_LON
if "selected_region_name" not in st.session_state:
    st.session_state["selected_region_name"] = Config.DEFAULT_LOCATION_NAME

# Configuration Expander
with st.expander("⚙️ Meteorological Controls & Heat-Health Alert Thresholds", expanded=False):
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        thresh_mod = st.number_input(
            "Moderate Alert Threshold (°C)",
            value=Config.HEAT_THRESHOLD_MODERATE,
            step=0.5,
            help="UKHSA Yellow Alert guidance trigger"
        )
    with c2:
        thresh_high = st.number_input(
            "High Alert Threshold (°C)",
            value=Config.HEAT_THRESHOLD_HIGH,
            step=0.5,
            help="UKHSA Amber Alert guidance trigger"
        )
    with c3:
        thresh_crit = st.number_input(
            "Critical Alert Threshold (°C)",
            value=Config.HEAT_THRESHOLD_CRITICAL,
            step=0.5,
            help="UKHSA Emergency Red Alert guidance trigger"
        )
    with c4:
        force_demo = st.checkbox(
            "Simulate Extreme Heatwave Spell",
            value=False,
            help="Overwrites live weather with a labelled synthetic extreme heatwave scenario for emergency stress testing"
        )

# Fetch weather data
with st.spinner("Fetching meteorological telemetry from weather provider..."):
    weather_data = WeatherService.fetch_weather_forecast(
        lat=st.session_state["selected_lat"],
        lon=st.session_state["selected_lon"],
        location_name=st.session_state["selected_region_name"],
        force_demo=force_demo,
        thresh_mod=thresh_mod,
        thresh_high=thresh_high,
        thresh_crit=thresh_crit
    )
    # Save to session state so demand and resource engines can access
    st.session_state["latest_weather_data"] = weather_data

# Data Provenance Banner
badge_mode = "VERIFIED FEED" if weather_data["mode"] == "LIVE_API" else "SIMULATED DEMO"
st.markdown(
    f"<div style='background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px 16px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;'>"
    f"<div>"
    f"<b>Provider:</b> {weather_data['data_source']} &nbsp;|&nbsp; "
    f"<b>Updated:</b> <code>{weather_data['last_updated']}</code> &nbsp;|&nbsp; "
    f"<b>Region:</b> {weather_data['location_name']}"
    f"</div>"
    f"<div>{get_verification_badge_html(badge_mode)}</div>"
    f"</div>",
    unsafe_allow_html=True
)

curr = weather_data["current"]
curr_risk = curr["heat_risk"]
forecast_list = weather_data["forecast"]

# Early Warning Banner
if curr_risk.get("early_warning") or any(f["heat_risk_level"] in ["High", "Critical"] for f in forecast_list):
    st.markdown(
        f"<div style='background: {curr_risk['bg_color']}; border-left: 6px solid {curr_risk['color']}; padding: 14px 18px; border-radius: 6px; margin-bottom: 20px;'>"
        f"<h4 style='color: {curr_risk['color']}; margin: 0 0 6px 0;'>🚨 HEAT-HEALTH EARLY WARNING: {curr_risk['level'].upper()} ALERT IN EFFECT</h4>"
        f"<p style='color: #1E293B; margin: 0; font-size: 0.95rem;'>{curr_risk['guidance']}</p>"
        f"</div>",
        unsafe_allow_html=True
    )

# Summary Metric Cards
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(
        f"<div class='metric-card'>"
        f"<div class='metric-title'>Current Observed Temp</div>"
        f"<div class='metric-val'>{curr['temperature_c']}°C</div>"
        f"<div class='metric-sub'>Heat Index (Feels Like): <b>{curr['heat_index_c']}°C</b></div>"
        f"</div>",
        unsafe_allow_html=True
    )

with m2:
    st.markdown(
        f"<div class='metric-card'>"
        f"<div class='metric-title'>Peak Forecast Temp</div>"
        f"<div class='metric-val' style='color: #EA580C;'>{weather_data['max_forecast_temp']}°C</div>"
        f"<div class='metric-sub'>Over 7-Day Forecast Horizon</div>"
        f"</div>",
        unsafe_allow_html=True
    )

with m3:
    st.markdown(
        f"<div class='metric-card'>"
        f"<div class='metric-title'>Relative Humidity</div>"
        f"<div class='metric-val'>{curr['humidity_pct']}%</div>"
        f"<div class='metric-sub'>Ambient Moisture Level</div>"
        f"</div>",
        unsafe_allow_html=True
    )

with m4:
    heatwave_days = weather_data["heatwave_duration_days"]
    hw_color = "#DC2626" if heatwave_days >= 3 else ("#EA580C" if heatwave_days >= 1 else "#16A34A")
    st.markdown(
        f"<div class='metric-card'>"
        f"<div class='metric-title'>Heatwave Spell Duration</div>"
        f"<div class='metric-val' style='color: {hw_color};'>{heatwave_days} Days</div>"
        f"<div class='metric-sub'>Consecutive days &ge; {thresh_mod}°C</div>"
        f"</div>",
        unsafe_allow_html=True
    )

# Visualizations: 7-Day Forecast Chart & Map
col_chart, col_map = st.columns([3, 2])

with col_chart:
    st.markdown("<div class='section-title'>📈 7-Day Temperature & Heat Stress Forecast</div>", unsafe_allow_html=True)
    
    dates = [f["date"] for f in forecast_list]
    t_max = [f["temp_max_c"] for f in forecast_list]
    t_min = [f["temp_min_c"] for f in forecast_list]
    hi = [f["heat_index_c"] for f in forecast_list]
    rh = [f["humidity_pct"] for f in forecast_list]
    
    fig = go.Figure()
    
    # Threshold Lines
    fig.add_hline(y=thresh_crit, line_dash="dot", line_color="#DC2626", annotation_text=f"Critical ({thresh_crit}°C)", annotation_position="top left")
    fig.add_hline(y=thresh_high, line_dash="dash", line_color="#EA580C", annotation_text=f"High ({thresh_high}°C)", annotation_position="top left")
    fig.add_hline(y=thresh_mod, line_dash="dot", line_color="#D97706", annotation_text=f"Moderate ({thresh_mod}°C)", annotation_position="top left")
    
    # Traces
    fig.add_trace(go.Scatter(
        x=dates, y=t_max,
        mode="lines+markers",
        name="Max Temperature (°C)",
        line=dict(color="#DC2626", width=3),
        marker=dict(size=8)
    ))
    fig.add_trace(go.Scatter(
        x=dates, y=hi,
        mode="lines+markers",
        name="Heat Index (°C)",
        line=dict(color="#7C3AED", width=2, dash="dash"),
        marker=dict(size=6)
    ))
    fig.add_trace(go.Scatter(
        x=dates, y=t_min,
        mode="lines+markers",
        name="Min Overnight Temp (°C)",
        line=dict(color="#2563EB", width=2),
        marker=dict(size=6)
    ))
    
    fig.update_layout(
        margin=dict(l=20, r=20, t=30, b=20),
        height=380,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor="#FFFFFF",
        xaxis=dict(showgrid=True, gridcolor="#F1F5F9"),
        yaxis=dict(title="Temperature (°C)", showgrid=True, gridcolor="#F1F5F9")
    )
    st.plotly_chart(fig, use_container_width=True)

with col_map:
    st.markdown("<div class='section-title'>🗺️ Regional Heat Monitoring Radius</div>", unsafe_allow_html=True)
    
    m = folium.Map(
        location=[st.session_state["selected_lat"], st.session_state["selected_lon"]],
        zoom_start=11,
        tiles="CartoDB positron"
    )
    
    # Regional heat perimeter circle
    circle_color = curr_risk["color"]
    folium.Circle(
        location=[st.session_state["selected_lat"], st.session_state["selected_lon"]],
        radius=14000,
        color=circle_color,
        fill=True,
        fill_color=circle_color,
        fill_opacity=0.25,
        tooltip=f"{weather_data['location_name']}: {curr_risk['level']} Heat Risk"
    ).add_to(m)
    
    folium.Marker(
        location=[st.session_state["selected_lat"], st.session_state["selected_lon"]],
        popup=f"<b>{weather_data['location_name']}</b><br>Temp: {curr['temperature_c']}°C<br>Status: {curr_risk['level']}",
        icon=folium.Icon(color="red" if "Crit" in curr_risk["level"] else "orange", icon="info-sign")
    ).add_to(m)
    
    folium_static(m, width=480, height=380)

# Forecast Schedule Table
st.markdown("<div class='section-title'>📋 7-Day Meteorological Schedule & Heat-Risk Classification</div>", unsafe_allow_html=True)

table_data = []
for f in forecast_list:
    table_data.append({
        "Date": f["date"],
        "Max Temp (°C)": f"{f['temp_max_c']}°C",
        "Min Temp (°C)": f"{f['temp_min_c']}°C",
        "Heat Index (°C)": f"{f['heat_index_c']}°C",
        "Relative Humidity": f"{f['humidity_pct']}%",
        "Heatwave Streak": f"{f['heatwave_streak']} day(s)",
        "Heat-Risk Level": f["heat_risk_level"]
    })

st.dataframe(table_data, use_container_width=True)
st.caption("ℹ️ Telemetry and risk metrics are linked directly to downstream AI demand forecasting and hospital resource engines.")
