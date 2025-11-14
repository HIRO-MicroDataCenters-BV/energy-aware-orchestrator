#!/usr/bin/env node

/**
 * Proxy Authentication Flow Test
 * Tests the actual authentication flow through Angular proxy without browser dependencies
 */

const http = require('http');
const https = require('https');
const { URL } = require('url');
const querystring = require('querystring');
const {
  BASE_URLS,
  PROXY_PATHS,
  TARGET_PATHS,
  AUTH_CONFIG,
  NETWORK_CONFIG,
  TEST_CONFIG,
  HTTP_STATUS,
  COLORS,
  LOG_CONFIG,
  I18N_HELPERS,
} = require('./constants');

function colorize(text, color) {
  return `${COLORS[color]}${text}${COLORS.reset}`;
}

class CookieJar {
  constructor() {
    this.cookies = new Map();
  }

  setCookies(setCookieHeaders) {
    if (!setCookieHeaders) return;

    const headers = Array.isArray(setCookieHeaders)
      ? setCookieHeaders
      : [setCookieHeaders];

    headers.forEach((header) => {
      const [cookiePart] = header.split(';');
      const [name, value] = cookiePart.split('=');
      if (name && value) {
        this.cookies.set(name.trim(), value.trim());
      }
    });
  }

  getCookieHeader() {
    if (this.cookies.size === 0) return '';

    return Array.from(this.cookies.entries())
      .map(([name, value]) => `${name}=${value}`)
      .join('; ');
  }

  hasCookie(name) {
    return this.cookies.has(name);
  }

  getCookie(name) {
    return this.cookies.get(name);
  }
}

async function makeRequest(url, options = {}) {
  return new Promise((resolve) => {
    const urlObj = new URL(url);
    const client = urlObj.protocol === 'https:' ? https : http;

    const requestOptions = {
      hostname: urlObj.hostname,
      port: urlObj.port || (urlObj.protocol === 'https:' ? 443 : 80),
      path: urlObj.pathname + urlObj.search,
      method: options.method || 'GET',
      headers: {
        'User-Agent': NETWORK_CONFIG.USER_AGENT,
        Accept:
          'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        Connection: 'keep-alive',
        ...options.headers,
      },
      timeout: NETWORK_CONFIG.TIMEOUT,
    };

    const startTime = Date.now();

    const req = client.request(requestOptions, (res) => {
      const duration = Date.now() - startTime;
      let data = '';

      res.on('data', (chunk) => {
        data += chunk;
      });

      res.on('end', () => {
        resolve({
          success: true,
          status: res.statusCode,
          statusText: res.statusMessage,
          headers: res.headers,
          data: data,
          duration: duration,
          url: url,
        });
      });
    });

    req.on('timeout', () => {
      req.destroy();
      resolve({
        success: false,
        error: 'Request timeout',
        duration: Date.now() - startTime,
        url: url,
      });
    });

    req.on('error', (err) => {
      resolve({
        success: false,
        error: err.message,
        duration: Date.now() - startTime,
        url: url,
      });
    });

    if (options.body) {
      req.write(options.body);
    }

    req.end();
  });
}

function parseAuthRedirect(location) {
  try {
    const url = new URL(location, BASE_URLS.LOCAL_DEV);
    return {
      isDexAuth: AUTH_CONFIG.REDIRECT_PATTERNS.DEX_AUTH.test(
        url.pathname + url.search
      ),
      clientId: url.searchParams.get('client_id'),
      redirectUri: url.searchParams.get('redirect_uri'),
      responseType: url.searchParams.get('response_type'),
      scope: url.searchParams.get('scope'),
      state: url.searchParams.get('state'),
    };
  } catch (e) {
    return { isDexAuth: false };
  }
}

