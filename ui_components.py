import streamlit as st
from typing import Dict, Any, List, Optional
from config import Config
from database import init_db, seed_demo_data

def apply_custom_theme():
    """Apply professional, clean healthcare tech styling."""
    st.markdown("""
    <style>
    /* Main container and font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Healthcare Metric Cards */
    .metric-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 16px 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        margin-bottom: 12px;
    }
    
    .metric-title {
        font-size: 0.82rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #64748B;
        margin-bottom: 4px;
    }
    
    .metric-val {
        font-size: 1.85rem;
        font-weight: 700;
        color: #0F172A;
        line-height: 1.2;
    }
    
    .metric-sub {
        font-size: 0.8rem;
        color: #475569;
        margin-top: 4px;
    }
    
    /* Badges */
    .badge {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        margin-right: 4px;
    }
    .badge-critical { background-color: #FEE2E2; color: #DC2626; border: 1px solid #FCA5A5; }
    .badge-high { background-color: #FFEDD5; color: #EA580C; border: 1px solid #FDBA74; }
    .badge-mod { background-color: #FEF3C7; color: #D97706; border: 1px solid #FDE68A; }
    .badge-low { background-color: #DCFCE7; color: #16A34A; border: 1px solid #86EFAC; }
    .badge-simulated { background-color: #F3E8FF; color: #7C3AED; border: 1px solid #D8B4FE; }
    .badge-verified { background-color: #E0F2FE; color: #0284C7; border: 1px solid #BAE6FD; }
    .badge-stale { background-color: #F1F5F9; color: #64748B; border: 1px solid #CBD5E1; }
    
    /* Section Headers */
    .section-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #1E293B;
        margin-top: 10px;
        margin-bottom: 12px;
        border-bottom: 2px solid #F1F5F9;
        padding-bottom: 6px;
    }
    
    /* Alert Banner */
    .alert-banner {
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    </style>
    """, unsafe_allow_html=True)

def render_sidebar_header():
    """Render sidebar system info, user role selector and database reset."""
    with st.sidebar:
        st.markdown(f"### 🛡️ **{Config.APP_NAME}**")
        st.caption(f"{Config.APP_SUBTITLE} • v{Config.APP_VERSION}")
        
        st.markdown(
            f"<div style='background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 6px; padding: 8px 10px; font-size: 0.78rem; color: #1E40AF; margin-bottom: 12px;'>"
            f"🎯 <b>{Config.PROBLEM_STATEMENT}</b>"
            f"</div>",
            unsafe_allow_html=True
        )
        
        # User Role Selection
        st.markdown("**Operational Role Selection**")
        selected_role = st.selectbox(
            "Active Session Role:",
            options=Config.ROLES,
            index=0,
            help="Simulates permissions and workflow perspectives across the regional health network."
        )
        st.session_state["user_role"] = selected_role
        
        st.divider()
        
        # Region selection
        st.markdown("**Active Healthcare Region**")
        preset_names = list(Config.PRESET_REGIONS.keys())
        selected_region = st.selectbox(
            "Select Regional Catchment:",
            options=preset_names,
            index=0
        )
        region_coords = Config.PRESET_REGIONS[selected_region]
        st.session_state["selected_region_name"] = selected_region
        st.session_state["selected_lat"] = region_coords["lat"]
        st.session_state["selected_lon"] = region_coords["lon"]
        
        st.caption(f"Coordinates: `{region_coords['lat']}, {region_coords['lon']}`")
        
        st.divider()
        st.markdown("**System & Database Status**")
        st.caption("SQLite DB: `heatshield.db` (Local)")
        if st.button("🔄 Reset to Default Demo Data", help="Re-seeds clean demonstration hospital records and initial telemetry"):
            init_db()
            seed_demo_data(force=True)
            st.success("Demonstration records reset successfully!")
            st.rerun()

def get_risk_badge_html(level: str) -> str:
    """Return styled HTML badge for risk severity."""
    lvl = level.lower()
    if "crit" in lvl:
        return '<span class="badge badge-critical">CRITICAL RISK</span>'
    elif "high" in lvl:
        return '<span class="badge badge-high">HIGH RISK</span>'
    elif "mod" in lvl:
        return '<span class="badge badge-mod">MODERATE RISK</span>'
    elif "low" in lvl:
        return '<span class="badge badge-low">LOW RISK</span>'
    else:
        return '<span class="badge badge-stale">UNKNOWN</span>'

def get_verification_badge_html(status: str) -> str:
    """Return styled HTML badge for data provenance."""
    st_low = status.lower()
    if "veri" in st_low:
        return '<span class="badge badge-verified">VERIFIED FEED</span>'
    elif "sim" in st_low or "demo" in st_low:
        return '<span class="badge badge-simulated">SIMULATED DEMO</span>'
    elif "stale" in st_low:
        return '<span class="badge badge-stale">STALE DATA</span>'
    else:
        return f'<span class="badge badge-stale">{status.upper()}</span>'
