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
}
