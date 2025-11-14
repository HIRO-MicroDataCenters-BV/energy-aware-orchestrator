/**
 * Authentication Models
 * Contains interfaces and types for authentication system
 */

// ===================
// User Models
// ===================

export interface User {
  id: string;
  email: string;
  name: string;
  firstName?: string;
  lastName?: string;
  roles: string[];
  permissions?: string[];
  avatar?: string;
  isEmailVerified?: boolean;
  lastLoginAt?: Date;
  createdAt?: Date;
  updatedAt?: Date;
}

export interface UserProfile {
  sub: string;
  email: string;
  name: string;
  given_name?: string;
  family_name?: string;
  picture?: string;
  email_verified?: boolean;
  locale?: string;
  preferred_username?: string;
  roles?: string[];
}

// ===================
// Token Models
// ===================

export interface TokenResponse {
  access_token: string;
  refresh_token?: string;
  id_token?: string;
  token_type: string;
  expires_in: number;
  scope?: string;
}

export interface AuthTokens {
  accessToken: string;
  refreshToken?: string;
  idToken?: string;
  expiresAt: number;
  scope?: string;
}

// ===================
// Auth State Models
// ===================

export interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: User | null;
  tokens: AuthTokens | null;
  error: string | null;
  lastActivity?: Date;
}

export interface LoginCredentials {
  email: string;
  password: string;
  rememberMe?: boolean;
}

export interface LoginResponse {
  success: boolean;
  user?: User;
  tokens?: AuthTokens;
  error?: string;
  message?: string;
}

// ===================
// OIDC Configuration Models
// ===================

export interface OidcConfig {
  authority: string;
  clientId: string;
  redirectUrl: string;
  postLogoutRedirectUri: string;
  scope: string;
  responseType: string;
  silentRenew: boolean;
  useRefreshToken: boolean;
  logLevel?: number;
  customParamsAuthRequest?: Record<string, string>;
  customParamsRefreshTokenRequest?: Record<string, string>;
  customParamsEndSessionRequest?: Record<string, string>;
  secureRoutes?: string[];
  postLoginRoute?: string;
  forbiddenRoute?: string;
  unauthorizedRoute?: string;
  historyCleanupOff?: boolean;
  autoUserInfo?: boolean;
  renewTimeBeforeTokenExpiresInSeconds?: number;
  triggerRefreshWhenIdTokenExpired?: boolean;
  silentRenewUrl?: string;
  ignoreNonceAfterRefresh?: boolean;
  triggerAuthorizationResultEvent?: boolean;
  usePushedAuthorisationRequests?: boolean;
  disableIdTokenValidation?: boolean;
  skipSubjectCheck?: boolean;
  storage?: Storage | null;
  wellKnownEndpoints?: {
    issuer?: string;
    authorizationEndpoint?: string;
    tokenEndpoint?: string;
    userinfoEndpoint?: string;
    endSessionEndpoint?: string;
    jwksUri?: string;
  };
}

// ===================
// Mock Auth Models
// ===================

export interface MockUser {
  email: string;
  password: string;
  user: User;
}

export interface MockAuthConfig {
  enabled: boolean;
  users: MockUser[];
  delay?: number;
  simulateNetworkDelay?: boolean;
}

// ===================
// Auth Error Models
// ===================

export interface AuthError {
  code: string;
  message: string;
  details?: string;
  timestamp: Date;
  type: AuthErrorType;
}

export enum AuthErrorType {
  INVALID_CREDENTIALS = 'INVALID_CREDENTIALS',
  TOKEN_EXPIRED = 'TOKEN_EXPIRED',
  NETWORK_ERROR = 'NETWORK_ERROR',
  OIDC_ERROR = 'OIDC_ERROR',
  UNAUTHORIZED = 'UNAUTHORIZED',
  FORBIDDEN = 'FORBIDDEN',
  UNKNOWN = 'UNKNOWN',
}

// ===================
// Route Guards Models
// ===================

export interface AuthGuardConfig {
  redirectToLogin: boolean;
  loginRoute: string;
  returnUrl?: string;
  requiredRoles?: string[];
  requiredPermissions?: string[];
}

// ===================
// Session Models
// ===================

export interface SessionInfo {
  sessionId: string;
  userId: string;
  createdAt: Date;
  lastActivityAt: Date;
  expiresAt: Date;
  isActive: boolean;
  deviceInfo?: DeviceInfo;
}

export interface DeviceInfo {
  userAgent: string;
  platform: string;
  browser: string;
  ip?: string;
  location?: string;
}

// ===================
// Auth Events Models
// ===================

export enum AuthEventType {
  LOGIN_SUCCESS = 'LOGIN_SUCCESS',
  LOGIN_FAILED = 'LOGIN_FAILED',
  LOGOUT = 'LOGOUT',
  TOKEN_REFRESHED = 'TOKEN_REFRESHED',
  TOKEN_EXPIRED = 'TOKEN_EXPIRED',
  SESSION_TIMEOUT = 'SESSION_TIMEOUT',
  UNAUTHORIZED_ACCESS = 'UNAUTHORIZED_ACCESS',
}

export interface AuthEvent {
  type: AuthEventType;
  timestamp: Date;
  userId?: string;
  data?: unknown;
  error?: AuthError;
}

// ===================
// Permission Models
// ===================

export interface Permission {
  id: string;
  name: string;
  description?: string;
  resource: string;
  action: string;
}

export interface Role {
  id: string;
  name: string;
  description?: string;
  permissions: Permission[];
  isDefault?: boolean;
}

// ===================
// Type Guards
// ===================

export const isUser = (obj: unknown): obj is User => {
  return (
    obj !== null &&
    typeof obj === 'object' &&
    'id' in obj &&
    'email' in obj &&
    typeof (obj as Record<string, unknown>)['id'] === 'string' &&
    typeof (obj as Record<string, unknown>)['email'] === 'string'
  );
};

export const isAuthTokens = (obj: unknown): obj is AuthTokens => {
  return (
    obj !== null &&
    typeof obj === 'object' &&
    'accessToken' in obj &&
    'expiresAt' in obj &&
    typeof (obj as Record<string, unknown>)['accessToken'] === 'string' &&
    typeof (obj as Record<string, unknown>)['expiresAt'] === 'number'
  );
};

export const isAuthError = (obj: unknown): obj is AuthError => {
  return (
    obj !== null &&
    typeof obj === 'object' &&
    'code' in obj &&
    'message' in obj &&
    typeof (obj as Record<string, unknown>)['code'] === 'string' &&
    typeof (obj as Record<string, unknown>)['message'] === 'string'
  );
};

// ===================
// Constants
// ===================

export const DEFAULT_ROLES = {
  ADMIN: 'admin',
  USER: 'user',
  VIEWER: 'viewer',
} as const;

export const DEFAULT_PERMISSIONS = {
  READ: 'read',
  WRITE: 'write',
  DELETE: 'delete',
  ADMIN: 'admin',
} as const;

export const AUTH_STORAGE_KEYS = {
  ACCESS_TOKEN: 'auth_access_token',
  REFRESH_TOKEN: 'auth_refresh_token',
  ID_TOKEN: 'auth_id_token',
  USER: 'auth_user',
  STATE: 'auth_state',
  RETURN_URL: 'auth_return_url',
} as const;
