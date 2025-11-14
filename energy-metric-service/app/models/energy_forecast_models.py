"""
Pydantic models for Energy Forecasting API
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class EnergyPredictionRequest(BaseModel):
    cpu_utilization_percent: float = Field(..., ge=0, le=100, description="CPU utilization percentage (0-100)")
    memory_utilization_percent: float = Field(..., ge=0, le=100, description="Memory utilization percentage (0-100)")


class TimeSeriesDataPoint(BaseModel):
    timestamp: str = Field(..., description="ISO timestamp")
    cpu_utilization_percent: float = Field(..., ge=0, le=100)
    memory_utilization_percent: float = Field(..., ge=0, le=100)


class TimeSeriesPredictionRequest(BaseModel):
    data_points: List[TimeSeriesDataPoint] = Field(..., min_items=1)


class ForecastRequest(BaseModel):
    recent_data: List[TimeSeriesDataPoint] = Field(..., min_items=1, description="Recent data points for pattern analysis")
    forecast_hours: Optional[int] = Field(24, ge=1, le=168, description="Number of hours to forecast (1-168)")


class EnergyPredictionResponse(BaseModel):
    predicted_energy_watts: float
    confidence: str
    inputs: Dict[str, float]
    model_info: Dict[str, Any]


class ForecastSummary(BaseModel):
    forecast_period_hours: int
    total_forecasted_energy_kwh: float
    average_hourly_energy_watts: float
    peak_hourly_energy_watts: float
    min_hourly_energy_watts: float
    energy_range_watts: float
    base_patterns: Dict[str, float]


class HourlyForecast(BaseModel):
    hour: int
    timestamp: str
    forecasted_cpu_utilization: float
    forecasted_memory_utilization: float
    forecasted_energy_watts: float
    confidence: str


class DayForecastResponse(BaseModel):
    hourly_forecasts: List[HourlyForecast]
    summary: ForecastSummary
    model_info: Dict[str, Any]
    generated_at: str


class MetricWithPrediction(BaseModel):
    # Original metric data
    timestamp: int
    node_name: str
    metric_source: str
    cpu_utilization_percent: float
    memory_utilization_percent: float
    energy_watts: float
    cpu_package_watts: float
    memory_power_watts: float
    platform_watts: float
    created_at: str

    # ML prediction data
    predicted_energy_watts: float
    prediction_error_watts: float
    prediction_error_percent: float
    prediction_confidence: str


class ForecastMetric(BaseModel):
    timestamp: int
    timestamp_iso: str
    hour_offset: int
    forecasted_cpu_utilization_percent: float
    forecasted_memory_utilization_percent: float
    forecasted_energy_watts: float
    confidence: str
    is_forecast: bool = True


class EnhancedMetricsResponse(BaseModel):
    status: str
    filters: Dict[str, Any]

    # Historical metrics with predictions
    historical_metrics: List[MetricWithPrediction]
    historical_count: int

    # 24-hour forecast
    forecast_metrics: List[ForecastMetric]
    forecast_count: int

    # Summary statistics
    prediction_accuracy: Dict[str, float]
    forecast_summary: Dict[str, Any]
    model_info: Dict[str, Any]
    generated_at: str
