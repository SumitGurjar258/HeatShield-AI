import csv
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def generate_sample_daily_demand(output_path: str = "data/sample_daily_demand.csv", seed: int = 42):
    np.random.seed(seed)
    
    # 730 days (2 full years of daily historical records)
    start_date = datetime(2024, 1, 1)
    dates = [start_date + timedelta(days=i) for i in range(730)]
    
    rows = []
    
    # Heatwave states
    heatwave_counter = 0
    
    for d in dates:
        day_of_year = d.timetuple().tm_yday
        day_of_week = d.weekday() # 0 = Monday, 6 = Sunday
        is_weekend = 1 if day_of_week >= 5 else 0
        month = d.month
        
        # Seasonality baseline temp: sinusoidal curve peaking in July (approx day 200)
        base_temp = 14.0 + 10.0 * np.sin(2 * np.pi * (day_of_year - 105) / 365.0)
        daily_noise = np.random.normal(0, 3.0)
        
        # Add realistic summer heatwave spikes in June, July, August
        is_summer = month in [6, 7, 8]
        heat_spike = 0.0
        
        # Simulate 3 distinct heatwave spells
        if is_summer and ((day_of_year in range(180, 187)) or (day_of_year in range(210, 218)) or (day_of_year in range(545, 553)) or (day_of_year in range(580, 587))):
            heat_spike = np.random.uniform(7.0, 12.0)
            heatwave_counter += 1
        else:
            heatwave_counter = 0
            
        temp_max_c = round(float(base_temp + daily_noise + heat_spike), 1)
        # Ensure realistic lower bounds
        temp_max_c = max(1.0, temp_max_c)
        temp_min_c = round(max(0.5, temp_max_c - np.random.uniform(6.0, 12.0)), 1)
        
        # Humidity inversely relates slightly with high heat, with noise
        humidity_pct = round(float(np.clip(75.0 - (temp_max_c - 15.0) * 1.2 + np.random.normal(0, 6.0), 30.0, 95.0)), 1)
        
        # Simplified Heat Index / Apparent Temperature
        if temp_max_c >= 26.0 and humidity_pct >= 40.0:
            heat_index_c = round(temp_max_c + 0.05 * (humidity_pct - 50.0) + 0.02 * (temp_max_c - 25.0) * (humidity_pct - 40.0), 1)
        else:
            heat_index_c = temp_max_c
            
        is_heatwave = 1 if (temp_max_c >= 28.0 and heatwave_counter >= 2) else 0
        
        # Healthcare Demand Formula (Ground truth with stochastic noise)
        # Baseline A&E attendance: ~300
        # Heat sensitivity: Non-linear surge above 28°C
        heat_excess = max(0.0, temp_max_c - 27.0)
        heat_surge = (heat_excess ** 1.65) * 8.5
        
        # Heatwave duration compounding impact
        duration_factor = 1.0 + (min(heatwave_counter, 5) * 0.08)
        
        weekend_effect = -15.0 if is_weekend else 10.0
        ae_noise = np.random.normal(0, 14.0)
        
        ae_attendances = int(np.clip(
            (295.0 + weekend_effect + (heat_surge * duration_factor) + ae_noise),
            180, 650
        ))
        
        # Emergency Admissions (typically ~24-28% of A&E attendances, higher during severe heatwaves due to vulnerable elderly/chronic illness decompensation)
        admission_rate = 0.25 + (0.008 * heat_excess)
        adm_noise = np.random.normal(0, 5.0)
        emergency_admissions = int(np.clip(
            (ae_attendances * admission_rate + adm_noise),
            40, 220
        ))
        
        rows.append({
            "date": d.strftime("%Y-%m-%d"),
            "region": "Greater London Health Region",
            "temp_max_c": temp_max_c,
            "temp_min_c": temp_min_c,
            "humidity_pct": humidity_pct,
            "heat_index_c": heat_index_c,
            "is_weekend": is_weekend,
            "day_of_week": day_of_week,
            "month": month,
            "is_heatwave": is_heatwave,
            "heatwave_day_streak": heatwave_counter,
            "ae_attendances": ae_attendances,
            "emergency_admissions": emergency_admissions,
            "data_label": "Labelled Demonstration Dataset"
        })
        
    df = pd.DataFrame(rows)
    df.to_csv(output_path, index=False)
    print(f"Generated {len(df)} rows in {output_path}")

if __name__ == "__main__":
    generate_sample_daily_demand()
