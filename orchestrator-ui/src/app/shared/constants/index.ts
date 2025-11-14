/**
 * Shared Constants Index
 * Central export point for all shared constants
 */

// Application constants
export * from './app.constants';

// API constants (if exists)
export * from './api.constants';

// Re-export commonly used constants
export {
  API_CONSTANTS,
  API_PATHS,
  HTTP_STATUS,
  STORAGE_KEYS,
  ROUTES,
  UI_CONSTANTS,
  VALIDATION,
  DATE_TIME,
  ENVIRONMENT,
  EXTERNAL_URLS,
  FEATURE_FLAGS,
  RESOURCE_UNITS,
  STATUS_COLORS,
  TABLE_CONSTANTS,
  K8S_CONSTANTS,
  ERROR_MESSAGES,
  SUCCESS_MESSAGES,
  LOADING_MESSAGES,
  isProduction,
  isDevelopment,
  isStaging,
  isTest,
} from './app.constants';
