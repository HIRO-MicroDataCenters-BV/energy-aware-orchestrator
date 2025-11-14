import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { EnergyDataPoint, NodeEnergyData } from '../interfaces/energy-data.interface';

@Injectable({
  providedIn: 'root'
})
export class EnergyDataService {

  constructor() { }

  /**
   * Generate mock energy data for Kubernetes nodes
   * @returns Observable<NodeEnergyData[]> Array of node energy data
   */
  generateMockData(): Observable<NodeEnergyData[]> {
    const nodeNames = ['master-node-01', 'worker-node-01', 'worker-node-02', 'worker-node-03'];
    const now = new Date().getTime();
    const hoursBack = 24;
    const hoursForward = 24;

    const mockData = nodeNames.map(nodeName => {
      const historical: EnergyDataPoint[] = [];
      const predictions: EnergyDataPoint[] = [];

      // Generate historical data (last 24 hours)
      for (let i = hoursBack; i >= 0; i--) {
        const timestamp = now - (i * 60 * 60 * 1000);
        const baseConsumption = nodeName.includes('master') ? 150 : 100;
        const variation = Math.sin((timestamp / (60 * 60 * 1000)) * Math.PI / 12) * 30;
        const randomFactor = (Math.random() - 0.5) * 20;
        
        historical.push({
          timestamp,
          actual: Math.max(0, baseConsumption + variation + randomFactor),
          nodeName
        });
      }

      // Generate prediction data (next 24 hours)
      for (let i = 1; i <= hoursForward; i++) {
        const timestamp = now + (i * 60 * 60 * 1000);
        const baseConsumption = nodeName.includes('master') ? 150 : 100;
        const variation = Math.sin((timestamp / (60 * 60 * 1000)) * Math.PI / 12) * 25;
        const trendFactor = Math.sin((i / hoursForward) * Math.PI) * 10;
        
        predictions.push({
          timestamp,
          predicted: Math.max(0, baseConsumption + variation + trendFactor),
          nodeName
        });
      }

      return { nodeName, historical, predictions };
    });

    return of(mockData);
  }

  /**
   * Generate comparison chart data for actual vs forecasted energy consumption
   * @returns Observable with actual, previous forecast, and future forecast data
   */
  generateComparisonData(): Observable<{
    actualData: [number, number][];
    previousForecastData: [number, number][];
    futureForecastData: [number, number][];
  }> {
    const now = new Date().getTime();
    const hoursInWeek = 7 * 24; // One week = 168 hours
    
    // Generate actual data (last week up to now)
    const actualData: [number, number][] = [];
    for (let i = hoursInWeek; i >= 0; i--) {
      const timestamp = now - (i * 60 * 60 * 1000);
      const baseConsumption = 400; // Total cluster consumption
      
      // Daily pattern (24-hour cycle)
      const dailyPattern = Math.sin((timestamp / (60 * 60 * 1000)) * Math.PI / 12) * 80;
      
      // Weekly pattern (7-day cycle) - higher consumption on weekdays
      const dayOfWeek = new Date(timestamp).getDay();
      const weeklyPattern = (dayOfWeek >= 1 && dayOfWeek <= 5) ? 50 : -30; // Weekday vs weekend
      
      // Random variations
      const randomFactor = (Math.random() - 0.5) * 40;
      
      const actualConsumption = baseConsumption + dailyPattern + weeklyPattern + randomFactor;
      actualData.push([timestamp, Math.max(0, actualConsumption)]);
    }

    // Generate previous forecast data (what was predicted for the last week)
    const previousForecastData: [number, number][] = [];
    for (let i = hoursInWeek; i >= 0; i--) {
      const timestamp = now - (i * 60 * 60 * 1000);
      const baseConsumption = 400;
      
      // Similar patterns but with prediction errors
      const dailyPattern = Math.sin((timestamp / (60 * 60 * 1000)) * Math.PI / 12) * 70;
      const dayOfWeek = new Date(timestamp).getDay();
      const weeklyPattern = (dayOfWeek >= 1 && dayOfWeek <= 5) ? 45 : -25; // Slightly different prediction
      
      // Prediction errors - more error for older predictions
      const ageHours = hoursInWeek - i;
      const predictionError = Math.sin((timestamp / (60 * 60 * 1000)) / 3) * (15 + ageHours * 0.2);
      const randomError = (Math.random() - 0.5) * (20 + ageHours * 0.3);
      
      const forecastConsumption = baseConsumption + dailyPattern + weeklyPattern + predictionError + randomError;
      previousForecastData.push([timestamp, Math.max(0, forecastConsumption)]);
    }

    // Generate future forecast data (next week from now)
    const futureForecastData: [number, number][] = [];
    for (let i = 1; i <= hoursInWeek; i++) {
      const timestamp = now + (i * 60 * 60 * 1000);
      const baseConsumption = 400;
      
      // Predicted patterns
      const dailyPattern = Math.sin((timestamp / (60 * 60 * 1000)) * Math.PI / 12) * 70;
      const dayOfWeek = new Date(timestamp).getDay();
      const weeklyPattern = (dayOfWeek >= 1 && dayOfWeek <= 5) ? 45 : -25;
      
      // Future trend and uncertainty
      const trendFactor = Math.sin((i / hoursInWeek) * Math.PI) * 15;
      const uncertainty = (Math.random() - 0.5) * (10 + i * 0.1); // Increasing uncertainty over time
      
      const forecastConsumption = baseConsumption + dailyPattern + weeklyPattern + trendFactor + uncertainty;
      futureForecastData.push([timestamp, Math.max(0, forecastConsumption)]);
    }

    return of({
      actualData,
      previousForecastData,
      futureForecastData
    });
  }

  /**
   * Generate forecast summary data for tomorrow and next week
   * @returns Observable with forecast summaries
   */
  generateForecastSummary(): Observable<{
    tomorrow: {
      peak: number;
      average: number;
      minimum: number;
      totalEnergy: number;
      note: string;
    };
    nextWeek: {
      weeklyPeak: number;
      weeklyAverage: number;
      totalEnergy: number;
      vsLastWeek: number;
      note: string;
    };
  }> {
    // Generate realistic forecast summary data
    const tomorrow = {
      peak: 2450,
      average: 1680,
      minimum: 950,
      totalEnergy: 40.3,
      note: 'Expected peak demand around 2:00 PM due to increased workload processing'
    };

    const nextWeek = {
      weeklyPeak: 2750,
      weeklyAverage: 1820,
      totalEnergy: 306.7,
      vsLastWeek: -8.2,
      note: 'Decreased usage expected due to scheduled maintenance on Thursday'
    };

    return of({ tomorrow, nextWeek });
  }
}