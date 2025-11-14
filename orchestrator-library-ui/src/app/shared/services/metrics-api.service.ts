import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, map } from 'rxjs';
import { MetricsApiResponse, NodeMetric, ChartDataPoint, EnergyForecast, EnergyForecastPoint, PrometheusMetricsResponse } from '../interfaces/metrics-api.interface';

@Injectable({
  providedIn: 'root'
})
export class MetricsApiService {
  private readonly baseUrl = 'http://0.0.0.0:8086/api/metrics/nodes/';
  private readonly prometheusUrl = 'http://0.0.0.0:8086/api/metrics/prometheus/metrics-v2/timeseries';

  constructor(private http: HttpClient) { }

  /**
   * Fetch metrics from the API
   * @param limit - Number of metrics to fetch (default: 100)
   * @param nodeName - Optional node name filter
   * @param hours - Optional hours filter
   * @param includePredictions - Optional include predictions flag (default: true)
   * @returns Observable<MetricsApiResponse>
   */
  getMetrics(limit = 10000, nodeName?: string, hours?: number, includePredictions = true): Observable<MetricsApiResponse> {
    let params = new HttpParams().set('limit', limit.toString());
    
    if (nodeName) {
      params = params.set('node_name', nodeName);
    }
    
    if (hours) {
      params = params.set('hours', hours.toString());
    }

    params = params.set('include_predictions', includePredictions.toString());

    return this.http.get<MetricsApiResponse>(this.baseUrl, { params });
  }

  /**
   * Transform metrics data for CPU watts chart
   * @param metrics - Array of NodeMetric
   * @returns Array of chart data points
   */
  transformCpuWattsData(metrics: NodeMetric[]): ChartDataPoint[] {
    return metrics.map(metric => ({
      timestamp: new Date(metric.timestamp).getTime(),
      value: metric.cpu_core_watts,
      nodeName: metric.node_name
    })).sort((a, b) => a.timestamp - b.timestamp);
  }

  /**
   * Transform metrics data for CPU utilization chart
   * @param metrics - Array of NodeMetric
   * @returns Array of chart data points
   */
  transformCpuUtilizationData(metrics: NodeMetric[]): ChartDataPoint[] {
    return metrics.map(metric => ({
      timestamp: new Date(metric.timestamp).getTime(),
      value: metric.cpu_utilization_percent,
      nodeName: metric.node_name
    })).sort((a, b) => a.timestamp - b.timestamp);
  }

  /**
   * Transform metrics data for memory utilization chart (percentage)
   * @param metrics - Array of NodeMetric
   * @returns Array of chart data points
   */
  transformMemoryUtilizationData(metrics: NodeMetric[]): ChartDataPoint[] {
    return metrics.map(metric => ({
      timestamp: new Date(metric.timestamp).getTime(),
      value: metric.memory_utilization_percent,
      nodeName: metric.node_name
    })).sort((a, b) => a.timestamp - b.timestamp);
  }

  /**
   * Get CPU watts data formatted for charts
   * @param limit - Number of records to fetch
   * @returns Observable with chart-formatted data
   */
  getCpuWattsChartData(limit = 100): Observable<{ [nodeName: string]: [number, number][] }> {
    return this.getMetrics(limit).pipe(
      map(response => {
        const chartData = this.transformCpuWattsData(response.metrics);
        return this.groupDataByNode(chartData);
      })
    );
  }

  /**
   * Get CPU utilization data formatted for charts
   * @param limit - Number of records to fetch
   * @returns Observable with chart-formatted data
   */
  getCpuUtilizationChartData(limit = 100): Observable<{ [nodeName: string]: [number, number][] }> {
    return this.getMetrics(limit).pipe(
      map(response => {
        const chartData = this.transformCpuUtilizationData(response.metrics);
        return this.groupDataByNode(chartData);
      })
    );
  }

  /**
   * Get memory utilization data formatted for charts
   * @param limit - Number of records to fetch
   * @returns Observable with chart-formatted data
   */
  getMemoryUtilizationChartData(limit = 100): Observable<{ [nodeName: string]: [number, number][] }> {
    return this.getMetrics(limit).pipe(
      map(response => {
        const chartData = this.transformMemoryUtilizationData(response.metrics);
        return this.groupDataByNode(chartData);
      })
    );
  }

