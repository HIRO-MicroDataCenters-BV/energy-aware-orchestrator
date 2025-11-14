import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HighchartsChartComponent } from 'highcharts-angular';
import * as Highcharts from 'highcharts';
import { Subject, takeUntil } from 'rxjs';
import { HlmCardImports } from '@spartan-ng/ui-card-helm';
import { HlmSidebarService } from '../../../../../libs/ui/ui-sidebar-helm/src/lib/hlm-sidebar.service';
import { EnergyDataService } from '../../../shared/services/energy-data.service';
import { EnergyDataPoint, NodeEnergyData } from '../../../shared/interfaces/energy-data.interface';

@Component({
  selector: 'app-energy-prediction',
  standalone: true,
  imports: [
    CommonModule,
    HighchartsChartComponent,
    ...HlmCardImports
  ],
  templateUrl: './energy-prediction.component.html',
  styleUrl: './energy-prediction.component.css'
})
export class EnergyPredictionComponent implements OnInit, OnDestroy {
  Highcharts: typeof Highcharts = Highcharts;
  
  overviewChartOptions: Partial<Highcharts.Options> = {};
  detailedChartOptions: Partial<Highcharts.Options> = {};
  comparisonChartOptions: Partial<Highcharts.Options> = {};
  
  private destroy$ = new Subject<void>();
  private mockData: NodeEnergyData[] = [];

  constructor(
    public sidebarService: HlmSidebarService,
    private energyDataService: EnergyDataService
  ) {}

