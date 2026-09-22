"""
Consolidated API endpoints for both node and container power metrics.
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_async_db
from app.repositories.node_power_metrics import NodePowerMetricsRepository
from app.services.prometheus_metrics_service import PrometheusMetricsService
from app.services.prometheus_metrics_service_v2 import PrometheusMetricsServiceV2
from app.services.energy_forecasting_service import EnergyForecastingService
from app.utils.constants import PROMETHEUS_METRICS_URL
import logging

router = APIRouter(prefix="/api/metrics", tags=["Prometheus Metrics"])


# Helper function for energy forecasting
def get_forecasting_service():
    """Get the singleton forecasting service instance"""
    try:
        return EnergyForecastingService.get_instance()
    except Exception as e:
        logging.warning(f"Failed to get forecasting service: {e}")
        return None


# =============================================================================
# NODE METRICS ENDPOINTS
# =============================================================================

@router.get("/nodes/")
async def get_node_metrics(
        node_name: Optional[str] = Query(None, description="Filter by node name"),
        limit: int = Query(1000, ge=1, le=10000, description="Number of records to return (1-10000)"),
        hours: Optional[int] = Query(None, ge=1, le=168, description="Get metrics from last N hours (1-168)"),
        include_predictions: bool = Query(False,
                                          description="Include ML energy predictions (predicted_energy_watts, prediction_confidence)"),
        db: AsyncSession = Depends(get_async_db)
):
    """
    Get node power metrics with optional filtering.
    
    Returns unified metrics including:
    - Power consumption from Kepler (CPU, memory, platform watts)
    - Resource utilization from cAdvisor (CPU%, memory%)
    - Memory usage in bytes
    - Optionally ML predictions (predicted_energy_watts, prediction_confidence) when include_predictions=true
    - Optionally 48-hour energy forecast (energy_forecast) when include_predictions=true
    """
    try:
        repository = NodePowerMetricsRepository(db)

        # Calculate time filter if hours specified
        start_time = None
        if hours:
            start_time = datetime.utcnow() - timedelta(hours=hours)

        metrics = await repository.get_all(
            node_name=node_name,
            start_time=start_time,
            limit=limit
        )

        # Process metrics and optionally add ML predictions
        energy_forecast = None
        
        if include_predictions:
            # Add ML predictions to each metric
            forecasting_service = get_forecasting_service()
            enhanced_metrics = []
            logging.info("starting to enhance metrics with predictions")
            
            for metric in metrics:
                metric_dict = metric.to_dict()

                if forecasting_service:
                    try:
                        prediction = forecasting_service.predict_single(
                            cpu_utilization=metric_dict['cpu_utilization_percent'],
                            memory_utilization=metric_dict['memory_utilization_percent']
                        )
                        metric_dict['predicted_energy_watts'] = round(prediction['predicted_energy_watts'], 4)
                        metric_dict['prediction_confidence'] = prediction['confidence']
                    except Exception as pred_error:
                        logging.warning(f"Failed to generate prediction for metric: {pred_error}")
                        metric_dict['predicted_energy_watts'] = None
                        metric_dict['prediction_confidence'] = "unavailable"
                else:
                    metric_dict['predicted_energy_watts'] = None
                    metric_dict['prediction_confidence'] = "unavailable"

                enhanced_metrics.append(metric_dict)
            
            # Generate 48-hour energy forecast based on recent patterns
            if forecasting_service and metrics:
                try:
                    logging.info("generating 48-hour energy forecast")
                    # Use recent metrics for pattern analysis (last 10 data points)
                    recent_data = []
                    for metric in metrics[:10]:
                        metric_dict = metric.to_dict()
                        recent_data.append({
                            'timestamp': metric_dict['created_at'],
                            'cpu_utilization_percent': metric_dict['cpu_utilization_percent'],
                            'memory_utilization_percent': metric_dict['memory_utilization_percent']
                        })
                    
                    # Generate 48-hour forecast
                    forecast_result = forecasting_service.forecast_next_day(
                        current_data=recent_data,
                        forecast_hours=48
                    )
                    
                    # Format forecast for response
                    base_timestamp = int(datetime.now().timestamp())
                    forecast_points = []
                    
                    for i, forecast_point in enumerate(forecast_result['hourly_forecasts']):
                        forecast_timestamp = base_timestamp + (i * 3600)  # Add hour in seconds
                        
                        forecast_points.append({
                            'hour_offset': forecast_point['hour'],
                            'timestamp': forecast_timestamp,
                            'timestamp_iso': forecast_point['timestamp'],
                            'forecasted_cpu_utilization_percent': forecast_point['forecasted_cpu_utilization'],
                            'forecasted_memory_utilization_percent': forecast_point['forecasted_memory_utilization'],
                            'forecasted_energy_watts': forecast_point['forecasted_energy_watts'],
                            'confidence': forecast_point['confidence']
                        })
                    
                    energy_forecast = {
                        'forecast_hours': 48,
                        'forecast_points': forecast_points,
                        'summary': {
                            'total_forecasted_energy_kwh': forecast_result['summary']['total_forecasted_energy_kwh'],
                            'average_hourly_energy_watts': forecast_result['summary']['average_hourly_energy_watts'],
                            'peak_hourly_energy_watts': forecast_result['summary']['peak_hourly_energy_watts'],
                            'min_hourly_energy_watts': forecast_result['summary']['min_hourly_energy_watts']
                        },
                        'generated_at': datetime.now().isoformat()
                    }
                    
                except Exception as forecast_error:
                    logging.warning(f"Failed to generate 48-hour energy forecast: {forecast_error}")
                    energy_forecast = None
                    
        else:
            # No predictions requested, just return original data
            enhanced_metrics = [metric.to_dict() for metric in metrics]
        logging.info("finished enhancing metrics with predictions")
        
        response = {
            "status": "success",
            "filters": {
                "node_name": node_name,
                "limit": limit,
                "hours": hours,
                "include_predictions": include_predictions
            },
            "metrics": enhanced_metrics,
            "count": len(enhanced_metrics)
        }
        
        # Add energy forecast if predictions were enabled and forecast was generated
        if include_predictions and energy_forecast:
            response["energy_forecast"] = energy_forecast
        
        return response
    except Exception as e:
        logging.error(f"Error retrieving node metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve node metrics")


# =============================================================================
# PROMETHEUS METRICS ENDPOINTS
# =============================================================================


@router.get("/prometheus/container-metrics")
async def get_container_metrics():
    """
    Get comprehensive container metrics from Prometheus including CPU and memory utilization.
    
    Returns unified metrics with:
    - CPU utilization %, total CPUs assigned, machine CPU cores
    - Memory utilization % and bytes/GB, memory assigned, total machine memory
    
    Uses optimized single call to fetch all container-related metrics.
    """
    try:
        prometheus_service = PrometheusMetricsService()

        # Fetch all metrics in a single optimized call
        metric_responses = await prometheus_service.fetch_all_container_metrics()

        # Parse all responses
        cpu_metrics = prometheus_service.parse_prometheus_response(metric_responses.get("cpu_utilization", {}))
        quota_metrics = prometheus_service.parse_prometheus_response(metric_responses.get("cpu_quota", {}))
        cores_metrics = prometheus_service.parse_prometheus_response(metric_responses.get("machine_cpu_cores", {}))
        memory_metrics = prometheus_service.parse_prometheus_response(metric_responses.get("memory_utilization", {}))
        memory_limit_metrics = prometheus_service.parse_prometheus_response(metric_responses.get("memory_limit", {}))
        machine_memory_metrics = prometheus_service.parse_prometheus_response(
            metric_responses.get("machine_memory_total", {}))

        # Get all unique instances
        all_instances = set()
        all_instances.update(cpu_metrics.keys())
        all_instances.update(quota_metrics.keys())
        all_instances.update(cores_metrics.keys())
        all_instances.update(memory_metrics.keys())
        all_instances.update(memory_limit_metrics.keys())
        all_instances.update(machine_memory_metrics.keys())

        return {
            "status": "success",
            "source": "prometheus-container-metrics",
            "prometheus_url": PROMETHEUS_METRICS_URL,
            "queries": {
                "cpu_utilization": "sum(rate(container_cpu_usage_seconds_total{id=\"/\"}[5m])) by (instance) * 100",
                "cpu_quota": "container_spec_cpu_quota{id=\"/\"} / container_spec_cpu_period{id=\"/\"}",
                "machine_cpu_cores": "machine_cpu_cores",
                "memory_utilization": "(sum(container_memory_usage_bytes{id=\"/\"}) by (instance) / sum(container_spec_memory_limit_bytes{id=\"/\"}) by (instance)) * 100",
                "memory_limit": "sum(container_spec_memory_limit_bytes{id=\"/\"}) by (instance)",
                "machine_memory_total": "machine_memory_bytes"
            },
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": [
                {
                    "instance": instance,
                    # CPU metrics
                    "cpu_utilization_percent": cpu_metrics.get(instance, 0.0),
                    "total_cpu_assigned": quota_metrics.get(instance, 0.0),
                    "machine_cpu_cores": cores_metrics.get(instance, 0.0),
                    # Memory metrics
                    "memory_utilization_percent": memory_metrics.get(instance, 0.0),
                    "memory_utilization_bytes": round(
                        (memory_metrics.get(instance, 0.0) / 100) * memory_limit_metrics.get(instance, 0.0)),
                    "memory_utilization_gb": round(
                        ((memory_metrics.get(instance, 0.0) / 100) * memory_limit_metrics.get(instance, 0.0)) / (
                                    1024 ** 3), 2),
                    "memory_assigned_bytes": memory_limit_metrics.get(instance, 0.0),
                    "memory_assigned_gb": round(memory_limit_metrics.get(instance, 0.0) / (1024 ** 3), 2),
                    "machine_memory_total_bytes": machine_memory_metrics.get(instance, 0.0),
                    "machine_memory_total_gb": round(machine_memory_metrics.get(instance, 0.0) / (1024 ** 3), 2)
                }
                for instance in all_instances
            ],
            "count": len(all_instances)
        }
    except Exception as e:
        logging.error(f"Error fetching container metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch container metrics: {str(e)}")


@router.get("/prometheus/metrics-v2/latest")
async def get_latest_metrics_v2(
    hours_back: int = Query(1, ge=1, le=24, description="Hours of data to fetch from Prometheus (1-24)")
):
    """
    Get latest node energy metrics using PrometheusMetricsServiceV2.

    This endpoint fetches data directly from Prometheus using range queries for the last N hours,
    then returns the latest values. Uses the same queries as the original service but with
    time series data from Prometheus REST API.

    Returns unified metrics with:
    - CPU utilization %, total CPUs assigned, machine CPU cores
    - Memory utilization % and bytes, memory assigned, total machine memory
    - Total energy consumption (watts) - calculated from Kepler components (package + memory + platform + uncore)
    """
    try:
        prometheus_service_v2 = PrometheusMetricsServiceV2()

        # Get latest metrics using range queries
        metrics = await prometheus_service_v2.scrape_and_transform_range(hours_back=hours_back)

        if not metrics:
            return {
                "status": "success",
                "source": "prometheus-metrics-service-v2",
                "data_source": "prometheus-rest-api-range-queries",
                "hours_back": hours_back,
                "timestamp": datetime.utcnow().isoformat(),
                "metrics": [],
                "count": 0,
                "message": "No metrics found for the specified time range"
            }

        # Convert NodeMetricsCreate objects to dictionaries
        metrics_data = []
        for metric in metrics:
            metrics_data.append({
                "timestamp": metric.timestamp,
                "node_name": metric.node_name,
                "metric_source": metric.metric_source,

                # CPU metrics
                "cpu_utilization_percent": metric.cpu_utilization_percent,
                "total_cpu_assigned": metric.total_cpu_assigned,
                "machine_cpu_cores": metric.machine_cpu_cores,

                # Memory metrics
                "memory_utilization_percent": metric.memory_utilization_percent,
                "memory_utilization_bytes": metric.memory_utilization_bytes,
                "memory_assigned_bytes": metric.memory_assigned_bytes,
                "machine_memory_total_bytes": metric.machine_memory_total_bytes,

                # Total energy consumption (Kepler) - calculated from package + memory + platform + uncore watts
                "energy_watts": metric.energy_watts
            })

        return {
            "status": "success",
            "source": "prometheus-metrics-service-v2",
            "data_source": "prometheus-rest-api-range-queries",
            "hours_back": hours_back,
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": metrics_data,
            "count": len(metrics_data)
        }

    except Exception as e:
        logging.error(f"Error fetching metrics with PrometheusMetricsServiceV2: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch metrics from Prometheus: {str(e)}")


@router.get("/prometheus/metrics-v2/timeseries")
async def get_timeseries_metrics_v2(
    hours_back: int = Query(1, ge=1, le=168, description="Hours of historical data to fetch (1-168)"),
    node_name: Optional[str] = Query(None, description="Filter by specific node name")
):
    """
    Get total energy time series data from Prometheus using PrometheusMetricsServiceV2.

    Returns complete historical time series data for the specified time range,
    with calculated total energy consumption per timestamp. Useful for charting and trend analysis.

    Returns:
    - Total energy time series (calculated from package + memory + platform + uncore watts)
    - CPU and memory utilization time series for context
    - Each data point includes timestamp and value
    - Data covers the specified number of hours back
    """
    try:
        prometheus_service_v2 = PrometheusMetricsServiceV2()

        # Get full time series data
        raw_time_series_data = await prometheus_service_v2.get_time_series_data(hours_back=hours_back)

        # Get all available nodes before filtering and clean them
        all_raw_nodes = set()
        for metric_data in raw_time_series_data.values():
            all_raw_nodes.update(metric_data.keys())

        # Filter out control-plane and IP addresses, keep only worker node hostnames
        all_available_nodes = []
        for node in all_raw_nodes:
            # Skip IP addresses (contain : or start with numbers)
            if ':' in node or node.replace('.', '').replace('-', '').isdigit():
                continue
            # Skip control-plane node
            if 'cp-' in node or 'control-plane' in node:
                continue
            # Only include worker nodes (should contain 'wk-' or be clean hostnames)
            if 'wk-' in node or (not node.startswith('10.') and not node.startswith('172.') and not node.startswith('192.')):
                all_available_nodes.append(node)

        all_available_nodes = sorted(list(set(all_available_nodes)))

        # Apply node filtering to the results if node_name is specified
        if node_name:
            filtered_time_series_data = {}
            for metric_name, metric_data in raw_time_series_data.items():
                # Filter to only include the specified node
                if node_name in metric_data:
                    filtered_time_series_data[metric_name] = {node_name: metric_data[node_name]}
                else:
                    filtered_time_series_data[metric_name] = {}
            raw_time_series_data = filtered_time_series_data

        # Check if we have any meaningful data instead of completely empty
        has_meaningful_data = False
        for metric_data in raw_time_series_data.values():
            if metric_data and any(len(time_series) > 0 for time_series in metric_data.values()):
                has_meaningful_data = True
                break

        if not has_meaningful_data:
            # Try to get available nodes from a shorter time range (last 1 hour) as fallback
            try:
                fallback_time_series_data = await prometheus_service_v2.get_time_series_data(hours_back=1)
                fallback_raw_nodes = set()
                for metric_data in fallback_time_series_data.values():
                    fallback_raw_nodes.update(metric_data.keys())

                # Filter out control-plane and IP addresses, keep only worker node hostnames
                fallback_available_nodes = []
                for node in fallback_raw_nodes:
                    # Skip IP addresses (contain : or start with numbers)
                    if ':' in node or node.replace('.', '').replace('-', '').isdigit():
                        continue
                    # Skip control-plane node
                    if 'cp-' in node or 'control-plane' in node:
                        continue
                    # Only include worker nodes (should contain 'wk-' or be clean hostnames)
                    if 'wk-' in node or (not node.startswith('10.') and not node.startswith('172.') and not node.startswith('192.')):
                        fallback_available_nodes.append(node)

                fallback_available_nodes = sorted(list(set(fallback_available_nodes)))

                # Use fallback nodes if we found any, otherwise use the original empty list
                final_available_nodes = fallback_available_nodes if fallback_available_nodes else all_available_nodes

                # Determine the actual time range that has data
                actual_time_range = "1 hour" if fallback_available_nodes else f"{hours_back} hours"

            except Exception as fallback_error:
                logging.warning(f"Failed to get fallback node list: {fallback_error}")
                final_available_nodes = all_available_nodes
                actual_time_range = f"{hours_back} hours"

            return {
                "status": "success",
                "source": "prometheus-metrics-service-v2-timeseries",
                "data_source": "prometheus-rest-api-range-queries",
                "hours_back": hours_back,
                "node_filter": node_name,
                "timestamp": datetime.utcnow().isoformat(),
                "time_series": {},
                "available_nodes": final_available_nodes,
                "actual_data_range": actual_time_range,
                "message": f"No time series data found for the last {hours_back} hour(s). Available nodes shown are from the last {actual_time_range} of available data."
            }

        # Calculate total energy time series for each node
        # Total = Package + Memory + Platform + Uncore (NOT including Core)
        processed_time_series = {}

        # Get ALL unique nodes from all metrics first
        all_unique_nodes = set()
        for metric_data in raw_time_series_data.values():
            all_unique_nodes.update(metric_data.keys())

        # Filter to only nodes that have energy data
        energy_nodes = set()
        for node in all_unique_nodes:
            # Check if this node has any energy metrics
            has_energy_data = False
            for energy_metric in ["kepler_cpu_package_watts", "kepler_memory_watts", "kepler_platform_watts", "kepler_uncore_watts"]:
                if energy_metric in raw_time_series_data and node in raw_time_series_data[energy_metric]:
                    has_energy_data = True
                    break

            if has_energy_data:
                energy_nodes.add(node)

        for node in energy_nodes:
            # Skip if filtering by node_name and this isn't the one
            if node_name and node != node_name:
                continue

            # Get time series for each energy component
            package_series = raw_time_series_data.get("kepler_cpu_package_watts", {}).get(node, [])
            memory_series = raw_time_series_data.get("kepler_memory_watts", {}).get(node, [])
            platform_series = raw_time_series_data.get("kepler_platform_watts", {}).get(node, [])
            uncore_series = raw_time_series_data.get("kepler_uncore_watts", {}).get(node, [])

            # Create a dictionary of timestamps to values for easier lookup
            package_dict = {point["timestamp"]: point["value"] for point in package_series}
            memory_dict = {point["timestamp"]: point["value"] for point in memory_series}
            platform_dict = {point["timestamp"]: point["value"] for point in platform_series}
            uncore_dict = {point["timestamp"]: point["value"] for point in uncore_series}

            # Get all unique timestamps
            all_timestamps = set()
            all_timestamps.update(package_dict.keys())
            all_timestamps.update(memory_dict.keys())
            all_timestamps.update(platform_dict.keys())
            all_timestamps.update(uncore_dict.keys())

            # Calculate total energy for each timestamp
            total_energy_series = []
            for timestamp in sorted(all_timestamps):
                components = [
                    package_dict.get(timestamp),
                    memory_dict.get(timestamp),
                    platform_dict.get(timestamp),
                    uncore_dict.get(timestamp)
                ]

                # Sum components that are not None
                total_watts = sum(w for w in components if w is not None) if any(w is not None for w in components) else None

                if total_watts is not None:
                    total_energy_series.append({
                        "timestamp": timestamp,
                        "value": round(total_watts, 4)
                    })

            if total_energy_series:
                processed_time_series[node] = total_energy_series

        # Restructure to match expected format
        time_series_data = {
            "total_energy_watts": processed_time_series
        }

        # Include CPU and memory utilization (node names are already normalized by get_time_series_data)
        if "cpu_utilization" in raw_time_series_data:
            cpu_data = raw_time_series_data["cpu_utilization"]
            if node_name:
                # Filter by specific node if requested
                time_series_data["cpu_utilization"] = {node_name: cpu_data.get(node_name, [])} if node_name in cpu_data else {}
            else:
                # Include all nodes
                time_series_data["cpu_utilization"] = cpu_data

        if "memory_utilization" in raw_time_series_data:
            memory_data = raw_time_series_data["memory_utilization"]
            if node_name:
                # Filter by specific node if requested
                time_series_data["memory_utilization"] = {node_name: memory_data.get(node_name, [])} if node_name in memory_data else {}
            else:
                # Include all nodes
                time_series_data["memory_utilization"] = memory_data

        # Calculate summary statistics and actual data time range
        total_data_points = sum(
            len(node_data)
            for metric_data in time_series_data.values()
            for node_data in metric_data.values()
        )

        unique_nodes = set()
        for metric_data in time_series_data.values():
            unique_nodes.update(metric_data.keys())

        # Find actual time range of returned data
        all_timestamps = []
        for metric_data in time_series_data.values():
            for node_data in metric_data.values():
                for point in node_data:
                    if isinstance(point, dict) and "timestamp" in point:
                        all_timestamps.append(point["timestamp"])

        actual_time_range = {}
        if all_timestamps:
            actual_time_range = {
                "earliest_timestamp": min(all_timestamps),
                "latest_timestamp": max(all_timestamps),
                "actual_hours_covered": round((max(all_timestamps) - min(all_timestamps)) / 3600, 2)
            }

        return {
            "status": "success",
            "source": "prometheus-metrics-service-v2-timeseries",
            "data_source": "prometheus-rest-api-range-queries",
            "hours_back": hours_back,
            "node_filter": node_name,
            "timestamp": datetime.utcnow().isoformat(),
            "time_series": time_series_data,
            "summary": {
                "total_data_points": total_data_points,
                "unique_nodes": list(unique_nodes),
                "node_count": len(unique_nodes),
                "metric_types": list(time_series_data.keys()),
                "metric_count": len(time_series_data),
                "actual_time_range": actual_time_range
            },
            "available_nodes": all_available_nodes
        }

    except Exception as e:
        logging.error(f"Error fetching time series data with PrometheusMetricsServiceV2: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch time series data from Prometheus: {str(e)}")