  /**
   * Transform metrics data for energy watts chart
   * @param metrics - Array of NodeMetric
   * @returns Array of chart data points
   */
  transformEnergyWattsData(metrics: NodeMetric[]): ChartDataPoint[] {
    return metrics.map(metric => ({
      timestamp: new Date(metric.timestamp).getTime(),
      value: metric.energy_watts,
      nodeName: metric.node_name
    })).sort((a, b) => a.timestamp - b.timestamp);
  }

  /**
   * Transform metrics data for predicted energy watts chart
   * @param metrics - Array of NodeMetric
   * @returns Array of chart data points
   */
  transformPredictedEnergyWattsData(metrics: NodeMetric[]): ChartDataPoint[] {
    return metrics.map(metric => ({
      timestamp: new Date(metric.timestamp).getTime(),
      value: metric.predicted_energy_watts,
      nodeName: metric.node_name
    })).sort((a, b) => a.timestamp - b.timestamp);
  }

  /**
   * Get energy watts data formatted for charts
   * @param limit - Number of records to fetch
   * @returns Observable with chart-formatted data
   */
  getEnergyWattsChartData(limit = 100): Observable<{ [nodeName: string]: [number, number][] }> {
    return this.getMetrics(limit).pipe(
      map(response => {
        const chartData = this.transformEnergyWattsData(response.metrics);
        return this.groupDataByNode(chartData);
      })
    );
  }

  /**
   * Group chart data points by node name
   * @param data - Array of ChartDataPoint
   * @returns Object with node names as keys and chart data arrays as values
   */
  groupDataByNode(data: ChartDataPoint[]): { [nodeName: string]: [number, number][] } {
    const grouped: { [nodeName: string]: [number, number][] } = {};
    
    data.forEach(point => {
      if (!grouped[point.nodeName]) {
        grouped[point.nodeName] = [];
      }
      grouped[point.nodeName].push([point.timestamp, point.value]);
    });

    return grouped;
  }

  /**
   * Get 24hr energy forecast data
   * @param nodeName - Optional node name filter
   * @returns Observable with energy forecast
   */
  getEnergyForecast(nodeName?: string): Observable<EnergyForecast | null> {
    return this.getMetrics(100, nodeName, undefined, true).pipe(
      map(response => response.energy_forecast || null)
    );
  }

  /**
   * Transform energy forecast data for charts
   * @param forecast - EnergyForecast object
   * @returns Array of chart data points for energy forecast
   */
  transformEnergyForecastData(forecast: EnergyForecast): [number, number][] {
    return forecast.forecast_points.map(point => [
      point.timestamp * 1000, // Convert to milliseconds
      point.forecasted_energy_watts
    ] as [number, number]).sort((a, b) => a[0] - b[0]);
  }

  /**
   * Transform energy forecast data for CPU utilization chart
   * @param forecast - EnergyForecast object
   * @returns Array of chart data points for CPU forecast
   */
  transformCpuForecastData(forecast: EnergyForecast): [number, number][] {
    return forecast.forecast_points.map(point => [
      point.timestamp * 1000, // Convert to milliseconds
      point.forecasted_cpu_utilization_percent
    ] as [number, number]).sort((a, b) => a[0] - b[0]);
  }

  /**
   * Transform energy forecast data for memory utilization chart
   * @param forecast - EnergyForecast object
   * @returns Array of chart data points for memory forecast
   */
  transformMemoryForecastData(forecast: EnergyForecast): [number, number][] {
    return forecast.forecast_points.map(point => [
      point.timestamp * 1000, // Convert to milliseconds
      point.forecasted_memory_utilization_percent
    ] as [number, number]).sort((a, b) => a[0] - b[0]);
  }

  /**
   * Get formatted forecast data for energy chart
   * @param nodeName - Optional node name filter
   * @returns Observable with chart-formatted forecast data
   */
  getEnergyForecastChartData(nodeName?: string): Observable<[number, number][]> {
    return this.getEnergyForecast(nodeName).pipe(
      map(forecast => forecast ? this.transformEnergyForecastData(forecast) : [])
    );
  }

