/**
 * Status utilities for consistent status handling across the application
 * Centralized logic for status colors, icons, and display
 */

import { StatusConfig } from '../types/table.types';

/**
 * Status type enumeration
 */
export enum StatusType {
  CREATED = 'created',
  RUNNING = 'running',
  PENDING = 'pending',
  BOUND = 'bound',
  BIND = 'bind',
  SUCCESS = 'success',
  SUCCESSFUL = 'successful',
  COMPLETED = 'completed',
  APPROVED = 'approved',
  FAILED = 'failed',
  ERROR = 'error',
  DELETED = 'deleted',
  NETWORK_ATTACK = 'network-attack',
  WARNING = 'warning',
  ABNORMAL = 'abnormal',
  INFO = 'info',
  OTHER = 'other',
  INACTIVE = 'inactive',
  UNKNOWN = 'unknown',
  // Workload action statuses
  PARTIAL = 'partial',
  // Alert types
  MODELA = 'modela',
  MODELB = 'modelb',
  MODELC = 'modelc',
}

/**
 * Alert type enumeration
 */
export enum AlertType {
  CRITICAL = 'critical',
  WARNING = 'warning',
  INFO = 'info',
  ERROR = 'error',
}

/**
 * Status configuration mapping
 */
const STATUS_CONFIG_MAP: Record<string, StatusConfig> = {
  // Running/Active states
  [StatusType.CREATED]: {
    value: StatusType.CREATED,
    label: 'Created',
    color: 'text-info-foreground',
    bgColor: 'bg-info/10',
    icon: 'lucideCircle',
  },
  [StatusType.RUNNING]: {
    value: StatusType.RUNNING,
    label: 'Running',
    color: 'text-info-foreground',
    bgColor: 'bg-info/10',
    icon: 'lucideCircle',
  },
  [StatusType.PENDING]: {
    value: StatusType.PENDING,
    label: 'Pending',
    color: 'text-yellow-700',
    bgColor: 'bg-yellow-100',
    icon: 'lucideCircle',
  },

  // Success states
  [StatusType.BOUND]: {
    value: StatusType.BOUND,
    label: 'Bound',
    color: 'text-success-foreground',
    bgColor: 'bg-success/10',
    icon: 'lucideCircleCheck',
  },
  [StatusType.BIND]: {
    value: StatusType.BIND,
    label: 'Bind',
    color: 'text-success-foreground',
    bgColor: 'bg-success/10',
    icon: 'lucideCircleCheck',
  },
  [StatusType.SUCCESS]: {
    value: StatusType.SUCCESS,
    label: 'Success',
    color: 'text-success-foreground',
    bgColor: 'bg-success/10',
    icon: 'lucideCircleCheck',
  },
  [StatusType.SUCCESSFUL]: {
    value: StatusType.SUCCESSFUL,
    label: 'Successful',
    color: 'text-success-foreground',
    bgColor: 'bg-success/10',
    icon: 'lucideCircleCheck',
  },
  [StatusType.COMPLETED]: {
    value: StatusType.COMPLETED,
    label: 'Completed',
    color: 'text-success-foreground',
    bgColor: 'bg-success/10',
    icon: 'lucideCircleCheck',
  },
  [StatusType.APPROVED]: {
    value: StatusType.APPROVED,
    label: 'Approved',
    color: 'text-success-foreground',
    bgColor: 'bg-success/10',
    icon: 'lucideCircleCheck',
  },

  // Error states
  [StatusType.FAILED]: {
    value: StatusType.FAILED,
    label: 'Failed',
    color: 'text-destructive-foreground',
    bgColor: 'bg-destructive/10',
    icon: 'lucideCircleX',
  },
  [StatusType.ERROR]: {
    value: StatusType.ERROR,
    label: 'Error',
    color: 'text-destructive-foreground',
    bgColor: 'bg-destructive/10',
    icon: 'lucideCircleX',
  },
  [StatusType.DELETED]: {
    value: StatusType.DELETED,
    label: 'Deleted',
    color: 'text-destructive-foreground',
    bgColor: 'bg-destructive/10',
    icon: 'lucideCircleX',
  },
  [StatusType.NETWORK_ATTACK]: {
    value: StatusType.NETWORK_ATTACK,
    label: 'Network Attack',
    color: 'text-destructive-foreground',
    bgColor: 'bg-destructive/10',
    icon: 'lucideCircleX',
  },

  // Warning states
  [StatusType.WARNING]: {
    value: StatusType.WARNING,
    label: 'Warning',
    color: 'text-yellow-700',
    bgColor: 'bg-yellow-100',
    icon: 'lucideTriangleAlert',
  },
  [StatusType.ABNORMAL]: {
    value: StatusType.ABNORMAL,
    label: 'Abnormal',
    color: 'text-yellow-700',
    bgColor: 'bg-yellow-100',
    icon: 'lucideTriangleAlert',
  },

  // Info states
  [StatusType.INFO]: {
    value: StatusType.INFO,
    label: 'Info',
    color: 'text-info-foreground',
    bgColor: 'bg-info/10',
    icon: 'lucideInfo',
  },
  [StatusType.OTHER]: {
    value: StatusType.OTHER,
    label: 'Other',
    color: 'text-muted-foreground',
    bgColor: 'bg-muted/50',
    icon: 'lucideInfo',
  },

  // Inactive/Unknown states
  [StatusType.INACTIVE]: {
    value: StatusType.INACTIVE,
    label: 'Inactive',
    color: 'text-muted-foreground',
    bgColor: 'bg-muted/50',
    icon: 'lucideCircle',
  },
  [StatusType.UNKNOWN]: {
    value: StatusType.UNKNOWN,
    label: 'Unknown',
    color: 'text-muted-foreground',
    bgColor: 'bg-muted/50',
    icon: 'lucideCircle',
  },

  // Workload action statuses
  [StatusType.PARTIAL]: {
    value: StatusType.PARTIAL,
    label: 'Partial',
    color: 'text-warning-foreground',
    bgColor: 'bg-warning/10',
    icon: 'lucideCircle',
  },

  // Alert types
  [StatusType.MODELA]: {
    value: StatusType.MODELA,
    label: 'Model A',
    color: 'text-blue-700',
    bgColor: 'bg-blue-100',
    icon: 'lucideInfo',
  },
  [StatusType.MODELB]: {
    value: StatusType.MODELB,
    label: 'Model B',
    color: 'text-blue-700',
    bgColor: 'bg-blue-100',
    icon: 'lucideInfo',
  },
  [StatusType.MODELC]: {
    value: StatusType.MODELC,
    label: 'Model C',
    color: 'text-blue-700',
    bgColor: 'bg-blue-100',
    icon: 'lucideInfo',
  },

  // Additional mappings for Alert API formats
  Abnormal: {
    value: 'Abnormal',
    label: 'Abnormal',
    color: 'text-yellow-700',
    bgColor: 'bg-yellow-100',
    icon: 'lucideTriangleAlert',
  },
  'Network-Attack': {
    value: 'Network-Attack',
    label: 'Network Attack',
    color: 'text-red-700',
    bgColor: 'bg-red-100',
    icon: 'lucideCircleX',
  },
  Other: {
    value: 'Other',
    label: 'Other',
    color: 'text-gray-700',
    bgColor: 'bg-gray-100',
    icon: 'lucideInfo',
  },

  // Workload Action Status mappings
  Bind: {
    value: 'Bind',
    label: 'Bind',
    color: 'text-green-700',
    bgColor: 'bg-green-100',
    icon: 'lucideCircleCheck',
  },
  Create: {
    value: 'Create',
    label: 'Create',
    color: 'text-blue-700',
    bgColor: 'bg-blue-100',
    icon: 'lucideCircle',
  },
  Delete: {
    value: 'Delete',
    label: 'Delete',
    color: 'text-red-700',
    bgColor: 'bg-red-100',
    icon: 'lucideCircleX',
  },
  Move: {
    value: 'Move',
    label: 'Move',
    color: 'text-yellow-700',
    bgColor: 'bg-yellow-100',
    icon: 'lucideCircle',
  },
  Swap: {
    value: 'Swap',
    label: 'Swap',
    color: 'text-yellow-700',
    bgColor: 'bg-yellow-100',
    icon: 'lucideCircle',
  },
};

