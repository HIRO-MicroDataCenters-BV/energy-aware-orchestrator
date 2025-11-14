/**
 * OpenID Connect Configuration
 * Configuration for angular-auth-oidc-client with DEX provider
 */

import { LogLevel } from 'angular-auth-oidc-client';
import { environment } from '../../../../environments/environment';
import { AUTH_CONSTANTS } from '../../../shared/constants/app.constants';
import { OidcConfig } from '../../../shared/models/auth.models';

/**
 * Get OIDC configuration for the current environment
 */
export function getOidcConfig(): OidcConfig {
  // Always use localhost:4200 for dev server regardless of browser URL
  const baseUrl = 'http://localhost:4200';

  return {
    authority: `${baseUrl}/dex`,
    redirectUrl: `${baseUrl}${AUTH_CONSTANTS.ROUTES.CALLBACK}`,
    postLogoutRedirectUri: `${baseUrl}${AUTH_CONSTANTS.ROUTES.AFTER_LOGOUT}`,
    clientId: AUTH_CONSTANTS.OIDC.CLIENT_ID,
    scope: AUTH_CONSTANTS.OIDC.SCOPE,
    responseType: AUTH_CONSTANTS.OIDC.RESPONSE_TYPE,
    silentRenew: false, // Disable silent renew to avoid discovery issues
    useRefreshToken: false, // Disable refresh tokens for now
    renewTimeBeforeTokenExpiresInSeconds:
      AUTH_CONSTANTS.OIDC.RENEW_TIME_BEFORE_TOKEN_EXPIRES,
    logLevel: LogLevel.Debug, // Always debug for now
    historyCleanupOff: true,
    autoUserInfo: false, // Disable auto user info to avoid discovery
    triggerRefreshWhenIdTokenExpired: false,

    // Completely disable discovery and use manual endpoints only
    wellKnownEndpoints: {
      issuer: 'http://localhost:4200/dex',
      authorizationEndpoint: 'http://localhost:4200/dex/auth',
      tokenEndpoint: 'http://localhost:4200/dex/token',
      userinfoEndpoint: 'http://localhost:4200/dex/userinfo',
      endSessionEndpoint: 'http://localhost:4200/dex/logout',
      jwksUri: 'http://localhost:4200/dex/keys',
    },

    // Routes for navigation after auth events
    postLoginRoute: AUTH_CONSTANTS.ROUTES.AFTER_LOGIN,
    forbiddenRoute: AUTH_CONSTANTS.ROUTES.FORBIDDEN,
    unauthorizedRoute: AUTH_CONSTANTS.ROUTES.UNAUTHORIZED,

    // Secure routes that require authentication
    secureRoutes: [
      environment.apiUrl,
      environment.dashboardUrl,
      environment.cogUrl,
    ],

    // Custom parameters for auth requests
    customParamsAuthRequest: {
      // Add any custom parameters required by DEX
      prompt: 'login',
      // client_name: 'Orchestrator UI',
    },

    // Custom parameters for refresh token requests
    customParamsRefreshTokenRequest: {},

    // Custom parameters for end session requests
    customParamsEndSessionRequest: {},

    // Silent renew configuration
    silentRenewUrl: `${baseUrl}/silent-renew.html`,

    // Token validation
    ignoreNonceAfterRefresh: true,
    triggerAuthorizationResultEvent: true,

    // PKCE configuration (recommended for SPA)
    usePushedAuthorisationRequests: false,

    // Additional security settings
    skipSubjectCheck: false,

    // Storage configuration
    storage:
      typeof window !== 'undefined' && typeof localStorage !== 'undefined'
        ? localStorage
        : null,
  };
}

/**
 * Get OIDC configuration for mock/development mode
 */
export function getMockOidcConfig(): OidcConfig {
  const baseUrl =
    typeof window !== 'undefined'
      ? window.location.origin
      : 'http://localhost:4200';

  return {
    authority: 'https://mock-authority.local',
    redirectUrl: `${baseUrl}${AUTH_CONSTANTS.ROUTES.CALLBACK}`,
    postLogoutRedirectUri: `${baseUrl}${AUTH_CONSTANTS.ROUTES.AFTER_LOGOUT}`,
    clientId: 'mock-client-id',
    scope: 'openid profile email',
    responseType: 'code',
    silentRenew: false,
    useRefreshToken: false,
    logLevel: LogLevel.Debug,
    historyCleanupOff: true,
    autoUserInfo: false,

    // Disable OIDC validation for mock mode
    disableIdTokenValidation: true,
    skipSubjectCheck: true,

    // Mock routes
    postLoginRoute: AUTH_CONSTANTS.ROUTES.AFTER_LOGIN,
    forbiddenRoute: AUTH_CONSTANTS.ROUTES.FORBIDDEN,
    unauthorizedRoute: AUTH_CONSTANTS.ROUTES.UNAUTHORIZED,
  };
}

/**
 // DEX-specific configuration overrides
 */
export const DEX_CONFIG_OVERRIDES = {
  // DEX typically uses these scopes
  scope: 'openid profile email groups',

  // Disable features that require discovery
  silentRenew: false,
  useRefreshToken: false,
  autoUserInfo: false,

  // Simplified custom parameters for DEX
  customParamsAuthRequest: {},
};

/**
 * Get final OIDC configuration with environment-specific overrides
 */
export function getFinalOidcConfig(): OidcConfig {
  const baseConfig = getOidcConfig();

  // Always apply DEX overrides since we're using DEX
  return {
    ...baseConfig,
    ...DEX_CONFIG_OVERRIDES,
  };
}

/**
 * Check if DEX is available
 */
export async function isDexAvailable(): Promise<boolean> {
  try {
    const response = await fetch(
      `${AUTH_CONSTANTS.OIDC.AUTHORITY}/.well-known/openid_configuration`,
      {
        method: 'GET',
        mode: 'cors',
        cache: 'no-cache',
      }
    );
    return response.ok;
  } catch (error) {
    console.warn('DEX availability check failed:', error);
    return false;
  }
}

/**
 * Get configuration based on DEX availability
 */
export async function getAdaptiveOidcConfig(): Promise<OidcConfig> {
  // Always return the real config - the auth service will handle mock mode
  return getFinalOidcConfig();
}
