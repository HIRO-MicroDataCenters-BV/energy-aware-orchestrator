/**
 * Alerts API models
 * Based on OpenAPI schema from /alerts/ endpoints
 */

/**
 * Alert type enum based on OpenAPI specification
 */
export enum AlertType {
  ABNORMAL = 'Abnormal',
  NETWORK_ATTACK = 'Network-Attack',
  OTHER = 'Other',
}

/**
 * Alert creation request based on OpenAPI AlertCreateRequest schema
 */
export interface AlertCreateRequest {
  alert_type: AlertType;
  alert_description: string;
  pod_id: string;
  node_id: string;
}

/**
 * Alert response based on OpenAPI AlertResponse schema
 */
export interface AlertResponse {
  id: number;
  alert_type: AlertType;
  alert_description: string;
  pod_id: string;
  node_id: string;
  created_at: string;
}

/**
 * Query parameters for alerts list API
 */
export interface AlertQueryParams {
  skip?: number;
  limit?: number;
}

/**
 * Alert list response
 */
export interface AlertListResponse {
  items: AlertResponse[];
  total: number;
  skip: number;
  limit: number;
}

/**
 * Alert statistics
 */
export interface AlertStatistics {
  total_count: number;
  by_type: Record<AlertType, number>;
  recent_count: number;
  active_count: number;
  resolved_count: number;
}

/**
 * Alert summary for dashboard
 */
export interface AlertSummary {
  critical_count: number;
  warning_count: number;
  info_count: number;
  total_count: number;
  latest_alerts: AlertResponse[];
}

/**
 * Type guards for Alert types
 */
export const isAlertType = (value: unknown): value is AlertType => {
  return Object.values(AlertType).includes(value as AlertType);
};

export const isAlertCreateRequest = (
  obj: unknown
): obj is AlertCreateRequest => {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    isAlertType((obj as AlertCreateRequest).alert_type) &&
    typeof (obj as AlertCreateRequest).alert_description === 'string' &&
    typeof (obj as AlertCreateRequest).pod_id === 'string' &&
    typeof (obj as AlertCreateRequest).node_id === 'string'
  );
};

export const isAlertResponse = (obj: unknown): obj is AlertResponse => {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    typeof (obj as AlertResponse).id === 'number' &&
    isAlertType((obj as AlertResponse).alert_type) &&
    typeof (obj as AlertResponse).alert_description === 'string' &&
    typeof (obj as AlertResponse).pod_id === 'string' &&
    typeof (obj as AlertResponse).node_id === 'string' &&
    typeof (obj as AlertResponse).created_at === 'string'
  );
};

/**
 * Utility functions for alerts
 */
export const getAlertTypeDisplayName = (type: AlertType): string => {
  const displayNames: Record<AlertType, string> = {
    [AlertType.ABNORMAL]: 'Abnormal Behavior',
    [AlertType.NETWORK_ATTACK]: 'Network Attack',
    [AlertType.OTHER]: 'Other',
  };
  return displayNames[type] || type;
};

export const getAlertTypeColor = (type: AlertType): string => {
  const colors: Record<AlertType, string> = {
    [AlertType.ABNORMAL]: '#f59e0b', // amber
    [AlertType.NETWORK_ATTACK]: '#ef4444', // red
    [AlertType.OTHER]: '#6b7280', // gray
  };
  return colors[type] || '#6b7280';
};

export const getAlertTypePriority = (type: AlertType): number => {
  const priorities: Record<AlertType, number> = {
    [AlertType.NETWORK_ATTACK]: 3,
    [AlertType.ABNORMAL]: 2,
    [AlertType.OTHER]: 1,
  };
  return priorities[type] || 0;
};

/**
 * Validation helpers
 */
export const validateAlertCreateRequest = (
  data: AlertCreateRequest
): string[] => {
  const errors: string[] = [];

  if (!data.alert_type) {
    errors.push('Alert type is required');
  } else if (!isAlertType(data.alert_type)) {
    errors.push('Invalid alert type');
  }

  if (!data.alert_description) {
    errors.push('Alert description is required');
  } else if (data.alert_description.length < 1) {
    errors.push('Alert description cannot be empty');
  } else if (data.alert_description.length > 1000) {
    errors.push('Alert description cannot exceed 1000 characters');
  }

  if (!data.pod_id) {
    errors.push('Pod ID is required');
  } else if (!isValidUUID(data.pod_id)) {
    errors.push('Pod ID must be a valid UUID');
  }

  if (!data.node_id) {
    errors.push('Node ID is required');
  } else if (!isValidUUID(data.node_id)) {
    errors.push('Node ID must be a valid UUID');
  }

  return errors;
};

