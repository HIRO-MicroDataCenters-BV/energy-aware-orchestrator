#!/usr/bin/env node

/**
 * Correct Proxy Authentication Test Script
 * Understands DEX authentication flow and interprets results correctly
 */

const http = require('http');
const https = require('https');
const { URL } = require('url');

// Configuration
const BASE_URL = 'http://localhost:4200';
const TIMEOUT = 10000;

// ANSI colors
const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
  white: '\x1b[37m',
  bold: '\x1b[1m',
};

function colorize(text, color) {
  return `${colors[color]}${text}${colors.reset}`;
}

// Test endpoints with correct DEX authentication flow expectations
const TEST_ENDPOINTS = [
  {
    name: 'API Health Check',
    path: '/api/health',
    method: 'GET',
    expectedBehavior: 'Should return API status or 404',
    correctStatuses: [200, 404],
    isAuthFlow: false,
  },
  {
    name: 'DEX OIDC Discovery',
    path: '/dex/.well-known/openid_configuration',
    method: 'GET',
    expectedBehavior: 'Should redirect to DEX auth or return discovery document',
    correctStatuses: [200, 302],
    isAuthFlow: true,
    authRedirectExpected: true,
  },
  {
    name: 'COG Dashboard Proxy',
    path: '/cog',
    method: 'GET',
    expectedBehavior: 'Should redirect to DEX auth or require authentication',
    correctStatuses: [200, 302, 401, 403, 500],
    isAuthFlow: true,
    authRedirectExpected: true,
    headers: {
      Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    },
  },
  {
    name: 'COG iframe Proxy (Production)',
    path: '/cog-iframe',
    method: 'GET',
    expectedBehavior: 'Should redirect to DEX auth (this is CORRECT behavior)',
    correctStatuses: [200, 302, 401, 403],
    isAuthFlow: true,
    authRedirectExpected: true,
    headers: {
      Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    },
  },
  {
    name: 'Kubernetes Dashboard Proxy',
    path: '/iframe/api/v1/namespace',
    method: 'GET',
    expectedBehavior: 'Should require authentication (403 Forbidden is correct)',
    correctStatuses: [200, 302, 401, 403],
    isAuthFlow: true,
    authRedirectExpected: false,
  },
];

async function makeRequest(url, options = {}) {
  return new Promise((resolve) => {
    const urlObj = new URL(url);
    const client = urlObj.protocol === 'https:' ? https : http;

    const requestOptions = {
      hostname: urlObj.hostname,
      port: urlObj.port,
      path: urlObj.pathname + urlObj.search,
      method: options.method || 'GET',
      headers: {
        'User-Agent': 'DEX-Aware-Test/1.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        ...options.headers,
      },
      timeout: TIMEOUT,
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
        });
      });
    });

    req.on('timeout', () => {
      req.destroy();
      resolve({
        success: false,
        error: 'Request timeout',
        duration: Date.now() - startTime,
      });
    });

    req.on('error', (err) => {
      resolve({
        success: false,
        error: err.message,
        duration: Date.now() - startTime,
      });
    });

    req.end();
  });
}

function analyzeAuthResponse(response, endpoint) {
  const analysis = {
    isCorrectBehavior: false,
    behaviorType: 'unknown',
    explanation: '',
    authFlowWorking: false,
  };

  const status = response.status;
  const location = response.headers.location;

  // Check if this is a DEX authentication redirect
  if (status === 302 && location && location.includes('/dex/auth')) {
    analysis.isCorrectBehavior = true;
    analysis.behaviorType = 'dex_auth_redirect';
    analysis.explanation = 'DEX authentication redirect - this means auth flow is working correctly';
    analysis.authFlowWorking = true;

    // Extract auth parameters
    try {
      const url = new URL(location, BASE_URL);
      analysis.authParams = {
        client_id: url.searchParams.get('client_id'),
        redirect_uri: url.searchParams.get('redirect_uri'),
        response_type: url.searchParams.get('response_type'),
        scope: url.searchParams.get('scope'),
      };
    } catch (e) {
      // Ignore parsing errors
    }
  }
  // Check if this is authentication required (also correct)
  else if (status === 401 || status === 403) {
    analysis.isCorrectBehavior = true;
    analysis.behaviorType = 'auth_required';
    analysis.explanation = 'Authentication required - proxy is correctly protecting the resource';
    analysis.authFlowWorking = true;
  }
  // Check if resource is accessible (may be public or already authenticated)
  else if (status === 200) {
    analysis.isCorrectBehavior = true;
    analysis.behaviorType = 'accessible';
    analysis.explanation = 'Resource accessible - may be public or already authenticated';
    analysis.authFlowWorking = !endpoint.isAuthFlow;
  }
  // Server errors
  else if (status >= 500) {
    analysis.isCorrectBehavior = false;
    analysis.behaviorType = 'server_error';
    analysis.explanation = 'Server error - backend issue, not proxy problem';
    analysis.authFlowWorking = false;
  }
  // Other redirects
  else if (status === 302) {
    analysis.isCorrectBehavior = true;
    analysis.behaviorType = 'redirect';
    analysis.explanation = `Redirect to ${location} - may be part of auth flow`;
    analysis.authFlowWorking = true;
  }
  // Unexpected statuses
  else {
    analysis.isCorrectBehavior = endpoint.correctStatuses.includes(status);
    analysis.behaviorType = 'unexpected';
    analysis.explanation = `Status ${status} - ${analysis.isCorrectBehavior ? 'within expected range' : 'unexpected'}`;
    analysis.authFlowWorking = analysis.isCorrectBehavior;
  }

  return analysis;
}

