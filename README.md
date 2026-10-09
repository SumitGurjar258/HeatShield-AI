# 🛡️ HeatShield AI — Extreme Heat Healthcare Preparedness System

> **Problem Statement HC-02:** Predicting Hospital Demand During Extreme Heat  
> **Author & GitHub:** [SumitGurjar258](https://github.com/SumitGurjar258)  
> **Repository:** [https://github.com/SumitGurjar258/HeatShield-AI](https://github.com/SumitGurjar258/HeatShield-AI)

---

## 📖 Executive Summary

**HeatShield AI** is a full-stack healthcare intelligence platform engineered to prepare regional healthcare systems and hospital networks for severe heatwaves and climate extremes. It connects **weather forecasting**, **scikit-learn ML demand forecasting**, **real-time staffed bed and inventory tracking**, **geographic risk heatmaps & GeoAlerts**, and **decision-supported ambulance triage routing**.

The application is structured into **exactly 3 major operational fields** without redundant modules or command centers:
1. **Weather Forecast & Heatwave Intelligence**
2. **Smart Hospital Resource Allocation, Geographic Risk & Ambulance Coordination**
3. **AI-Based Healthcare Demand Prediction & Impact Monitoring**

---

## 🏛️ System Architecture & End-to-End Workflow

```
[ Meteorological Data (Open-Meteo API / Live Weather) ]
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. Weather Forecast & Heatwave Intelligence                 │
│    • Real-time Temp, Humidity & Apparent Heat Index         │
│    • Configurable UKHSA/WHO Heat-Health Alert Thresholds    │
│    • Heatwave Spell Duration Tracking                       │
└────────────────────────┬────────────────────────────────────┘
                         │ Forecasted Temperatures & Streaks
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. AI Healthcare Demand Prediction & Impact Monitoring      │
│    • Chronological Scikit-Learn Random Forest Regressors    │
│    • Honest Evaluation Metrics (Test MAE, RMSE, R²)         │
│    • Empirical 90% Uncertainty Intervals                    │
│    • Interactive What-If Heatwave Stress Testing Simulator  │
└────────────────────────┬────────────────────────────────────┘
                         │ Projected A&E & Admission Surge
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Smart Hospital Resource Allocation & Ambulance Coord.    │
│    • Shortfall Engine: max(0, Expected - Available Staffed) │
│    • Differentiates Total Beds vs Staffed Ready-to-Admit    │
│    • Interactive Capacity Heatmap (Folium)                  │
│    • Documented GeoAlerts & Clinical Acknowledgement Audit   │
│    • Ambulance Triage Destination Matching (ETA + Caps)     │
│    • Incoming Patient Alerts Transmitted to Hospital Ward   │
└─────────────────────────────────────────────────────────────┘
```

---

## 🌟 Key Features Across the 3 Modules

### Module 1: Weather Forecast & Heatwave Intelligence
- **Live Meteorological Ingestion:** Global Open-Meteo integration (accurate lat/long weather without API keys) with graceful, labelled synthetic extreme heatwave demo fallback.
- **Biometeorological Heat Index:** Calculates Apparent Heat Index using Rothfusz polynomial regression.
- **Early-Warning Alerts:** Flags hazardous conditions based on configurable thresholds (Yellow/Moderate ≥28°C, Amber/High ≥32°C, Red/Critical ≥35°C, or prolonged spells).
- **Duration Tracking:** Quantifies consecutive hot days to model cumulative thermal fatigue.

### Module 2: Smart Hospital Resource Allocation & Ambulance Coordination
- **Rigorous Bed Accounting:** Explicitly separates **Total Registered Beds** from **Available Staffed Beds**. Unreported telemetry is represented as `Unknown`, never assumed to be zero or available.
- **Resource Shortfall Engine:** Calculates projected deficits:
  $$\text{Bed Shortfall} = \max(0, \text{Expected Admissions} - \text{Available Staffed Beds})$$
- **Geographic Risk Heatmap:** Interactive Folium map displaying registered hospitals color-coded by capacity risk (Green, Yellow, Amber, Red).
- **GeoAlerts Engine:** Generates active alerts with clear bottleneck explanations (e.g., Staffed Bed Deficit, IV Cooling Fluid Depletion, Nursing Shortage).
- **Ambulance-to-Hospital Coordination:**
  - Standardized urgency categorization (Red - Category 1 Life Threat, Amber - Category 2 Urgent, Green - Standard).
  - Matches candidate hospitals based on verified clinical capabilities (e.g. *Heat Stroke Resuscitation*, *Burns/Cooling Unit*, *Renal Dialysis*, *ICU*), Haversine distance, and urban ETA.
  - Generates real-time **Incoming Patient Alerts** directly to the receiving hospital ward dashboard.
  - Triage staff can **Acknowledge**, **Prepare Resources**, and log admissions with an immutable audit trail.
  - *Decision Support Notice:* Explicitly guides dispatch without replacing paramedic judgment or clinical protocols.

### Module 3: AI Healthcare Demand Prediction & Impact Monitoring
- **Chronological Training & Testing:** Strictly splits data chronologically (first 80% train, last 20% holdout test). Avoids data leakage and never reports train accuracy as test accuracy.
- **Evaluation Metrics:** Reports test MAE, RMSE, and $R^2$ score for both A&E attendances and emergency admissions.
- **Defensible Uncertainty Intervals:** Computes empirical 90th-percentile error margins based on test residual distributions.
- **What-If Heatwave Simulator:** Allows clinicians to simulate temperature spikes (+1°C to +10°C) and multi-day heatwave spells to observe projected surges.
- **Data Ingestion:** Supports CSV upload with schema validation, missing data imputation, and re-training.

---

## 🛠️ Technology Stack

- **Frontend & App Framework:** Streamlit (v1.53+)
- **Backend & Logic:** Python 3.12+
- **Database:** SQLite with foreign keys, indexes, and audit logging
- **Data Processing:** Pandas, NumPy
- **Machine Learning:** Scikit-learn (RandomForestRegressor, GradientBoostingRegressor)
- **Geospatial Mapping:** Folium, Streamlit-Folium
- **Data Visualization:** Plotly (interactive charts)
- **Configuration:** Python-dotenv, `.env`
- **Testing:** Pytest

---

## 💻 Setup and Installation (Windows / VS Code)

### 1. Clone the Repository
```powershell
git clone https://github.com/SumitGurjar258/HeatShield-AI.git
cd HeatShield-AI
```

### 2. Create and Activate Virtual Environment (Recommended)
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```
*(Default settings run immediately using free Open-Meteo live weather or labelled demo fallback.)*

### 5. Run the Application
```powershell
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 🧪 Running Unit Tests

Run the complete test suite:
```powershell
pytest -v
```
Tests cover:
- Database schema initialization and seed integrity (`test_database.py`)
- Bed shortfall calculation and `Unknown` value safety (`test_resource_engine.py`)
- Capability filtering, ETA calculation, and alert lifecycle (`test_ambulance_workflow.py`)
- Chronological train/test split, evaluation metrics, and what-if simulation (`test_demand_forecasting.py`)

---

## 🔒 Security, Ethics & Clinical Boundaries

- **Decision Support Only:** This system is decision support for healthcare operational readiness, not an automated clinical diagnosis tool.
- **Data Provenance:** Displays whether telemetry is from a **Verified Feed**, **Simulated Demo**, or **Stale (>12h/24h)**.
- **Role-Based Audit Logging:** All hospital resource modifications and alert acknowledgments are permanently logged in SQLite with timestamps and role identifiers.
- **Privacy:** Minimal patient data transmission (urgency category, clinical condition summary, ETA) to respect confidentiality.

---

## 📄 License
MIT License. Built for the Hackathon Healthcare Preparedness Challenge (HC-02).
