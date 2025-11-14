/**
 * Shared Utils Index
 * Central export point for all shared utilities
 */

// Storage utilities
export * from './storage.utils';

// Status utilities
export * from './status.utils';

// Table data utilities
export * from './table-data.utils';

// Table action utilities
export * from './table-actions.utils';

// Navigation utilities
export * from './navigation.utils';

// Re-export commonly used functions with shorter names
export {
  getStorageItem as getStorage,
  setStorageItem as setStorage,
  removeStorageItem as removeStorage,
  clearStorage,
  getStorageObject,
  setStorageObject,
  hasStorageItem as hasStorage,
  isLocalStorageAvailable,
  TokenStorage,
  SessionStorage,
} from './storage.utils';

// Re-export commonly used status functions
export {
  getStatusConfig,
  getStatusColor,
  getStatusIcon,
  getStatusLabel,
  getStatusTextColor as getTextColor,
  getProgressColor,
  isSuccessStatus,
  isErrorStatus,
  isWarningStatus,
  isActiveStatus,
} from './status.utils';

// Re-export commonly used table data functions
export {
  getMainText,
  getSubText,
  getStatusValue,
  getProgressValue,
  getFormattedDate,
  getTruncatedText,
  formatBytes,
  formatNumber,
} from './table-data.utils';

// Re-export commonly used table action functions
export {
  createTableAction,
  createTableActionGroup,
  getAvailableActions,
  createCrudActions,
  createClusterActions,
  createWorkloadActions,
  createAlertActions,
} from './table-actions.utils';

// Re-export commonly used navigation functions
export {
  generateBreadcrumbs,
  formatSegmentLabel,
  getPageTitle,
  getParentRoute,
  isRouteActive,
} from './navigation.utils';