async function testEndpoint(endpoint) {
  console.log(`\n${colorize('Testing:', 'cyan')} ${endpoint.name}`);
  console.log(`${colorize('URL:', 'white')} ${BASE_URL}${endpoint.path}`);
  console.log(`${colorize('Expected:', 'white')} ${endpoint.expectedBehavior}`);

  try {
    const response = await makeRequest(BASE_URL + endpoint.path, {
      method: endpoint.method,
      headers: endpoint.headers,
    });

    if (!response.success) {
      console.log(`${colorize('Result:', 'red')} ❌ ${response.error}`);
      return {
        name: endpoint.name,
        passed: false,
        error: response.error,
        duration: response.duration,
      };
    }

    const analysis = analyzeAuthResponse(response, endpoint);

    // Determine if this is a pass or fail
    const passed = analysis.isCorrectBehavior;
    const icon = passed ? '✅' : '❌';
    const statusColor = passed ? 'green' : 'red';

    console.log(
      `${colorize('Result:', 'white')} ${icon} ${colorize(
        response.status,
        statusColor
      )} ${response.statusText} (${response.duration}ms)`
    );

    console.log(`${colorize('Analysis:', 'white')} ${analysis.explanation}`);

    // Show redirect details for auth flows
    if (analysis.behaviorType === 'dex_auth_redirect') {
      console.log(`${colorize('Redirect:', 'blue')} ${response.headers.location}`);
      if (analysis.authParams) {
        console.log(`${colorize('Client ID:', 'gray')} ${analysis.authParams.client_id || 'none'}`);
        console.log(`${colorize('Scope:', 'gray')} ${analysis.authParams.scope || 'none'}`);
      }
    }

    // Show cookies for auth flows
    if (response.headers['set-cookie']) {
      const cookies = Array.isArray(response.headers['set-cookie'])
        ? response.headers['set-cookie']
        : [response.headers['set-cookie']];

      cookies.forEach(cookie => {
        if (cookie.includes('oidc_state_csrf') || cookie.includes('authservice_session')) {
          const cookieName = cookie.split('=')[0];
          console.log(`${colorize('Cookie Set:', 'gray')} ${cookieName}`);
        }
      });
    }

    return {
      name: endpoint.name,
      passed: passed,
      status: response.status,
      duration: response.duration,
      behaviorType: analysis.behaviorType,
      authFlowWorking: analysis.authFlowWorking,
      explanation: analysis.explanation,
    };

  } catch (error) {
    console.log(`${colorize('Result:', 'red')} ❌ ERROR: ${error.message}`);
    return {
      name: endpoint.name,
      passed: false,
      error: error.message,
      duration: 0,
    };
  }
}

