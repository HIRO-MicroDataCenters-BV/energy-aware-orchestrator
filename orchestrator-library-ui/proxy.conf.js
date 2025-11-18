// Environment-based proxy configuration
const proxyTargets = {
  api: process.env.API_TARGET || 'http://51.44.28.47:30015',
  dex: process.env.DEX_TARGET || 'http://51.44.28.47:30080',
  dashboard: process.env.DASHBOARD_TARGET || 'http://51.44.28.47:30016',
  grafana: process.env.GRAFANA_TARGET || 'http://51.44.28.47:30000',
  cog: process.env.COG_TARGET || 'https://dashboard.cog.hiro-develop.nl',
};

const isDevelopment = process.env.NODE_ENV !== 'production';

module.exports = {
  '/api/**': {
    target: proxyTargets.api,
    secure: false,
    changeOrigin: true,
    logLevel: isDevelopment ? 'debug' : 'error',
    pathRewrite: {
      '^/api': '',
    },
    onError: function (err, req, res) {
      res.writeHead(500, { 'Content-Type': 'text/plain' });
      res.end('API proxy error: ' + err.message);
    },
  },
  '/.well-known/openid-configuration': {
    target: proxyTargets.dex,
    secure: false,
    changeOrigin: true,
    logLevel: isDevelopment ? 'debug' : 'error',
    pathRewrite: {
      '^/.well-known/openid-configuration':
        '/dex/.well-known/openid-configuration',
    },
    onError: function (err, req, res) {
      res.writeHead(500, { 'Content-Type': 'text/plain' });
      res.end('OIDC discovery proxy error: ' + err.message);
    },
  },
  '/dex/.well-known/**': {
    target: proxyTargets.dex,
    secure: false,
    changeOrigin: true,
    logLevel: isDevelopment ? 'debug' : 'error',
    pathRewrite: {
      '^/dex/.well-known': '/dex/.well-known',
    },
    onError: function (err, req, res) {
      res.writeHead(500, { 'Content-Type': 'text/plain' });
      res.end('DEX OIDC discovery proxy error: ' + err.message);
    },
  },
  '/iframe-dashboard/**': {
    target: proxyTargets.dashboard,
    secure: false,
    changeOrigin: true,
    logLevel: isDevelopment ? 'debug' : 'error',
    followRedirects: true,
    cookieDomainRewrite: 'localhost',
    pathRewrite: {
      '^/iframe-dashboard': '',
    },
    onError: function (err, req, res) {
      res.writeHead(500, { 'Content-Type': 'text/plain' });
      res.end('K8s dashboard proxy error: ' + err.message);
    },
    onProxyRes: function (proxyRes, req, res) {
      // Handle CORS headers for K8s dashboard
      proxyRes.headers['access-control-allow-origin'] = '*';
      proxyRes.headers['access-control-allow-credentials'] = 'true';
      proxyRes.headers['access-control-allow-methods'] =
        'GET, POST, PUT, DELETE, OPTIONS';
      proxyRes.headers['access-control-allow-headers'] =
        'Origin, X-Requested-With, Content-Type, Accept, Authorization';

      // Remove X-Frame-Options to allow iframe embedding
      delete proxyRes.headers['x-frame-options'];

      // Set CSP to allow iframe embedding
      proxyRes.headers['content-security-policy'] = proxyRes.headers[
        'content-security-policy'
      ]
        ? proxyRes.headers['content-security-policy'].replace(
            /frame-ancestors[^;]*;?/g,
            ''
          ) + '; frame-ancestors *'
        : 'frame-ancestors *';
    },
  },
  '/iframe-grafana/**': {
    target: proxyTargets.grafana,
    secure: false,
    changeOrigin: true,
    logLevel: isDevelopment ? 'debug' : 'error',
    followRedirects: true,
    cookieDomainRewrite: 'localhost',
    pathRewrite: {
      '^/iframe-grafana': '',
    },
    onError: function (err, req, res) {
      res.writeHead(500, { 'Content-Type': 'text/plain' });
      res.end('Grafana iframe proxy error: ' + err.message);
    },
    onProxyRes: function (proxyRes, req, res) {
      // Handle CORS headers for Grafana
      proxyRes.headers['access-control-allow-origin'] = '*';
      proxyRes.headers['access-control-allow-credentials'] = 'true';
      proxyRes.headers['access-control-allow-methods'] =
        'GET, POST, PUT, DELETE, OPTIONS';
      proxyRes.headers['access-control-allow-headers'] =
        'Origin, X-Requested-With, Content-Type, Accept, Authorization';

      // Remove X-Frame-Options to allow iframe embedding
      delete proxyRes.headers['x-frame-options'];

      // Set CSP to allow iframe embedding
      proxyRes.headers['content-security-policy'] = proxyRes.headers[
        'content-security-policy'
      ]
        ? proxyRes.headers['content-security-policy'].replace(
            /frame-ancestors[^;]*;?/g,
            ''
          ) + '; frame-ancestors *'
        : 'frame-ancestors *';
    },
    onProxyReq: function (proxyReq, req, res) {
      // Extract token from query parameter and add to Authorization header
      const url = new URL(req.url, 'http://localhost');
      const token = url.searchParams.get('access_token');

      if (token) {
        proxyReq.setHeader('Authorization', `Bearer ${token}`);
        // Remove token from URL to avoid passing it to Grafana
        url.searchParams.delete('access_token');
        proxyReq.path = url.pathname + url.search;
      } else if (req.headers.authorization) {
        proxyReq.setHeader('Authorization', req.headers.authorization);
      }
    },
  },
  '/iframe-cog/**': {
    target: proxyTargets.cog,
    secure: false,
    changeOrigin: true,
    logLevel: isDevelopment ? 'debug' : 'error',
    followRedirects: true,
    cookieDomainRewrite: 'localhost',
    pathRewrite: {
      '^/iframe-cog': '',
    },
    onError: function (err, req, res) {
      res.writeHead(500, { 'Content-Type': 'text/plain' });
      res.end('COG iframe proxy error: ' + err.message);
    },
    onProxyRes: function (proxyRes, req, res) {
      // Handle CORS headers for COG
      proxyRes.headers['access-control-allow-origin'] = '*';
      proxyRes.headers['access-control-allow-credentials'] = 'true';
      proxyRes.headers['access-control-allow-methods'] =
        'GET, POST, PUT, DELETE, OPTIONS';
      proxyRes.headers['access-control-allow-headers'] =
        'Origin, X-Requested-With, Content-Type, Accept, Authorization';

      // Remove X-Frame-Options to allow iframe embedding
      delete proxyRes.headers['x-frame-options'];

      // Set CSP to allow iframe embedding
      proxyRes.headers['content-security-policy'] = proxyRes.headers[
        'content-security-policy'
      ]
        ? proxyRes.headers['content-security-policy'].replace(
            /frame-ancestors[^;]*;?/g,
            ''
          ) + '; frame-ancestors *'
        : 'frame-ancestors *';
    },
    onProxyReq: function (proxyReq, req, res) {
      // Extract token from query parameter and add to Authorization header
      const url = new URL(req.url, 'http://localhost');
      const token = url.searchParams.get('access_token');

      if (token) {
        proxyReq.setHeader('Authorization', `Bearer ${token}`);
        // Remove token from URL to avoid passing it to COG
        url.searchParams.delete('access_token');
        proxyReq.path = url.pathname + url.search;
      } else if (req.headers.authorization) {
        proxyReq.setHeader('Authorization', req.headers.authorization);
      }
    },
  },
  '/dex/**': {
    target: proxyTargets.dex,
    secure: false,
    changeOrigin: true,
    logLevel: isDevelopment ? 'debug' : 'error',
    onError: function (err, req, res) {
      res.writeHead(500, { 'Content-Type': 'text/plain' });
      res.end('DEX proxy error: ' + err.message);
    },
  },
  '/authservice/**': {
    target: proxyTargets.dex,
    secure: false,
    changeOrigin: true,
    logLevel: isDevelopment ? 'debug' : 'error',
    onError: function (err, req, res) {
      res.writeHead(500, { 'Content-Type': 'text/plain' });
      res.end('AuthService proxy error: ' + err.message);
    },
  },
};
