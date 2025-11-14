import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  PodsResponse,
  ScheduledDeployment,
  WorkloadDefinitionResponse,
} from '../interfaces/workload.interface';
import { K8sConnectionTestResponse } from '../models/kubernetes.model';

@Injectable({
  providedIn: 'root',
})
export class WorkloadService {
  private readonly baseUrl = `${environment.backendBaseUrl}/api/kubernetes`;
  private readonly deploymentApiUrl = `${environment.backendBaseUrl}/app/deployment-request`;
  private readonly workloadDefinitionsApiUrl = `${environment.backendBaseUrl}/app/definitions`;

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
   * Get pods grouped by application
   * @returns Observable<AppPodsResponse>
   */
  getPodsByApp(): Observable<any> {
    const fullUrl = `${this.baseUrl}/pods/by-app`;
    return this.http.get<any>(fullUrl);
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
   * Test Kubernetes cluster connection
   * @returns Observable with connection status
   */
  testKubernetesConnection(): Observable<K8sConnectionTestResponse> {
    const url = `${this.baseUrl}/status`;
    return this.http.get<K8sConnectionTestResponse>(url);
  }
}
