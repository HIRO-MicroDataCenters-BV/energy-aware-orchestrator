import { Environment } from './environment.interface';

export const environment: Environment = {
  production: false,
  apiUrl: '/api',
  backendBaseUrl: 'http://0.0.0.0:8086',
  tokenKey: 'auth_token',
  refreshTokenKey: 'refresh_token',
  userKey: 'user',
  dashboardUrl: 'http://51.44.28.47:30016',
};
