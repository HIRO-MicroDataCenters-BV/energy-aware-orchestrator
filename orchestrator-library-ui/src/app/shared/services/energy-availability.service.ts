import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { RUNTIME_CONFIG } from '../../core/config/runtime.config';

export interface EnergyAvailabilityResponse {
  status: string;
  filters: {
    provider_name: string | null;
    location: string | null;
    energy_source_type: string | null;
    hours_ahead: number | null;
    is_active: boolean;
    limit: number;
  };
  availability: EnergyAvailabilitySlot[];
}

export interface EnergyAvailabilitySlot {
  id: number;
  provider_name: string;
  location: string;
  energy_source_type: string;
  slot_start_time: string;
  slot_end_time: string;
  available_watts: number;
  guaranteed_minimum_watts: number;
  potential_maximum_watts: number;
  confidence_percentage: number;
  weather_dependency: boolean;
  forecast_date: string;
  is_active: boolean;
  created_at: string;
}

@Injectable({
  providedIn: 'root'
})
export class EnergyAvailabilityService {
  private readonly baseUrl = `${RUNTIME_CONFIG.apiBaseUrl}/metrics/energy-availability`;

  constructor(private http: HttpClient) { }

  /**
   * Fetch energy availability data from the API
   * @param limit - Number of records to fetch (default: 100)
   * @param isActive - Filter by active status (default: true)
   * @param providerName - Optional provider name filter
   * @param location - Optional location filter
   * @param energySourceType - Optional energy source type filter
   * @param hoursAhead - Optional hours ahead filter
   * @returns Observable<EnergyAvailabilityResponse>
   */
  getEnergyAvailability(
    limit = 100, 
    isActive = true, 
    providerName?: string,
    location?: string,
    energySourceType?: string,
    hoursAhead?: number
  ): Observable<EnergyAvailabilityResponse> {
    let params = new HttpParams()
      .set('limit', limit.toString())
      .set('is_active', isActive.toString());
    
    if (providerName) {
      params = params.set('provider_name', providerName);
    }
    
    if (location) {
      params = params.set('location', location);
    }
    
    if (energySourceType) {
      params = params.set('energy_source_type', energySourceType);
    }
    
    if (hoursAhead !== undefined) {
      params = params.set('hours_ahead', hoursAhead.toString());
    }

    return this.http.get<EnergyAvailabilityResponse>(this.baseUrl, { params });
  }


  /**
   * Get all active energy availability slots
   * @param limit - Number of records to fetch
   * @returns Observable<EnergyAvailabilityResponse>
   */
  getActiveEnergySlots(limit = 100): Observable<EnergyAvailabilityResponse> {
    return this.getEnergyAvailability(limit, true);
  }
}