/**
 * Numeric status mapping (for legacy numeric status codes)
 */
const NUMERIC_STATUS_MAP: Record<number, StatusType> = {
  [-2]: StatusType.FAILED,
  [-1]: StatusType.WARNING,
  [0]: StatusType.INACTIVE,
  [1]: StatusType.RUNNING,
  [2]: StatusType.SUCCESS,
};

/**
 * Normalize status value to lowercase with underscores
 */
const normalizeStatus = (status: string | number | boolean): string => {
  if (typeof status === 'number') {
    return String(status);
  }

  if (typeof status === 'boolean') {
    return status ? 'approved' : 'rejected';
  }

  return String(status)
    .toLowerCase()
    .replace(/[^a-z0-9]/g, '_')
    .replace(/_+/g, '_')
    .replace(/^_|_$/g, '');
};

/**
 * Get status configuration for a given status value
 */
export const getStatusConfig = (
  status: string | number | boolean
): StatusConfig => {
  // Handle numeric status codes
  if (typeof status === 'number') {
    const mappedStatus = NUMERIC_STATUS_MAP[status];
    if (mappedStatus) {
      return STATUS_CONFIG_MAP[mappedStatus];
    }
  }

  // Handle boolean status
  if (typeof status === 'boolean') {
    return status
      ? STATUS_CONFIG_MAP[StatusType.SUCCESS]
      : STATUS_CONFIG_MAP[StatusType.FAILED];
  }

  // Handle string status with normalization
  if (typeof status === 'string') {
    const normalizedStatus = normalizeStatus(status);
    const config = STATUS_CONFIG_MAP[normalizedStatus];
    if (config) {
      return config;
    }

    // Also try direct lowercase lookup for backward compatibility
    const lowercaseStatus = status.toLowerCase();
    const fallbackConfig = STATUS_CONFIG_MAP[lowercaseStatus];
    if (fallbackConfig) {
      return fallbackConfig;
    }

    // Try exact match with enum values
    const enumConfig = STATUS_CONFIG_MAP[status as StatusType];
    if (enumConfig) {
      return enumConfig;
    }
  }

  // Default to unknown status
  return STATUS_CONFIG_MAP[StatusType.UNKNOWN];
};

