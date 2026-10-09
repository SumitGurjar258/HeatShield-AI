import pytest
import pandas as pd
from services.demand_forecasting import DemandForecastingService

def test_data_validation_and_cleaning():
    service = DemandForecastingService()
    
    # Missing required column
    invalid_df = pd.DataFrame({
        "date": ["2024-01-01", "2024-01-02"],
        "temp_max_c": [22.0, 24.0]
    })
    _, report = service.validate_and_clean_data(invalid_df)
    assert report["status"] == "INVALID"
    assert "ae_attendances" in report["missing_required_columns"]
    
    # Valid dataframe with missing value that needs imputation
    valid_with_nan = pd.DataFrame({
        "date": ["2024-01-01", "2024-01-02", "2024-01-03"],
        "temp_max_c": [22.0, None, 25.0],
        "ae_attendances": [300, 310, 320],
        "emergency_admissions": [75, 80, 82]
    })
    clean_df, report = service.validate_and_clean_data(valid_with_nan)
    assert report["status"] == "VALID"
    assert clean_df["temp_max_c"].isna().sum() == 0

def test_chronological_training_and_metrics():
    service = DemandForecastingService()
    sample_path = "data/sample_daily_demand.csv"
    df = pd.read_csv(sample_path)
    
    metrics = service.train_and_evaluate(df, test_ratio=0.20)
    
    # Check that evaluation metrics exist
    assert "ae_attendances" in metrics
    assert "emergency_admissions" in metrics
    
    ae_metrics = metrics["ae_attendances"]
    assert "test_mae" in ae_metrics
    assert "test_rmse" in ae_metrics
    assert "test_r2" in ae_metrics
    assert "train_mae" in ae_metrics
    
    # Check uncertainty interval
    assert ae_metrics["uncertainty_90ci"] > 0
    
    # Check data split summary (strictly chronological)
    summary = metrics["data_summary"]
    assert summary["test_rows"] > 0
    assert summary["train_rows"] > summary["test_rows"]

def test_what_if_simulator():
    service = DemandForecastingService()
    sim_result = service.simulate_what_if_scenario(
        base_temp_c=25.0,
        temp_delta_c=8.0, # 33°C heatwave spike
        heatwave_days=3,
        baseline_bed_capacity=80
    )
    
    assert sim_result["sim_temp_max"] == 33.0
    assert sim_result["predicted_ae_attendances"] > sim_result["baseline_ae"]
    assert sim_result["ae_surge_pct"] > 0
    assert "uncertainty_interval_ae" in sim_result
    assert sim_result["uncertainty_interval_ae"][0] < sim_result["uncertainty_interval_ae"][1]
