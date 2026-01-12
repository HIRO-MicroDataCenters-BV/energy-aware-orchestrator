/**
 * TypeScript interfaces for the /api/kubernetes/pods/by-app/v2 endpoint
 * API returns applications grouped by type with enhanced identification
 */

export interface PodInfo {
  name: string;
  namespace: string;
  uid: string;
  node_name?: string;
  phase: string;
  pod_ip?: string;
  host_ip?: string;
  start_time?: string;
  created_at: string;
  labels: { [key: string]: string };
  annotations: { [key: string]: string };
  containers: ContainerInfo[];
  container_statuses: ContainerStatus[];
  restart_policy?: string;
  service_account?: string;
  conditions: any[];
}

export interface ContainerInfo {
  name: string;
  image: string;
  resources: any;
}

export interface ContainerStatus {
  name: string;
  ready: boolean;
  restart_count: number;
  image: string;
  state: any;
}

/**
 * App information from v2 API
 * Supports three types: standard, custom, custom-resource
 */
export interface AppPodsInfoV2 {
  app_name: string;
  app_type: 'standard' | 'custom' | 'custom-resource';
  label_source: string;
  
  // NEW: App-name label value (e.g., "K8s", "Custom-app")
  app_name_label?: string | null;
  
  // Standard K8s app fields
  app_instance?: string | null;
  app_version?: string | null;
  app_component?: string | null;
  managed_by?: string | null;
  
  // Custom app fields
  app_definition_id?: string | null;
  workload_type?: string | null;
  
  // Custom Resource fields
  custom_resource_name?: string | null;
  custom_resource_namespace?: string | null;
  custom_resource_priority?: string | null;
  custom_resource_phase?: string | null;
  custom_resource_decision?: string | null;
  target_app_name?: string | null;
  target_app_kind?: string | null;
  target_app_namespace?: string | null;
  
  // Pods and metadata
  pods: PodInfo[];
  pod_count: number;
  namespaces: string[];
}

/**
 * Response from /api/kubernetes/pods/by-app/v2
 */
export interface AppPodsResponseV2 {
  status: string;
  apps: AppPodsInfoV2[];
  total_apps: number;
  total_pods: number;
  standard_apps_count: number;
  custom_apps_count: number;
  custom_resource_count: number;
  timestamp: string;
}

