/**
 * Shared Module Index
 * Central export point for all shared modules, types, constants, models, and utilities
 */

// Export all types and interfaces
export * from './types';

// Export all constants
export * from './constants';

// Export specific models (avoid duplicates with types)
export * from './models/kubernetes.model';

// Export all utilities
export * from './utils';

// Re-export legacy model aliases for backward compatibility
export type { AlertCreateRequest, AlertResponse, AlertUpdate } from './models';

// Re-export commonly used enums
export {
  WorkloadActionType,
  WorkloadActionStatus,
  AlertType,
  AlertSeverity,
  AlertStatus,
} from './types';

// Re-export commonly used constants
export {
  API_CONSTANTS,
  STORAGE_KEYS,
  ROUTES,
  ERROR_MESSAGES,
  SUCCESS_MESSAGES,
} from './constants';

// Re-export commonly used utilities
export {
  TokenStorage,
  getStorage,
  setStorage,
  removeStorage,
  isLocalStorageAvailable,
} from './utils';
