import streamlit as st
from config import Config
from database import init_db, seed_demo_data
from ui_components import render_sidebar_header, apply_custom_theme

# Page Configuration
st.set_page_config(
    page_title="HeatShield AI — Extreme Heat Healthcare Preparedness",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database schemas and synthetic demonstration data
init_db()
seed_demo_data()

# Render common sidebar controls (Role switcher, Region selector, DB reset)
render_sidebar_header()

# Exactly 3 major fields per hackathon problem statement specification
page_weather = st.Page(
    "pages/1_Weather_Heatwave.py",
    title="Weather & Heatwave Intelligence",
    icon="☀️",
    default=True
)

page_resources = st.Page(
    "pages/2_Hospital_Resources_Ambulance.py",
    title="Hospital Resources & Ambulance Coordination",
    icon="🏥"
)

page_demand = st.Page(
    "pages/3_Demand_Prediction.py",
    title="Demand Prediction & Impact Monitoring",
    icon="🔮"
)

# Execute navigation router with exactly 3 modules
pg = st.navigation([page_weather, page_resources, page_demand])
pg.run()
