import math
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from config import Config
from database import get_connection

class WeatherService:
    """Weather Forecast & Heatwave Intelligence Service.
    
    Provides real-time and forecast meteorological intelligence with configurable
    heat risk thresholds, heatwave duration tracking, and demonstration fallback.
    """
    
    @staticmethod
    def calculate_heat_index(temp_c: float, humidity_pct: float) -> float:
        """Calculate Apparent Temperature / Heat Index in Celsius using Rothfusz regression.
        
        Formula uses Fahrenheit conversion per NOAA standard, then converted back to Celsius.
        """
        if temp_c < 20.0:
            return round(temp_c, 1)
            
        t_f = temp_c * 9.0 / 5.0 + 32.0
        rh = max(0.0, min(100.0, humidity_pct))
        
        # Simple formula first
        hi_f = 0.5 * (t_f + 61.0 + ((t_f - 68.0) * 1.2) + (rh * 0.094))
        
        if hi_f >= 80.0:
            # Full Rothfusz regression
            hi_f = (
                -42.379
                + 2.04901523 * t_f
                + 10.14333127 * rh
                - 0.22475541 * t_f * rh
                - 0.00683783 * (t_f ** 2)
                - 0.05481717 * (rh ** 2)
                + 0.00122874 * (t_f ** 2) * rh
                + 0.00085282 * t_f * (rh ** 2)
                - 0.00000199 * (t_f ** 2) * (rh ** 2)
            )
            # Adjustments
            if rh < 13.0 and 80.0 <= t_f <= 112.0:
                adj = ((13.0 - rh) / 4.0) * math.sqrt((17.0 - abs(t_f - 95.0)) / 17.0)
                hi_f -= adj
            elif rh > 85.0 and 80.0 <= t_f <= 87.0:
                adj = ((rh - 85.0) / 10.0) * ((87.0 - t_f) / 5.0)
                hi_f += adj
                
        hi_c = (hi_f - 32.0) * 5.0 / 9.0
        return round(hi_c, 1)
        
    @classmethod
    def evaluate_heat_risk(
        cls,
        temp_c: float,
        duration_days: int = 1,
        thresh_mod: Optional[float] = None,
        thresh_high: Optional[float] = None,
        thresh_crit: Optional[float] = None
    ) -> Dict[str, Any]:
        """Evaluate heat-health risk level based on configurable thresholds and heatwave duration.
        
        Returns:
            Dict containing risk level (Low, Moderate, High, Critical), badge color, and guidance.
        """
        mod = thresh_mod if thresh_mod is not None else Config.HEAT_THRESHOLD_MODERATE
        high = thresh_high if thresh_high is not None else Config.HEAT_THRESHOLD_HIGH
        crit = thresh_crit if thresh_crit is not None else Config.HEAT_THRESHOLD_CRITICAL
        
        if temp_c >= crit or (temp_c >= high and duration_days >= 3):
            return {
                "level": "Critical",
                "color": "#DC2626", # Red
                "bg_color": "#FEE2E2",
                "early_warning": True,
                "guidance": "Emergency Red Alert: Severe heatwave. High mortality risk among vulnerable groups and fit individuals. Extreme surge in acute admissions and ambulance dispatch expected."
            }
        elif temp_c >= high or (temp_c >= mod and duration_days >= Config.HEATWAVE_MIN_DAYS):
            return {
                "level": "High",
                "color": "#EA580C", # Amber/Orange
                "bg_color": "#FFEDD5",
                "early_warning": True,
                "guidance": "Amber Heat-Health Warning: Sustained elevated temperatures. Escalating strain across emergency departments, heat-related cardiovascular and renal crises."
            }
        elif temp_c >= mod:
            return {
                "level": "Moderate",
                "color": "#D97706", # Yellow/Amber
                "bg_color": "#FEF3C7",
                "early_warning": False,
                "guidance": "Yellow Heat-Health Alert: Temperatures reaching vigilance threshold. Monitor vulnerable patients, heat exhaustion cases rising."
            }
        else:
            return {
                "level": "Low",
                "color": "#16A34A", # Green
                "bg_color": "#DCFCE7",
                "early_warning": False,
                "guidance": "Normal / Green: Temperature within seasonal baseline limits. Routine emergency care operational profile."
            }

    @classmethod
    def fetch_weather_forecast(
        cls,
        lat: float,
        lon: float,
        location_name: str = "Target Region",
        force_demo: bool = False,
        thresh_mod: Optional[float] = None,
        thresh_high: Optional[float] = None,
        thresh_crit: Optional[float] = None
    ) -> Dict[str, Any]:
        """Fetch current and 7-day forecast weather from Open-Meteo or fallback demo stream.
        
        Never invents live weather data: if live API is unavailable or offline, returns
        explicitly labelled Demonstration Mode.
        """
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        
        if not force_demo:
            try:
                # Open-Meteo is a publicly accessible, high-precision weather API (no private key needed)
                url = (
                    f"https://api.open-meteo.com/v1/forecast?"
                    f"latitude={lat}&longitude={lon}&"
                    f"current=temperature_2m,relative_humidity_2m,weather_code&"
                    f"daily=temperature_2m_max,temperature_2m_min,relative_humidity_2m_mean&"
                    f"forecast_days=7&timezone=auto"
                )
                resp = requests.get(url, timeout=5.0)
                if resp.status_code == 200:
                    data = resp.json()
                    curr = data.get("current", {})
                    daily = data.get("daily", {})
                    
                    curr_temp = float(curr.get("temperature_2m", 22.0))
                    curr_rh = float(curr.get("relative_humidity_2m", 50.0))
                    curr_hi = cls.calculate_heat_index(curr_temp, curr_rh)
                    
                    dates = daily.get("time", [])
                    max_temps = daily.get("temperature_2m_max", [])
                    min_temps = daily.get("temperature_2m_min", [])
                    humidities = daily.get("relative_humidity_2m_mean", [curr_rh] * len(dates))
                    
                    forecast_list = []
                    heatwave_days = 0
                    mod_thresh = thresh_mod or Config.HEAT_THRESHOLD_MODERATE
                    
                    for i in range(len(dates)):
                        t_max = float(max_temps[i])
                        t_min = float(min_temps[i])
                        rh = float(humidities[i]) if i < len(humidities) else curr_rh
                        hi = cls.calculate_heat_index(t_max, rh)
                        
                        if t_max >= mod_thresh:
                            heatwave_days += 1
                        else:
                            heatwave_days = 0
                            
                        risk = cls.evaluate_heat_risk(
                            t_max,
                            duration_days=heatwave_days,
                            thresh_mod=thresh_mod,
                            thresh_high=thresh_high,
                            thresh_crit=thresh_crit
                        )
                        
                        forecast_list.append({
                            "date": dates[i],
                            "temp_max_c": t_max,
                            "temp_min_c": t_min,
                            "humidity_pct": rh,
                            "heat_index_c": hi,
                            "heatwave_streak": heatwave_days,
                            "heat_risk_level": risk["level"],
                            "risk_color": risk["color"],
                            "is_heatwave": 1 if heatwave_days >= Config.HEATWAVE_MIN_DAYS else 0
                        })
                    
                    curr_risk = cls.evaluate_heat_risk(
                        curr_temp,
                        duration_days=forecast_list[0]["heatwave_streak"] if forecast_list else 1,
                        thresh_mod=thresh_mod,
                        thresh_high=thresh_high,
                        thresh_crit=thresh_crit
                    )
                    
                    result = {
                        "mode": "LIVE_API",
                        "data_source": "Open-Meteo Global Meteorological Forecast",
                        "location_name": location_name,
                        "latitude": lat,
                        "longitude": lon,
                        "last_updated": now_str,
                        "current": {
                            "temperature_c": curr_temp,
                            "humidity_pct": curr_rh,
                            "heat_index_c": curr_hi,
                            "heat_risk": curr_risk
                        },
                        "forecast": forecast_list,
                        "heatwave_duration_days": max([f["heatwave_streak"] for f in forecast_list], default=0),
                        "max_forecast_temp": max(max_temps) if max_temps else curr_temp,
                        "note": "Live meteorological model output retrieved."
                    }
                    cls._save_forecast_to_db(result)
                    return result
            except Exception as e:
                # Log and proceed to explicit demo mode
                pass
                
        # Graceful, labelled Demonstration Mode
        return cls._generate_demonstration_weather(
            lat, lon, location_name, thresh_mod, thresh_high, thresh_crit
        )
        
    @classmethod
    def _generate_demonstration_weather(
        cls,
        lat: float,
        lon: float,
        location_name: str,
        thresh_mod: Optional[float] = None,
        thresh_high: Optional[float] = None,
        thresh_crit: Optional[float] = None
    ) -> Dict[str, Any]:
        """Generate clearly labelled synthetic heatwave demonstration data."""
        now = datetime.now(timezone.utc)
        now_str = now.strftime("%Y-%m-%d %H:%M:%S UTC")
        
        # Synthetic scenario: Escalating Heatwave spell
        base_days = 7
        temps_max = [31.5, 34.2, 36.8, 35.5, 33.0, 29.5, 27.2]
        temps_min = [19.2, 22.0, 24.5, 23.8, 21.0, 18.5, 16.0]
        hum_list = [52.0, 48.0, 44.0, 47.0, 55.0, 60.0, 65.0]
        
        forecast_list = []
        heatwave_days = 0
        mod_thresh = thresh_mod or Config.HEAT_THRESHOLD_MODERATE
        
        for i in range(base_days):
            day_date = (now + timedelta(days=i)).strftime("%Y-%m-%d")
            t_max = temps_max[i]
            t_min = temps_min[i]
            rh = hum_list[i]
            hi = cls.calculate_heat_index(t_max, rh)
            
            if t_max >= mod_thresh:
                heatwave_days += 1
            else:
                heatwave_days = 0
                
            risk = cls.evaluate_heat_risk(
                t_max,
                duration_days=heatwave_days,
                thresh_mod=thresh_mod,
                thresh_high=thresh_high,
                thresh_crit=thresh_crit
            )
            
            forecast_list.append({
                "date": day_date,
                "temp_max_c": t_max,
                "temp_min_c": t_min,
                "humidity_pct": rh,
                "heat_index_c": hi,
                "heatwave_streak": heatwave_days,
                "heat_risk_level": risk["level"],
                "risk_color": risk["color"],
                "is_heatwave": 1 if heatwave_days >= Config.HEATWAVE_MIN_DAYS else 0
            })
            
        curr_temp = temps_max[0]
        curr_rh = hum_list[0]
        curr_risk = cls.evaluate_heat_risk(
            curr_temp,
            duration_days=1,
            thresh_mod=thresh_mod,
            thresh_high=thresh_high,
            thresh_crit=thresh_crit
        )
        
        result = {
            "mode": "DEMO_SYNTHETIC",
            "data_source": "Explicitly Labelled Demonstration Weather Stream (Simulated Heatwave)",
            "location_name": f"{location_name} (Simulated Scenario)",
            "latitude": lat,
            "longitude": lon,
            "last_updated": now_str,
            "current": {
                "temperature_c": curr_temp,
                "humidity_pct": curr_rh,
                "heat_index_c": cls.calculate_heat_index(curr_temp, curr_rh),
                "heat_risk": curr_risk
            },
            "forecast": forecast_list,
            "heatwave_duration_days": 4, # 4 consecutive peak days
            "max_forecast_temp": max(temps_max),
            "note": "Demonstration Mode Active: Weather service is operating in simulated scenario mode."
        }
        cls._save_forecast_to_db(result)
        return result

    @staticmethod
    def _save_forecast_to_db(weather_data: Dict[str, Any]) -> None:
        """Persist weather forecast snapshot to SQLite database."""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            
            # Save observation
            curr = weather_data.get("current", {})
            cursor.execute("""
            INSERT INTO weather_observations (
                location_name, latitude, longitude, recorded_at,
                temperature_c, humidity_pct, heat_index_c, heat_risk_level, data_source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                weather_data["location_name"],
                weather_data["latitude"],
                weather_data["longitude"],
                weather_data["last_updated"],
                curr.get("temperature_c", 0.0),
                curr.get("humidity_pct", 0.0),
                curr.get("heat_index_c", 0.0),
                curr.get("heat_risk", {}).get("level", "Unknown"),
                weather_data["data_source"]
            ))
            
            # Save forecast rows
            for f in weather_data.get("forecast", []):
                cursor.execute("""
                INSERT INTO weather_forecasts (
                    location_name, latitude, longitude, forecast_time,
                    temp_max_c, temp_min_c, humidity_pct, heatwave_flag,
                    heat_risk_level, data_source, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    weather_data["location_name"],
                    weather_data["latitude"],
                    weather_data["longitude"],
                    f["date"],
                    f["temp_max_c"],
                    f["temp_min_c"],
                    f["humidity_pct"],
                    f["is_heatwave"],
                    f["heat_risk_level"],
                    weather_data["data_source"],
                    now_iso
                ))
                
            conn.commit()
            conn.close()
        except Exception:
            pass
