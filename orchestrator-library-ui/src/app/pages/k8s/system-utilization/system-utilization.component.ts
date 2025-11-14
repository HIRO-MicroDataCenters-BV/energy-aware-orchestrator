import { Component, OnInit, OnDestroy, Inject } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { PLATFORM_ID } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HighchartsChartComponent } from 'highcharts-angular';
import * as Highcharts from 'highcharts';
import { Subject, takeUntil, interval } from 'rxjs';
import { MetricsApiService } from '../../../shared/services/metrics-api.service';
import { HlmSidebarService } from '../../../../../libs/ui/ui-sidebar-helm/src/lib/hlm-sidebar.service';
import { EnergyAvailabilityHeatmapComponent } from '../../../components/energy-availability-heatmap/energy-availability-heatmap.component';
import { ChartConfigurations } from '../../../shared/utils/chart-configurations.util';
import { EnergyAvailabilityGeneratorService } from '../../../shared/services/energy-availability-generator.service';
import { BrnSelectModule } from '@spartan-ng/brain/select';
import { HlmSelectModule } from '@spartan-ng/ui-select-helm';

@Component({
  selector: 'app-system-utilization',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    HighchartsChartComponent,
    EnergyAvailabilityHeatmapComponent,
    BrnSelectModule,
    HlmSelectModule,
  ],
  templateUrl: './system-utilization.component.html',
  styleUrl: './system-utilization.component.css',
})
export class SystemUtilizationComponent implements OnInit, OnDestroy {
  cpuUtilizationChartOptions: Partial<Highcharts.Options> = {};
  memoryUtilizationChartOptions: Partial<Highcharts.Options> = {};
  energyWattsChartOptions: Partial<Highcharts.Options> = {};
  forecastChartOptions: Partial<Highcharts.Options> = {};
  
  // Chart recreation key
  chartKey = 0;
  
  // Make Math available in template
  Math = Math;
  
  // Prediction toggle state
  showPredictions = true;

  // Data source toggle state
  usePrometheusApi = true;

  // Time period filter state
  selectedTimePeriod = '1';

  // Node filter state
  selectedNode = '';
  availableNodes: string[] = [];

  // Alert rotation data
  allAlerts = [
    {
      type: 'critical',
      title: 'Energy Shortfall Critical',
      message: 'Expected demand 320W > Available 280W - 1 min ago',
      bgColor: 'bg-red-50',
      borderColor: 'border-red-400',
      titleColor: 'text-red-800',
      messageColor: 'text-red-600'
    },
    {
      type: 'critical',
      title: 'High CPU Usage',
      message: 'worker-node-2 - 2 min ago',
      bgColor: 'bg-red-50',
      borderColor: 'border-red-400',
      titleColor: 'text-red-800',
      messageColor: 'text-red-600'
    },
    {
      type: 'warning',
      title: 'Energy Budget Warning',
      message: '90% of daily energy allowance used - 8 min ago',
      bgColor: 'bg-orange-50',
      borderColor: 'border-orange-400',
      titleColor: 'text-orange-800',
      messageColor: 'text-orange-600'
    },
    {
      type: 'warning',
      title: 'Memory Warning',
      message: 'master-node-1 - 15 min ago',
      bgColor: 'bg-yellow-50',
      borderColor: 'border-yellow-400',
      titleColor: 'text-yellow-800',
      messageColor: 'text-yellow-600'
    },
    {
      type: 'info',
      title: 'Energy Peak Prediction',
      message: 'High demand expected at 2:00 PM - 18 min ago',
      bgColor: 'bg-purple-50',
      borderColor: 'border-purple-400',
      titleColor: 'text-purple-800',
      messageColor: 'text-purple-600'
    }
  ];
  
  visibleAlerts: any[] = [];
  currentAlertIndex = 0;
  alertRotationInterval: any;
  
  // Summary data
  utilizationSummary = {
    averageCpuUsage: 0,
    peakCpuUsage: 0,
    averageMemoryUsage: 0,
    peakMemoryUsage: 0,
    averageEnergyUsage: 0,
    peakEnergyUsage: 0,
    totalNodes: 0,
    lastUpdated: new Date(),
  };

  private destroy$ = new Subject<void>();
  private refreshInterval$ = interval(30000); // Refresh every 30 seconds

