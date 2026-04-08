/**
 * Environment Interface
 * Defines the structure for all environment configuration files
 */

export interface Environment {
  production: boolean;
  backendBaseUrl: string;
  tokenKey: string;
  refreshTokenKey: string;
  userKey: string;
}
