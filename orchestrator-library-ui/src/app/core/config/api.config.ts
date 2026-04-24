import { InjectionToken } from '@angular/core';
import { RUNTIME_CONFIG } from './runtime.config';

export interface ApiConfig {
  baseUrl: string;
  timeout: number;
  retryAttempts: number;
  endpoints: {
    k8s: {
      pods: string;
      nodes: string;
      token: string;
    };
  };
}

export const DEFAULT_API_CONFIG: ApiConfig = {
  baseUrl: RUNTIME_CONFIG.apiBaseUrl,
  timeout: 30000,
  retryAttempts: 3,
  endpoints: {
    k8s: {
      pods: '/k8s_pod/',
      nodes: '/k8s_node/',
      token: '/k8s_token/',
    },
  },
};

export const API_CONFIG = new InjectionToken<ApiConfig>('api.config', {
  providedIn: 'root',
  factory: () => DEFAULT_API_CONFIG,
});
