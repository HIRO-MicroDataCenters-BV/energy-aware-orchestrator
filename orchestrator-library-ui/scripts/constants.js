/**
 * Constants for Proxy Configuration and Testing
 * Centralized configuration using environment variables and i18n
 */

const fs = require('fs');
const path = require('path');

// Load environment configuration
function loadEnvironment() {
  const envPath =
    process.env.NODE_ENV === 'production'
      ? '../src/environments/environment.prod.ts'
      : '../src/environments/environment.development.ts';

  try {
    // For now, use default values as we can't easily import TS from Node.js
    // In a real scenario, you'd convert to JSON or use a build step
    return {
      production: process.env.NODE_ENV === 'production',
      apiUrl: process.env.API_URL || 'http://localhost:8086',
      dashboardUrl: process.env.DASHBOARD_URL || 'http://localhost:8086',
      cogUrl: process.env.COG_URL || '/cog',
      oidc: {
        authority: process.env.OIDC_AUTHORITY || '/dex',
        clientId: process.env.OIDC_CLIENT_ID || 'authservice-oidc',
        scope: process.env.OIDC_SCOPE || 'openid profile email groups',
      },
    };
  } catch (error) {
    console.warn('Could not load environment, using defaults');
    return {
      production: false,
      apiUrl: 'http://localhost:8086',
      dashboardUrl: 'http://localhost:8086',
      cogUrl: '/cog',
      oidc: {
        authority: '/dex',
        clientId: 'authservice-oidc',
        scope: 'openid profile email groups',
      },
    };
  }
}

// Load i18n messages
function loadI18nMessages() {
  try {
    const i18nPath = path.join(
      __dirname,
      '..',
      'public',
      'assets',
      'i18n',
      'en.json'
    );
    const content = fs.readFileSync(i18nPath, 'utf8');
    return JSON.parse(content);
  } catch (error) {
    console.warn('Could not load i18n messages, using defaults');
    return { proxy_test: {} };
  }
}

const ENV = loadEnvironment();
const I18N = loadI18nMessages();

// Base URLs from environment
const BASE_URLS = {
  LOCAL_DEV: process.env.LOCAL_DEV_URL || 'http://localhost:4200',
  API_BACKEND: process.env.API_BACKEND_URL || 'http://51.44.28.47:30015',
  K8S_DASHBOARD: process.env.K8S_DASHBOARD_URL || 'http://51.44.28.47:30016',
  COG_DEV: process.env.COG_DEV_URL || 'https://dashboard.cog.hiro-develop.nl',
  COG_PROD: process.env.COG_PROD_URL || 'http://51.44.28.47:30080',
  DEX_AUTH: process.env.DEX_AUTH_URL || 'http://51.44.28.47:30080',
};

// Proxy paths configuration
const PROXY_PATHS = {
  API: '/api',
  IFRAME: '/iframe',
  COG: '/cog',
  COG_IFRAME: '/cog-iframe',
  DEX: '/dex',
};

// Target paths on backend servers
const TARGET_PATHS = {
  API_HEALTH: '/health',
  K8S_NAMESPACES: '/api/v1/namespace',
  COG_UI: '/cogui',
  DEX_AUTH: '/dex/auth',
  DEX_CALLBACK: '/authservice/oidc/callback',
  OIDC_DISCOVERY: '/.well-known/openid_configuration',
};

