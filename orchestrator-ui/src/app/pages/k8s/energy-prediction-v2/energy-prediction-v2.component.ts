import { Component, OnInit, OnDestroy, Inject } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { PLATFORM_ID } from '@angular/core';
import { HighchartsChartComponent } from 'highcharts-angular';
import { EnergyAvailabilityHeatmapComponent } from '../../../components/energy-availability-heatmap/energy-availability-heatmap.component';
import * as Highcharts from 'highcharts';
import { Subject, takeUntil, forkJoin } from 'rxjs';
import { EnergyDataService } from '../../../shared/services/energy-data.service';
import { MetricsApiService } from '../../../shared/services/metrics-api.service';
import { EnergyAvailabilityService } from '../../../shared/services/energy-availability.service';
import { HlmSidebarService } from '../../../../../libs/ui/ui-sidebar-helm/src/lib/hlm-sidebar.service';

@Component({
  selector: 'app-energy-prediction-v2',
  standalone: true,
  imports: [
    CommonModule,
    HighchartsChartComponent,
    EnergyAvailabilityHeatmapComponent,
  ],
  templateUrl: './energy-prediction-v2.component.html',
  styleUrl: './energy-prediction-v2.component.css',
})
export class EnergyPredictionV2Component implements OnInit, OnDestroy {
  comparisonChartOptions: Partial<Highcharts.Options> = {};
  cpuWattsChartOptions: Partial<Highcharts.Options> = {};
  cpuUtilizationChartOptions: Partial<Highcharts.Options> = {};
  memoryUsageChartOptions: Partial<Highcharts.Options> = {};

  energyForecastSummary = {
    totalSlots: 0,
    totalCapacity: 0,
    averageConfidence: 0,
    providers: [] as string[],
    sourcesTypes: [] as string[],
  };

  private destroy$ = new Subject<void>();

  constructor(
    private energyDataService: EnergyDataService,
    private metricsApiService: MetricsApiService,
    private energyAvailabilityService: EnergyAvailabilityService,
    public sidebarService: HlmSidebarService,
    @Inject(PLATFORM_ID) private platformId: Object
  ) {}

