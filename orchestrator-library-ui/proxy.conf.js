module.exports = {
  '/api/**': {
    target: 'http://51.44.28.47:30015',
    secure: false,
    changeOrigin: true,
    logLevel: 'debug',
    pathRewrite: {
      '^/api': '',
    },
  },
  '/iframe/**': {
    target: 'http://51.44.28.47:30016',
    secure: false,
    changeOrigin: true,
    logLevel: 'debug',
    pathRewrite: {
      '^/iframe': '',
    },
  },
  '/cog/**': {
    target: 'https://dashboard.cog.hiro-develop.nl',
    secure: true,
    changeOrigin: true,
    logLevel: 'debug',
    pathRewrite: {
      '^/cog': '/cogui',
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

      console.log(
        '[COG PROXY]',
        req.method,
        req.url,
        '->',
        proxyReq.host + proxyReq.path
      );
    },
  },
  '/cog-iframe/**': {
    target: 'http://51.44.28.47:30080',
    secure: false,
    changeOrigin: true,
    logLevel: 'debug',
    pathRewrite: {
      '^/cog-iframe': '/cogui',
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

      console.log(
        '[COG-IFRAME PROXY]',
        req.method,
        req.url,
        '->',
        proxyReq.host + proxyReq.path
      );
    },
  },
  '/.well-known/openid_configuration': {
    target: 'http://51.44.28.47:30080',
    secure: false,
    changeOrigin: true,
    logLevel: 'debug',
    onProxyReq: function (proxyReq, req, res) {
      console.log(
        '[ROOT OIDC DISCOVERY PROXY]',
        req.method,
        req.url,
        '->',
        proxyReq.host + proxyReq.path
      );
    },
  },
  '/dex/.well-known/**': {
    target: 'http://51.44.28.47:30080',
    secure: false,
    changeOrigin: true,
    logLevel: 'debug',
    pathRewrite: {
      '^/dex/.well-known': '/.well-known',
    },
    onProxyReq: function (proxyReq, req, res) {
      console.log(
        '[DEX OIDC DISCOVERY PROXY]',
        req.method,
        req.url,
        '->',
        proxyReq.host + proxyReq.path
      );
    },
  },
  ///dex/auth?client_id=authservice-oidc&redirect_uri=%2Fauthservice%2Foidc%2Fcallback&response_type=code&scope=openid+profile+email+groups&state=MTc1NDQ5NDc0M3xOd3dBTkU5VFYxRklRMWhJVjAxS1YxUkxNMFpNTms5VFJrTlpVbGxRVlVoRVFqTkNOMVJLVWtZMlZ6Vk5OemRZTWt0UFJqZFpSMUU9fOeT9wkSBfFpJUGKNZeOstHH9pYP14GlxMT_4NEBiQPR
  '/dex/**': {
    target: 'http://51.44.28.47:30080',
    secure: false,
    changeOrigin: true,
    logLevel: 'debug',
    onProxyReq: function (proxyReq, req, res) {
      console.log(
        '[DEX PROXY]',
        req.method,
        req.url,
        '->',
        proxyReq.host + proxyReq.path
      );
    },
  },
  '/authservice/**': {
    target: 'http://51.44.28.47:30080',
    secure: false,
    changeOrigin: true,
    logLevel: 'debug',
    onProxyReq: function (proxyReq, req, res) {
      console.log(
        '[AUTHSERVICE PROXY]',
        req.method,
        req.url,
        '->',
        proxyReq.host + proxyReq.path
      );
    },
  },
};