// Test endpoints configuration
const TEST_ENDPOINTS = [
  {
    name: I18N.proxy_test?.endpoints?.api_health || 'API Health Check',
    path: PROXY_PATHS.API + '/health',
    target: BASE_URLS.API_BACKEND,
    targetPath: TARGET_PATHS.API_HEALTH,
    expectedStatus: [200, 404],
    description: 'Backend API health endpoint',
  },
  {
    name:
      I18N.proxy_test?.endpoints?.cog_dashboard_dev ||
      'COG Dashboard Proxy (Dev)',
    path: PROXY_PATHS.COG,
    target: BASE_URLS.COG_DEV,
    targetPath: TARGET_PATHS.COG_UI,
    expectedStatus: [200, 302, 401, 403, 500],
    description: 'COG dashboard development environment',
    authRequired: true,
    authRedirectExpected: true,
  },
  {
    name:
      I18N.proxy_test?.endpoints?.cog_iframe_prod ||
      'COG iframe Proxy (Production)',
    path: PROXY_PATHS.COG_IFRAME,
    target: BASE_URLS.COG_PROD,
    targetPath: TARGET_PATHS.COG_UI,
    expectedStatus: [200, 302, 401, 403],
    description: 'COG dashboard production environment',
    authRequired: true,
    authRedirectExpected: true,
  },
  {
    name:
      I18N.proxy_test?.endpoints?.kubernetes_dashboard ||
      'Kubernetes Dashboard Proxy',
    path: PROXY_PATHS.IFRAME + TARGET_PATHS.K8S_NAMESPACES,
    target: BASE_URLS.K8S_DASHBOARD,
    targetPath: TARGET_PATHS.K8S_NAMESPACES,
    expectedStatus: [200, 302, 401, 403],
    description: 'Kubernetes API server namespaces',
    authRequired: true,
    authRedirectExpected: false,
  },
  {
    name: I18N.proxy_test?.endpoints?.dex_auth || 'DEX Auth Endpoint',
    path: PROXY_PATHS.DEX + '/.well-known/openid_configuration',
    target: BASE_URLS.DEX_AUTH,
    targetPath: TARGET_PATHS.OIDC_DISCOVERY,
    expectedStatus: [200, 302, 404],
    description: 'DEX OIDC discovery endpoint',
    authRequired: false,
    authRedirectExpected: true,
  },
];

// Authentication flow configuration from environment
const AUTH_CONFIG = {
  // DEX authentication parameters from environment
  DEX_CLIENT_ID: ENV.oidc.clientId,
  DEX_RESPONSE_TYPE: process.env.OIDC_RESPONSE_TYPE || 'code',
  DEX_SCOPE: ENV.oidc.scope,

  // Cookie names
  COOKIES: {
    SESSION: 'authservice_session',
    OIDC_STATE: 'oidc_state_csrf',
  },

  // Auth flow paths
  FLOW_PATHS: {
    AUTH: '/dex/auth',
    CALLBACK: '/authservice/oidc/callback',
    LOGIN: '/dex/auth/local',
  },

  // Expected auth redirect patterns
  REDIRECT_PATTERNS: {
    DEX_AUTH: /\/dex\/auth\?/,
    AUTH_CALLBACK: /\/authservice\/oidc\/callback/,
    ERROR_PAGE: /\/error\//,
  },
};

// Network configuration from environment
const NETWORK_CONFIG = {
  TIMEOUT: parseInt(process.env.REQUEST_TIMEOUT) || 15000, // 15 seconds
  USER_AGENT: process.env.USER_AGENT || 'Orchestrator-Proxy-Test/1.0',
  MAX_REDIRECTS: parseInt(process.env.MAX_REDIRECTS) || 5,
  RETRY_ATTEMPTS: parseInt(process.env.RETRY_ATTEMPTS) || 3,
  RETRY_DELAY: parseInt(process.env.RETRY_DELAY) || 1000, // 1 second
};

