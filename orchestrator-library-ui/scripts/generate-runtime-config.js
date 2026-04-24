const fs = require('fs');
const path = require('path');
const dotenv = require('dotenv');

const projectRoot = path.resolve(__dirname, '..');
const envPath = path.join(projectRoot, '.env');
const envLocalPath = path.join(projectRoot, '.env.local');
const runtimeConfigPath = path.join(
  projectRoot,
  'src/app/core/config/runtime.config.ts'
);

dotenv.config({ path: envPath });
dotenv.config({ path: envLocalPath, override: true });

const useEnvMode = process.argv.includes('--from-env');

let apiBaseUrl = '/api';
let appBaseUrl = '/app';

if (useEnvMode) {
  const configuredBase =
    process.env.API_URL ||
    process.env.API_BACKEND_URL ||
    process.env.API_TARGET ||
    'http://0.0.0.0:8086';

  const normalized = configuredBase.trim().replace(/\/+$/, '');
  const origin = normalized.replace(/\/(api|app)$/, '');
  apiBaseUrl = `${origin}/api`;
  appBaseUrl = `${origin}/app`;
}

const content = `export const RUNTIME_CONFIG = {
  apiBaseUrl: '${apiBaseUrl}',
  appBaseUrl: '${appBaseUrl}',
  tokenKey: 'auth_token',
  refreshTokenKey: 'refresh_token',
  userKey: 'user',
} as const;
`;

fs.writeFileSync(runtimeConfigPath, content, 'utf8');
console.log(
  `[runtime-config] mode=${useEnvMode ? 'env' : 'relative'} apiBaseUrl=${apiBaseUrl} appBaseUrl=${appBaseUrl}`
);

