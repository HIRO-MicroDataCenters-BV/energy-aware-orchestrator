import * as Highcharts from 'highcharts';

export class ChartConfigurations {
  
  /**
   * Creates CPU Utilization chart configuration
   */
  static createCpuUtilizationChart(): Partial<Highcharts.Options> {
    return {
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
      series: []
    };
  }

  /**
   * Creates Memory Utilization chart configuration
   */
  static createMemoryUtilizationChart(): Partial<Highcharts.Options> {
    return {
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
      series: []
    };
  }

  /**
   * Creates Energy Watts chart configuration
   */
  static createEnergyWattsChart(): Partial<Highcharts.Options> {
    return {
      chart: { 
        type: 'spline', 
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
        title: { text: 'Energy Usage (W)' },
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
      series: []
    };
  }

  /**
   * Creates 24hr Energy Forecast chart configuration
   */
  static createEnergyForecastChart(height = 300, showTitle = true): Partial<Highcharts.Options> {
    return {
      chart: {
        type: 'line',
        height: height,
        backgroundColor: 'transparent'
      },
      title: showTitle ? {
        text: '',
        style: {
          fontSize: '16px',
          fontWeight: '600'
        }
      } : { text: undefined },
      xAxis: {
        type: 'datetime',
        title: {
          text: 'Time'
        }
      },
      yAxis: {
        title: {
          text: 'Energy (W)'
        },
        startOnTick: false,
        endOnTick: false
      },
      tooltip: {
        shared: true,
        formatter: function() {
          const points = this.points || [];
          let tooltip = `<b>${Highcharts.dateFormat('%H:%M - %d %b', this.x)}</b><br/>`;
          points.forEach(point => {
            tooltip += `<span style="color:${point.color}">${point.series.name}</span>: <b>${point.y?.toFixed(1)}W</b><br/>`;
          });
          return tooltip;
        }
      },
      legend: {
        enabled: true,
        itemStyle: {
          fontSize: '12px'
        }
      },
      plotOptions: {
        line: {
          marker: {
            enabled: false,
            states: {
              hover: {
                enabled: true
              }
            }
          }
        }
      },
      series: []
    };
  }

  /**
   * Creates compact Energy Forecast chart for workload deployment page
   */
  static createCompactEnergyForecastChart(): Partial<Highcharts.Options> {
    return this.createEnergyForecastChart(250, false);
  }

  /**
   * Get standard color palette for charts
   */
  static getColorPalette(): string[] {
    return ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6', '#f97316'];
  }

  /**
   * Get CPU chart colors
   */
  static getCpuChartColors(): string[] {
    return ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6', '#f97316'];
  }

  /**
   * Get Memory chart colors
   */
  static getMemoryChartColors(): string[] {
    return ['#10b981', '#ef4444', '#3b82f6', '#f59e0b', '#8b5cf6', '#f97316'];
  }

  /**
   * Get Energy chart colors
   */
  static getEnergyChartColors(): string[] {
    return ['#f59e0b', '#ef4444', '#10b981', '#3b82f6', '#8b5cf6', '#f97316'];
  }

  /**
   * Get Predicted Energy chart colors
   */
  static getPredictedEnergyChartColors(): string[] {
    return ['#1e40af', '#2563eb', '#3b82f6', '#60a5fa', '#93c5fd', '#dbeafe'];
  }
}