/**
 * Get status color classes for a given status
 */
export const getStatusColor = (status: string | number | boolean): string => {
  const config = getStatusConfig(status);
  return `${config.color} ${config.bgColor}`;
};

/**
 * Get status icon for a given status
 */
export const getStatusIcon = (status: string | number | boolean): string => {
  const config = getStatusConfig(status);
  return config.icon;
};

/**
 * Get status label for a given status
 */
export const getStatusLabel = (status: string | number | boolean): string => {
  const config = getStatusConfig(status);
  return config.label;
};

/**
 * Get text color only for a given status
 */
export const getStatusTextColor = (
  status: string | number | boolean
): string => {
  const config = getStatusConfig(status);
  return config.color;
};

/**
 * Get progress color based on percentage
 */
export const getProgressColor = (percent: number): string => {
  if (percent >= 80) {
    return 'text-red-500';
  } else if (percent >= 60) {
    return 'text-yellow-700';
  } else {
    return 'text-green-700';
  }
};

/**
 * Get progress status based on percentage
 */
export const getProgressStatus = (percent: number): StatusType => {
  if (percent >= 80) {
    return StatusType.ERROR;
  } else if (percent >= 60) {
    return StatusType.WARNING;
  } else {
    return StatusType.SUCCESS;
  }
};

/**
 * Check if status is considered successful
 */
export const isSuccessStatus = (status: string | number | boolean): boolean => {
  const config = getStatusConfig(status);
  return [
    StatusType.SUCCESS,
    StatusType.SUCCESSFUL,
    StatusType.COMPLETED,
    StatusType.APPROVED,
    StatusType.BOUND,
    StatusType.BIND,
  ].includes(config.value as StatusType);
};

/**
 * Check if status is considered an error
 */
export const isErrorStatus = (status: string | number | boolean): boolean => {
  const config = getStatusConfig(status);
  return [
    StatusType.FAILED,
    StatusType.ERROR,
    StatusType.DELETED,
    StatusType.NETWORK_ATTACK,
  ].includes(config.value as StatusType);
};

/**
 * Check if status is considered a warning
 */
export const isWarningStatus = (status: string | number | boolean): boolean => {
  const config = getStatusConfig(status);
  return [StatusType.WARNING, StatusType.ABNORMAL].includes(
    config.value as StatusType
  );
};

/**
 * Check if status is considered active/running
 */
export const isActiveStatus = (status: string | number | boolean): boolean => {
  const config = getStatusConfig(status);
  return [StatusType.RUNNING, StatusType.CREATED, StatusType.PENDING].includes(
    config.value as StatusType
  );
};

/**
 * Get all available status types
 */
export const getAllStatusTypes = (): StatusType[] => {
  return Object.values(StatusType);
};

/**
 * Get status types by category
 */
export const getStatusTypesByCategory = () => {
  return {
    success: [
      StatusType.SUCCESS,
      StatusType.SUCCESSFUL,
      StatusType.COMPLETED,
      StatusType.APPROVED,
      StatusType.BOUND,
      StatusType.BIND,
    ],
    error: [
      StatusType.FAILED,
      StatusType.ERROR,
      StatusType.DELETED,
      StatusType.NETWORK_ATTACK,
    ],
    warning: [StatusType.WARNING, StatusType.ABNORMAL],
    active: [StatusType.RUNNING, StatusType.CREATED, StatusType.PENDING],
    info: [StatusType.INFO, StatusType.OTHER],
    inactive: [StatusType.INACTIVE, StatusType.UNKNOWN],
  };
};
