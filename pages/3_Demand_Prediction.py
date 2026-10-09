import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from config import Config
from services.demand_forecasting import DemandForecastingService
from services.weather_service import WeatherService
from ui_components import apply_custom_theme, get_verification_badge_html

apply_custom_theme()

st.title("🔮 AI Healthcare Demand Prediction & Impact Monitoring")
st.caption("Major Field 3 (Supporting AI Module) • Chronological ML forecasting, defensible uncertainty intervals, and What-If heatwave stress simulation")

# Load session forecast service
if "demand_service" not in st.session_state:
    st.session_state["demand_service"] = DemandForecastingService()
demand_service: DemandForecastingService = st.session_state["demand_service"]

# Ensure default model is trained
if demand_service.model_ae is None:
    default_csv = Config.BASE_DIR / "data" / "sample_daily_demand.csv"
    if default_csv.exists():
        df_init = pd.read_csv(default_csv)
        demand_service.train_and_evaluate(df_init)

# Connect with weather forecast
if "latest_weather_data" not in st.session_state:
    st.session_state["latest_weather_data"] = WeatherService.fetch_weather_forecast(
        lat=st.session_state.get("selected_lat", Config.DEFAULT_LAT),
        lon=st.session_state.get("selected_lon", Config.DEFAULT_LON),
        location_name=st.session_state.get("selected_region_name", Config.DEFAULT_LOCATION_NAME)
    )
weather_data = st.session_state["latest_weather_data"]

# Tabs inside Demand Prediction
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 7-Day Demand Forecast",
    "🧪 What-If Heatwave Simulator",
    "🤖 ML Model Evaluation & Metrics",
    "📂 Data Import & Validation"
])

# -------------------------------------------------------------
# TAB 1: 7-DAY DEMAND FORECAST
# -------------------------------------------------------------
with tab1:
    st.markdown("<div class='section-title'>📈 Projected Daily Healthcare Demand</div>", unsafe_allow_html=True)
    st.caption("Coupled with live meteorological intelligence from Major Field 1")
    
    forecast_results = demand_service.predict_forecast_demand(weather_data.get("forecast", []))
    
    # Summary cards
    total_ae = sum([f["predicted_ae_attendances"] for f in forecast_results])
    total_adm = sum([f["predicted_emergency_admissions"] for f in forecast_results])
    peak_adm_day = max(forecast_results, key=lambda x: x["predicted_emergency_admissions"])
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f"<div class='metric-card'>"
            f"<div class='metric-title'>7-Day Projected A&E Surge</div>"
            f"<div class='metric-val' style='color: #7C3AED;'>{int(total_ae)}</div>"
            f"<div class='metric-sub'>Total attendances</div>"
            f"</div>",
            unsafe_allow_html=True
        )
    with c2:
        st.markdown(
            f"<div class='metric-card'>"
            f"<div class='metric-title'>7-Day Emergency Admissions</div>"
            f"<div class='metric-val' style='color: #2563EB;'>{int(total_adm)}</div>"
            f"<div class='metric-sub'>Inpatient bed demand</div>"
            f"</div>",
            unsafe_allow_html=True
        )
    with c3:
        st.markdown(
            f"<div class='metric-card'>"
            f"<div class='metric-title'>Peak Daily Admission Need</div>"
            f"<div class='metric-val' style='color: #EA580C;'>{peak_adm_day['predicted_emergency_admissions']}</div>"
            f"<div class='metric-sub'>Peak day: {peak_adm_day['date']}</div>"
            f"</div>",
            unsafe_allow_html=True
        )
    with c4:
        st.markdown(
            f"<div class='metric-card'>"
            f"<div class='metric-title'>Demand Uncertainty Buffer</div>"
            f"<div class='metric-val'>±{demand_service.uncertainty_margin_adm}</div>"
            f"<div class='metric-sub'>90% empirical error interval</div>"
            f"</div>",
            unsafe_allow_html=True
        )
        
    # Plot forecast demand with uncertainty band
    f_dates = [f["date"] for f in forecast_results]
    f_ae = [f["predicted_ae_attendances"] for f in forecast_results]
    f_adm = [f["predicted_emergency_admissions"] for f in forecast_results]
    f_adm_upper = [f["adm_upper_ci"] for f in forecast_results]
    f_adm_lower = [f["adm_lower_ci"] for f in forecast_results]
    
    fig_f = go.Figure()
    
    # Uncertainty band
    fig_f.add_trace(go.Scatter(
        x=f_dates + f_dates[::-1],
        y=f_adm_upper + f_adm_lower[::-1],
        fill='toself',
        fillcolor='rgba(37, 99, 235, 0.15)',
        line=dict(color='rgba(255,255,255,0)'),
        hoverinfo="skip",
        name='Admissions 90% Confidence Interval'
    ))
    
    # Emergency Admissions
    fig_f.add_trace(go.Scatter(
        x=f_dates, y=f_adm,
        mode='lines+markers',
        name='Predicted Emergency Admissions',
        line=dict(color='#2563EB', width=3),
        marker=dict(size=8)
    ))
    
    # A&E Attendances (secondary axis or scaled)
    fig_f.add_trace(go.Scatter(
        x=f_dates, y=f_ae,
        mode='lines+markers',
        name='Predicted A&E Attendances',
        line=dict(color='#7C3AED', width=2, dash='dot'),
        yaxis='y2'
    ))
    
    fig_f.update_layout(
        margin=dict(l=20, r=20, t=30, b=20),
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor="#FFFFFF",
        xaxis=dict(showgrid=True, gridcolor="#F1F5F9"),
        yaxis=dict(title="Emergency Admissions", showgrid=True, gridcolor="#F1F5F9"),
        yaxis2=dict(title="A&E Attendances", overlaying='y', side='right', showgrid=False)
    )
    st.plotly_chart(fig_f, use_container_width=True)
    
    # Table of forecast figures
    st.dataframe(pd.DataFrame(forecast_results), use_container_width=True)