// Test configuration from environment
const TEST_CONFIG = {
  // Test timeouts
  TIMEOUTS: {
    ENDPOINT: parseInt(process.env.TEST_ENDPOINT_TIMEOUT) || 10000, // 10 seconds per endpoint
    AUTH_FLOW: parseInt(process.env.TEST_AUTH_FLOW_TIMEOUT) || 30000, // 30 seconds for auth flow
    CONNECTIVITY: parseInt(process.env.TEST_CONNECTIVITY_TIMEOUT) || 5000, // 5 seconds for connectivity
  },

  // Test intervals
  INTERVALS: {
    BETWEEN_TESTS: parseInt(process.env.TEST_INTERVAL_BETWEEN) || 1000, // 1 second between tests
    HEALTH_CHECK: parseInt(process.env.TEST_INTERVAL_HEALTH) || 500, // 0.5 seconds for health checks
    AUTH_STEP: parseInt(process.env.TEST_INTERVAL_AUTH_STEP) || 2000, // 2 seconds between auth steps
  },

  // Test paths for different scenarios
  SCENARIOS: {
    PROTECTED_RESOURCES: [
      '/cog-iframe',
      '/cog',
      '/iframe/api/v1/namespace',
      '/pipeline',
    ],
    PUBLIC_RESOURCES: ['/', '/assets/config.json'],
    AUTH_ENDPOINTS: ['/dex/auth', '/authservice/oidc/callback'],
  },
};

// OIDC discovery test paths
const OIDC_TEST_PATHS = [
  '/.well-known/openid_configuration',
  '/dex/.well-known/openid_configuration',
  '/auth/.well-known/openid_configuration',
  '/oidc/.well-known/openid_configuration',
  '/authservice/.well-known/openid_configuration',
];

// HTTP status codes and their meanings in auth context
const HTTP_STATUS = {
  // Success responses
  OK: 200,

  // Redirection responses
  FOUND: 302,

  // Client error responses
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,

  // Server error responses
  INTERNAL_ERROR: 500,
  BAD_GATEWAY: 502,
  SERVICE_UNAVAILABLE: 503,

  // Auth flow meanings
  AUTH_MEANINGS: {
    200: 'Resource accessible or login form',
    302: 'Authentication redirect (expected)',
    401: 'Authentication required (expected)',
    403: 'Authorization required (expected)',
    404: 'Endpoint not found',
    500: 'Backend server error',
    502: 'Proxy/gateway error',
    503: 'Service unavailable',
  },
};

// Color codes for console output
const COLORS = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m',
  white: '\x1b[37m',
  gray: '\x1b[90m',
  bold: '\x1b[1m',
};

// Log levels and formatting
const LOG_CONFIG = {
  LEVELS: {
    ERROR: 'error',
    WARN: 'warning',
    INFO: 'info',
    SUCCESS: 'success',
    DEBUG: 'debug',
  },

  ICONS: {
    ERROR: '❌',
    WARN: '⚠️',
    INFO: 'ℹ️',
    SUCCESS: '✅',
    DEBUG: '🔍',
    PENDING: '⏳',
    REDIRECT: '↗️',
    AUTH: '🔐',
    COOKIE: '🍪',
  },
};

// File paths
const FILE_PATHS = {
  PROXY_CONFIG: './proxy.conf.js',
  PROXY_BACKUP: './proxy.conf.js.backup',
  PACKAGE_JSON: './package.json',
  TEST_HTML: './public/test-dex-auth.html',
};

// I18n helper functions
const I18N_HELPERS = {
  getMessage: (key, defaultValue = '') => {
    const keys = key.split('.');
    let value = I18N;
    for (const k of keys) {
      value = value?.[k];
      if (!value) break;
    }
    return value || defaultValue;
  },

  getProxyTestMessage: (key, defaultValue = '') => {
    return I18N.proxy_test?.[key] || defaultValue;
  },
};

// Export all constants
module.exports = {
  ENV,
  I18N,
  I18N_HELPERS,
  BASE_URLS,
  PROXY_PATHS,
  TARGET_PATHS,
  TEST_ENDPOINTS,
  AUTH_CONFIG,
  NETWORK_CONFIG,
  TEST_CONFIG,
  OIDC_TEST_PATHS,
  HTTP_STATUS,
  COLORS,
  LOG_CONFIG,
  FILE_PATHS,
};
