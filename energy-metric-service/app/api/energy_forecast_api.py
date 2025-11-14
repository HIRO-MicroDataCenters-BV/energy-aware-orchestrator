"""
Energy Forecasting API endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.services.energy_forecasting_service import EnergyForecastingService
from app.db.database import get_async_db
from app.repositories.node_power_metrics import NodePowerMetricsRepository
from app.models.energy_forecast_models import (
    EnergyPredictionRequest,
    TimeSeriesPredictionRequest,
    ForecastRequest,
    EnergyPredictionResponse,
    DayForecastResponse,
    MetricWithPrediction,
    ForecastMetric,
    EnhancedMetricsResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/energy-forecast", tags=["Energy Forecasting"])


# Dependency to get forecasting service
def get_forecasting_service() -> EnergyForecastingService:
    """Get the singleton energy forecasting service instance"""
    try:
        return EnergyForecastingService.get_instance()
    except Exception as e:
        logger.error(f"Failed to get forecasting service: {e}")
        raise HTTPException(status_code=500, detail="Forecasting service unavailable")


@router.get("/health")
async def health_check(service: EnergyForecastingService = Depends(get_forecasting_service)):
    """Check if the forecasting service is healthy"""
    try:
        model_info = service.get_model_info()
        return {
            "status": "healthy",
            "model_loaded": True,
            "model_info": model_info
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Service unhealthy: {str(e)}")


@router.post("/predict", response_model=EnergyPredictionResponse)
async def predict_energy(
        request: EnergyPredictionRequest,
        service: EnergyForecastingService = Depends(get_forecasting_service)
):
    """
    Predict energy consumption for given CPU and memory utilization
    
    - **cpu_utilization_percent**: CPU utilization percentage (0-100)
    - **memory_utilization_percent**: Memory utilization percentage (0-100)
    """
    try:
        result = service.predict_single(
            cpu_utilization=request.cpu_utilization_percent,
            memory_utilization=request.memory_utilization_percent
        )
        return EnergyPredictionResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail="Prediction failed")


@router.post("/predict-timeseries")
async def predict_timeseries(
        request: TimeSeriesPredictionRequest,
        service: EnergyForecastingService = Depends(get_forecasting_service)
):
    """
    Predict energy consumption for a time series of data points
    """
    try:
        # Convert Pydantic models to dictionaries
        data_points = [point.dict() for point in request.data_points]

        results = service.predict_timeseries(data_points)
        return {
            "predictions": results,
            "total_predictions": len(results),
            "generated_at": datetime.now().isoformat()
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Time series prediction error: {e}")
        raise HTTPException(status_code=500, detail="Time series prediction failed")


@router.post("/forecast-day", response_model=DayForecastResponse)
async def forecast_next_day(
        request: ForecastRequest,
        service: EnergyForecastingService = Depends(get_forecasting_service)
):
    """
    Generate energy consumption forecast for the next day (or specified hours)
    based on recent data patterns
    
    - **recent_data**: Recent data points to analyze patterns
    - **forecast_hours**: Number of hours to forecast (default: 24)
    """
    try:
        # Convert Pydantic models to dictionaries
        recent_data = [point.dict() for point in request.recent_data]

        result = service.forecast_next_day(
            current_data=recent_data,
            forecast_hours=request.forecast_hours
        )

        return DayForecastResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Day forecast error: {e}")
        raise HTTPException(status_code=500, detail="Day forecast failed")


@router.get("/model-info")
async def get_model_info(service: EnergyForecastingService = Depends(get_forecasting_service)):
    """Get information about the loaded ML model"""
    try:
        return service.get_model_info()
    except Exception as e:
        logger.error(f"Model info error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get model info")


@router.get("/sample-prediction")
async def sample_prediction(
        cpu_utilization: float = Query(30.0, ge=0, le=100, description="Sample CPU utilization %"),
        memory_utilization: float = Query(15.0, ge=0, le=100, description="Sample memory utilization %"),
        service: EnergyForecastingService = Depends(get_forecasting_service)
):
    """
    Get a sample prediction with query parameters (useful for testing)
    """
    try:
        result = service.predict_single(
            cpu_utilization=cpu_utilization,
            memory_utilization=memory_utilization
        )

        return {
            "sample_input": {
                "cpu_utilization_percent": cpu_utilization,
                "memory_utilization_percent": memory_utilization
            },
            "prediction": result,
            "note": "This is a sample prediction. Use POST /predict for production use."
        }

    except Exception as e:
        logger.error(f"Sample prediction error: {e}")
        raise HTTPException(status_code=500, detail="Sample prediction failed")


@router.get("/metrics-with-forecast", response_model=EnhancedMetricsResponse)
async def get_metrics_with_forecast(
        node_name: Optional[str] = Query(None, description="Filter by node name"),
        limit: int = Query(100, ge=1, le=1000, description="Number of historical records to return (1-1000)"),
        hours: Optional[int] = Query(None, ge=1, le=168,
                                     description="Get metrics from last N hours (1-168), None for all data"),
        forecast_hours: int = Query(24, ge=1, le=168, description="Number of hours to forecast (1-168)"),
        db: AsyncSession = Depends(get_async_db),
        service: EnergyForecastingService = Depends(get_forecasting_service)
):
    """
    Get historical node metrics with ML predictions and extend with 24-hour forecast.
    
    This endpoint:
    1. Fetches historical metrics from the database
    2. Generates ML predictions for each historical data point
    3. Compares actual vs predicted energy consumption
    4. Extends timeline with forecasted energy consumption for next 24 hours
    
    Returns comprehensive analysis including:
    - Historical metrics with prediction accuracy
    - Future forecasts based on recent patterns
    - Model performance statistics
    """
    try:
        # Get historical metrics from database
        repository = NodePowerMetricsRepository(db)

        # Calculate time filter
        start_time = None
        if hours:
            start_time = datetime.utcnow() - timedelta(hours=hours)

        metrics = await repository.get_all(
            node_name=node_name,
            start_time=start_time,
            limit=limit
        )

        if not metrics:
            raise HTTPException(status_code=404, detail="No metrics found for the specified criteria")

        # Process historical metrics with predictions
        historical_with_predictions = []
        prediction_errors = []

        for metric in metrics:
            # Convert metric to dictionary format
            metric_dict = metric.to_dict()

            # Generate ML prediction for this data point
            try:
                prediction = service.predict_single(
                    cpu_utilization=metric_dict['cpu_utilization_percent'],
                    memory_utilization=metric_dict['memory_utilization_percent']
                )

                predicted_energy = prediction['predicted_energy_watts']
                actual_energy = metric_dict['energy_watts']

                # Calculate prediction error
                error_watts = abs(predicted_energy - actual_energy)
                error_percent = (error_watts / actual_energy) * 100 if actual_energy > 0 else 0

                prediction_errors.append(error_percent)

                # Create enhanced metric with prediction
                enhanced_metric = MetricWithPrediction(
                    # Original metric data
                    timestamp=metric_dict['timestamp'],
                    node_name=metric_dict['node_name'],
                    metric_source=metric_dict['metric_source'],
                    cpu_utilization_percent=metric_dict['cpu_utilization_percent'],
                    memory_utilization_percent=metric_dict['memory_utilization_percent'],
                    energy_watts=actual_energy,
                    cpu_package_watts=metric_dict['cpu_package_watts'],
                    memory_power_watts=metric_dict['memory_power_watts'],
                    platform_watts=metric_dict['platform_watts'],
                    created_at=metric_dict['created_at'],

                    # ML prediction data
                    predicted_energy_watts=round(predicted_energy, 4),
                    prediction_error_watts=round(error_watts, 4),
                    prediction_error_percent=round(error_percent, 2),
                    prediction_confidence=prediction['confidence']
                )

                historical_with_predictions.append(enhanced_metric)

            except Exception as pred_error:
                logger.warning(f"Failed to generate prediction for metric: {pred_error}")
                continue

        # Generate 24-hour forecast based on recent patterns
        recent_data = []
        for metric in metrics[:10]:  # Use last 10 data points for pattern analysis
            metric_dict = metric.to_dict()
            recent_data.append({
                'timestamp': metric_dict['created_at'],
                'cpu_utilization_percent': metric_dict['cpu_utilization_percent'],
                'memory_utilization_percent': metric_dict['memory_utilization_percent']
            })

        # Generate forecast
        forecast_result = service.forecast_next_day(
            current_data=recent_data,
            forecast_hours=forecast_hours
        )

        # Convert forecast to our format
        forecast_metrics = []
        base_timestamp = int(datetime.now().timestamp())

        for i, forecast_point in enumerate(forecast_result['hourly_forecasts']):
            forecast_timestamp = base_timestamp + (i * 3600)  # Add hour in seconds

            forecast_metric = ForecastMetric(
                timestamp=forecast_timestamp,
                timestamp_iso=forecast_point['timestamp'],
                hour_offset=forecast_point['hour'],
                forecasted_cpu_utilization_percent=forecast_point['forecasted_cpu_utilization'],
                forecasted_memory_utilization_percent=forecast_point['forecasted_memory_utilization'],
                forecasted_energy_watts=forecast_point['forecasted_energy_watts'],
                confidence=forecast_point['confidence'],
                is_forecast=True
            )

            forecast_metrics.append(forecast_metric)

        # Calculate prediction accuracy statistics
        if prediction_errors:
            avg_error = sum(prediction_errors) / len(prediction_errors)
            max_error = max(prediction_errors)
            min_error = min(prediction_errors)
            accuracy = max(0, 100 - avg_error)  # Simple accuracy metric
        else:
            avg_error = max_error = min_error = accuracy = 0

        prediction_accuracy = {
            "average_error_percent": round(avg_error, 2),
            "max_error_percent": round(max_error, 2),
            "min_error_percent": round(min_error, 2),
            "accuracy_percent": round(accuracy, 2),
            "total_predictions": len(prediction_errors)
        }

        # Create comprehensive response
        response = EnhancedMetricsResponse(
            status="success",
            filters={
                "node_name": node_name,
                "limit": limit,
                "hours": hours,
                "forecast_hours": forecast_hours
            },
            historical_metrics=historical_with_predictions,
            historical_count=len(historical_with_predictions),
            forecast_metrics=forecast_metrics,
            forecast_count=len(forecast_metrics),
            prediction_accuracy=prediction_accuracy,
            forecast_summary=forecast_result['summary'],
            model_info=service.get_model_info(),
            generated_at=datetime.now().isoformat()
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Enhanced metrics error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate enhanced metrics: {str(e)}")