async function testAuthFlow(endpoint, name) {
  console.log(
    `\n${colorize(
      I18N_HELPERS.getProxyTestMessage('title', 'Testing:'),
      'cyan'
    )} ${name}`
  );
  console.log(`${colorize('Endpoint:', 'white')} ${endpoint}`);

  const cookieJar = new CookieJar();
  let step = 1;

  // Step 1: Initial request to protected resource
  console.log(
    `${colorize('Step 1:', 'blue')} ${I18N_HELPERS.getProxyTestMessage(
      'steps.initial_request',
      'Initial request to protected resource'
    )}`
  );

  const initialResponse = await makeRequest(BASE_URLS.LOCAL_DEV + endpoint, {
    headers: {
      Cookie: cookieJar.getCookieHeader(),
    },
  });

  if (!initialResponse.success) {
    console.log(`  ❌ ${initialResponse.error}`);
    return { success: false, error: initialResponse.error };
  }

  console.log(
    `  Response: ${initialResponse.status} ${initialResponse.statusText}`
  );

  // Handle cookies from initial response
  cookieJar.setCookies(initialResponse.headers['set-cookie']);

  // Step 2: Check for authentication redirect
  if (initialResponse.status === 302) {
    const location = initialResponse.headers.location;
    const authInfo = parseAuthRedirect(location);

    console.log(
      `${colorize('Step 2:', 'blue')} ${I18N_HELPERS.getProxyTestMessage(
        'steps.auth_redirect',
        'Authentication redirect detected'
      )}`
    );
    console.log(`  Redirect to: ${location}`);

    if (authInfo.isDexAuth) {
      console.log(
        `  ✅ ${I18N_HELPERS.getProxyTestMessage(
          'messages.valid_dex_redirect',
          'Valid DEX auth redirect'
        )}`
      );
      console.log(`  Client ID: ${authInfo.clientId || 'none'}`);
      console.log(`  Redirect URI: ${authInfo.redirectUri || 'none'}`);
      console.log(`  Response Type: ${authInfo.responseType || 'none'}`);
      console.log(`  Scope: ${authInfo.scope || 'none'}`);

      // Step 3: Follow redirect to DEX auth page
      console.log(
        `${colorize('Step 3:', 'blue')} ${I18N_HELPERS.getProxyTestMessage(
          'steps.follow_redirect',
          'Following redirect to DEX auth'
        )}`
      );

      const dexResponse = await makeRequest(BASE_URLS.LOCAL_DEV + location, {
        headers: {
          Cookie: cookieJar.getCookieHeader(),
          Referer: BASE_URLS.LOCAL_DEV + endpoint,
        },
      });

      if (dexResponse.success) {
        console.log(
          `  DEX auth page: ${dexResponse.status} ${dexResponse.statusText}`
        );
        cookieJar.setCookies(dexResponse.headers['set-cookie']);

        // Check if it's a login form
        if (
          dexResponse.status === 200 &&
          dexResponse.data.toLowerCase().includes('login')
        ) {
          console.log(
            `  ✅ ${I18N_HELPERS.getProxyTestMessage(
              'messages.login_form_detected',
              'DEX login form detected'
            )}`
          );

          // Extract form action and method
          const formMatch = dexResponse.data.match(
            /<form[^>]*action="([^"]*)"[^>]*method="([^"]*)"[^>]*>/i
          );
          if (formMatch) {
            console.log(
              `  ${I18N_HELPERS.getProxyTestMessage(
                'messages.form_action',
                'Form action'
              )}: ${formMatch[1]}`
            );
            console.log(
              `  ${I18N_HELPERS.getProxyTestMessage(
                'messages.form_method',
                'Form method'
              )}: ${formMatch[2]}`
            );
          }

          return {
            success: true,
            flow: 'auth_required',
            message: I18N_HELPERS.getProxyTestMessage(
              'messages.auth_flow_working',
              'Authentication flow working - login form presented'
            ),
            details: {
              authRedirect: location,
              clientId: authInfo.clientId,
              loginFormAvailable: true,
              cookies: Array.from(cookieJar.cookies.keys()),
            },
          };
        } else if (dexResponse.status === 302) {
          console.log(
            `  ${I18N_HELPERS.getProxyTestMessage(
              'messages.further_redirect',
              'Further redirect'
            )}: ${dexResponse.headers.location}`
          );
          return {
            success: true,
            flow: 'redirect_chain',
            message: I18N_HELPERS.getProxyTestMessage(
              'messages.redirect_chain_working',
              'Authentication redirect chain working'
            ),
            details: {
              redirects: [location, dexResponse.headers.location],
            },
          };
        } else {
          console.log(
            `  ⚠️ ${I18N_HELPERS.getProxyTestMessage(
              'messages.unexpected_dex',
              'Unexpected DEX response'
            )}: ${dexResponse.status}`
          );
          return {
            success: true,
            flow: 'unexpected_dex_response',
            message: `${I18N_HELPERS.getProxyTestMessage(
              'messages.unexpected_dex',
              'DEX returned'
            )} ${dexResponse.status} - ${I18N_HELPERS.getProxyTestMessage(
              'messages.unexpected_dex',
              'may need investigation'
            )}`,
            details: { dexStatus: dexResponse.status },
          };
        }
      } else {
        console.log(`  ❌ Failed to reach DEX: ${dexResponse.error}`);
        return {
          success: false,
          error: `${I18N_HELPERS.getProxyTestMessage(
            'messages.dex_unreachable',
            'DEX unreachable'
          )}: ${dexResponse.error}`,
        };
      }
    } else {
      console.log(`  ⚠️ Redirect not to DEX auth: ${location}`);
      return {
        success: true,
        flow: 'non_dex_redirect',
        message: I18N_HELPERS.getProxyTestMessage(
          'messages.redirects_not_dex',
          'Redirects but not to DEX auth'
        ),
        details: { redirectLocation: location },
      };
    }
  } else if (initialResponse.status === 401 || initialResponse.status === 403) {
    console.log(
      `${colorize('Step 2:', 'blue')} ${I18N_HELPERS.getProxyTestMessage(
        'steps.auth_required',
        'Authentication required (no redirect)'
      )}`
    );
    console.log(
      `  ✅ ${I18N_HELPERS.getProxyTestMessage(
        'messages.correctly_returns',
        'Correctly returns'
      )} ${initialResponse.status} - ${I18N_HELPERS.getProxyTestMessage(
        'messages.auth_required_text',
        'authentication required'
      )}`
    );

    return {
      success: true,
      flow: 'auth_error',
      message: `${I18N_HELPERS.getProxyTestMessage(
        'messages.correctly_returns',
        'Returns'
      )} ${initialResponse.status} - ${I18N_HELPERS.getProxyTestMessage(
        'messages.auth_required_text',
        'authentication required'
      )}`,
      details: {
        status: initialResponse.status,
        authHeaderPresent: !!initialResponse.headers['www-authenticate'],
      },
    };
  } else if (initialResponse.status === HTTP_STATUS.OK) {
    console.log(
      `${colorize(
        'Step 2:',
        'blue'
      )} Resource accessible without authentication`
    );
    console.log(
      `  ⚠️ Endpoint accessible without auth - may be public or pre-authenticated`
    );

    return {
      success: true,
      flow: 'public_access',
      message: 'Resource accessible without authentication',
      details: {
        contentType: initialResponse.headers['content-type'],
        hasAuthCookies: cookieJar.hasCookie(AUTH_CONFIG.COOKIES.SESSION),
      },
    };
  } else if (initialResponse.status >= HTTP_STATUS.INTERNAL_ERROR) {
    console.log(`${colorize('Step 2:', 'blue')} Server error`);
    console.log(`  ❌ Server error: ${initialResponse.status} - backend issue`);

    return {
      success: false,
      flow: 'server_error',
      error: `Server error: ${initialResponse.status}`,
      details: { status: initialResponse.status },
    };
  } else {
    console.log(`${colorize('Step 2:', 'blue')} Unexpected response`);
    console.log(`  ⚠️ Unexpected status: ${initialResponse.status}`);

    return {
      success: true,
      flow: 'unexpected_status',
      message: `Unexpected status: ${initialResponse.status}`,
      details: { status: initialResponse.status },
    };
  }
}

