import { CommonModule, isPlatformBrowser } from '@angular/common';
import { Component, Inject, Input, OnChanges, OnInit, PLATFORM_ID, SimpleChanges, OnDestroy } from '@angular/core';
import { HighchartsChartComponent } from 'highcharts-angular';
import * as Highcharts from 'highcharts';
import { Subject, takeUntil } from 'rxjs';
import { EnergyAvailabilityGeneratorService, EnergyAvailabilityData } from '../../shared/services/energy-availability-generator.service';

@Component({
  selector: 'app-energy-availability-heatmap',
  standalone: true,
  imports: [CommonModule, HighchartsChartComponent],
  templateUrl: './energy-availability-heatmap.component.html',
  styleUrls: ['./energy-availability-heatmap.component.css']
})
export class EnergyAvailabilityHeatmapComponent implements OnInit, OnChanges, OnDestroy {
  @Input() dataSource?: string; // Optional data source identifier
  @Input() refreshInterval?: number = 30000; // Not used - auto-refresh disabled
  
  chartOptions: Partial<Highcharts.Options> = {};
  private destroy$ = new Subject<void>();
  private energySlots: EnergyAvailabilityData[] = [];

  constructor(
    @Inject(PLATFORM_ID) private platformId: object,
    private energyAvailabilityGenerator: EnergyAvailabilityGeneratorService
  ) {}

  async ngOnInit(): Promise<void> {
    if (isPlatformBrowser(this.platformId)) {
      try {
        // Dynamically import the heatmap module
        const heatmapModule = await import('highcharts/modules/heatmap');
        // Call the default export function with Highcharts
        if (heatmapModule.default && typeof heatmapModule.default === 'function') {
          (heatmapModule.default as any)(Highcharts);
        }
        
        // Load initial data only (no periodic refresh)
        await this.loadEnergyData();
      } catch (error) {
        console.error('Failed to load heatmap module:', error);
        // Load data anyway, might work without heatmap
        await this.loadEnergyData();
      }
    }
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['dataSource'] && isPlatformBrowser(this.platformId)) {
      this.loadEnergyData();
    }
    // Note: Refresh functionality is disabled
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private async loadEnergyData(): Promise<void> {
    try {
      // Use the common energy availability generator service
      this.energySlots = this.energyAvailabilityGenerator.generateWeeklyEnergyAvailabilityData();
      this.buildChart();
    } catch (error) {
      console.error('Failed to load energy data:', error);
      // Use empty data on error
      this.energySlots = [];
      this.buildChart();
    }
  }

  // Note: Auto-refresh functionality has been disabled
  // Data is loaded once on component initialization only