  /**
   * Fetch Prometheus metrics timeseries data
   * @param hoursBack - Number of hours back to fetch data (default: 1)
   * @param nodeFilter - Optional node name filter
   * @returns Observable<PrometheusMetricsResponse>
   */
  getPrometheusMetrics(hoursBack = 1, nodeFilter?: string): Observable<PrometheusMetricsResponse> {
    let params = new HttpParams().set('hours_back', hoursBack.toString());

    if (nodeFilter) {
      params = params.set('node_name', nodeFilter);
    }

    const fullUrl = `${this.prometheusUrl}?${params.toString()}`;
    console.log('🌐 Making HTTP GET request to:', fullUrl);

    return this.http.get<PrometheusMetricsResponse>(this.prometheusUrl, { params });
  }

  /**
   * Transform Prometheus CPU utilization data for charts
   * @param cpuData - CPU utilization time series data
   * @returns Object with node names as keys and chart data arrays as values
   */
  transformPrometheusCpuData(cpuData: { [nodeName: string]: { timestamp: number; value: number }[] }): { [nodeName: string]: [number, number][] } {
    const result: { [nodeName: string]: [number, number][] } = {};

    Object.keys(cpuData).forEach(nodeName => {
      result[nodeName] = cpuData[nodeName].map(point => [
        point.timestamp * 1000, // Convert to milliseconds
        point.value
      ] as [number, number]).sort((a, b) => a[0] - b[0]);
    });

    return result;
  }

  /**
   * Transform Prometheus memory utilization data for charts
   * @param memoryData - Memory utilization time series data
   * @returns Object with node names as keys and chart data arrays as values
   */
  transformPrometheusMemoryData(memoryData: { [nodeName: string]: { timestamp: number; value: number }[] }): { [nodeName: string]: [number, number][] } {
    const result: { [nodeName: string]: [number, number][] } = {};

    Object.keys(memoryData).forEach(nodeName => {
      result[nodeName] = memoryData[nodeName].map(point => [
        point.timestamp * 1000, // Convert to milliseconds
        point.value
      ] as [number, number]).sort((a, b) => a[0] - b[0]);
    });

    return result;
  }

  /**
   * Transform Prometheus total energy watts data for charts
   * @param energyData - Total energy watts time series data
   * @returns Object with node names as keys and chart data arrays as values
   */
  transformPrometheusTotalEnergyData(energyData: { [nodeName: string]: { timestamp: number; value: number }[] }): { [nodeName: string]: [number, number][] } {
    const result: { [nodeName: string]: [number, number][] } = {};

    Object.keys(energyData).forEach(nodeName => {
      result[nodeName] = energyData[nodeName].map(point => [
        point.timestamp * 1000, // Convert to milliseconds
        point.value
      ] as [number, number]).sort((a, b) => a[0] - b[0]);
    });

    return result;
  }

  /**
   * Get CPU utilization data from Prometheus formatted for charts
   * @param hoursBack - Number of hours back to fetch data (default: 1)
   * @param nodeFilter - Optional node name filter
   * @returns Observable with chart-formatted CPU data
   */
  getPrometheusCpuUtilizationChartData(hoursBack = 1, nodeFilter?: string): Observable<{ [nodeName: string]: [number, number][] }> {
    return this.getPrometheusMetrics(hoursBack, nodeFilter).pipe(
      map(response => this.transformPrometheusCpuData(response.time_series.cpu_utilization))
    );
  }

  /**
   * Get memory utilization data from Prometheus formatted for charts
   * @param hoursBack - Number of hours back to fetch data (default: 1)
   * @param nodeFilter - Optional node name filter
   * @returns Observable with chart-formatted memory data
   */
  getPrometheusMemoryUtilizationChartData(hoursBack = 1, nodeFilter?: string): Observable<{ [nodeName: string]: [number, number][] }> {
    return this.getPrometheusMetrics(hoursBack, nodeFilter).pipe(
      map(response => this.transformPrometheusMemoryData(response.time_series.memory_utilization))
    );
  }
}
