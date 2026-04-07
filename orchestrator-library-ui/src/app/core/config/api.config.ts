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
      token: string;
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
      token: '/k8s_token/',
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