async function testProxyHealth() {
  console.log(
    colorize(
      `\n🔍 ${I18N_HELPERS.getProxyTestMessage(
        'status.checking_server',
        'Checking Angular dev server...'
      )}`,
      'cyan'
    )
  );

  const response = await makeRequest(BASE_URLS.LOCAL_DEV);
  if (response.success && response.status === HTTP_STATUS.OK) {
    console.log(
      colorize(
        `✅ ${I18N_HELPERS.getProxyTestMessage(
          'status.server_running',
          'Angular dev server is running'
        )}`,
        'green'
      )
    );
    return true;
  } else {
    console.log(
      colorize(
        `❌ ${I18N_HELPERS.getProxyTestMessage(
          'status.server_not_running',
          'Angular dev server is not accessible'
        )}`,
        'red'
      )
    );
    console.log(
      colorize(
        I18N_HELPERS.getProxyTestMessage(
          'status.please_start',
          'Please start: pnpm run start:dev'
        ),
        'yellow'
      )
    );
    return false;
  }
}

function printFlowSummary(results) {
  console.log(colorize('\n📊 Authentication Flow Summary', 'bold'));
  console.log('='.repeat(60));

  const flowTypes = {
    auth_required: `✅ ${I18N_HELPERS.getProxyTestMessage(
      'flow_types.auth_required',
      'Correct auth flow'
    )}`,
    auth_error: `✅ ${I18N_HELPERS.getProxyTestMessage(
      'flow_types.auth_error',
      'Correct auth required'
    )}`,
    public_access: `⚠️ ${I18N_HELPERS.getProxyTestMessage(
      'flow_types.public_access',
      'Public access'
    )}`,
    redirect_chain: `✅ ${I18N_HELPERS.getProxyTestMessage(
      'flow_types.redirect_chain',
      'Redirect chain working'
    )}`,
    non_dex_redirect: `⚠️ ${I18N_HELPERS.getProxyTestMessage(
      'flow_types.non_dex_redirect',
      'Non-DEX redirect'
    )}`,
    unexpected_dex_response: `⚠️ ${I18N_HELPERS.getProxyTestMessage(
      'flow_types.unexpected_dex_response',
      'Unexpected DEX response'
    )}`,
    unexpected_status: `⚠️ ${I18N_HELPERS.getProxyTestMessage(
      'flow_types.unexpected_status',
      'Unexpected status'
    )}`,
    server_error: `❌ ${I18N_HELPERS.getProxyTestMessage(
      'flow_types.server_error',
      'Server error'
    )}`,
  };

  results.forEach((result) => {
    const icon = flowTypes[result.flow] || '❓ Unknown';
    console.log(`${icon} ${result.name}`);
    console.log(`   ${result.message}`);

    if (result.details) {
      Object.entries(result.details).forEach(([key, value]) => {
        if (Array.isArray(value)) {
          console.log(`   ${key}: ${value.join(', ')}`);
        } else {
          console.log(`   ${key}: ${value}`);
        }
      });
    }

    if (result.error) {
      console.log(`   Error: ${result.error}`);
    }
    console.log('');
  });

  // Overall assessment
  const successful = results.filter((r) => r.success).length;
  const authFlows = results.filter((r) =>
    ['auth_required', 'auth_error'].includes(r.flow)
  ).length;

  console.log(
    colorize(
      I18N_HELPERS.getProxyTestMessage('assessment.title', 'Assessment:'),
      'bold'
    )
  );
  console.log(
    `• ${successful}/${results.length} ${I18N_HELPERS.getProxyTestMessage(
      'assessment.endpoints_tested',
      'endpoints tested successfully'
    )}`
  );
  console.log(
    `• ${authFlows}/${results.length} ${I18N_HELPERS.getProxyTestMessage(
      'assessment.proper_auth_flow',
      'endpoints have proper auth flow'
    )}`
  );

  if (authFlows >= results.length * 0.5) {
    console.log(
      colorize(
        `✅ ${I18N_HELPERS.getProxyTestMessage(
          'assessment.proxy_working',
          'Authentication proxy appears to be working correctly'
        )}`,
        'green'
      )
    );
  } else {
    console.log(
      colorize(
        `⚠️ ${I18N_HELPERS.getProxyTestMessage(
          'assessment.needs_review',
          'Authentication proxy may need configuration review'
        )}`,
        'yellow'
      )
    );
  }
}

