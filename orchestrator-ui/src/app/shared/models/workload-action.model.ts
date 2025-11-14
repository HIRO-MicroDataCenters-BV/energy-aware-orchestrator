/**
 * Workload Action API models
 * Based on OpenAPI schema from /workload_action/ endpoints
 * Updated to use shared types from common types
 */

// Import shared types instead of local BaseEntity
import {
  WorkloadAction,
  WorkloadActionCreate,
  WorkloadActionUpdate,
  WorkloadActionQueryParams,
  WorkloadActionListResponse,
  WorkloadActionStatistics,
  ActionExecutionSummary,
  WorkloadActionType,
  WorkloadActionStatus,
  PodParentType,
  getActionTypeDisplayName,
  getActionStatusDisplayName,
  getPodParentTypeDisplayName,
  isWorkloadActionType,
  isWorkloadActionStatus,
  isPodParentType,
} from '../types';

// Re-export all types and enums for backward compatibility
export {
  WorkloadActionType,
  WorkloadActionStatus,
  PodParentType,
  getActionTypeDisplayName,
  getActionStatusDisplayName,
  getPodParentTypeDisplayName,
  isWorkloadActionType,
  isWorkloadActionStatus,
  isPodParentType,
};

export type {
  WorkloadAction,
  WorkloadActionCreate,
  WorkloadActionUpdate,
  WorkloadActionQueryParams,
  WorkloadActionListResponse,
  WorkloadActionStatistics,
  ActionExecutionSummary,
};

// Additional utility functions specific to this model
export const createWorkloadActionFromResponse = (
  data: Record<string, unknown>
): WorkloadAction => {
  return {
    id: data['id'] as string,
    action_type: data['action_type'] as WorkloadActionType,
    action_status: (data['action_status'] as WorkloadActionStatus) || null,
    action_start_time: (data['action_start_time'] as string) || null,
    action_end_time: (data['action_end_time'] as string) || null,
    action_reason: (data['action_reason'] as string) || null,
    pod_parent_name: (data['pod_parent_name'] as string) || null,
    pod_parent_type: (data['pod_parent_type'] as PodParentType) || null,
    pod_parent_uid: (data['pod_parent_uid'] as string) || null,
    created_pod_name: (data['created_pod_name'] as string) || null,
    created_pod_namespace: (data['created_pod_namespace'] as string) || null,
    created_node_name: (data['created_node_name'] as string) || null,
    deleted_pod_name: (data['deleted_pod_name'] as string) || null,
    deleted_pod_namespace: (data['deleted_pod_namespace'] as string) || null,
    deleted_node_name: (data['deleted_node_name'] as string) || null,
    bound_pod_name: (data['bound_pod_name'] as string) || null,
    bound_pod_namespace: (data['bound_pod_namespace'] as string) || null,
    bound_node_name: (data['bound_node_name'] as string) || null,
    created_at: (data['created_at'] as string) || null,
    updated_at: (data['updated_at'] as string) || null,
  };
};

export const validateWorkloadActionCreate = (
  data: WorkloadActionCreate
): string[] => {
  const errors: string[] = [];

  if (!data.action_type) {
    errors.push('Action type is required');
  } else if (!isWorkloadActionType(data.action_type)) {
    errors.push('Invalid action type');
  }

  return errors;
};

export const getWorkloadActionDescription = (
  action: WorkloadAction
): string => {
  const actionName = getActionTypeDisplayName(action.action_type);
  const status = action.action_status
    ? getActionStatusDisplayName(action.action_status)
    : 'Unknown';

  let description = `${actionName} - ${status}`;

  if (action.pod_parent_name && action.pod_parent_type) {
    description += ` (${getPodParentTypeDisplayName(action.pod_parent_type)}: ${
      action.pod_parent_name
    })`;
  }

  return description;
};