# -------------------------------------------------------------
# TAB 2: WHAT-IF HEATWAVE SIMULATOR
# -------------------------------------------------------------
with tab2:
    st.markdown("<div class='section-title'>🧪 What-If Heatwave Stress Testing Simulator</div>", unsafe_allow_html=True)
    st.caption("Evaluate non-linear surge and capacity strain by altering heat intensity and spell duration")
    
    sim_c1, sim_c2 = st.columns([1, 2])
    
    with sim_c1:
        st.markdown("#### Scenario Assumptions")
        sim_base_temp = st.slider("Baseline Seasonal Temperature (°C)", 18.0, 30.0, 24.0, 0.5)
        sim_temp_delta = st.slider("Heatwave Temperature Spike (+°C)", 1.0, 10.0, 6.0, 0.5)
        sim_duration = st.slider("Heatwave Consecutive Days", 1, 7, 3)
        sim_humidity = st.slider("Relative Humidity (%)", 30.0, 90.0, 50.0, 5.0)
        sim_capacity = st.number_input("Hospital Network Staffed Bed Capacity", min_value=10, max_value=200, value=75)
        
        sim_res = demand_service.simulate_what_if_scenario(
            base_temp_c=sim_base_temp,
            temp_delta_c=sim_temp_delta,
            heatwave_days=sim_duration,
            humidity_pct=sim_humidity,
            baseline_bed_capacity=sim_capacity
        )
        
    with sim_c2:
        st.markdown("#### Scenario Impact Assessment")
        
        w1, w2, w3 = st.columns(3)
        with w1:
            st.markdown(
                f"<div class='metric-card'>"
                f"<div class='metric-title'>Simulated Max Temp</div>"
                f"<div class='metric-val' style='color: #DC2626;'>{sim_res['sim_temp_max']}°C</div>"
                f"<div class='metric-sub'>Spike: +{sim_res['temp_delta_c']}°C</div>"
                f"</div>",
                unsafe_allow_html=True
            )
        with w2:
            st.markdown(
                f"<div class='metric-card'>"
                f"<div class='metric-title'>Predicted A&E Surge</div>"
                f"<div class='metric-val' style='color: #7C3AED;'>+{sim_res['ae_surge_pct']}%</div>"
                f"<div class='metric-sub'>{sim_res['predicted_ae_attendances']} vs {sim_res['baseline_ae']} baseline</div>"
                f"</div>",
                unsafe_allow_html=True
            )
        with w3:
            shortfall = sim_res["projected_bed_shortfall"]
            sh_c = "#DC2626" if shortfall > 0 else "#16A34A"
            st.markdown(
                f"<div class='metric-card'>"
                f"<div class='metric-title'>Projected Bed Shortfall</div>"
                f"<div class='metric-val' style='color: {sh_c};'>{shortfall} Beds</div>"
                f"<div class='metric-sub'>Req: {sim_res['predicted_emergency_admissions']} | Cap: {sim_res['baseline_bed_capacity']}</div>"
                f"</div>",
                unsafe_allow_html=True
            )
            
        # Comparison Bar Chart
        categories = ["A&E Attendances", "Emergency Admissions"]
        baseline_vals = [sim_res["baseline_ae"], sim_res["baseline_adm"]]
        sim_vals = [sim_res["predicted_ae_attendances"], sim_res["predicted_emergency_admissions"]]
        
        fig_bar = go.Figure(data=[
            go.Bar(name='Normal Seasonal Baseline', x=categories, y=baseline_vals, marker_color='#94A3B8'),
            go.Bar(name=f'Heatwave Scenario ({sim_res["sim_temp_max"]}°C)', x=categories, y=sim_vals, marker_color='#DC2626')
        ])
        fig_bar.update_layout(
            barmode='group',
            height=300,
            margin=dict(l=20, r=20, t=20, b=20),
            plot_bgcolor="#FFFFFF",
            yaxis=dict(title="Daily Patient Count", showgrid=True, gridcolor="#F1F5F9")
        )
        st.plotly_chart(fig_bar, use_container_width=True)
        
        st.markdown(
            f"**Defensible Uncertainty Estimates (90% Confidence Interval):**<br>"
            f"• A&E Attendances: `[{sim_res['uncertainty_interval_ae'][0]} , {sim_res['uncertainty_interval_ae'][1]}]`<br>"
            f"• Emergency Admissions: `[{sim_res['uncertainty_interval_adm'][0]} , {sim_res['uncertainty_interval_adm'][1]}]`",
            unsafe_allow_html=True
        )

