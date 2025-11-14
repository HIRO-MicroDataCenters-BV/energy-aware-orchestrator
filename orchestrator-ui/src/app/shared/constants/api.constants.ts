/**
 * API Constants
 * Centralized API endpoints and related constants
 */

// ======================
// API Endpoints
// ======================

export const API_ENDPOINTS = {
  // Kubernetes endpoints
  K8S: {
    PODS: '/k8s_pod/',
    NODES: '/k8s_node/',
    CLUSTER_INFO: '/k8s_cluster_info/',
    TOKEN: '/k8s_get_token/',
    USER_PODS: '/k8s_user_pod/',
    POD_PARENT: '/k8s_pod_parent/',
  },

  // Alert endpoints
  ALERTS: '/alerts/',

  // Workload Request Decision endpoints
  WORKLOAD_REQUEST_DECISION: {
    BASE: '/workload_request_decision/',
    BY_ID: (id: string) => `/workload_request_decision/${id}`,
  },

  // Workload Action endpoints
  WORKLOAD_ACTION: {
    BASE: '/workload_action/',
    BY_ID: (id: string) => `/workload_action/${id}`,
  },

  // Dummy ACES UI
  DUMMY_ACES_UI: '/dummy_aces_ui/',
} as const;

// ======================
// HTTP Headers
// ======================

export const HTTP_HEADERS = {
  CONTENT_TYPE: 'application/json',
  AUTHORIZATION: 'Authorization',
  BEARER_PREFIX: 'Bearer',
} as const;

// ======================
// LocalStorage Keys
// ======================

export const STORAGE_KEYS = {
  ACCESS_TOKEN: 'auth_token',
  REFRESH_TOKEN: 'refresh_token',
  USER: 'user',
} as const;

// ======================
// API Configuration
// ======================

export const API_CONFIG = {
  DEFAULT_PAGINATION: {
    SKIP: 0,
    LIMIT: 100,
  },
  TIMEOUT: 30000, // 30 seconds
  RETRY_ATTEMPTS: 3,
} as const;

// ======================
// HTTP Status Codes
// ======================

export const HTTP_STATUS = {
  OK: 200,
  CREATED: 201,
  NO_CONTENT: 204,
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  INTERNAL_SERVER_ERROR: 500,
  SERVICE_UNAVAILABLE: 503,
} as const;

// ======================
// Error Messages
// ======================

export const ERROR_MESSAGES = {
  NETWORK_ERROR: 'common.networkError',
  UNAUTHORIZED: 'common.unauthorized',
  NOT_FOUND: 'common.notFound',
  SERVER_ERROR: 'common.serverError',
  UNKNOWN_ERROR: 'common.unknownError',
  CLIENT_ERROR: 'common.clientError',
  UNSUPPORTED_METHOD: 'common.unsupportedMethod',
} as const;

// ======================
// Query Parameter Keys
// ======================

export const QUERY_PARAMS = {
  // Common pagination
  SKIP: 'skip',
  LIMIT: 'limit',

  // Date filtering
  START_DATE: 'start_date',
  END_DATE: 'end_date',

  // Kubernetes specific
  NAMESPACE: 'namespace',
  NODE_NAME: 'node_name',
  POD_NAME: 'name',
  POD_ID: 'pod_id',
  NODE_ID: 'node_id',
  STATUS: 'status',
  SERVICE_ACCOUNT_NAME: 'service_account_name',

  // Workload Actions
  ACTION_TYPE: 'action_type',
  ACTION_STATUS: 'action_status',
} as const;

// ======================
// Default Values
// ======================

export const DEFAULT_VALUES = {
  NAMESPACE: 'hiros',
  SERVICE_ACCOUNT: 'readonly-user',
} as const;

// ======================
// Content Types
// ======================

export const CONTENT_TYPES = {
  JSON: 'application/json',
  HTML: 'text/html',
  XML: 'application/xml',
  FORM_DATA: 'multipart/form-data',
  URL_ENCODED: 'application/x-www-form-urlencoded',
} as const;
