/**
 * Auth Services Index
 * Central export point for all authentication services, guards, and utilities
 */

// ===================
// Core Services
// ===================
export * from './auth.service';
export * from './oidc.config';

// ===================
// Guards
// ===================
export * from './auth.guard';

// ===================
// Interceptors
// ===================
export * from './auth.interceptor';

// ===================
// Re-export from mock service
// ===================
export { MockAuthService } from '../../../mock/auth.mock';

// ===================
// Auth Configuration Utilities
// ===================
export {
  getOidcConfig,
  getMockOidcConfig,
  getFinalOidcConfig,
  getAdaptiveOidcConfig,
  isDexAvailable,
  DEX_CONFIG_OVERRIDES,
} from './oidc.config';

// ===================
// Guard Factories
// ===================
export {
  createPermissionGuard,
  createRoleGuard,
  AdminGuard,
  GuestGuard,
} from './auth.guard';

// ===================
// Interceptor Functions
// ===================
export {
  authInterceptor,
  AuthInterceptor,
} from './auth.interceptor';

// ===================
// Type Re-exports for convenience
// ===================
export type {
  User,
  AuthState,
  LoginCredentials,
  LoginResponse,
  AuthTokens,
  AuthError,
  AuthErrorType,
  UserProfile,
  OidcConfig,
  MockUser,
  MockAuthConfig,
  AuthGuardConfig,
  SessionInfo,
  DeviceInfo,
  AuthEvent,
  AuthEventType,
  Permission,
  Role,
} from '../../../shared/models/auth.models';

// ===================
// Constants Re-export
// ===================
export {
  DEFAULT_ROLES,
  DEFAULT_PERMISSIONS,
  AUTH_STORAGE_KEYS,
} from '../../../shared/models/auth.models';

export {
  AUTH_CONSTANTS,
} from '../../../shared/constants/app.constants';

// ===================
// Utility Functions
// ===================
export {
  isUser,
  isAuthTokens,
  isAuthError,
} from '../../../shared/models/auth.models';
