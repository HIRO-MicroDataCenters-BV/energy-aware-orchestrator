import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, BehaviorSubject } from 'rxjs';
import { catchError, finalize } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root',
})
export class ApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiUrl;

  private loadingSubject = new BehaviorSubject<boolean>(false);
  public loading$ = this.loadingSubject.asObservable();

  private token: string | null = null;

  /**
   * Get all pods from Kubernetes cluster
   * @param params Query parameters for filtering
   */
  listPods(params?: any): Observable<any> {
    return this.get('/k8s_pod/', params);
  }

  /**
   * Get all nodes from Kubernetes cluster
   * @param params Query parameters for filtering
   */
  listNodes(params?: any): Observable<any> {
    return this.get('/k8s_node/', params);
  }

  /**
   * Get cluster information
   * @param params Query parameters
   */
  getClusterInfo(params?: any): Observable<any> {
    return this.get('/k8s_cluster_info/', params);
  }

  /**
   * Get Kubernetes service account token
   * @param params Token request parameters
   */
  getK8sToken(params?: any): Observable<any> {
    const defaultParams = {
      namespace: 'hiros',
      service_account_name: 'readonly-user',
      ...params,
    };
    return this.get('/k8s_get_token/', defaultParams);
  }

  /**
   * Get all workload decisions
   * @param params Query parameters for filtering
   */
  getWorkloadDecisions(params?: any): Observable<any> {
    return this.get('/workload_request_decision/', params);
  }

  /**
   * Get specific workload decision by ID
   * @param id Decision ID
   */
  getWorkloadDecision(id: string): Observable<any> {
    return this.get(`/workload_request_decision/${id}`);
  }

  /**
   * Create new workload decision
   * @param data Decision data
   */
  createWorkloadDecision(data: any): Observable<any> {
    return this.post('/workload_request_decision/', data);
  }

  /**
   * Update existing workload decision
   * @param id Decision ID
   * @param data Updated decision data
   */
  updateWorkloadDecision(id: string, data: any): Observable<any> {
    return this.put(`/workload_request_decision/${id}`, data);
  }

  /**
   * Delete workload decision
   * @param id Decision ID
   */
  deleteWorkloadDecision(id: string): Observable<any> {
    return this.delete(`/workload_request_decision/${id}`);
  }

  /**
   * Get all workload actions
   * @param params Query parameters for filtering
   */
  getWorkloadActions(params?: any): Observable<any> {
    return this.get('/workload_action/', params);
  }

  /**
   * Get specific workload action by ID
   * @param id Action ID
   */
  getWorkloadAction(id: string): Observable<any> {
    return this.get(`/workload_action/${id}`);
  }

  /**
   * Create new workload action
   * @param data Action data
   */
  createWorkloadAction(data: any): Observable<any> {
    return this.post('/workload_action/', data);
  }

  /**
   * Update existing workload action
   * @param id Action ID
   * @param data Updated action data
   */
  updateWorkloadAction(id: string, data: any): Observable<any> {
    return this.put(`/workload_action/${id}`, data);
  }

  /**
   * Delete workload action
   * @param id Action ID
   */
  deleteWorkloadAction(id: string): Observable<any> {
    return this.delete(`/workload_action/${id}`);
  }

  /**
   * Get all alerts
   * @param params Query parameters for filtering
   */
  getAlerts(params?: any): Observable<any> {
    return this.get('/alerts/', params);
  }

  /**
   * Create new alert
   * @param data Alert data
   */
  createAlert(data: any): Observable<any> {
    return this.post('/alerts/', data);
  }

  /**
   * Get tuning parameters
   * @param params Query parameters for filtering
   */
  getTuningParameters(params?: any): Observable<any> {
    return this.get('/tuning_parameters/', params);
  }

  /**
   * Create new tuning parameter
   * @param data Parameter data
   */
  createTuningParameter(data: any): Observable<any> {
    return this.post('/tuning_parameters/', data);
  }

  /**
   * Get latest tuning parameters
   * @param limit Number of parameters to retrieve
   */
  getLatestTuningParameters(limit: number): Observable<any> {
    return this.get(`/tuning_parameters/latest/${limit}`);
  }

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    return !!this.token;
  }

  /**
   * Logout user and clear token
   */
  logout(): void {
    this.token = null;
    localStorage.removeItem('auth_token');
  }

  private get(endpoint: string, params?: any): Observable<any> {
    return this.request('GET', endpoint, null, params);
  }

  private post(endpoint: string, data: any): Observable<any> {
    return this.request('POST', endpoint, data);
  }

  private put(endpoint: string, data: any): Observable<any> {
    return this.request('PUT', endpoint, data);
  }

  private delete(endpoint: string): Observable<any> {
    return this.request('DELETE', endpoint);
  }

  private request(
    method: string,
    endpoint: string,
    data?: any,
    params?: any
  ): Observable<any> {
    this.loadingSubject.next(true);

    const url = `${this.baseUrl}${endpoint}`;
    const options: any = {
      headers: { 'Content-Type': 'application/json' },
    };

    if (this.token) {
      options.headers['Authorization'] = `Bearer ${this.token}`;
    }

    if (params) {
      options.params = this.buildParams(params);
    }

    let request$: Observable<any>;

    switch (method) {
      case 'GET':
        request$ = this.http.get(url, options);
        break;
      case 'POST':
        request$ = this.http.post(url, data, options);
        break;
      case 'PUT':
        request$ = this.http.put(url, data, options);
        break;
      case 'DELETE':
        request$ = this.http.delete(url, options);
        break;
      default:
        throw new Error(`Unsupported method: ${method}`);
    }

    return request$.pipe(
      catchError((error) => {
        throw error;
      }),
      finalize(() => this.loadingSubject.next(false))
    );
  }

  private buildParams(params: any): HttpParams {
    let httpParams = new HttpParams();

    Object.keys(params).forEach((key) => {
      const value = params[key];
      if (value !== null && value !== undefined && value !== '') {
        httpParams = httpParams.set(key, String(value));
      }
    });

    return httpParams;
  }

  getPods = this.listPods;
  getNodes = this.listNodes;
  getPodRequestDecisions = this.getWorkloadDecisions;
}
