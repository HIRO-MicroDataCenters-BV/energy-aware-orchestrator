/**
 * Environment Interface
 * Defines the structure for all environment configuration files
 */

export interface Environment {
  production: boolean;
  apiUrl: string;
  backendBaseUrl: string;
  tokenKey: string;
  refreshTokenKey: string;
  userKey: string;
  dashboardUrl: string;
  cogUrl: string;
  oidc: {
    authority: string;
    clientId: string;
    clientSecret: string;
    scope: string;
    responseType: string;
    silentRenew: boolean;
    useRefreshToken: boolean;
    renewTimeBeforeTokenExpiresInSeconds: number;
    historyCleanupOff: boolean;
    autoUserInfo: boolean;
    triggerRefreshWhenIdTokenExpired: boolean;
    logLevel: number;
    redirectUri: string;
    postLogoutRedirectUri: string;
    tokenEndpoint: string;
    authorizationEndpoint: string;
    userInfoEndpoint: string;
    endSessionEndpoint: string;
  };
}
