/**
 * Workload Types and Enums
 * Contains all workload-related types, enums, and interfaces
 */

import { BaseEntity, PaginatedResponse, FilterParams } from './common.types';

// ===================
// Workload Action Types
// ===================

/**
 * Action types enum
 */
export enum WorkloadActionType {
  BIND = 'bind',
  CREATE = 'create',
  DELETE = 'delete',
  MOVE = 'move',
  SWAP_X = 'swap_x',
  SWAP_Y = 'swap_y'
}

/**
 * Action status enum
 */
export enum WorkloadActionStatus {
  PENDING = 'pending',
  SUCCESSFUL = 'succeeded',
  FAILED = 'failed',
}

/**
 * Pod parent types enum
 */
export enum PodParentType {
  DEPLOYMENT = 'deployment',
  STATEFUL_SET = 'stateful_set',
  REPLICA_SET = 'replica_set',
  JOB = 'job',
  DAEMON_SET = 'daemon_set',
  CRON_JOB = 'cron_job'
}

// ===================
// Workload Action Interfaces
// ===================

/**
 * Workload Action create request
 */
export interface WorkloadActionCreate {
  action_type: WorkloadActionType;
  action_status?: WorkloadActionStatus | null;
  action_start_time?: string | null;
  action_end_time?: string | null;
  action_reason?: string | null;
  pod_parent_name?: string | null;
  pod_parent_type?: PodParentType | null;
  pod_parent_uid?: string | null;
  created_pod_name?: string | null;
  created_pod_namespace?: string | null;
  created_node_name?: string | null;
  deleted_pod_name?: string | null;
  deleted_pod_namespace?: string | null;
  deleted_node_name?: string | null;
  bound_pod_name?: string | null;
  bound_pod_namespace?: string | null;
  bound_node_name?: string | null;
}

/**
 * Workload Action response/schema
 */
export interface WorkloadAction extends BaseEntity {
  action_type: WorkloadActionType;
  action_status?: WorkloadActionStatus | null;
  action_start_time?: string | null;
  action_end_time?: string | null;
  action_reason?: string | null;
  pod_parent_name?: string | null;
  pod_parent_type?: PodParentType | null;
  pod_parent_uid?: string | null;
  created_pod_name?: string | null;
  created_pod_namespace?: string | null;
  created_node_name?: string | null;
  deleted_pod_name?: string | null;
  deleted_pod_namespace?: string | null;
  deleted_node_name?: string | null;
  bound_pod_name?: string | null;
  bound_pod_namespace?: string | null;
  bound_node_name?: string | null;
}

/**
 * Workload Action update request
 */
export interface WorkloadActionUpdate {
  action_type?: WorkloadActionType | null;
  action_status?: WorkloadActionStatus | null;
  action_start_time?: string | null;
  action_end_time?: string | null;
  action_reason?: string | null;
  pod_parent_name?: string | null;
  pod_parent_type?: PodParentType | null;
  pod_parent_uid?: string | null;
  created_pod_name?: string | null;
  created_pod_namespace?: string | null;
  created_node_name?: string | null;
  deleted_pod_name?: string | null;
  deleted_pod_namespace?: string | null;
  deleted_node_name?: string | null;
  bound_pod_name?: string | null;
  bound_pod_namespace?: string | null;
  bound_node_name?: string | null;
}

/**
 * Workload Action query parameters
 */
export interface WorkloadActionQueryParams extends FilterParams {
  action_type?: WorkloadActionType;
  action_status?: WorkloadActionStatus;
  pod_parent_type?: PodParentType;
  start_date?: string;
  end_date?: string;
  namespace?: string;
  node_name?: string;
  skip?: number;
  limit?: number;
}

/**
 * Workload Action list response
 */
export interface WorkloadActionListResponse extends PaginatedResponse<WorkloadAction> {
  actions: WorkloadAction[];
}

// ===================
// Workload Request Decision Types
// ===================

/** 
 * Decision status enum 
 */
export enum WorkloadDecisionStatus {
  PENDING = 'pending',
  SUCCESSFUL = 'successful',
  FAILED = 'failed',
}

/**
 * Workload Request Decision create request
 */
export interface WorkloadRequestDecisionCreate {
  pod_id: string;
  pod_name: string;
  namespace: string;
  node_id: string;
  is_elastic: boolean;
  queue_name: string;
  demand_cpu: number;
  demand_memory: number;
  demand_slack_cpu?: number | null;
  demand_slack_memory?: number | null;
  decision_status: WorkloadDecisionStatus;
  pod_parent_id: string;
  pod_parent_kind: string;
}

/**
 * Workload Request Decision schema/response
 */
export interface WorkloadRequestDecisionSchema extends BaseEntity {
  pod_id: string;
  pod_name: string;
  namespace: string;
  node_id: string;
  is_elastic: boolean;
  queue_name: string;
  demand_cpu: number;
  demand_memory: number;
  demand_slack_cpu?: number | null;
  demand_slack_memory?: number | null;
  decision_status: WorkloadDecisionStatus;
  pod_parent_id: string;
  pod_parent_kind: string;
}

/**
 * Workload Request Decision update request
 */