  private buildChart(): void {
    const dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    const timeSlots = ['00-06', '06-12', '12-18', '18-24'];

    const dataMap = new Map<string, {watts: number, weatherIcon: string, weatherCondition: string, energySourceType: string}>();

    (this.energySlots || []).forEach(slot => {
      const startDate = new Date(slot.slot_start_time);
      const dayOfWeek = startDate.getDay();
      const adjustedDay = dayOfWeek === 0 ? 6 : dayOfWeek - 1; // Monday = 0
      const startHour = startDate.getHours();
      const timeSlotIndex = Math.floor(startHour / 6);
      const key = `${adjustedDay}-${timeSlotIndex}`;
      dataMap.set(key, {
        watts: slot.available_watts || 0,
        weatherIcon: slot.weather_icon || '',
        weatherCondition: slot.weather_condition || 'CLEAR',
        energySourceType: slot.energy_source_type || 'Solar'
      });
    });

    // Determine today's day index (Monday=0) and the current 6-hour time slot
    const now = new Date();
    const nowDay = now.getDay();
    const currentDayIndex = nowDay === 0 ? 6 : nowDay - 1;
    const currentSlotIndex = Math.floor(now.getHours() / 6);

    const heatmapData: any[] = [];
    for (let day = 0; day < 7; day++) {
      for (let timeSlot = 0; timeSlot < 4; timeSlot++) {
        const key = `${day}-${timeSlot}`;
        const slotData = dataMap.get(key) || { watts: 0, weatherIcon: '', weatherCondition: 'CLEAR', energySourceType: 'Solar' };
        const value = slotData.watts;
        
        // Highlight the cell for today's date and current time slot
        if (day === currentDayIndex && timeSlot === currentSlotIndex) {
          heatmapData.push({
            x: timeSlot,
            y: day,
            value,
            borderColor: '#2563eb',
            borderWidth: 1,
            weatherIcon: slotData.weatherIcon,
            weatherCondition: slotData.weatherCondition,
            energy_source_type: slotData.energySourceType
          });
        } else {
          heatmapData.push({
            x: timeSlot,
            y: day,
            value,
            weatherIcon: slotData.weatherIcon,
            weatherCondition: slotData.weatherCondition,
            energy_source_type: slotData.energySourceType
          });
        }
      }
    }

    this.chartOptions = {
      chart: {
        type: 'heatmap',
        backgroundColor: 'transparent',
        marginTop: 0,
        marginBottom: 10,
        plotBorderWidth: 0,
        borderWidth: 0,
        style: {
          position: 'relative',
          overflow: 'visible'
        },
        events: {
          load: function() {
            // Ensure tooltip container has high z-index
            const tooltip = (this as any).tooltip;
            if (tooltip && tooltip.label) {
              tooltip.label.attr({
                zIndex: 10000
              });
            }
          }
        }
      },
      title: { text: undefined },
      credits: { enabled: false },
      xAxis: {
        categories: timeSlots,
        title: { text: '', style: { fontSize: '1px' } },
        opposite: true,
        lineWidth: 0,
        tickWidth: 0,
        labels: {
          style: {
            fontSize: '9px',
            fontWeight: 'normal'
          }
        },
        // Plot band to subtly highlight the current time-slot column
        plotBands: [{
          from: currentSlotIndex - 0.5,
          to: currentSlotIndex + 0.5,
          color: 'rgba(37, 99, 235, 0.08)'
        }]
      },
      yAxis: {
        categories: dayNames,
        title: { text: '', style: { fontSize: '1px' } },
        reversed: true,
        lineWidth: 0,
        tickWidth: 0,
        labels: {
          style: {
            fontSize: '9px',
            fontWeight: 'normal'
          }
        },
        // Plot band to subtly highlight today's row
        plotBands: [{
          from: currentDayIndex - 0.5,
          to: currentDayIndex + 0.5,
          color: 'rgba(16, 185, 129, 0.08)'
        }]
      },
      colorAxis: {
        visible: false,
        min: 0,
        minColor: '#FFFBEB',
        maxColor: '#D97706',
        stops: [
          [0, '#FFFBEB'],
          [0.2, '#FEF3C7'],
          [0.4, '#FDE68A'],
          [0.6, '#FBBF24'],
          [0.8, '#F59E0B'],
          [1, '#D97706']
        ]
      },
      legend: { enabled: false },
      tooltip: {
        enabled: true,
        shared: false,
        useHTML: true,
        hideDelay: 0,
        animation: false,
        backgroundColor: 'rgba(255, 255, 255, 1)',
        borderColor: 'transparent',
        borderRadius: 6,
        borderWidth: 0,
        shadow: {
          color: 'rgba(0, 0, 0, 0.3)',
          offsetX: 2,
          offsetY: 2,
          opacity: 0.8,
          width: 3
        },
        style: {
          fontSize: '11px',
          fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
          color: '#333333',
          padding: '8px 10px',
          lineHeight: '14px',
          whiteSpace: 'nowrap'
        },
        formatter: function(this: any) {
          const timeSlot = timeSlots[this.x];
          const day = dayNames[this.y];
          const value = this.value || 0;
          const weatherIcon = this.point.weatherIcon || '';
          const weatherCondition = this.point.weatherCondition || 'CLEAR';
          const energySourceType = this.point.energy_source_type || 'Solar';
          const fullTimeSlot = timeSlot.replace('-', ':00-') + ':00';
          return `
            <div style="background-color: white; border-radius: 6px; padding: 8px; text-align: center; min-width: 120px; box-sizing: border-box;">
              <strong style="color: #2563eb; font-size: 12px;">${day}</strong><br/>
              <span style="color: #666; font-size: 10px;">${fullTimeSlot}</span><br/>
              <div style="margin: 2px 0; padding: 2px 4px; background: linear-gradient(90deg, #fbbf24, #f59e0b); border-radius: 4px;">
                <span style="color: white; font-size: 9px; font-weight: bold;">☀️ ${energySourceType} Energy</span>
              </div>
              <div style="margin: 4px 0; padding: 2px 0; border-top: 1px solid #eee;">
                <strong style="color: #059669;">${(value / 1000).toFixed(1)}kW</strong><br/>
                <span style="font-size: 9px; color: #888;">(${value.toLocaleString()}W)</span>
              </div>
              ${weatherIcon ? `<div style="margin-top: 4px; font-size: 11px;">
                <span style="font-size: 14px; filter: drop-shadow(1px 1px 2px rgba(0,0,0,0.3));">${weatherIcon}</span> <span style="color: #7c3aed;">${weatherCondition}</span>
              </div>` : ''}
            </div>
          `;
        },
        positioner: function(labelWidth: number, labelHeight: number, point: any) {
          const chart = this.chart;
          const plotLeft = chart.plotLeft;
          const plotTop = chart.plotTop;
          const plotWidth = chart.plotWidth;
          
          let x = point.plotX + plotLeft + 15;
          let y = point.plotY + plotTop - labelHeight - 10;
          
          // Prevent tooltip from going outside chart bounds
          if (x + labelWidth > plotLeft + plotWidth) {
            x = point.plotX + plotLeft - labelWidth - 15;
          }
          if (y < plotTop) {
            y = point.plotY + plotTop + 15;
          }
          
          return { x, y };
        }
      },
      series: [{
        name: 'Energy Availability',
        type: 'heatmap',
        data: heatmapData,
        dataLabels: {
          enabled: true,
          color: '#000000',
          formatter: function(this: any) {
            const value = this.point?.value || this.value || 0;
            const weatherIcon = this.point?.weatherIcon || '';
            if (value === 0) return '';
            return `${weatherIcon ? `<span style="filter: drop-shadow(1px 1px 1px rgba(0,0,0,0.5)); font-size: 10px;">${weatherIcon}</span><br/>` : ''}<span style="color: #000; text-shadow: 1px 1px 1px rgba(255,255,255,0.8);">${(value / 1000).toFixed(0)}kW</span>`;
          },
          style: {
            textOutline: 'none',
            fontSize: '8px',
            fontWeight: 'bold'
          },
          useHTML: true
        },
        states: {
          inactive: { opacity: 1 }
        }
      }]
    };
  }
}


