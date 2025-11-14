/**
 * Table data utilities for extracting and formatting display data
 * Centralized logic for table row data processing
 */

import { BaseTableData } from '../types/table.types';

/**
 * Extract main display text from table row data
 * Priority order: pod_name > cluster_name > name > alert_description > id
 */
export const getMainText = (element: BaseTableData): string => {
  const item = element as Record<string, unknown>;

  // Check each field and return the first non-empty value
  const fields = [
    'pod_name',
    'cluster_name',
    'name',
    'alert_description',
    'pod_parent_name',
    'action_type',
    'action_reason',
    'id',
  ];

  for (const field of fields) {
    const value = item[field];
    if (value !== null && value !== undefined && value !== '') {
      return String(value);
    }
  }

  return 'Unknown';
};

/**
 * Extract secondary display text from table row data
 * Returns contextual information based on available data
 */
export const getSubText = (element: BaseTableData): string => {
  const item = element as Record<string, unknown>;

  // Pod-specific information
  if (item['pod_id']) {
    return `ID: ${String(item['pod_id']).substring(0, 8)}...`;
  }

  if (item['namespace']) {
    return `Namespace: ${item['namespace']}`;
  }

  if (item['pod_parent_kind']) {
    return `${item['pod_parent_kind']}`;
  }

  if (item['pod_parent_type']) {
    return `${item['pod_parent_type']}`;
  }

  // Alert-specific information
  if (item['alert_type']) {
    return `Type: ${String(item['alert_type'])}`;
  }

  if (item['alert_model']) {
    return `Model: ${String(item['alert_model'])}`;
  }

  // Workload Action information - prioritize pod names over status
  if (item['bound_pod_name'] && item['bound_pod_namespace']) {
    return `Pod: ${item['bound_pod_name']} (${item['bound_pod_namespace']})`;
  }

  if (item['created_pod_name'] && item['created_pod_namespace']) {
    return `Created: ${item['created_pod_name']} (${item['created_pod_namespace']})`;
  }

  if (item['action_status'] && item['action_type']) {
    return `${String(item['action_type'])}: ${String(item['action_status'])}`;
  }

  if (item['action_status']) {
    return `Status: ${String(item['action_status'])}`;
  }

  if (item['action_reason']) {
    return `${String(item['action_reason'])}`;
  }

  // Workload Decision information
  if (item['is_elastic'] !== undefined) {
    const elasticStatus = item['is_elastic'] ? 'Elastic' : 'Fixed';
    return `Type: ${elasticStatus}`;
  }

  if (item['queue_name']) {
    return `Queue: ${String(item['queue_name'])}`;
  }

  if (item['model_version']) {
    return String(item['model_version']);
  }

  // Node information
  if (item['node_name']) {
    return `Node: ${String(item['node_name'])}`;
  }

  // Date information as fallback
  if (item['action_start_time']) {
    return `Started: ${new Date(
      String(item['action_start_time'])
    ).toLocaleDateString()}`;
  }

  if (item['created_at']) {
    return `Created: ${new Date(
      String(item['created_at'])
    ).toLocaleDateString()}`;
  }

  if (item['updated_at']) {
    return `Updated: ${new Date(
      String(item['updated_at'])
    ).toLocaleDateString()}`;
  }

  return '';
};

/**
 * Extract status value from table row data
 * Handles different status field names and types
 */
export const getStatusValue = (
  element: BaseTableData
): string | number | boolean => {
  const item = element as Record<string, unknown>;

  // Check for explicit status fields first
  if (item['status']) {
    return item['status'] as string | number | boolean;
  }

  if (item['action_status']) {
    return item['action_status'] as string | number | boolean;
  }

  if (item['alert_type']) {
    return item['alert_type'] as string | number | boolean;
  }

  if (item['action_type']) {
    return item['action_type'] as string | number | boolean;
  }

  // Handle workload decision status
  // if (item['is_decision_status'] !== undefined) {
  //   return item['is_decision_status'] ? 'approved' : 'rejected';
  // }

  if (item['decision_status']) {
    return item['decision_status'] as string | number | boolean;
  }

  if (item['phase']) {
    return item['phase'] as string | number | boolean;
  }

  if (item['state']) {
    return item['state'] as string | number | boolean;
  }

  return 'unknown';
};

/**
 * Extract numeric progress value from table row data
 * Returns percentage value for progress indicators
 */
export const getProgressValue = (
  element: BaseTableData,
  field: string
): number => {
  const item = element as Record<string, unknown>;
  const value = item[field];

  if (typeof value === 'number') {
    return Math.max(0, Math.min(100, value));
  }

  if (typeof value === 'string') {
    const parsed = parseFloat(value);
    return isNaN(parsed) ? 0 : Math.max(0, Math.min(100, parsed));
  }

  return 0;
};

/**
 * Check if element has specific field
 */
export const hasField = (element: BaseTableData, field: string): boolean => {
  const item = element as Record<string, unknown>;
  return field in item && item[field] !== null && item[field] !== undefined;
};

/**
 * Get formatted date string from element
 */
export const getFormattedDate = (
  element: BaseTableData,
  field?: string,
  includeTime = false
): string => {
  const item = element as Record<string, unknown>;
  const dateValue = field
    ? item[field]
    : item['created_at'] ||
      item['updated_at'] ||
      item['action_start_time'] ||
      item['action_end_time'];

  if (!dateValue) return '';

  try {
    const date = new Date(String(dateValue));
    return includeTime ? date.toLocaleString() : date.toLocaleDateString();
  } catch {
    return String(dateValue);
  }
};

/**
 * Get truncated text with ellipsis
 */
export const getTruncatedText = (text: string, maxLength = 50): string => {
  return text && text.length > maxLength
    ? `${text.substring(0, maxLength)}...`
    : text || '';
};

/**
 * Get nested field value safely
 */
export const getNestedValue = (
  element: BaseTableData,
  path: string
): unknown => {
  const keys = path.split('.');
  let value: unknown = element as Record<string, unknown>;

  for (const key of keys) {
    if (value && typeof value === 'object' && key in value) {
      value = (value as Record<string, unknown>)[key];
    } else {
      return undefined;
    }
  }
  return value;
};

/**
 * Format bytes to human readable format
 */
export const formatBytes = (bytes: number, decimals = 2): string => {
  if (bytes === 0) return '0 Bytes';

  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(decimals))} ${
    sizes[i]
  }`;
};

/**
 * Format number with thousand separators
 */
export const formatNumber = (num: number): string => {
  return new Intl.NumberFormat().format(num);
};

/**
 * Check if value is a valid URL
 */
export const isValidUrl = (value: unknown): boolean => {
  if (typeof value !== 'string') return false;
  try {
    new URL(value);
    return true;
  } catch {
    return false;
  }
};

/**
 * Get field value with fallback options
 */
export const getFieldWithFallback = (
  element: BaseTableData,
  fields: string[],
  fallback = ''
): unknown => {
  for (const field of fields) {
    const value = getNestedValue(element, field);
    if (value !== undefined && value !== null && value !== '') {
      return value;
    }
  }
  return fallback;
};

export const getDuration = (start: string, end: string): number => {
  const dateStart = new Date(start);
  const dateEnd = new Date(end);
  const diffMilliseconds = Math.abs(dateStart.getTime() - dateEnd.getTime());
  const diffSeconds = diffMilliseconds / 1000;

  return diffSeconds;
};
