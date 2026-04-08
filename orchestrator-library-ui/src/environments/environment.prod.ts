import { Environment } from './environment.interface';

export const environment: Environment = {
  production: true,
  backendBaseUrl: 'http://0.0.0.0:8086/api',
  tokenKey: 'auth_token',
  refreshTokenKey: 'refresh_token',
  userKey: 'user',
};
