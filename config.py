import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables
load_dotenv(BASE_DIR / ".env")

class Config:
    BASE_DIR = BASE_DIR
    APP_NAME = "HeatShield AI"
    APP_SUBTITLE = "Extreme Heat Healthcare Preparedness & Response System"
    APP_VERSION = "1.0.0-hackathon"
    PROBLEM_STATEMENT = "HC-02 — Predicting Hospital Demand During Extreme Heat"
    
    # Database
    DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "heatshield.db"))
    
    # Weather
    WEATHER_PROVIDER = os.getenv("WEATHER_API_PROVIDER", "open-meteo")
    OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY", "")
    
    # Geographic defaults (e.g. Greater London Healthcare Region)
    DEFAULT_LAT = float(os.getenv("DEFAULT_LAT", "51.5074"))
    DEFAULT_LON = float(os.getenv("DEFAULT_LON", "-0.1278"))
    DEFAULT_LOCATION_NAME = os.getenv("DEFAULT_LOCATION_NAME", "Greater London Region")
    
    # Pre-configured geographic regions for easy exploration
    PRESET_REGIONS = {
        "Greater London Region (UK)": {"lat": 51.5074, "lon": -0.1278},
        "West Midlands / Birmingham (UK)": {"lat": 52.4862, "lon": -1.8904},
        "Greater Manchester (UK)": {"lat": 53.4808, "lon": -2.2426},
        "Phoenix Metro (US - Extreme Heat Demo)": {"lat": 33.4484, "lon": -112.0740},
        "Madrid Community (ES - Mediterranean Heatwave)": {"lat": 40.4168, "lon": -3.7038},
        "Delhi NCR (IN - Tropical Heatwave)": {"lat": 28.6139, "lon": 77.2090},
    }
    
    # Heat-health alert default thresholds (Celsius)
    # Based on UKHSA & WHO Heat-Health guidance
    HEAT_THRESHOLD_MODERATE = float(os.getenv("HEAT_THRESHOLD_MODERATE", "28.0"))
    HEAT_THRESHOLD_HIGH = float(os.getenv("HEAT_THRESHOLD_HIGH", "32.0"))
    HEAT_THRESHOLD_CRITICAL = float(os.getenv("HEAT_THRESHOLD_CRITICAL", "35.0"))
    HEATWAVE_MIN_DAYS = int(os.getenv("HEATWAVE_MIN_DAYS", "2"))
    
    # Safety buffer
    BED_SAFETY_BUFFER_PCT = float(os.getenv("BED_SAFETY_BUFFER_PCT", "10.0"))
    
    # User roles for demonstration
    ROLES = [
        "Regional Emergency Planner / Admin",
        "Hospital Charge Nurse / Clinician",
        "Ambulance Paramedic / Dispatcher"
    ]
