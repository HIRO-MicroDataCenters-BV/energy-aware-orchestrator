/**
 * Common Types and Interfaces
 * Contains shared types used across the entire application
 */

// ===================
// Base Types
// ===================

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';

export type Nullable<T> = T | null;
export type Optional<T> = T | undefined;
export type NullableOptional<T> = T | null | undefined;

// ===================
// API Response Types
// ===================

/**
 * Generic API response wrapper
 */
export interface ApiResponse<T = unknown> {
  data?: T;
  message?: string;
  status: number;
}

/**
 * API error interface
 */
export interface ApiError {
  status: number;
  message: string;
  details?: unknown;
}

/**
 * Message response interface
 */
export interface MessageResponse {
  message: string;
}

/**
 * ID response interface
 */
export interface IdResponse {
  id: string | number;
}

/**
 * HTTP validation error structure (from FastAPI)
 */
export interface HTTPValidationError {
  detail: ValidationError[];
}

/**
 * Validation error detail
 */
export interface ValidationError {
  loc: (string | number)[];
  msg: string;
  type: string;
}

// ===================
// Base Entity
// ===================

/**
 * Base entity with common fields
 * Note: Using string | null to match API responses
 */
export interface BaseEntity {
  id: string;
  created_at?: string | null;
  updated_at?: string | null;
}

// ===================
// Pagination Types
// ===================

/**
 * Pagination parameters
 */
export interface PaginationParams {
  skip?: number;
  limit?: number;
}

/**
 * Paginated response wrapper
 */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

// ===================
// Date and Time Types
// ===================

/**
 * Date range filtering parameters
 */
export interface DateRangeParams {
  start_date?: string;
  end_date?: string;
}

/**
 * Timestamp interface
 */
export interface Timestamp {
  created_at: string;
  updated_at?: string;
}

// ===================
// Filter Types
// ===================

/**
 * Generic filter parameters
 */
export interface FilterParams {
  [key: string]: string | number | boolean | undefined | null;
}

/**
 * Sort parameters
 */
export interface SortParams {
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

// ===================
// API Request Types
// ===================

/**
 * API request configuration
 */
export interface ApiRequestConfig {
  method: HttpMethod;
  url: string;
  data?: unknown;
  params?: Record<string, unknown>;
  headers?: Record<string, string>;
}

/**
 * Generic API query parameters
 */
export interface ApiQueryParams
  extends PaginationParams,
    DateRangeParams,
    SortParams {
  [key: string]: unknown;
}

// ===================
// UI Component Types
// ===================

/**
 * Generic table column definition
 */
export interface TableColumn {
  key: string;
  label: string;
  sortable?: boolean;
  width?: string;
  type?: 'string' | 'number' | 'date' | 'boolean' | 'custom';
}

/**
 * Menu item interface
 */
export interface MenuItem {
  label: string | null;
  icon: string | null;
  route: string;
  items?: MenuItem[];
  expanded?: boolean;
  disabled?: boolean;
}

/**
 * Loading state
 */
export interface LoadingState {
  isLoading: boolean;
  error?: string | null;
}

// ===================
// Status Types
// ===================

/**
 * Generic status enum
 */
export enum GenericStatus {
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  PENDING = 'pending',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
}

/**
 * Operation result
 */
export interface OperationResult<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

// ===================
// Resource Types
// ===================

/**
 * Resource usage statistics
 */
export interface ResourceUsage {
  cpu: number;
  memory: number;
  storage?: number;
}

/**
 * Resource limits
 */
export interface ResourceLimits {
  cpu_limit?: number;
  memory_limit?: number;
  storage_limit?: number;
}

// ===================
// Utility Types
// ===================

/**
 * Deep partial type
 */
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

/**
 * Pick properties of specific type
 */
export type PickByType<T, U> = {
  [K in keyof T as T[K] extends U ? K : never]: T[K];
};

/**
 * Omit properties of specific type
 */
export type OmitByType<T, U> = {
  [K in keyof T as T[K] extends U ? never : K]: T[K];
};

/**
 * Create type with all properties required
 */
export type RequiredAll<T> = {
  [K in keyof T]-?: T[K];
};

// ===================
// Event Types
// ===================

/**
 * Generic event interface
 */
export interface AppEvent<T = unknown> {
  type: string;
  payload?: T;
  timestamp: string;
  source?: string;
}

/**
 * User action event
 */
export interface UserActionEvent extends AppEvent {
  userId?: string;
  action: string;
  target?: string;
}
