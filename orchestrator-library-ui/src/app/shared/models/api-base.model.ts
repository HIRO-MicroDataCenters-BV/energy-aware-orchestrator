/**
 * Base API types and interfaces
 * Contains common types used across all API services
 */

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';

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
 * Pagination parameters
 */
export interface PaginationParams {
  skip?: number;
  limit?: number;
}

/**
 * Date range filtering parameters
 */
export interface DateRangeParams {
  start_date?: string;
  end_date?: string;
}

/**
 * Paginated response interface
 */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

/**
 * Base entity with common fields
 * Note: Changed to use string | null to match API responses and fix compatibility
 */
export interface BaseEntity {
  id: string;
  created_at?: string | null;
  updated_at?: string | null;
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

/**
 * Common response types
 */
export interface MessageResponse {
  message: string;
}

export interface IdResponse {
  id: string | number;
}

/**
 * Generic filter parameters
 */
export interface FilterParams {
  [key: string]: string | number | boolean | undefined | null;
}

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
