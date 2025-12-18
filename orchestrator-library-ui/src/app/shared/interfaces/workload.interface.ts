export interface Pod {
  name: string;
  namespace: string;
  status: string;
  ready: string;
  restarts: number;
  age: string;
  node: string;
  cpu_request?: string;
  memory_request?: string;
  cpu_limit?: string;
  memory_limit?: string;
  labels?: { [key: string]: string };
  annotations?: { [key: string]: string };
  created_at?: string;
  updated_at?: string;
}

export interface PodsResponse {
  status: string;
  namespace: string;
  pods: Pod[];
  total_count: number;
  timestamp: string;
}

export interface Deployment {
  name: string;
  namespace: string;
  ready_replicas: number;
  desired_replicas: number;
  available_replicas: number;
  updated_replicas: number;
  age: string;
  labels?: { [key: string]: string };
  annotations?: { [key: string]: string };
  created_at?: string;
  updated_at?: string;
}

export interface DeploymentsResponse {
  status: string;
  namespace: string;
  deployments: Deployment[];
  total_count: number;
  timestamp: string;
}

export interface Service {
  name: string;
  namespace: string;
  type: string;
  cluster_ip: string;
  external_ip?: string;
  ports: string[];
  age: string;
  labels?: { [key: string]: string };
  annotations?: { [key: string]: string };
  created_at?: string;
  updated_at?: string;
}

export interface ServicesResponse {
  status: string;
  namespace: string;
  services: Service[];
  total_count: number;
  timestamp: string;
}

export interface Namespace {
  name: string;
  status: string;
  age: string;
  labels?: { [key: string]: string };
  annotations?: { [key: string]: string };
  created_at?: string;
}

export interface NamespacesResponse {
  status: string;
  namespaces: Namespace[];
  total_count: number;
  timestamp: string;
}

// Scheduled workloads API (non-Kubernetes namespace)
export interface ScheduledDeployment {
  id: string;
  app_definition_id: string;
  status: string;
  estimated_energy_watts: number;
  created_at: string; // ISO string
  deployed_at: string | null; // ISO string or null
  error_message?: string | null;
  app_name: string;
  app_namespace: string;
  workload_type: string;
  app_description: string;
  manifest: string;
}

export interface WorkloadDefinitionResponse {
  id: string;
  name: string;
  namespace: string;
  description?: string | null;
  manifest: string;
  workload_type: string;
  deployment_type?: string;
  estimated_energy_required?: number | null;
}