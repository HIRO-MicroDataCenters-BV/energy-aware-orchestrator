export interface K8sPodResponse {
  pods?: K8sPod[];
  total?: number;
}

export interface K8sPod {
  id?: string;
  name: string;
  namespace: string;
  phase: string;
  status?: string;
  node_name?: string;
  pod_id?: string;
  created_at?: string;
  labels?: Record<string, string>;
  annotations?: Record<string, string>;
  containers?: K8sContainer[];
  resources?: K8sResourceRequirements;
}

export interface K8sContainer {
  name: string;
  image: string;
  state?: string;
  ready?: boolean;
  restart_count?: number;
  resources?: K8sResourceRequirements;
}

export interface K8sResourceRequirements {
  requests?: K8sResourceList;
  limits?: K8sResourceList;
}

export interface K8sResourceList {
  cpu?: string;
  memory?: string;
  [key: string]: string | undefined;
}

export interface K8sNodeResponse {
  nodes?: K8sNode[];
  total?: number;
}

export interface K8sNode {
  id?: string;
  name: string;
  status: string;
  node_id?: string;
  roles?: string[];
  version?: string;
  capacity?: K8sResourceList;
  allocatable?: K8sResourceList;
  conditions?: K8sNodeCondition[];
  addresses?: K8sNodeAddress[];
  node_info?: K8sNodeInfo;
  created_at?: string;
}

export interface K8sNodeCondition {
  type: string;
  status: string;
  reason?: string;
  message?: string;
  last_transition_time?: string;
}

export interface K8sNodeAddress {
  type: string;
  address: string;
}

export interface K8sNodeInfo {
  machine_id?: string;
  system_uuid?: string;
  boot_id?: string;
  kernel_version?: string;
  os_image?: string;
  container_runtime_version?: string;
  kubelet_version?: string;
  kube_proxy_version?: string;
  operating_system?: string;
  architecture?: string;
}

export interface K8sClusterInfoResponse {
  cluster_id?: string;
  cluster_name?: string;
  server_version?: string;
  kubernetes_version?: string;
  nodes_count?: number;
  namespaces_count?: number;
  pods_count?: number;
  services_count?: number;
  deployments_count?: number;
  cluster_cpu_usage?: number;
  cluster_memory_usage?: number;
  cluster_cpu_availability?: number;
  cluster_memory_availability?: number;
  cluster_cpu_utilization?: number;
  cluster_memory_utilization?: number;
  nodes?: K8sNode[];
  pods?: K8sPod[];
  namespaces?: any[];
  components?: any[];
  deployments?: any[];
  statefulsets?: any[];
  daemonsets?: any[];
  jobs?: any[];
  kube_system_pods?: any[];
  advanced_info?: K8sAdvancedClusterInfo;
}

export interface K8sAdvancedClusterInfo {
  api_versions?: string[];
  resource_types?: string[];
  storage_classes?: K8sStorageClass[];
  persistent_volumes?: K8sPersistentVolume[];
  [key: string]: unknown;
}

export interface K8sStorageClass {
  name: string;
  provisioner: string;
  reclaim_policy?: string;
  volume_binding_mode?: string;
}

export interface K8sPersistentVolume {
  name: string;
  capacity?: K8sResourceList;
  access_modes?: string[];
  status?: string;
  claim?: string;
}

export interface K8sTokenResponse {
  token: string;
  expires_at?: string;
}

export type K8sPodParentType =
  | 'Deployment'
  | 'StatefulSet'
  | 'ReplicaSet'
  | 'Job'
  | 'DaemonSet'
  | 'CronJob';

export interface K8sPodParent {
  name: string;
  type: K8sPodParentType;
  uid: string;
  namespace: string;
  labels?: Record<string, string>;
  annotations?: Record<string, string>;
  replicas?: number;
  ready_replicas?: number;
  available_replicas?: number;
}

export interface K8sPodQueryParams {
  namespace?: string;
  name?: string;
  pod_id?: string;
  status?: string;
  node_name?: string;
  [key: string]: unknown;
}

export interface K8sNodeQueryParams {
  name?: string;
  node_id?: string;
  status?: string;
  namespace?: string;
  [key: string]: unknown;
}

export interface K8sPodParentQueryParams {
  namespace: string;
  name?: string;
  pod_id?: string;
  [key: string]: unknown;
}

export interface K8sTokenQueryParams {
  namespace?: string;
  service_account_name?: string;
  [key: string]: unknown;
}

export interface K8sClusterInfoQueryParams {
  advanced?: boolean;
  [key: string]: unknown;
}

export interface K8sVersionInfo {
  major: string;
  minor: string;
  gitVersion: string;
  gitCommit: string;
  gitTreeState: string;
  buildDate: string;
  goVersion: string;
  compiler: string;
  platform: string;
}

export interface K8sConnectionTestResponse {
  status: 'connected' | 'disconnected' | 'error';
  api_server: string;
  authenticated: boolean;
  version: K8sVersionInfo | null;
  error: string | null;
}