# -------------------------------------------------------------
# TAB 3: ML MODEL EVALUATION & METRICS
# -------------------------------------------------------------
with tab3:
    st.markdown("<div class='section-title'>🤖 ML Model Architecture & Chronological Evaluation</div>", unsafe_allow_html=True)
    st.info(
        "🛡️ **Methodological Rigor:** The model is trained and evaluated using strict **Chronological Split** (first 80% training, last 20% holdout test period). "
        "Training metrics are never reported as test performance. Random cross-validation is intentionally avoided to prevent future data leakage."
    )
    
    metrics = demand_service.metrics
    if not metrics:
        st.warning("Model metrics not available.")
    else:
        ae_m = metrics["ae_attendances"]
        adm_m = metrics["emergency_admissions"]
        ds = metrics["data_summary"]
        
        st.markdown(
            f"<div style='background: #F8FAFC; border: 1px solid #E2E8F0; padding: 12px 16px; border-radius: 8px; margin-bottom: 16px;'>"
            f"<b>Model Architecture:</b> {metrics.get('model_version')} &nbsp;|&nbsp; "
            f"<b>Total Dataset:</b> {ds['total_rows']} records &nbsp;|&nbsp; "
            f"<b>Training Period:</b> {ds['train_period']} ({ds['train_rows']} rows) &nbsp;|&nbsp; "
            f"<b>Test Period:</b> {ds['test_period']} ({ds['test_rows']} rows)"
            f"</div>",
            unsafe_allow_html=True
        )
        
        col_ae_m, col_adm_m = st.columns(2)
        
        with col_ae_m:
            st.markdown("#### A&E Attendances (Holdout Test Performance)")
            m1, m2, m3 = st.columns(3)
            m1.metric("Test MAE", f"{ae_m['test_mae']} pts", help="Mean Absolute Error on holdout test set")
            m2.metric("Test RMSE", f"{ae_m['test_rmse']} pts", help="Root Mean Squared Error on holdout test set")
            m3.metric("Test R² Score", f"{ae_m['test_r2']}", help="Variance explained on holdout test set")
            st.caption(f"Train MAE: {ae_m['train_mae']} pts | Train RMSE: {ae_m['train_rmse']} pts (Honest Separation)")
            
        with col_adm_m:
            st.markdown("#### Emergency Admissions (Holdout Test Performance)")
            m4, m5, m6 = st.columns(3)
            m4.metric("Test MAE", f"{adm_m['test_mae']} pts")
            m5.metric("Test RMSE", f"{adm_m['test_rmse']} pts")
            m6.metric("Test R² Score", f"{adm_m['test_r2']}")
            st.caption(f"Train MAE: {adm_m['train_mae']} pts | Train RMSE: {adm_m['train_rmse']} pts (Honest Separation)")

        st.divider()
        st.markdown("#### Chronological Holdout: Actual vs Predicted Demand Comparison")
        comp = metrics.get("test_comparison", [])
        if comp:
            comp_df = pd.DataFrame(comp)
            fig_comp = go.Figure()
            fig_comp.add_trace(go.Scatter(
                x=comp_df["date"], y=comp_df["actual_ae"],
                mode="lines", name="Observed Actual A&E",
                line=dict(color="#64748B", width=1.5)
            ))
            fig_comp.add_trace(go.Scatter(
                x=comp_df["date"], y=comp_df["pred_ae"],
                mode="lines", name="Predicted A&E (Model)",
                line=dict(color="#7C3AED", width=2)
            ))
            fig_comp.update_layout(
                height=350,
                margin=dict(l=20, r=20, t=20, b=20),
                plot_bgcolor="#FFFFFF",
                xaxis=dict(title="Holdout Test Date", showgrid=True, gridcolor="#F1F5F9"),
                yaxis=dict(title="A&E Daily Attendances", showgrid=True, gridcolor="#F1F5F9")
            )
            st.plotly_chart(fig_comp, use_container_width=True)

        st.markdown("#### Feature Importance Weights")
        feat_imp = metrics.get("feature_importance", {})
        if feat_imp:
            feat_df = pd.DataFrame(list(feat_imp.items()), columns=["Feature", "Importance"]).sort_values("Importance", ascending=False)
            fig_feat = px.bar(feat_df, x="Importance", y="Feature", orientation="h", color="Importance", color_continuous_scale="Purples")
            fig_feat.update_layout(height=280, margin=dict(l=20, r=20, t=10, b=10))
            st.plotly_chart(fig_feat, use_container_width=True)

