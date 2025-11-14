import { Injectable } from '@angular/core';

export interface EnergyAvailabilityData {
  slot_start_time: string;
  available_watts: number;
  weather_condition: string;
  weather_icon: string;
  weather_dependency: boolean;
  energy_source_type: string;
}

export interface TimeSeriesEnergyData {
  timestamp: number;
  watts: number;
}

@Injectable({
  providedIn: 'root'
})
export class EnergyAvailabilityGeneratorService {

  // Weather conditions for forecast
  private weatherConditions = {
    CLEAR: { icon: '☀️', multiplier: 1.0 },
    CLOUDY: { icon: '☁️', multiplier: 0.8 },
    THUNDERSTORM: { icon: '⛈️', multiplier: 0.3 },
    RAINY: { icon: '🌧️', multiplier: 0.6 }
  };

  /**
   * Generate energy availability data for heatmap (weekly view with 6-hour slots)
   */
  generateWeeklyEnergyAvailabilityData(): EnergyAvailabilityData[] {
    const mockData: EnergyAvailabilityData[] = [];
    const baseDate = new Date();
    const startOfWeek = new Date(baseDate);
    startOfWeek.setDate(baseDate.getDate() - baseDate.getDay() + 1); // Start from Monday

    // Get current time info for determining next 2 upcoming slots
    const now = new Date();
    const currentDay = now.getDay();
    const currentDayIndex = currentDay === 0 ? 6 : currentDay - 1; // Monday = 0
    const currentSlotIndex = Math.floor(now.getHours() / 6);
    
    let upcomingSlotsCount = 0;

    for (let day = 0; day < 7; day++) {
      for (let timeSlot = 0; timeSlot < 4; timeSlot++) {
        const slotDate = new Date(startOfWeek);
        slotDate.setDate(startOfWeek.getDate() + day);
        slotDate.setHours(timeSlot * 6, 0, 0, 0);
        
        // Generate varying energy levels based on time of day and day of week
        const isWeekend = day >= 5;
        const isPeakHours = timeSlot >= 1 && timeSlot <= 2; // 06:00-18:00
        
        let baseWatts = 1000;
        if (isPeakHours) baseWatts += 1500;
        if (!isWeekend) baseWatts += 500;
        
        // Determine if this is one of the next 2 upcoming time slots
        const isUpcomingSlot = this.isUpcomingSlot(day, timeSlot, currentDayIndex, currentSlotIndex, upcomingSlotsCount);
        if (isUpcomingSlot && upcomingSlotsCount < 2) {
          upcomingSlotsCount++;
        }
        
        // Add weather forecast - only bad weather for next 2 upcoming slots
        let weatherCondition = 'CLEAR';
        
        if (isUpcomingSlot && upcomingSlotsCount <= 2) {
          // Force thunderstorm for next 2 upcoming slots
          weatherCondition = 'THUNDERSTORM';
        } else {
          // Normal weather distribution for other slots
          const weatherRandom = Math.random();
          if (weatherRandom < 0.05) {
            weatherCondition = 'RAINY';
          } else if (weatherRandom < 0.2) {
            weatherCondition = 'CLOUDY';
          }
        }

        // Apply weather multiplier to energy availability
        const weatherMultiplier = this.weatherConditions[weatherCondition as keyof typeof this.weatherConditions].multiplier;
        let weatherIcon = '';
        
        // Only show icons for cloudy, rainy, and thunderstorm conditions
        if (weatherCondition === 'CLOUDY') {
          weatherIcon = '☁️';
        } else if (weatherCondition === 'RAINY') {
          weatherIcon = '🌧️';
        } else if (weatherCondition === 'THUNDERSTORM') {
          weatherIcon = '⛈️';
        }
        // Clear conditions show no icon
        
        // Add some random variation
        const variation = Math.random() * 800 - 400;
        const baseAvailableWatts = Math.max(800, Math.round(baseWatts + variation));
        const availableWatts = Math.round(baseAvailableWatts * weatherMultiplier);

        mockData.push({
          slot_start_time: slotDate.toISOString(),
          available_watts: availableWatts,
          weather_condition: weatherCondition,
          weather_icon: weatherIcon,
          weather_dependency: weatherCondition !== 'CLEAR',
          energy_source_type: 'Solar'
        });
      }
    }

    return mockData;
  }

  /**
   * Generate energy availability data for time series charts using the same heatmap data
   * Converts 6-hour slots to hourly data points for the next 24 hours
   */
  generateTimeSeriesEnergyAvailabilityData(hours: number = 24): TimeSeriesEnergyData[] {
    const now = Date.now();
    const data: TimeSeriesEnergyData[] = [];
    
    // Get the same weekly data used by heatmap
    const weeklyData = this.generateWeeklyEnergyAvailabilityData();
    
    // Convert each 6-hour slot to 6 hourly data points
    for (let i = 0; i < hours; i++) {
      const timestamp = now + (i * 3600000); // Add hours in milliseconds
      const hourDate = new Date(timestamp);
      
      // Find the corresponding 6-hour slot from weekly data
      const dayOfWeek = hourDate.getDay();
      const adjustedDay = dayOfWeek === 0 ? 6 : dayOfWeek - 1; // Monday = 0
      const hour = hourDate.getHours();
      const slotIndex = Math.floor(hour / 6);
      
      // Find matching slot from weekly data
      const matchingSlot = weeklyData.find(slot => {
        const slotDate = new Date(slot.slot_start_time);
        const slotDay = slotDate.getDay();
        const slotAdjustedDay = slotDay === 0 ? 6 : slotDay - 1;
        const slotSlotIndex = Math.floor(slotDate.getHours() / 6);
        
        return slotAdjustedDay === adjustedDay && slotSlotIndex === slotIndex;
      });
      
      let watts = 1500; // Default fallback
      
      if (matchingSlot) {
        // Use the exact same watts value as in heatmap
        watts = matchingSlot.available_watts;
      }
      
      data.push({
        timestamp,
        watts
      });
    }
    
    return data;
  }

  /**
   * Convert time series data to chart format [timestamp, value][]
   */
  convertToChartFormat(data: TimeSeriesEnergyData[]): [number, number][] {
    return data.map(item => [item.timestamp, item.watts]);
  }

  private isUpcomingSlot(day: number, timeSlot: number, currentDayIndex: number, currentSlotIndex: number, upcomingSlotsCount: number): boolean {
    // Calculate if this slot is in the future (upcoming)
    if (day < currentDayIndex) {
      return false; // Past day
    } else if (day === currentDayIndex) {
      return timeSlot > currentSlotIndex; // Same day, future time slot
    } else {
      // Future day - but only consider it if we haven't found 2 slots yet
      return upcomingSlotsCount < 2;
    }
  }
}