export interface WorkloadRequestDecisionUpdate {
  pod_name?: string | null;
  namespace?: string | null;
  node_id?: string | null;
  is_elastic?: boolean | null;
  queue_name?: string | null;
  demand_cpu?: number | null;
  demand_memory?: number | null;
  demand_slack_cpu?: number | null;
  demand_slack_memory?: number | null;
  decision_status?: WorkloadDecisionStatus | null;
  pod_parent_id?: string | null;
  pod_parent_kind?: string | null;
}

/**
 * Workload Request Decision query parameters
 */
export interface WorkloadRequestDecisionQueryParams extends FilterParams {
  skip?: number;
  limit?: number;
  pod_name?: string;
  namespace?: string;
  node_id?: string;
  is_elastic?: boolean;
  queue_name?: string;
  decision_status?: string;
  pod_parent_kind?: string;
}

/**
 * Workload Request Decision list response
 */
export interface WorkloadRequestDecisionListResponse extends PaginatedResponse<WorkloadRequestDecisionSchema> {
  decisions: WorkloadRequestDecisionSchema[];
}

// ===================
// Statistics and Analytics
// ===================

/**
 * Workload Action statistics
 */
export interface WorkloadActionStatistics {
  total_actions: number;
  actions_by_type: Record<WorkloadActionType, number>;
  actions_by_status: Record<WorkloadActionStatus, number>;
  actions_by_parent_type: Record<PodParentType, number>;
  recent_actions: WorkloadAction[];
  success_rate: number;
  avg_execution_time: number;
}

/**
 * Workload Request Decision statistics
 */
export interface WorkloadRequestDecisionStatistics {
  total_decisions: number;
  elastic_decisions: number;
  non_elastic_decisions: number;
  decisions_by_namespace: Record<string, number>;
  decisions_by_queue: Record<string, number>;
  decisions_by_parent_kind: Record<string, number>;
  avg_cpu_demand: number;
  avg_memory_demand: number;
  recent_decisions: WorkloadRequestDecisionSchema[];
}

/**
 * Resource demand summary
 */
export interface ResourceDemandSummary {
  total_cpu_demand: number;
  total_memory_demand: number;
  total_slack_cpu_demand: number;
  total_slack_memory_demand: number;
  pods_count: number;
  elastic_pods_count: number;
}

/**
 * Action execution summary
 */
export interface ActionExecutionSummary {
  action_id: string;
  action_type: WorkloadActionType;
  status: WorkloadActionStatus;
  start_time?: string;
  end_time?: string;
  duration_ms?: number;
  success: boolean;
  error_message?: string;
  affected_resources: string[];
}

// ===================
// Legacy Type Aliases (for backward compatibility)
// ===================

export type PodRequestDecisionCreate = WorkloadRequestDecisionCreate;
export type PodRequestDecisionSchema = WorkloadRequestDecisionSchema;
export type PodRequestDecisionUpdate = WorkloadRequestDecisionUpdate;
export type PodRequestDecisionQueryParams = WorkloadRequestDecisionQueryParams;
export type PodRequestDecisionListResponse = WorkloadRequestDecisionListResponse;

// ===================
// Type Guards
// ===================

export const isWorkloadActionType = (value: string): value is WorkloadActionType => {
  return Object.values(WorkloadActionType).includes(value as WorkloadActionType);
};

export const isWorkloadActionStatus = (value: string): value is WorkloadActionStatus => {
  return Object.values(WorkloadActionStatus).includes(value as WorkloadActionStatus);
};

export const isPodParentType = (value: string): value is PodParentType => {
  return Object.values(PodParentType).includes(value as PodParentType);
};

// ===================
// Utility Functions
// ===================

export const getActionTypeDisplayName = (actionType: WorkloadActionType): string => {
  const displayNames: Record<WorkloadActionType, string> = {
    [WorkloadActionType.BIND]: 'Bind Pod',
    [WorkloadActionType.CREATE]: 'Create Pod',
    [WorkloadActionType.DELETE]: 'Delete Pod',
    [WorkloadActionType.MOVE]: 'Move Pod',
    [WorkloadActionType.SWAP_X]: 'Swap_X Pod',
    [WorkloadActionType.SWAP_Y]: 'Swap_Y Pod'
  };
  return displayNames[actionType] || actionType;
};

export const getActionStatusDisplayName = (status: WorkloadActionStatus): string => {
  const displayNames: Record<WorkloadActionStatus, string> = {
    [WorkloadActionStatus.PENDING]: 'Pending',
    [WorkloadActionStatus.SUCCESSFUL]: 'Successful',
    [WorkloadActionStatus.FAILED]: 'Failed',
  };
  return displayNames[status] || status;
};

export const getPodParentTypeDisplayName = (parentType: PodParentType): string => {
  const displayNames: Record<PodParentType, string> = {
    [PodParentType.DEPLOYMENT]: 'Deployment',
    [PodParentType.STATEFUL_SET]: 'StatefulSet',
    [PodParentType.REPLICA_SET]: 'ReplicaSet',
    [PodParentType.JOB]: 'Job',
    [PodParentType.DAEMON_SET]: 'DaemonSet',
    [PodParentType.CRON_JOB]: 'CronJob',
  };
  return displayNames[parentType] || parentType;
};