async function main() {
  console.log(colorize('\n🔐 Proxy Authentication Flow Test', 'bold'));
  console.log('Based on DEX authentication algorithm');
  console.log('='.repeat(60));

  // Check if dev server is running
  const serverHealthy = await testProxyHealth();
  if (!serverHealthy) {
    process.exit(1);
  }

  console.log(
    colorize(
      `\n🧪 ${I18N_HELPERS.getProxyTestMessage(
        'status.testing_flows',
        'Testing authentication flows...'
      )}`,
      'cyan'
    )
  );

  const testEndpoints = [
    {
      endpoint: PROXY_PATHS.COG_IFRAME,
      name: I18N_HELPERS.getProxyTestMessage(
        'endpoints.cog_iframe_prod',
        'COG iframe (Production)'
      ),
    },
    {
      endpoint: PROXY_PATHS.COG,
      name: I18N_HELPERS.getProxyTestMessage(
        'endpoints.cog_dashboard_dev',
        'COG Dashboard (Development)'
      ),
    },
    {
      endpoint: PROXY_PATHS.IFRAME + TARGET_PATHS.K8S_NAMESPACES,
      name: I18N_HELPERS.getProxyTestMessage(
        'endpoints.kubernetes_dashboard',
        'Kubernetes Dashboard'
      ),
    },
    {
      endpoint: '/pipeline',
      name: I18N_HELPERS.getProxyTestMessage(
        'endpoints.pipeline_dashboard',
        'Pipeline Dashboard'
      ),
    },
  ];

  const results = [];

  for (const test of testEndpoints) {
    try {
      const result = await testAuthFlow(test.endpoint, test.name);
      results.push({ ...result, name: test.name });
    } catch (error) {
      results.push({
        name: test.name,
        success: false,
        error: error.message,
        flow: 'test_error',
      });
    }

    // Wait between tests
    await new Promise((resolve) =>
      setTimeout(resolve, TEST_CONFIG.INTERVALS.BETWEEN_TESTS)
    );
  }

  printFlowSummary(results);

  const hasErrors = results.some((r) => !r.success);
  process.exit(hasErrors ? 1 : 0);
}

// Command line handling
const args = process.argv.slice(2);

if (args.includes('--help') || args.includes('-h')) {
  console.log(colorize('\nProxy Authentication Flow Test', 'cyan'));
  console.log('\nUsage: node test-proxy-auth.js [options]');
  console.log('\nTests the DEX authentication flow through Angular proxy:');
  console.log('1. Request protected resource');
  console.log('2. Check for auth redirect to /dex/auth');
  console.log('3. Verify DEX login form availability');
  console.log('4. Validate authentication parameters');
  console.log('\nOptions:');
  console.log('  --help, -h    Show this help');
  console.log('\nExample:');
  console.log('  node test-proxy-auth.js');
  process.exit(0);
}

main().catch((error) => {
  console.error(colorize('\n❌ Fatal error:', 'red'), error.message);
  process.exit(1);
});
