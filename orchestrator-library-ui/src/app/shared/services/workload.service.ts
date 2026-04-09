import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { RUNTIME_CONFIG } from '../../core/config/runtime.config';
import {
  PodsResponse,
  ScheduledDeployment,
  WorkloadDefinitionResponse,
} from '../interfaces/workload.interface';
import { K8sConnectionTestResponse } from '../models/kubernetes.model';
import { AppPodsResponseV2 } from '../interfaces/app-pods.interface';

@Injectable({
  providedIn: 'root',
})
export class WorkloadService {
  private readonly apiBaseUrl = RUNTIME_CONFIG.apiBaseUrl;
  private readonly baseUrl = `${this.apiBaseUrl}/kubernetes`;
  private readonly deploymentApiUrl = `${RUNTIME_CONFIG.appBaseUrl}/deployment-request`;
  private readonly workloadDefinitionsApiUrl = `${RUNTIME_CONFIG.appBaseUrl}/definitions`;

  constructor(private http: HttpClient) {}

  /**
   * Retrieve all pods from a specific namespace
   * @param namespace - Kubernetes namespace (default: 'energy-metrics')
   * @returns Observable<PodsResponse>
   */
  getPods(namespace = 'default'): Observable<PodsResponse> {
    const params = new HttpParams().set('namespace', namespace);
    const fullUrl = `${this.baseUrl}/pods?${params.toString()}`;
    console.log(fullUrl);
    return this.http.get<PodsResponse>(`${this.baseUrl}/pods`, { params });
  }

  /**
   * Get pods grouped by application (V2 API)
   * Returns apps with enhanced identification including app_name_label
   * @returns Observable<AppPodsResponseV2>
   */
  getPodsByApp(): Observable<AppPodsResponseV2> {
    const fullUrl = `${this.baseUrl}/pods/by-app/v2`;
    return this.http.get<AppPodsResponseV2>(fullUrl);
  }

  /**
   * Get scheduled deployments (energy-aware scheduler)
   * @param limit - number of items to return
   * @param offset - pagination offset
   */
  getScheduledDeployments(
    limit = 100,
    offset = 0
  ): Observable<ScheduledDeployment[]> {
    const params = new HttpParams().set('limit', limit).set('offset', offset);

    const fullUrl = `${this.deploymentApiUrl}?${params.toString()}`;

    return this.http.get<ScheduledDeployment[]>(
      `${this.deploymentApiUrl}/requests`,
      { params }
    );
  }

  /**
   * Get deployment requests (Application Deployment Requests)
   * @param limit - number of items to return
   * @param offset - pagination offset
   */
  getDeploymentRequests(
    limit = 100,
    offset = 0
  ): Observable<ScheduledDeployment[]> {
    const params = new HttpParams().set('limit', limit).set('offset', offset);

    const fullUrl = `${this.deploymentApiUrl}/requests?${params.toString()}`;

    return this.http.get<ScheduledDeployment[]>(
      `${this.deploymentApiUrl}/requests`,
      { params }
    );
  }

  /**
   * Create a scheduled deployment (workload)
   */
  createScheduledDeployment(body: {
    app_definition_id: string;
    estimated_energy_watts: number;
    schedule_at?: string;
  }): Observable<ScheduledDeployment> {
    const url = `${this.deploymentApiUrl}/deploy`;
    return this.http.post<ScheduledDeployment>(url, body);
  }

  /**
   * Upload YAML to create workload definition
   */
  uploadWorkloadYaml(payload: {
    file: File;
    name: string;
    namespace?: string;
    workload_type?: string;
    deployment_type?: string;
    description?: string;
    estimated_energy_required?: number;
  }): Observable<WorkloadDefinitionResponse> {
    const form = new FormData();

    // Append file with explicit type
    form.append('file', payload.file, payload.file.name);

    // Append all required fields (matching the curl command exactly)
    form.append('name', payload.name);
    form.append('namespace', payload.namespace || 'default');
    form.append('workload_type', payload.workload_type || 'Optional');
    form.append('deployment_type', payload.deployment_type || 'kubernetes');
    form.append('description', payload.description || '');

    // Always append estimated_energy_required as string
    const energyValue =
      payload.estimated_energy_required !== undefined &&
      payload.estimated_energy_required !== null
        ? String(payload.estimated_energy_required)
        : '10'; // default value matching the curl example
    form.append('estimated_energy_required', energyValue);

    const url = `${this.workloadDefinitionsApiUrl}/upload`;

    // Don't set Content-Type header explicitly - let the browser set it with boundary
    return this.http.post<WorkloadDefinitionResponse>(url, form);
  }

  /**
   * List created workload definitions
   */
  getWorkloadDefinitions(
    limit = 100,
    offset = 0
  ): Observable<WorkloadDefinitionResponse[]> {
    const params = new HttpParams().set('limit', limit).set('offset', offset);
    const url = `${this.workloadDefinitionsApiUrl}/`;
    return this.http.get<WorkloadDefinitionResponse[]>(url, { params });
  }

  /**
   * Get a workload definition by ID
   */
  getWorkloadDefinition(id: string): Observable<WorkloadDefinitionResponse> {
    const url = `${this.workloadDefinitionsApiUrl}/${id}`;
    return this.http.get<WorkloadDefinitionResponse>(url);
  }

  /**
   * Delete a workload definition by ID
   */
  deleteWorkloadDefinition(id: string): Observable<void> {
    const url = `${this.workloadDefinitionsApiUrl}/${id}`;
    return this.http.delete<void>(url);
  }

  /**
   * Delete a deployment request by ID
   */
  deleteDeploymentRequest(id: string): Observable<void> {
    const url = `${this.deploymentApiUrl}/requests/${id}`;
    return this.http.delete<void>(url);
  }

  /**
   * Update deployment request status
   * @param id - Deployment request ID
   * @param status - New status (e.g., 'Scheduled')
   * @param scheduledAt - Optional scheduled date/time (formatted string)
   */
  updateDeploymentRequestStatus(id: string, status: string, scheduledAt?: string): Observable<any> {
    const url = `${this.deploymentApiUrl}/requests/${id}/status`;
    const body: any = { status };

    if (scheduledAt) {
      body.schedule_at = scheduledAt;
    }

    return this.http.patch<any>(url, body);
  }

  /**
   * Update only the schedule time for a deployment request
   * @param id - Deployment request ID
   * @param scheduleAt - New schedule time (formatted string YYYY-MM-DDTHH:mm:ss)
   */
  updateDeploymentRequestSchedule(id: string, scheduleAt: string): Observable<any> {
    const url = `${this.deploymentApiUrl}/requests/${id}/schedule`;
    const params = new HttpParams().set('schedule_at', scheduleAt);
    // Backend expects schedule_at as a query param; body can be empty
    return this.http.patch<any>(url, null, { params });
  }

  /**
   * Test Kubernetes cluster connection
   * @returns Observable with connection status
   */
  testKubernetesConnection(): Observable<K8sConnectionTestResponse> {
    const url = `${this.baseUrl}/status`;
    return this.http.get<K8sConnectionTestResponse>(url);
  }
}