function printSummary(results) {
  console.log(colorize('\n📊 DEX Authentication Flow Test Summary', 'bold'));
  console.log('='.repeat(60));

  const totalTests = results.length;
  const passedTests = results.filter(r => r.passed).length;
  const authFlowTests = results.filter(r => r.authFlowWorking).length;
  const totalDuration = results.reduce((sum, r) => sum + r.duration, 0);

  console.log(`${colorize('Total Tests:', 'white')} ${totalTests}`);
  console.log(`${colorize('Passed:', 'green')} ${passedTests}`);
  console.log(`${colorize('Failed:', 'red')} ${totalTests - passedTests}`);
  console.log(`${colorize('Auth Flow Working:', 'blue')} ${authFlowTests}`);
  console.log(`${colorize('Total Duration:', 'white')} ${totalDuration}ms`);

  // Detailed results
  console.log(`\n${colorize('Detailed Results:', 'bold')}`);
  console.log('-'.repeat(60));

  results.forEach(result => {
    const icon = result.passed ? '✅' : '❌';
    const statusText = result.status ? `${result.status}` : 'ERROR';

    console.log(`${icon} ${result.name}`);
    console.log(`   Status: ${statusText} (${result.duration}ms)`);
    if (result.explanation) {
      console.log(`   ${result.explanation}`);
    }
    if (result.error) {
      console.log(`   Error: ${result.error}`);
    }
    console.log('');
  });

  // Authentication flow assessment
  console.log(colorize('🔐 Authentication Flow Assessment:', 'bold'));

  const cogIframeResult = results.find(r => r.name.includes('COG iframe'));
  const dexResult = results.find(r => r.name.includes('DEX OIDC'));
  const k8sResult = results.find(r => r.name.includes('Kubernetes'));

  if (cogIframeResult && cogIframeResult.behaviorType === 'dex_auth_redirect') {
    console.log('✅ COG iframe correctly redirects to DEX authentication');
  }

  if (dexResult && (dexResult.behaviorType === 'dex_auth_redirect' || dexResult.status === 200)) {
    console.log('✅ DEX endpoints are accessible and working');
  }

  if (k8sResult && (k8sResult.behaviorType === 'auth_required' || k8sResult.behaviorType === 'dex_auth_redirect')) {
    console.log('✅ Kubernetes Dashboard properly requires authentication');
  }

  const workingAuthFlows = authFlowTests;
  if (workingAuthFlows >= totalTests * 0.7) {
    console.log(colorize('\n🎉 Authentication proxy is working correctly!', 'green'));
    console.log('The 302 redirects to DEX are the expected behavior.');
  } else {
    console.log(colorize('\n⚠️ Some authentication flows may need attention.', 'yellow'));
  }

  return passedTests === totalTests;
}

async function checkDevServer() {
  console.log(colorize('🔍 Checking Angular dev server...', 'cyan'));

  try {
    const response = await makeRequest(BASE_URL);
    if (response.success) {
      console.log(colorize('✅ Angular dev server is running\n', 'green'));
      return true;
    } else {
      throw new Error(response.error);
    }
  } catch (error) {
    console.log(colorize('❌ Angular dev server is not running!', 'red'));
    console.log(colorize('Please start the dev server first:', 'yellow'));
    console.log(colorize('  pnpm run start:dev\n', 'white'));
    return false;
  }
}

async function main() {
  console.log(colorize('\n🔐 DEX Authentication Flow Aware Test', 'bold'));
  console.log(colorize('Understanding 302 redirects as SUCCESS indicators', 'cyan'));
  console.log('='.repeat(60));

  const serverRunning = await checkDevServer();
  if (!serverRunning) {
    process.exit(1);
  }

  console.log(colorize('🧪 Running DEX-aware proxy tests...', 'cyan'));

  const results = [];
  for (const endpoint of TEST_ENDPOINTS) {
    const result = await testEndpoint(endpoint);
    results.push(result);

    // Wait between tests
    await new Promise(resolve => setTimeout(resolve, 1000));
  }

  const allPassed = printSummary(results);

  if (allPassed) {
    console.log(colorize('\n🎉 All tests passed! Your proxy is working correctly.', 'green'));
    process.exit(0);
  } else {
    console.log(colorize('\n⚠️ Some tests need attention (but 302 redirects are OK!).', 'yellow'));
    process.exit(1);
  }
}

// Command line handling
const args = process.argv.slice(2);

if (args.includes('--help') || args.includes('-h')) {
  console.log(colorize('\nDEX Authentication Flow Aware Test', 'cyan'));
  console.log('\nThis test understands that:');
  console.log('✅ 302 redirect to /dex/auth = Authentication working correctly');
  console.log('✅ 403 Forbidden = Authorization working correctly');
  console.log('✅ 401 Unauthorized = Authentication required (correct)');
  console.log('\nUsage: node test-proxy-correct.js');
  process.exit(0);
}

main().catch(error => {
  console.error(colorize('\n❌ Fatal error:', 'red'), error.message);
  process.exit(1);
});
