const http = require('http');
const https = require('https');
const url = require('url');
const querystring = require('querystring');

const PORT = process.env.K8S_PROXY_PORT || process.env.PORT;

// Configuration
const config = {
  k8sApi: process.env.API_BACKEND_URL,
  k8sDashboard: process.env.K8S_DASHBOARD_URL,
  namespace: process.env.K8S_NAMESPACE,
  serviceAccount: process.env.K8S_SERVICE_ACCOUNT
};

// In-memory token cache
let tokenCache = {
  token: null,
  expiresAt: null
};

// Function to make HTTP request
function makeRequest(options, postData = null) {
  return new Promise((resolve, reject) => {
    const httpModule = options.protocol === 'https:' ? https : http;
    const req = httpModule.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        resolve({
          statusCode: res.statusCode,
          headers: res.headers,
          data: data
        });
      });
    });

    req.on('error', reject);

    if (postData) {
      req.write(postData);
    }
    req.end();
  });
}

// Function to get K8s token
async function getK8sToken() {
  try {
    // Check if we have a valid cached token
    if (tokenCache.token && tokenCache.expiresAt && new Date() < tokenCache.expiresAt) {
      console.log('Using cached token');
      return tokenCache.token;
    }

    console.log('Fetching new K8s token...');

    const apiUrl = url.parse(config.k8sApi);
    const options = {
      hostname: apiUrl.hostname,
      port: apiUrl.port || (apiUrl.protocol === 'https:' ? 443 : 80),
      path: `/k8s_get_token/?namespace=${config.namespace}&service_account_name=${config.serviceAccount}`,
      method: 'GET',
      headers: {
        'Accept': 'application/json'
      }
    };

    const response = await makeRequest(options);

    if (response.statusCode === 200) {
      const tokenData = JSON.parse(response.data);

      if (tokenData && tokenData.token) {
        // Decode JWT to get expiration time
        const tokenParts = tokenData.token.split('.');
        if (tokenParts.length === 3) {
          try {
            const payload = JSON.parse(Buffer.from(tokenParts[1], 'base64').toString());
            if (payload.exp) {
              // Cache token with 5 minute buffer before expiration
              tokenCache = {
                token: tokenData.token,
                expiresAt: new Date((payload.exp - 300) * 1000)
              };
              console.log('Token cached until:', tokenCache.expiresAt);
            }
          } catch (e) {
            console.warn('Could not decode token expiration, using 30 minute default cache');
            tokenCache = {
              token: tokenData.token,
              expiresAt: new Date(Date.now() + 30 * 60 * 1000) // 30 minutes
            };
          }
        }

        return tokenData.token;
      }
    }

    throw new Error('Failed to get token from API');
  } catch (error) {
    console.error('Error fetching K8s token:', error.message);
    throw new Error('Failed to get K8s token');
  }
}

// CORS headers function
function setCORSHeaders(res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept, Authorization');
  res.setHeader('Access-Control-Allow-Credentials', 'true');
}

// Health check handler
function handleHealth(req, res) {
  setCORSHeaders(res);
  res.writeHead(200, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({
    status: 'ok',
    timestamp: new Date().toISOString(),
    tokenCached: !!tokenCache.token,
    tokenExpiresAt: tokenCache.expiresAt
  }));
}

// Token test handler
async function handleGetToken(req, res) {
  setCORSHeaders(res);
  try {
    const token = await getK8sToken();
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      success: true,
      token: token,
      cached: tokenCache.expiresAt && new Date() < tokenCache.expiresAt
    }));
  } catch (error) {
    res.writeHead(500, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      success: false,
      error: error.message
    }));
  }
}

// Dashboard proxy handler
async function handleDashboardProxy(req, res) {
  try {
    // Get token
    const token = await getK8sToken();

    // Parse request URL
    const reqUrl = url.parse(req.url, true);

    // Add token to query if not present
    if (!reqUrl.query.token) {
      reqUrl.query.token = token;
    }

    // Build target URL
    const dashboardUrl = url.parse(config.k8sDashboard);
    const finalPath = reqUrl.pathname + '?' + querystring.stringify(reqUrl.query);

    console.log(`Proxying ${req.method} ${req.url} -> ${config.k8sDashboard}${finalPath}`);

    // Proxy options
    const options = {
      hostname: dashboardUrl.hostname,
      port: dashboardUrl.port || (dashboardUrl.protocol === 'https:' ? 443 : 80),
      path: finalPath,
      method: req.method,
      headers: {
        ...req.headers,
        host: dashboardUrl.host
      }
    };

    // Choose http or https
    const httpModule = dashboardUrl.protocol === 'https:' ? https : http;

    const proxyReq = httpModule.request(options, (proxyRes) => {
      // Set CORS and iframe headers
      const responseHeaders = {
        ...proxyRes.headers,
        'access-control-allow-origin': '*',
        'access-control-allow-credentials': 'true',
        'access-control-allow-methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'access-control-allow-headers': 'Origin, X-Requested-With, Content-Type, Accept, Authorization'
      };

      // Remove X-Frame-Options to allow iframe embedding
      delete responseHeaders['x-frame-options'];

      // Set CSP to allow iframe embedding
      if (responseHeaders['content-security-policy']) {
        responseHeaders['content-security-policy'] = responseHeaders['content-security-policy']
          .replace(/frame-ancestors[^;]*;?/g, '') + '; frame-ancestors *';
      } else {
        responseHeaders['content-security-policy'] = 'frame-ancestors *';
      }

      // Write response
      res.writeHead(proxyRes.statusCode, responseHeaders);
      proxyRes.pipe(res);
    });

    proxyReq.on('error', (error) => {
      console.error('Proxy request error:', error.message);
      if (!res.headersSent) {
        setCORSHeaders(res);
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Proxy request failed: ' + error.message }));
      }
    });

    // Pipe request body
    req.pipe(proxyReq);

  } catch (error) {
    console.error('Proxy error:', error.message);
    if (!res.headersSent) {
      setCORSHeaders(res);
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Failed to proxy request: ' + error.message }));
    }
  }
}

// Main request handler
function handleRequest(req, res) {
  const reqUrl = url.parse(req.url, true);

  // Handle CORS preflight
  if (req.method === 'OPTIONS') {
    setCORSHeaders(res);
    res.writeHead(204);
    res.end();
    return;
  }

  // Route requests
  if (reqUrl.pathname === '/health') {
    handleHealth(req, res);
  } else if (reqUrl.pathname === '/get-token') {
    handleGetToken(req, res);
  } else {
    // Proxy everything else to Dashboard
    handleDashboardProxy(req, res);
  }
}

// Create and start server
const server = http.createServer(handleRequest);

server.listen(PORT, () => {
  console.log(`K8s Dashboard Proxy Server running on port ${PORT}`);
  console.log('Configuration:', config);
  console.log('Dashboard will be available at: http://localhost:' + PORT);
});

server.on('error', (error) => {
  console.error('Server error:', error.message);
});