  ngOnInit(): void {
    this.loadData();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private loadData(): void {
    this.energyDataService.generateMockData()
      .pipe(takeUntil(this.destroy$))
      .subscribe(data => {
        this.mockData = data;
        this.initializeCharts();
      });
  }

  private initializeCharts(): void {
    this.setupOverviewChart();
    this.setupDetailedChart();
    this.setupComparisonChart();
  }

  private setupOverviewChart(): void {
    const now = new Date().getTime();
    
    // Aggregate data for overview
    const aggregatedHistorical: [number, number][] = [];
    const aggregatedPredicted: [number, number][] = [];

    // Group by timestamp and sum energy consumption
    const timestampMap = new Map<number, number>();
    const predictionMap = new Map<number, number>();

    this.mockData.forEach(nodeData => {
      nodeData.historical.forEach(point => {
        const existing = timestampMap.get(point.timestamp) || 0;
        timestampMap.set(point.timestamp, existing + (point.actual || 0));
      });

      nodeData.predictions.forEach(point => {
        const existing = predictionMap.get(point.timestamp) || 0;
        predictionMap.set(point.timestamp, existing + (point.predicted || 0));
      });
    });

    // Convert to arrays
    Array.from(timestampMap.entries())
      .sort(([a], [b]) => a - b)
      .forEach(([timestamp, value]) => {
        aggregatedHistorical.push([timestamp, value]);
      });

    Array.from(predictionMap.entries())
      .sort(([a], [b]) => a - b)
      .forEach(([timestamp, value]) => {
        aggregatedPredicted.push([timestamp, value]);
      });

    this.overviewChartOptions = {
      chart: {
        type: 'spline',
        backgroundColor: 'transparent'
      },
      title: {
        text: undefined
      },
      credits: {
        enabled: false
      },
      xAxis: {
        type: 'datetime',
        plotLines: [{
          color: '#ff6b6b',
          dashStyle: 'ShortDash',
          value: now,
          width: 2,
          label: {
            text: 'Now',
            style: {
              color: '#ff6b6b'
            }
          }
        }]
      },
      yAxis: {
        title: {
          text: 'Energy Consumption (W)'
        }
      },
      tooltip: {
        shared: true,
        valueSuffix: 'W'
      },
      legend: {
        enabled: true
      },
      plotOptions: {
        spline: {
          states: {
            inactive: {
              opacity: 1
            }
          }
        }
      },
      series: [
        {
          name: 'Historical Usage',
          type: 'spline',
          data: aggregatedHistorical,
          color: '#4ade80',
          lineWidth: 1,
          marker: {
            enabled: false
          }
        },
        {
          name: 'Predicted Usage',
          type: 'spline',
          data: aggregatedPredicted,
          color: '#fbbf24',
          dashStyle: 'ShortDot',
          lineWidth: 1,
          marker: {
            enabled: false
          }
        }
      ]
    };
  }


  private setupDetailedChart(): void {
    const series: Highcharts.SeriesOptionsType[] = [];
    const now = new Date().getTime();

    this.mockData.forEach((nodeData, index) => {
      const colors = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b'];
      const color = colors[index % colors.length];

      // Historical data series
      series.push({
        name: `${nodeData.nodeName} (Historical)`,
        type: 'spline',
        data: nodeData.historical.map(point => [point.timestamp, point.actual || 0]),
        color: color,
        lineWidth: 1,
        marker: {
          enabled: false
        }
      });

      // Prediction data series
      series.push({
        name: `${nodeData.nodeName} (Predicted)`,
        type: 'spline',
        data: nodeData.predictions.map(point => [point.timestamp, point.predicted || 0]),
        color: color,
        dashStyle: 'ShortDot',
        lineWidth: 1,
        marker: {
          enabled: false
        }
      });
    });

    this.detailedChartOptions = {
      chart: {
        type: 'spline',
        backgroundColor: 'transparent'
      },
      title: {
        text: undefined
      },
      credits: {
        enabled: false
      },
      xAxis: {
        type: 'datetime',
        plotLines: [{
          color: '#ff6b6b',
          dashStyle: 'ShortDash',
          value: now,
          width: 2,
          label: {
            text: 'Current Time',
            style: {
              color: '#ff6b6b'
            }
          }
        }]
      },
      yAxis: {
        title: {
          text: 'Energy Consumption (W)'
        }
      },
      tooltip: {
        shared: false,
        valueSuffix: 'W'
      },
      legend: {
        enabled: true
      },
      series: series
    };
  }

  private setupComparisonChart(): void {
    this.energyDataService.generateComparisonData()
      .pipe(takeUntil(this.destroy$))
      .subscribe(({ actualData, previousForecastData, futureForecastData }) => {
        this.buildComparisonChart(actualData, previousForecastData, futureForecastData);
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
          type: 'x'
        },
        zooming: {
          type: 'x'
        }
      },
      title: {
        text: undefined
      },
      subtitle: {
        text: 'Click and drag to zoom in. Hold shift key to pan.',
        style: {
          fontSize: '11px',
          color: '#666'
        }
      },
      credits: {
        enabled: false
      },
      xAxis: {
        type: 'datetime',
        title: {
          text: 'Time'
        },
        plotLines: [{
          color: '#ff6b6b',
          dashStyle: 'ShortDash',
          value: now,
          width: 0.3,
          label: {
            text: 'Now',
            style: {
              color: '#ff6b6b'
            }
          }
        }],
        events: {
          afterSetExtremes: function() {
            // Optional: Add custom behavior after zoom/pan
          }
        }
      },
      yAxis: {
        title: {
          text: 'Energy Consumption (W)'
        }
      },
      tooltip: {
        shared: true,
        formatter: function() {
          let tooltip = `<b>${new Date(this.x!).toLocaleString()}</b><br/>`;
          this.points!.forEach(point => {
            tooltip += `<span style="color:${point.color}">${point.series.name}</span>: <b>${point.y?.toFixed(1)}W</b><br/>`;
          });
          return tooltip;
        }
      },
      legend: {
        enabled: true
      },
      navigation: {
        buttonOptions: {
          enabled: true
        }
      },
      rangeSelector: {
        enabled: false
      },
      scrollbar: {
        enabled: false
      },
      navigator: {
        enabled: false
      },
      plotOptions: {
        area: {
          fillOpacity: 0.3,
          lineWidth: 1,
          marker: {
            enabled: false
          },
          states: {
            inactive: {
              opacity: 1
            }
          }
        },
        line: {
          lineWidth: 2,
          marker: {
            enabled: false
          },
          states: {
            inactive: {
              opacity: 1
            }
          }
        }
      },
      series: [
        {
          name: 'Actual Energy Consumption',
          type: 'line',
          data: actualData,
          color: '#10b981',
          lineWidth: 1,
          marker: {
            enabled: false
          }
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
              [1, 'rgba(59, 130, 246, 0.05)']
            ]
          },
          lineWidth: 0.5,
          marker: {
            enabled: false
          }
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
              [1, 'rgba(59, 130, 246, 0.08)']
            ]
          },
          lineWidth: 0.5,
          marker: {
            enabled: false
          }
        }
      ]
    };
  }
}
