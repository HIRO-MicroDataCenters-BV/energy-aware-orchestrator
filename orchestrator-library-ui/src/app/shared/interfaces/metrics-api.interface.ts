export interface NodeMetric {
  timestamp: string;
  node_name: string;
  metric_source: string;
  cpu_core_watts: number;
  cpu_package_watts: number;
  memory_power_watts: number;
  platform_watts: number;
  energy_watts: number; // this is total watt for node
  cpu_utilization_percent: number;
  memory_utilization_percent: number;
  memory_usage_bytes: number;
  predicted_energy_watts: number;
  prediction_confidence: string;
}

export interface EnergyForecastPoint {
  hour_offset: number;
  timestamp: number;
  timestamp_iso: string;
  forecasted_cpu_utilization_percent: number;
  forecasted_memory_utilization_percent: number;
  forecasted_energy_watts: number;
  confidence: 'high' | 'medium' | 'low';
}

export interface EnergyForecast {
  forecast_hours: number;
  forecast_points: EnergyForecastPoint[];
}

export interface MetricsApiResponse {
  status: string;
  filters: {
    node_name: string | null;
    limit: number;
    hours: number | null;
  };
  metrics: NodeMetric[];
  energy_forecast?: EnergyForecast;
}

export interface ChartDataPoint {
  timestamp: number;
  value: number;
  nodeName: string;
}

export interface TimeSeriesDataPoint {
  timestamp: number;
  value: number;
}

export interface TimeSeriesData {
  [nodeName: string]: TimeSeriesDataPoint[];
}

export interface PrometheusMetricsResponse {
  status: string;
  source: string;
  data_source: string;
  hours_back: number;
  node_filter: string | null;
  timestamp: string;
  available_nodes: string[];
  time_series: {
    cpu_utilization: TimeSeriesData;
    cpu_quota: TimeSeriesData;
    memory_utilization: TimeSeriesData;
    memory_limit: TimeSeriesData;
    machine_cpu_cores: TimeSeriesData;
    machine_memory_total: TimeSeriesData;
    total_energy_watts: TimeSeriesData;
  };
}