  ngOnInit(): void {
    if (isPlatformBrowser(this.platformId)) {
      import('highcharts/modules/heatmap')
        .then((module) => {
          (module as any).default(Highcharts);
        })
        .catch((err) => {
          console.error('Failed to load Highcharts heatmap module:', err);
        })
        .finally(() => {
          this.loadData();
        });
    } else {
      // Skip on server; charts will initialize after hydration
    }
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private loadData(): void {
    // Load energy forecast chart (original functionality)
    this.setupComparisonChart();

    // Load energy availability data
    this.loadEnergyAvailabilityData();

    // Also try to load real data (this will override mock data if successful)
    this.loadRealMetricsData();
  }

  private loadRealMetricsData(): void {

    forkJoin({
      cpuWatts: this.metricsApiService.getCpuWattsChartData(),
      cpuUtilization: this.metricsApiService.getCpuUtilizationChartData(),
      memoryUtilization: this.metricsApiService.getMemoryUtilizationChartData(),
    })
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: ({ cpuWatts, cpuUtilization, memoryUtilization }) => {
          console.log('Received metrics data:', {
            cpuWatts,
            cpuUtilization,
            memoryUtilization,
          });

          if (Object.keys(cpuWatts).length > 0) {
            this.setupCpuWattsChart(cpuWatts);
            console.log('CPU Watts chart setup complete');
          } else {
            console.warn('No CPU watts data received');
          }

          if (Object.keys(cpuUtilization).length > 0) {
            this.setupCpuUtilizationChart(cpuUtilization);
            console.log('CPU Utilization chart setup complete');
          } else {
            console.warn('No CPU utilization data received');
          }

          if (Object.keys(memoryUtilization).length > 0) {
            this.setupMemoryUsageChart(memoryUtilization);
            console.log('Memory Utilization chart setup complete');
          } else {
            console.warn('No memory utilization data received');
          }
        },
        error: (error) => {
          console.error('Error loading metrics data:', error);
          console.log('Attempting to use mock data for testing...');
          this.loadMockDataForTesting();
        },
      });
  }

  private loadMockDataForTesting(): void {
    console.log('Loading mock data for testing...');
    const mockData: { [nodeName: string]: [number, number][] } = {
      minikube: [
        [Date.now() - 300000, 150.5] as [number, number], // 5 min ago
        [Date.now() - 240000, 145.2] as [number, number], // 4 min ago
        [Date.now() - 180000, 148.9] as [number, number], // 3 min ago
        [Date.now() - 120000, 152.1] as [number, number], // 2 min ago
        [Date.now() - 60000, 149.8] as [number, number], // 1 min ago
        [Date.now(), 151.2] as [number, number], // now
      ],
    };

    this.setupCpuWattsChart(mockData);

    const mockCpuUtil: { [nodeName: string]: [number, number][] } = {
      minikube: [
        [Date.now() - 300000, 65.2] as [number, number],
        [Date.now() - 240000, 70.1] as [number, number],
        [Date.now() - 180000, 68.5] as [number, number],
        [Date.now() - 120000, 72.8] as [number, number],
        [Date.now() - 60000, 69.3] as [number, number],
        [Date.now(), 71.5] as [number, number],
      ],
    };

    this.setupCpuUtilizationChart(mockCpuUtil);

    const mockMemory: { [nodeName: string]: [number, number][] } = {
      minikube: [
        [Date.now() - 300000, 2400] as [number, number],
        [Date.now() - 240000, 2450] as [number, number],
        [Date.now() - 180000, 2380] as [number, number],
        [Date.now() - 120000, 2520] as [number, number],
        [Date.now() - 60000, 2480] as [number, number],
        [Date.now(), 2510] as [number, number],
      ],
    };

    this.setupMemoryUsageChart(mockMemory);
    console.log('Mock data setup complete');
  }

  private setupCpuWattsChart(data: {
    [nodeName: string]: [number, number][];
  }): void {
    console.log('Setting up CPU Watts chart with data:', data);
    const series: Highcharts.SeriesOptionsType[] = [];
    const colors = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b'];
    let colorIndex = 0;

    Object.keys(data).forEach((nodeName) => {
      const color = colors[colorIndex % colors.length];
      series.push({
        name: `${nodeName} - CPU Watts`,
        type: 'area',
        data: data[nodeName],
        color: color,
        fillColor: {
          linearGradient: { x1: 0, y1: 0, x2: 0, y2: 1 },
          stops: [
            [0, `${color}40`], // 25% opacity
            [1, `${color}10`], // 6% opacity
          ],
        },
        lineWidth: 1,
        marker: {
          enabled: false,
        },
      });
      colorIndex++;
    });

    this.cpuWattsChartOptions = {
      chart: {
        type: 'area',
        backgroundColor: 'transparent',
      },
      title: {
        text: undefined,
      },
      credits: {
        enabled: false,
      },
      xAxis: {
        type: 'datetime',
        title: {
          text: 'Time',
        },
      },
      yAxis: {
        title: {
          text: 'CPU Watts',
        },
      },
      tooltip: {
        shared: true,
        valueSuffix: 'W',
      },
      legend: {
        enabled: true,
      },
      plotOptions: {
        line: {
          states: {
            inactive: {
              opacity: 1,
            },
          },
        },
      },
      series: series,
    };
    console.log('CPU Watts chart options set:', this.cpuWattsChartOptions);
  }

  private setupCpuUtilizationChart(data: {
    [nodeName: string]: [number, number][];
  }): void {
    console.log('Setting up CPU Utilization chart with data:', data);
    const series: Highcharts.SeriesOptionsType[] = [];
    const colors = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b'];
    let colorIndex = 0;

    Object.keys(data).forEach((nodeName) => {
      const color = colors[colorIndex % colors.length];
      series.push({
        name: `${nodeName} - CPU Utilization`,
        type: 'area',
        data: data[nodeName],
        color: color,
        fillColor: {
          linearGradient: { x1: 0, y1: 0, x2: 0, y2: 1 },
          stops: [
            [0, `${color}40`], // 25% opacity
            [1, `${color}10`], // 6% opacity
          ],
        },
        lineWidth: 1,
        marker: {
          enabled: false,
        },
      });
      colorIndex++;
    });

    this.cpuUtilizationChartOptions = {
      chart: {
        type: 'area',
        backgroundColor: 'transparent',
      },
      title: {
        text: undefined,
      },
      credits: {
        enabled: false,
      },
      xAxis: {
        type: 'datetime',
        title: {
          text: 'Time',
        },
      },
      yAxis: {
        title: {
          text: 'CPU Utilization (%)',
        },
        max: 100,
      },
      tooltip: {
        shared: true,
        valueSuffix: '%',
      },
      legend: {
        enabled: true,
      },
      plotOptions: {
        line: {
          states: {
            inactive: {
              opacity: 1,
            },
          },
        },
      },
      series: series,
    };
  }

  private setupMemoryUsageChart(data: {
    [nodeName: string]: [number, number][];
  }): void {
    console.log('Setting up Memory Usage chart with data:', data);
    const series: Highcharts.SeriesOptionsType[] = [];
    const colors = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b'];
    let colorIndex = 0;

    Object.keys(data).forEach((nodeName) => {
      const color = colors[colorIndex % colors.length];
      series.push({
        name: `${nodeName} - Memory Usage`,
        type: 'area',
        data: data[nodeName],
        color: color,
        fillColor: {
          linearGradient: { x1: 0, y1: 0, x2: 0, y2: 1 },
          stops: [
            [0, `${color}40`], // 25% opacity
            [1, `${color}10`], // 6% opacity
          ],
        },
        lineWidth: 1,
        marker: {
          enabled: false,
        },
      });
      colorIndex++;
    });

    this.memoryUsageChartOptions = {
      chart: {
        type: 'area',
        backgroundColor: 'transparent',
      },
      title: {
        text: undefined,
      },
      credits: {
        enabled: false,
      },
      xAxis: {
        type: 'datetime',
        title: {
          text: 'Time',
        },
      },
      yAxis: {
        title: {
          text: 'Memory Usage (MB)',
        },
      },
      tooltip: {
        shared: true,
        valueSuffix: ' MB',
      },
      legend: {
        enabled: true,
      },
      plotOptions: {
        line: {
          states: {
            inactive: {
              opacity: 1,
            },
          },
        },
      },
      series: series,
    };
  }

  private setupComparisonChart(): void {
    this.energyDataService
      .generateComparisonData()
      .pipe(takeUntil(this.destroy$))
      .subscribe(({ actualData, previousForecastData, futureForecastData }) => {
        this.buildComparisonChart(
          actualData,
          previousForecastData,
          futureForecastData
        );
      });
  }

  private buildComparisonChart(
    actualData: [number, number][],
    previousForecastData: [number, number][],
    futureForecastData: [number, number][]
  ): void {
    const now = new Date().getTime();

    this.comparisonChartOptions = {
      chart: {
        type: 'line',
        backgroundColor: 'transparent',
        panKey: 'shift',
        panning: {
          enabled: true,
          type: 'x',
        },
        zooming: {
          type: 'x',
        },
      },
      title: {
        text: undefined,
      },
      subtitle: {
        text: 'Click and drag to zoom in. Hold shift key to pan.',
        style: {
          fontSize: '11px',
          color: '#666',
        },
      },
      credits: {
        enabled: false,
      },
      xAxis: {
        type: 'datetime',
        title: {
          text: 'Time',
        },
        plotLines: [
          {
            color: '#ff6b6b',
            dashStyle: 'ShortDash',
            value: now,
            width: 0.3,
            label: {
              text: 'Now',
              style: {
                color: '#ff6b6b',
              },
            },
          },
        ],
        events: {
          afterSetExtremes: function () {
            // Optional: Add custom behavior after zoom/pan
          },
        },
      },
      yAxis: {
        title: {
          text: 'Energy Consumption (W)',
        },
      },
      tooltip: {
        shared: true,
        formatter: function () {
          let tooltip = `<b>${new Date(this.x!).toLocaleString()}</b><br/>`;
          this.points!.forEach((point) => {
            tooltip += `<span style="color:${point.color}">${
              point.series.name
            }</span>: <b>${point.y?.toFixed(1)}W</b><br/>`;
          });
          return tooltip;
        },
      },
      legend: {
        enabled: true,
      },
      navigation: {
        buttonOptions: {
          enabled: true,
        },
      },
      rangeSelector: {
        enabled: false,
      },
      scrollbar: {
        enabled: false,
      },
      navigator: {
        enabled: false,
      },
      plotOptions: {
        area: {
          fillOpacity: 0.3,
          lineWidth: 1,
          marker: {
            enabled: false,
          },
          states: {
            inactive: {
              opacity: 1,
            },
          },
        },
        line: {
          lineWidth: 2,
          marker: {
            enabled: false,
          },
          states: {
            inactive: {
              opacity: 1,
            },
          },
        },
      },
      series: [
        {
          name: 'Actual Energy Consumption',
          type: 'line',
          data: actualData,
          color: '#10b981',
          lineWidth: 1,
          marker: {
            enabled: false,
          },
        },
        {
          name: 'Previous Forecast (Historical)',
          type: 'area',
          data: previousForecastData,
          color: 'rgba(59, 130, 246, 0.4)',
          fillColor: {
            linearGradient: { x1: 0, y1: 0, x2: 0, y2: 1 },
            stops: [
              [0, 'rgba(59, 130, 246, 0.15)'],
              [1, 'rgba(59, 130, 246, 0.05)'],
            ],
          },
          lineWidth: 0.5,
          marker: {
            enabled: false,
          },
        },
        {
          name: 'Future Forecast',
          type: 'area',
          data: futureForecastData,
          color: 'rgba(59, 130, 246, 0.6)',
          fillColor: {
            linearGradient: { x1: 0, y1: 0, x2: 0, y2: 1 },
            stops: [
              [0, 'rgba(59, 130, 246, 0.25)'],
              [1, 'rgba(59, 130, 246, 0.08)'],
            ],
          },
          lineWidth: 0.5,
          marker: {
            enabled: false,
          },
        },
      ],
    };
  }

  private updateEnergyForecastSummary(slots: any[]): void {
    const totalCapacity = slots.reduce(
      (sum, slot) => sum + slot.available_watts,
      0
    );
    const averageConfidence =
      slots.reduce((sum, slot) => sum + slot.confidence_percentage, 0) /
      slots.length;
    const uniqueProviders = [
      ...new Set(slots.map((slot) => slot.provider_name)),
    ];
    const uniqueSourceTypes = [
      ...new Set(slots.map((slot) => slot.energy_source_type)),
    ];

    this.energyForecastSummary = {
      totalSlots: slots.length,
      totalCapacity: totalCapacity,
      averageConfidence: Math.round(averageConfidence * 10) / 10,
      providers: uniqueProviders,
      sourcesTypes: uniqueSourceTypes,
    };

    console.log('Energy forecast summary updated:', this.energyForecastSummary);
  }

  private loadEnergyAvailabilityData(): void {
    console.log('Loading energy availability data...');

    this.energyAvailabilityService
      .getActiveEnergySlots(100)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response) => {
          console.log('Energy availability data received:', response);

          if (
            response.status === 'success' &&
            response.availability.length > 0
          ) {
            this.updateEnergyForecastSummary(response.availability);
          } else {
            console.warn('No energy availability data received');
          }
        },
        error: (error) => {
          console.error('Error loading energy availability data:', error);
        },
      });
  }
}