/**
 * Helper to validate UUID format
 */
const isValidUUID = (uuid: string): boolean => {
  const uuidRegex =
    /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
  return uuidRegex.test(uuid);
};

/**
 * Sort alerts by priority (highest first)
 */
export const sortAlertsByPriority = (
  alerts: AlertResponse[]
): AlertResponse[] => {
  return [...alerts].sort((a, b) => {
    const priorityA = getAlertTypePriority(a.alert_type);
    const priorityB = getAlertTypePriority(b.alert_type);
    return priorityB - priorityA;
  });
};

/**
 * Sort alerts by creation date (newest first)
 */
export const sortAlertsByDate = (alerts: AlertResponse[]): AlertResponse[] => {
  return [...alerts].sort((a, b) => {
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });
};

/**
 * Filter alerts by type
 */
export const filterAlertsByType = (
  alerts: AlertResponse[],
  type: AlertType
): AlertResponse[] => {
  return alerts.filter((alert) => alert.alert_type === type);
};

/**
 * Group alerts by type
 */
export const groupAlertsByType = (
  alerts: AlertResponse[]
): Record<AlertType, AlertResponse[]> => {
  return alerts.reduce((groups, alert) => {
    if (!groups[alert.alert_type]) {
      groups[alert.alert_type] = [];
    }
    groups[alert.alert_type].push(alert);
    return groups;
  }, {} as Record<AlertType, AlertResponse[]>);
};

/**
 * Get alert age in milliseconds
 */
export const getAlertAge = (alert: AlertResponse): number => {
  return new Date().getTime() - new Date(alert.created_at).getTime();
};

/**
 * Format alert age as human readable string
 */
export const formatAlertAge = (alert: AlertResponse): string => {
  const ageMs = getAlertAge(alert);
  const ageMinutes = Math.floor(ageMs / (1000 * 60));
  const ageHours = Math.floor(ageMinutes / 60);
  const ageDays = Math.floor(ageHours / 24);

  if (ageDays > 0) {
    return `${ageDays}d ${ageHours % 24}h`;
  } else if (ageHours > 0) {
    return `${ageHours}h ${ageMinutes % 60}m`;
  } else {
    return `${ageMinutes}m`;
  }
};

/**
 * Create alert statistics from alert list
 */
export const createAlertStatistics = (
  alerts: AlertResponse[]
): AlertStatistics => {
  const byType = alerts.reduce((counts, alert) => {
    counts[alert.alert_type] = (counts[alert.alert_type] || 0) + 1;
    return counts;
  }, {} as Record<AlertType, number>);

  // Ensure all types have a count (even if 0)
  Object.values(AlertType).forEach((type) => {
    if (!(type in byType)) {
      byType[type] = 0;
    }
  });

  const now = new Date();
  const oneDayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000);
  const recentAlerts = alerts.filter(
    (alert) => new Date(alert.created_at) > oneDayAgo
  );

  return {
    total_count: alerts.length,
    by_type: byType,
    recent_count: recentAlerts.length,
    active_count: alerts.length, // All alerts are considered active in this API
    resolved_count: 0, // No resolved status in this API
  };
};

/**
 * Create alert summary for dashboard
 */
export const createAlertSummary = (alerts: AlertResponse[]): AlertSummary => {
  const networkAttackCount = alerts.filter(
    (a) => a.alert_type === AlertType.NETWORK_ATTACK
  ).length;
  const abnormalCount = alerts.filter(
    (a) => a.alert_type === AlertType.ABNORMAL
  ).length;
  const otherCount = alerts.filter(
    (a) => a.alert_type === AlertType.OTHER
  ).length;

  // Get latest 5 alerts
  const latestAlerts = sortAlertsByDate(alerts).slice(0, 5);

  return {
    critical_count: networkAttackCount, // Network attacks are critical
    warning_count: abnormalCount, // Abnormal behavior is warning
    info_count: otherCount, // Other alerts are info
    total_count: alerts.length,
    latest_alerts: latestAlerts,
  };
};

// Legacy type aliases for backward compatibility
export type Alert = AlertResponse;
export type AlertCreate = AlertCreateRequest;
export type AlertUpdate = Partial<AlertCreateRequest>;
