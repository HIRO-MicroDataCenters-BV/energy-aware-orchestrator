/**
 * Shared Models Index
 * Central export point for all shared models and types
 */

// ===================
// API Base Models
// ===================
export * from './api-base.model';

// ===================
// Kubernetes Models
// ===================
export * from './kubernetes.model';

// ===================
// Alerts Models
// ===================
export * from './alerts.model';

// ===================
// Auth Models
// ===================
export * from './auth.models';

// ===================
// Tuning Parameters Models
// ===================
export * from './tuning-parameters.model';

// ===================
// Workload Models
// ===================
export * from './workload-action.model';
export * from './workload-request-decision.model';

// ===================
// Export new centralized types
// ===================
export * from '../types/table.types';
export * from '../types/navigation.types';

// ===================
// Re-export shared types for convenience
// ===================
export type {
  // Base types
  BaseEntity,
  FilterParams,
  LoadingState,
  OperationResult,
  // Common HTTP types
  HttpMethod,
  ApiResponse,
  ApiError,
  ApiRequestConfig,
  // Additional API types
  PaginatedResponse,
  MessageResponse,
  IdResponse,
  ValidationError,
  HTTPValidationError,
} from '../types';

// ===================
// Re-export new centralized types
// ===================
export type {
  // Table types
  BaseTableData,
  ClusterTableData,
  PodTableData,
  AlertTableData,
  TableAction,
  TableActionGroup,
  TableColumn,
  TableConfig,
  TableDataSource,
  TableFilter,
  TableSort,
  TableState,
  ColumnVisibility,
  TableRowClickEvent,
  TableActionClickEvent,
  StatusConfig,
} from '../types/table.types';

export type {
  // Navigation types
  BreadcrumbItem,
  MenuItem,
  NavigationConfig,
  BreadcrumbConfig,
  RouteMetadata,
  NavigationState,
} from '../types/navigation.types';

// ===================
// Export enums from types
// ===================
export {
  GenericStatus,
  WorkloadActionType,
  WorkloadActionStatus,
  PodParentType,
} from '../types';

// ===================
// Export utility functions from types
// ===================
export {
  getActionTypeDisplayName,
  getActionStatusDisplayName,
  getPodParentTypeDisplayName,
  isWorkloadActionType,
  isWorkloadActionStatus,
  isPodParentType,
} from '../types';

// ===================
// Export new status utilities
// ===================
export {
  StatusType,
  getStatusConfig,
  getStatusColor,
  getStatusIcon,
  getStatusLabel,
  getStatusTextColor,
  getProgressColor,
  getProgressStatus,
  isSuccessStatus,
  isErrorStatus,
  isWarningStatus,
  isActiveStatus,
  getAllStatusTypes,
  getStatusTypesByCategory,
} from '../utils/status.utils';

// ===================
// Export table data utilities
// ===================
export {
  getMainText,
  getSubText,
  getStatusValue,
  getProgressValue,
  hasField,
  getFormattedDate,
  getTruncatedText,
  getNestedValue,
  formatBytes,
  formatNumber,
  isValidUrl,
  getFieldWithFallback,
} from '../utils/table-data.utils';

// ===================
// Export table action utilities
// ===================
export {
  createTableAction,
  createTableActionGroup,
  filterVisibleActions,
  filterEnabledActions,
  getActionById,
  isActionAvailable,
  getAvailableActions,
  groupActionsByCategory,
  formatCategoryLabel,
  sortActionsByPriority,
  createCrudActions,
  createClusterActions,
  createWorkloadActions,
  createAlertActions,
  isValidTableAction,
  isValidTableActionGroup,
  getActionConfirmationMessage,
  doesActionRequireConfirmation,
} from '../utils/table-actions.utils';

// ===================
// Export navigation utilities
// ===================
export {
  generateBreadcrumbs,
  formatSegmentLabel,
  isUUID,
  isShortId,
  getPageTitle,
  getParentRoute,
  isRouteActive,
  getRouteDepth,
  extractRouteParams,
  buildRoute,
  getRouteSegments,
  isProtectedRoute,
  getRouteIcon,
  getRouteTitle,
  isValidBreadcrumbItem,
  filterValidBreadcrumbs,
  truncateBreadcrumbs,
} from '../utils/navigation.utils';

// ===================
// Legacy aliases for backward compatibility
// ===================
// Alert aliases
export type { Alert, AlertCreate, AlertUpdate } from './alerts.model';

// Kubernetes aliases
export type {
  K8sPod,
  K8sNode,
  K8sPodResponse,
  K8sNodeResponse,
  K8sClusterInfoResponse,
  K8sTokenResponse,
  K8sPodParent,
} from './kubernetes.model';

// Tuning Parameters aliases
export type {
  TuningParameterCreate,
  TuningParameterResponse,
  TuningParameterUpdate,
} from './tuning-parameters.model';

// Workload aliases
export type {
  WorkloadAction,
  WorkloadActionCreate,
  WorkloadActionUpdate,
} from './workload-action.model';

export type {
  WorkloadRequestDecisionSchema,
  WorkloadRequestDecisionCreate,
  WorkloadRequestDecisionUpdate,
} from './workload-request-decision.model';

// ===================
// Re-export from api-base.model to avoid duplicates
// ===================
export type {
  PaginationParams as CommonQueryParams,
  DateRangeParams as DateRangeQueryParams,
  PaginatedResponse as ListResponse,
} from './api-base.model';

// ===================
// Utility type guards moved to separate files
// ===================

// ===================
// Legacy exports for convenience
// ===================
export type {
  AlertCreateRequest,
  AlertResponse,
  AlertQueryParams,
} from './alerts.model';

export { AlertType } from './alerts.model';