# -------------------------------------------------------------
# TAB 4: DATA IMPORT & VALIDATION
# -------------------------------------------------------------
with tab4:
    st.markdown("<div class='section-title'>📂 Healthcare Demand Data Ingestion & Quality Diagnostics</div>", unsafe_allow_html=True)
    st.caption("Upload historical daily healthcare records or inspect current training data")
    
    uploaded_file = st.file_uploader("Upload Daily Healthcare Demand CSV:", type=["csv"])
    if uploaded_file is not None:
        try:
            user_df = pd.read_csv(uploaded_file)
            clean_df, report = demand_service.validate_and_clean_data(user_df)
            
            if report["status"] == "INVALID":
                st.error(f"❌ Data Validation Error: {report.get('error')}")
            else:
                st.success(f"✅ Data validated successfully! {report['total_rows_clean']} valid rows found.")
                st.json(report)
                if st.button("Retrain Models on Uploaded Dataset", type="primary"):
                    with st.spinner("Retraining Random Forest regressors..."):
                        demand_service.train_and_evaluate(clean_df)
                    st.success("Model retrained successfully on new dataset!")
                    st.rerun()
        except Exception as e:
            st.error(f"Error reading CSV: {str(e)}")
            
    st.divider()
    st.markdown("#### Current Loaded Dataset Sample (First 10 Rows)")
    if demand_service.historical_df is not None:
        st.dataframe(demand_service.historical_df.head(10), use_container_width=True)
    else:
        st.caption("No dataset loaded yet.")
