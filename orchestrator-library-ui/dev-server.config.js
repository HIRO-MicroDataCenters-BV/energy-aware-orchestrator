/**
 * Development Server Configuration
 * This file ensures proper handling of proxy routes and prevents Angular routing conflicts
 */

const proxyConfig = require('./proxy.conf.js');

module.exports = {
  // Development server options
  host: 'localhost',
  port: 4200,

  // Proxy configuration
  proxy: proxyConfig,

  // History API fallback configuration
  // This is crucial for SPA routing to work correctly with proxy routes
  historyApiFallback: {
    // Define which routes should be handled by Angular vs proxy
    rewrites: [
      // Proxy routes should NOT be rewritten to index.html
      {
        from: /^\/api\/.*$/,
        to: function (context) {
          return context.parsedUrl.pathname;
        },
      },
      {
        from: /^\/iframe-dashboard\/.*$/,
        to: function (context) {
          return context.parsedUrl.pathname;
        },
      },
      {
        from: /^\/iframe-grafana\/.*$/,
        to: function (context) {
          return context.parsedUrl.pathname;
        },
      },
      {
        from: /^\/iframe-cog\/.*$/,
        to: function (context) {
          return context.parsedUrl.pathname;
        },
      },
      {
        from: /^\/dex\/.*$/,
        to: function (context) {
          return context.parsedUrl.pathname;
        },
      },
      {
        from: /^\/authservice\/.*$/,
        to: function (context) {
          return context.parsedUrl.pathname;
        },
      },
      {
        from: /^\/\.well-known\/.*$/,
        to: function (context) {
          return context.parsedUrl.pathname;
        },
      },

      // All other routes should fall back to index.html for Angular routing
      {
        from: /^(?!.*\.(js|css|ico|svg|png|jpg|jpeg|gif|woff|woff2|ttf|eot)).*$/,
        to: '/index.html',
      },
    ],

    // Don't log rewrites to reduce console noise
    verbose: false,

    // Handle index.html fallback
    index: '/index.html',

    // Disable dotfiles to prevent serving hidden files
    disableDotRule: true,
  },

  // Additional dev server options
  compress: true,

  // Hot reloading
  hot: true,
  liveReload: true,

  // CORS headers for development
  headers: {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, PATCH, OPTIONS',
    'Access-Control-Allow-Headers':
      'X-Requested-With, content-type, Authorization',
  },

  // Custom middleware to handle proxy route debugging
  before: function (app, server, compiler) {
    // Log all incoming requests for debugging
    app.use('*', (req, res, next) => {
      const isProxyRoute = [
        '/api',
        '/iframe-dashboard',
        '/iframe-grafana',
        '/iframe-cog',
        '/dex',
        '/authservice',
        '/.well-known',
      ].some((pattern) => req.originalUrl.startsWith(pattern));

      if (isProxyRoute) {
        console.log(
          `[DEV-SERVER] Proxy route detected: ${req.method} ${req.originalUrl}`
        );
      }

      next();
    });

    // Handle OPTIONS requests for CORS preflight
    app.options('*', (req, res) => {
      res.header('Access-Control-Allow-Origin', '*');
      res.header(
        'Access-Control-Allow-Methods',
        'GET, POST, PUT, DELETE, PATCH, OPTIONS'
      );
      res.header(
        'Access-Control-Allow-Headers',
        'X-Requested-With, content-type, Authorization'
      );
      res.sendStatus(200);
    });
  },

  // Error handling
  onError: function (err) {
    console.error('[DEV-SERVER ERROR]', err);
  },

  // Proxy error handling
  onProxyError: function (err, req, res) {
    console.error('[PROXY ERROR]', err.message, 'for', req.url);
    res.writeHead(500, { 'Content-Type': 'text/plain' });
    res.end('Proxy error: ' + err.message);
  },
};
