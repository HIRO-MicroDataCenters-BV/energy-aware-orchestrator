import { InjectionToken } from '@angular/core';
import { environment } from '../../../environments/environment';

export interface ApiConfig {
  baseUrl: string;
  timeout: number;
  retryAttempts: number;
  endpoints: {
    k8s: {
      pods: string;
      nodes: string;
      clusterInfo: string;
      token: string;
    };
    emdc: {
      alerts: string;
      workloadDecisions: string;
      workloadActions: string;
    };
    auth: {
      login: string;
      callback: string;
      logout: string;
    };
  };
}

export const DEFAULT_API_CONFIG: ApiConfig = {
  baseUrl: environment.apiUrl,
  timeout: 30000,
  retryAttempts: 3,
  endpoints: {
    k8s: {
      pods: '/k8s_pod/',
      nodes: '/k8s_node/',
      clusterInfo: '/k8s_cluster_info/',
      token: '/k8s_token/',
    },
    emdc: {
      alerts: '/alerts/',
      workloadDecisions: '/workload_decision/',
      workloadActions: '/workload_action/',
    },
    auth: {
      login: '/auth/login',
      callback: '/auth/callback',
      logout: '/auth/logout',
    },
  },
};

export const API_CONFIG = new InjectionToken<ApiConfig>('api.config', {
  providedIn: 'root',
  factory: () => DEFAULT_API_CONFIG,
});