  constructor(
    private metricsApiService: MetricsApiService,
    public sidebarService: HlmSidebarService,
    private energyAvailabilityGenerator: EnergyAvailabilityGeneratorService,
    @Inject(PLATFORM_ID) private platformId: Object
  ) {}

  ngOnInit(): void {
    if (isPlatformBrowser(this.platformId)) {
      this.initializeCharts();
      this.loadUtilizationData();
      this.startAlertRotation();
      
      // Set up auto-refresh
      this.refreshInterval$
        .pipe(takeUntil(this.destroy$))
        .subscribe(() => {
          this.loadUtilizationData();
        });
    }
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
    if (this.alertRotationInterval) {
      clearInterval(this.alertRotationInterval);
    }
  }

  private initializeCharts(): void {
    this.cpuUtilizationChartOptions = ChartConfigurations.createCpuUtilizationChart();
    this.memoryUtilizationChartOptions = ChartConfigurations.createMemoryUtilizationChart();
    this.energyWattsChartOptions = ChartConfigurations.createEnergyWattsChart();
    this.forecastChartOptions = ChartConfigurations.createEnergyForecastChart();
  }

  private loadUtilizationData(): void {
    this.loadPrometheusData();
  }

  private loadPrometheusData(): void {
    const hoursBack = this.getHoursFromTimePeriod(this.selectedTimePeriod);
    const nodeFilter = this.selectedNode || undefined;
    console.log(`📊 Loading Prometheus data for ${this.selectedTimePeriod} (${hoursBack} hours) ${nodeFilter ? `for node: ${nodeFilter}` : 'for all nodes'}`);

    // Use the new Prometheus API
    this.metricsApiService.getPrometheusMetrics(hoursBack, nodeFilter)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response) => {
          console.log('✅ Prometheus data received successfully!');
          console.log('📊 Response keys:', Object.keys(response));
          console.log('📈 Time series keys:', Object.keys(response.time_series));

          if (response.time_series) {
            // Extract available nodes from response
            this.extractAvailableNodes(response);

            // Transform Prometheus data for charts
            const cpuUtilizationData = this.metricsApiService.transformPrometheusCpuData(response.time_series.cpu_utilization);
            const memoryUtilizationData = this.metricsApiService.transformPrometheusMemoryData(response.time_series.memory_utilization);

            // Transform total energy data if available
            let totalEnergyData: { [nodeName: string]: [number, number][] } = {};
            if (response.time_series.total_energy_watts) {
              totalEnergyData = this.metricsApiService.transformPrometheusTotalEnergyData(response.time_series.total_energy_watts);
            }

            // Setup charts with transformed data
            this.setupCpuUtilizationChart(cpuUtilizationData);
            this.setupMemoryUtilizationChart(memoryUtilizationData);

            // Setup energy chart with total energy data if available
            if (Object.keys(totalEnergyData).length > 0) {
              this.setupEnergyWattsChart(totalEnergyData);
            } else {
              this.energyWattsChartOptions = {};
            }

            this.updateSummaryDataFromPrometheus(cpuUtilizationData, memoryUtilizationData, totalEnergyData);

            // Clear forecast chart since Prometheus doesn't provide forecast data
            this.forecastChartOptions = {};

            // Force chart updates
            this.chartKey++;
          } else {
            console.error('❌ Invalid Prometheus response structure');
            this.clearAllCharts();
          }
        },
        error: (error) => {
          console.error('❌ Error loading Prometheus data:', error);
          this.clearAllCharts();
        },
      });
  }

  private setupCpuUtilizationChart(data: { [nodeName: string]: [number, number][] }): void {
    
    const series: Highcharts.SeriesOptionsType[] = [];
    const colors = ChartConfigurations.getCpuChartColors();
    let colorIndex = 0;

    // Calculate min and max values from all data points
    let allValues: number[] = [];
    Object.values(data).forEach(nodeData => {
      nodeData.forEach(([, value]) => allValues.push(value));
    });

    let yAxisMin = 0;
    let yAxisMax = 100; // CPU utilization cap at 100%

    if (allValues.length > 0) {
      const dataMin = Math.min(...allValues);
      const dataMax = Math.max(...allValues);
      const range = dataMax - dataMin;
      
      // Add 5% padding above and below for better visualization
      const padding = Math.max(range * 0.05, 2); // Minimum 2% padding
      
      yAxisMin = Math.max(0, Math.floor(dataMin - padding));
      yAxisMax = Math.min(100, Math.ceil(dataMax + padding));

    }

    Object.keys(data).forEach((nodeName) => {
      const color = colors[colorIndex % colors.length];
      series.push({
        name: nodeName,
        type: 'area',
        data: data[nodeName],
        color: color,
        fillColor: {
          linearGradient: { x1: 0, y1: 0, x2: 0, y2: 1 },
          stops: [
            [0, `${color}40`],
            [1, `${color}10`],
          ],
        } as Highcharts.GradientColorObject,
        lineWidth: 1,
        marker: { enabled: false },
      });
      colorIndex++;
    });

    // Update the CPU chart options with dynamic Y-axis
    this.cpuUtilizationChartOptions = {
      chart: { 
        type: 'area', 
        backgroundColor: 'transparent',
        height: 300 
      },
      title: { text: undefined },
      credits: { enabled: false },
      xAxis: { 
        type: 'datetime', 
        title: { text: 'Time' } 
      },
      yAxis: { 
        title: { text: 'CPU Utilization (%)' },
        min: yAxisMin,
        max: yAxisMax,
        startOnTick: false,
        endOnTick: false
      },
      tooltip: { 
        shared: true, 
        valueSuffix: '%',
        formatter: function() {
          let tooltip = `<b>${new Date(this.x!).toLocaleString()}</b><br/>`;
          this.points!.forEach((point) => {
            tooltip += `<span style="color:${point.color}">${point.series.name}</span>: <b>${point.y?.toFixed(1)}%</b><br/>`;
          });
          return tooltip;
        }
      },
      legend: { enabled: true },
      plotOptions: {
        area: {
          fillOpacity: 0.3,
          lineWidth: 1,
          marker: { enabled: false },
          states: { inactive: { opacity: 1 } }
        }
      },
      series: series
    };

    console.log('✅ CPU Utilization chart updated with dynamic Y-axis');
  }

  private setupMemoryUtilizationChart(data: { [nodeName: string]: [number, number][] }): void {
    console.log('📊 Setting up Memory Utilization chart');
    
    const series: Highcharts.SeriesOptionsType[] = [];
    const colors = ChartConfigurations.getMemoryChartColors();
    let colorIndex = 0;

    // Calculate min and max values from all data points
    let allValues: number[] = [];
    Object.values(data).forEach(nodeData => {
      nodeData.forEach(([, value]) => allValues.push(value));
    });

    let yAxisMin = 0;
    let yAxisMax = 100; // Memory utilization cap at 100%

    if (allValues.length > 0) {
      const dataMin = Math.min(...allValues);
      const dataMax = Math.max(...allValues);
      const range = dataMax - dataMin;
      
      // Use minimal padding like energy chart for better normalization
      const padding = Math.max(range * 0.02, 1); // Only 2% padding, minimum 1%
      
      yAxisMin = Math.max(0, dataMin - padding);
      yAxisMax = Math.min(100, dataMax + padding);
      
      console.log(`📊 Memory chart Y-axis range: ${yAxisMin.toFixed(1)}% to ${yAxisMax.toFixed(1)}% (data range: ${dataMin.toFixed(1)}% - ${dataMax.toFixed(1)}%)`);
    }

    Object.keys(data).forEach((nodeName) => {
      const color = colors[colorIndex % colors.length];
      series.push({
        name: nodeName,
        type: 'area',
        data: data[nodeName],
        color: color,
        fillColor: {
          linearGradient: { x1: 0, y1: 0, x2: 0, y2: 1 },
          stops: [
            [0, `${color}40`],
            [1, `${color}10`],
          ],
        } as Highcharts.GradientColorObject,
        lineWidth: 1,
        marker: { enabled: false },
      });
      colorIndex++;
    });

    // Update the memory chart options with dynamic Y-axis
    this.memoryUtilizationChartOptions = {
      chart: { 
        type: 'area', 
        backgroundColor: 'transparent',
        height: 300 
      },
      title: { text: undefined },
      credits: { enabled: false },
      xAxis: { 
        type: 'datetime', 
        title: { text: 'Time' } 
      },
      yAxis: { 
        title: { text: 'Memory Utilization (%)' },
        min: yAxisMin,
        max: yAxisMax,
        startOnTick: false,
        endOnTick: false
      },
      tooltip: { 
        shared: true, 
        valueSuffix: '%',
        formatter: function() {
          let tooltip = `<b>${new Date(this.x!).toLocaleString()}</b><br/>`;
          this.points!.forEach((point) => {
            tooltip += `<span style="color:${point.color}">${point.series.name}</span>: <b>${point.y?.toFixed(1)}%</b><br/>`;
          });
          return tooltip;
        }
      },
      legend: { enabled: true },
      plotOptions: {
        area: {
          fillOpacity: 0.3,
          lineWidth: 1,
          marker: { enabled: false },
          states: { inactive: { opacity: 1 } }
        }
      },
      series: series
    };

    console.log('✅ Memory Utilization chart updated with dynamic Y-axis');
  }

  private setupEnergyWattsChart(data: { [nodeName: string]: [number, number][] }, predictedData?: { [nodeName: string]: [number, number][] }): void {
    console.log('📊 Setting up Energy Watts chart', { showPredictions: this.showPredictions, hasPredictedData: !!predictedData });
    
    const series: Highcharts.SeriesOptionsType[] = [];
    const colors = ChartConfigurations.getEnergyChartColors();
    let colorIndex = 0;

    // Calculate min and max values from all data points including predicted data
    let allValues: number[] = [];
    Object.values(data).forEach(nodeData => {
      nodeData.forEach(([, value]) => allValues.push(value));
    });
    
    if (predictedData) {
      Object.values(predictedData).forEach(nodeData => {
        nodeData.forEach(([, value]) => allValues.push(value));
      });
    }

    let yAxisMin = 0;
    let yAxisMax = undefined;

    if (allValues.length > 0) {
      const dataMin = Math.min(...allValues);
      const dataMax = Math.max(...allValues);
      const range = dataMax - dataMin;
      
      // Use minimal padding for energy chart to show curve better
      const padding = Math.max(range * 0.02, 1); // Only 2% padding, minimum 1W
      
      yAxisMin = Math.max(0, dataMin - padding);
      yAxisMax = dataMax + padding;
      
      console.log(`📊 Energy chart Y-axis range: ${yAxisMin.toFixed(1)}W to ${yAxisMax.toFixed(1)}W (data range: ${dataMin.toFixed(1)}W - ${dataMax.toFixed(1)}W)`);
    }

    // Add actual energy data series
    Object.keys(data).forEach((nodeName) => {
      const color = colors[colorIndex % colors.length];
      series.push({
        name: nodeName,
        type: 'spline',
        data: data[nodeName],
        color: color,
        lineWidth: 1,
        marker: { 
          enabled: false
        },
      });
      colorIndex++;
    });

    // Add predicted energy data series if available
    if (predictedData) {
      const predictedColors = ChartConfigurations.getPredictedEnergyChartColors();
      let predictedColorIndex = 0;
      
      Object.keys(predictedData).forEach((nodeName) => {
        const predictedColor = predictedColors[predictedColorIndex % predictedColors.length];
        series.push({
          name: `${nodeName} (Predicted)`,
          type: 'spline',
          data: predictedData[nodeName],
          color: predictedColor,
          lineWidth: 1,
          dashStyle: 'Dash',
          marker: { 
            enabled: false
          },
        });
        predictedColorIndex++;
      });
    }

    // Create completely new chart options to force refresh
    this.energyWattsChartOptions = {
      chart: { 
        type: 'spline', 
        backgroundColor: 'transparent',
        height: 300,
        animation: false,
        // Add unique key to force recreation
        renderTo: `energy-chart-${this.chartKey}`
      },
      title: { text: undefined },
      credits: { enabled: false },
      xAxis: { 
        type: 'datetime', 
        title: { text: 'Time' } 
      },
      yAxis: { 
        title: { text: 'Energy Usage (W)' },
        min: yAxisMin,
        max: yAxisMax,
        startOnTick: false,
        endOnTick: false
      },
      tooltip: { 
        shared: true, 
        valueSuffix: 'W',
        formatter: function() {
          let tooltip = `<b>${new Date(this.x!).toLocaleString()}</b><br/>`;
          this.points!.forEach((point) => {
            tooltip += `<span style="color:${point.color}">${point.series.name}</span>: <b>${point.y?.toFixed(1)}W</b><br/>`;
          });
          return tooltip;
        }
      },
      legend: { enabled: true },
      plotOptions: {
        spline: {
          lineWidth: 1,
          marker: { 
            enabled: false
          },
          states: { inactive: { opacity: 1 } }
        }
      },
      series: [...series] // Create new array to ensure change detection
    };

    console.log('✅ Energy Watts chart updated with dynamic Y-axis', {
      totalSeries: series.length,
      seriesNames: series.map(s => s.name),
      showPredictions: this.showPredictions,
      hasPredictedData: !!predictedData
    });
  }


  private updateSummaryData(
    cpuData: { [nodeName: string]: [number, number][] },
    memoryData: { [nodeName: string]: [number, number][] },
    energyData: { [nodeName: string]: [number, number][] }
  ): void {
    const allCpuValues: number[] = [];
    const allMemoryValues: number[] = [];
    const allEnergyValues: number[] = [];

    // Collect all CPU values
    Object.values(cpuData).forEach(nodeData => {
      nodeData.forEach(([, value]) => allCpuValues.push(value));
    });

    // Collect all memory values (now percentages)
    Object.values(memoryData).forEach(nodeData => {
      nodeData.forEach(([, value]) => allMemoryValues.push(value));
    });

    // Collect all energy values
    Object.values(energyData).forEach(nodeData => {
      nodeData.forEach(([, value]) => allEnergyValues.push(value));
    });

    this.utilizationSummary = {
      averageCpuUsage: allCpuValues.length > 0
        ? Math.round((allCpuValues.reduce((sum, val) => sum + val, 0) / allCpuValues.length) * 10) / 10
        : 0,
      peakCpuUsage: allCpuValues.length > 0
        ? Math.round(Math.max(...allCpuValues) * 10) / 10
        : 0,
      averageMemoryUsage: allMemoryValues.length > 0
        ? Math.round((allMemoryValues.reduce((sum, val) => sum + val, 0) / allMemoryValues.length) * 10) / 10
        : 0,
      peakMemoryUsage: allMemoryValues.length > 0
        ? Math.round(Math.max(...allMemoryValues) * 10) / 10
        : 0,
      averageEnergyUsage: allEnergyValues.length > 0
        ? Math.round((allEnergyValues.reduce((sum, val) => sum + val, 0) / allEnergyValues.length) * 10) / 10
        : 0,
      peakEnergyUsage: allEnergyValues.length > 0
        ? Math.round(Math.max(...allEnergyValues) * 10) / 10
        : 0,
      totalNodes: Math.max(Object.keys(cpuData).length, Object.keys(memoryData).length, Object.keys(energyData).length),
      lastUpdated: new Date(),
    };

    console.log('📊 Summary updated:', this.utilizationSummary);
  }

  private updateSummaryDataFromPrometheus(
    cpuData: { [nodeName: string]: [number, number][] },
    memoryData: { [nodeName: string]: [number, number][] },
    energyData?: { [nodeName: string]: [number, number][] }
  ): void {
    const allCpuValues: number[] = [];
    const allMemoryValues: number[] = [];
    const allEnergyValues: number[] = [];

    // Collect all CPU values
    Object.values(cpuData).forEach(nodeData => {
      nodeData.forEach(([, value]) => allCpuValues.push(value));
    });

    // Collect all memory values
    Object.values(memoryData).forEach(nodeData => {
      nodeData.forEach(([, value]) => allMemoryValues.push(value));
    });

    // Collect all energy values if available
    if (energyData) {
      Object.values(energyData).forEach(nodeData => {
        nodeData.forEach(([, value]) => allEnergyValues.push(value));
      });
    }

    this.utilizationSummary = {
      averageCpuUsage: allCpuValues.length > 0
        ? Math.round((allCpuValues.reduce((sum, val) => sum + val, 0) / allCpuValues.length) * 10) / 10
        : 0,
      peakCpuUsage: allCpuValues.length > 0
        ? Math.round(Math.max(...allCpuValues) * 10) / 10
        : 0,
      averageMemoryUsage: allMemoryValues.length > 0
        ? Math.round((allMemoryValues.reduce((sum, val) => sum + val, 0) / allMemoryValues.length) * 10) / 10
        : 0,
      peakMemoryUsage: allMemoryValues.length > 0
        ? Math.round(Math.max(...allMemoryValues) * 10) / 10
        : 0,
      averageEnergyUsage: allEnergyValues.length > 0
        ? Math.round((allEnergyValues.reduce((sum, val) => sum + val, 0) / allEnergyValues.length) * 10) / 10
        : 0,
      peakEnergyUsage: allEnergyValues.length > 0
        ? Math.round(Math.max(...allEnergyValues) * 10) / 10
        : 0,
      totalNodes: Math.max(Object.keys(cpuData).length, Object.keys(memoryData).length, energyData ? Object.keys(energyData).length : 0),
      lastUpdated: new Date(),
    };

    console.log('📊 Prometheus summary updated:', this.utilizationSummary);
  }

  private clearAllCharts(): void {
    console.log('🗑️ Clearing all charts due to API error');

    // Clear all chart options
    this.cpuUtilizationChartOptions = {};
    this.memoryUtilizationChartOptions = {};
    this.energyWattsChartOptions = {};
    this.forecastChartOptions = {};

    // Reset summary data to show error state
    this.utilizationSummary = {
      averageCpuUsage: 0,
      peakCpuUsage: 0,
      averageMemoryUsage: 0,
      peakMemoryUsage: 0,
      averageEnergyUsage: 0,
      peakEnergyUsage: 0,
      totalNodes: 0,
      lastUpdated: new Date(),
    };

    // Force chart updates
    this.chartKey++;
  }


  refreshData(): void {
    console.log('🔄 Manual refresh triggered');
    this.loadUtilizationData();
  }

  togglePredictions(): void {
    console.log('🔄 Prediction toggle changed:', this.showPredictions);

    // Clear chart options to force complete rebuild
    this.energyWattsChartOptions = {};
    this.chartKey++;

    // Small delay to ensure the chart is cleared before rebuilding
    setTimeout(() => {
      this.loadUtilizationData();
    }, 50);
  }

  toggleDataSource(): void {
    console.log('🔄 Data source toggle changed to:', this.usePrometheusApi ? 'Prometheus API' : 'Node Metrics API');

    // Clear all chart options to force complete rebuild
    this.cpuUtilizationChartOptions = {};
    this.memoryUtilizationChartOptions = {};
    this.energyWattsChartOptions = {};
    this.forecastChartOptions = {};
    this.chartKey++;

    // Small delay to ensure charts are cleared before rebuilding
    setTimeout(() => {
      console.log('🚀 Loading data from:', this.usePrometheusApi ? 'Prometheus API' : 'Node Metrics API');
      this.loadUtilizationData();
    }, 50);
  }

  onTimePeriodChange(): void {
    console.log('⏱️ Time period changed to:', this.selectedTimePeriod);

    // Clear all chart options to force complete rebuild
    this.cpuUtilizationChartOptions = {};
    this.memoryUtilizationChartOptions = {};
    this.energyWattsChartOptions = {};
    this.forecastChartOptions = {};
    this.chartKey++;

    // Small delay to ensure charts are cleared before rebuilding
    setTimeout(() => {
      this.loadUtilizationData();
    }, 50);
  }

  onNodeFilterChange(): void {
    console.log('🖥️ Node filter changed to:', this.selectedNode || 'All Nodes');

    // Clear all chart options to force complete rebuild
    this.cpuUtilizationChartOptions = {};
    this.memoryUtilizationChartOptions = {};
    this.energyWattsChartOptions = {};
    this.forecastChartOptions = {};
    this.chartKey++;

    // Small delay to ensure charts are cleared before rebuilding
    setTimeout(() => {
      this.loadUtilizationData();
    }, 50);
  }

  private getHoursFromTimePeriod(timePeriod: string): number {
    return parseInt(timePeriod, 10) || 1; // Convert string to number, default to 1 hour
  }

  private extractAvailableNodes(response: any): void {
    if (response.available_nodes && Array.isArray(response.available_nodes)) {
      // Use the available_nodes field directly from the API response
      this.availableNodes = response.available_nodes.sort();
      console.log('📋 Available nodes from API:', this.availableNodes);
    } else if (response.metrics && response.metrics.length > 0) {
      // Fallback: Extract node names from Node Metrics API response
      const nodes = new Set<string>();
      response.metrics.forEach((metric: any) => {
        if (metric.node_name) {
          nodes.add(metric.node_name);
        }
      });
      this.availableNodes = Array.from(nodes).sort();
      console.log('📋 Available nodes extracted from metrics:', this.availableNodes);
    } else if (response.time_series) {
      // Fallback: Extract node names from Prometheus time series data
      const nodes = new Set<string>();
      Object.keys(response.time_series).forEach(metricType => {
        if (response.time_series[metricType]) {
          Object.keys(response.time_series[metricType]).forEach(nodeName => {
            nodes.add(nodeName);
          });
        }
      });
      this.availableNodes = Array.from(nodes).sort();
      console.log('📋 Available nodes extracted from time series:', this.availableNodes);
    }
  }


  private startAlertRotation(): void {
    // Initialize with first 2 alerts
    this.updateVisibleAlerts();
    
    // Rotate alerts every 10 seconds (slow rotation)
    this.alertRotationInterval = setInterval(() => {
      this.rotateAlerts();
    }, 10000);
  }

  private updateVisibleAlerts(): void {
    // Show 2 alerts starting from currentAlertIndex
    this.visibleAlerts = [];
    for (let i = 0; i < 2; i++) {
      const index = (this.currentAlertIndex + i) % this.allAlerts.length;
      this.visibleAlerts.push(this.allAlerts[index]);
    }
  }

  private rotateAlerts(): void {
    // Move to next set of alerts
    this.currentAlertIndex = (this.currentAlertIndex + 2) % this.allAlerts.length;
    this.updateVisibleAlerts();
  }

  goToAlertGroup(groupIndex: number): void {
    // Stop automatic rotation temporarily
    if (this.alertRotationInterval) {
      clearInterval(this.alertRotationInterval);
    }
    
    // Set the alert index based on group
    this.currentAlertIndex = groupIndex * 2;
    this.updateVisibleAlerts();
    
    // Restart automatic rotation after 8 seconds
    setTimeout(() => {
      this.startAlertRotation();
    }, 8000);
  }


  private updateForecastChart(forecast: any): void {
    if (!this.forecastChartOptions.series) return;

    const energyData = this.metricsApiService.transformEnergyForecastData(forecast);
    const availableData = this.generateAvailableEnergyData(energyData.length);
    
    // Calculate min and max values from both datasets for dynamic y-axis
    const allValues = [...energyData.map(d => d[1]), ...availableData.map(d => d[1])];
    const dataMin = Math.min(...allValues);
    const dataMax = Math.max(...allValues);
    const range = dataMax - dataMin;
    
    // Add minimal padding (2% of range, minimum 5W)
    const padding = Math.max(range * 0.02, 5);
    const yAxisMin = Math.max(0, dataMin - padding);
    const yAxisMax = dataMax + padding;

    // Update y-axis with dynamic range
    if (this.forecastChartOptions.yAxis && typeof this.forecastChartOptions.yAxis === 'object' && !Array.isArray(this.forecastChartOptions.yAxis)) {
      this.forecastChartOptions.yAxis.min = yAxisMin;
      this.forecastChartOptions.yAxis.max = yAxisMax;
    }
    
    this.forecastChartOptions.series = [
      {
        name: 'Forecasted Energy',
        type: 'line',
        data: energyData,
        color: '#3b82f6',
        lineWidth: 2
      },
      {
        name: 'Available Energy',
        type: 'line',
        data: availableData,
        color: '#10b981',
        lineWidth: 2,
        dashStyle: 'Dash'
      }
    ];
  }


  private generateAvailableEnergyData(length: number): [number, number][] {
    // Use the common energy availability generator service
    const timeSeriesData = this.energyAvailabilityGenerator.generateTimeSeriesEnergyAvailabilityData(length);
    return this.energyAvailabilityGenerator.convertToChartFormat(timeSeriesData);
  }
}
