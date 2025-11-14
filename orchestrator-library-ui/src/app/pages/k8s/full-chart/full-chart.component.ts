import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HighchartsChartComponent } from 'highcharts-angular';
import * as Highcharts from 'highcharts';
import { Subject } from 'rxjs';
import { HlmSidebarService } from '../../../../../libs/ui/ui-sidebar-helm/src/lib/hlm-sidebar.service';

@Component({
  selector: 'app-full-chart',
  standalone: true,
  imports: [
    CommonModule,
    HighchartsChartComponent
  ],
  templateUrl: './full-chart.component.html',
  styleUrl: './full-chart.component.css'
})
export class FullChartComponent implements OnInit, OnDestroy {
  Highcharts: typeof Highcharts = Highcharts;
  chartOptions: Highcharts.Options = {};
  
  private destroy$ = new Subject<void>();

  constructor(public sidebarService: HlmSidebarService) {}

  ngOnInit(): void {
    this.generateMockData();
    this.initializeChart();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private generateMockData(): void {
    const now = new Date().getTime();
    const data: [number, number][] = [];
    
    // Generate data for the last 24 hours
    for (let i = 24; i >= 0; i--) {
      const timestamp = now - (i * 60 * 60 * 1000);
      const baseValue = 100;
      const variation = Math.sin((timestamp / (60 * 60 * 1000)) * Math.PI / 12) * 50;
      const randomFactor = (Math.random() - 0.5) * 30;
      const value = Math.max(0, baseValue + variation + randomFactor);
      
      data.push([timestamp, value]);
    }

    this.chartOptions = {
      chart: {
        type: 'spline',
        backgroundColor: 'transparent',
        margin: [40, 40, 60, 80],
        spacing: [0, 0, 0, 0],
        width: null,
        height: null
      },
      title: {
        text: undefined
      },
      credits: {
        enabled: false
      },
      legend: {
        enabled: false
      },
      xAxis: {
        type: 'datetime',
        lineWidth: 1,
        tickWidth: 1,
        labels: {
          style: {
            fontSize: '12px'
          }
        }
      },
      yAxis: {
        title: {
          text: 'Energy Consumption (W)',
          style: {
            fontSize: '14px'
          }
        },
        gridLineWidth: 1,
        labels: {
          style: {
            fontSize: '12px'
          }
        }
      },
      tooltip: {
        shared: true,
        valueSuffix: 'W',
        formatter: function() {
          return `<b>${new Date(this.x!).toLocaleString()}</b><br/>Energy: <b>${this.y?.toFixed(1)}W</b>`;
        }
      },
      plotOptions: {
        spline: {
          marker: {
            enabled: false
          },
          lineWidth: 2,
          states: {
            hover: {
              lineWidth: 3
            }
          }
        }
      },
      series: [{
        name: 'Energy Consumption',
        type: 'spline',
        data: data,
        color: '#3b82f6',
        lineWidth: 2
      }]
    };
  }

  private initializeChart(): void {
    // Chart is initialized through the template
  }
}