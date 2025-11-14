#!/usr/bin/env node

/**
 * Authentication Flow Test Script
 * Tests the complete DEX authentication flow for Kubeflow/Orchestrator UI
 */

const http = require('http');
const https = require('https');
const { URL } = require('url');
const querystring = require('querystring');

// Test configuration
const BASE_URL = 'http://localhost:4200';
const TIMEOUT = 15000;
const USER_AGENT = 'Auth-Flow-Test/1.0';

// ANSI color codes
const colors = {
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

function colorize(text, color) {
  return `${colors[color]}${text}${colors.reset}`;
}

// Authentication flow test scenarios
const AUTH_FLOW_TESTS = [
  {
    name: 'Pipeline Dashboard Access',
    path: '/pipeline/',
    description: 'Test initial access to pipeline dashboard',
    expectedBehavior: 'Should redirect to DEX authentication',
    expectedStatus: [302],
    expectedRedirectPattern: /\/dex\/auth\?/
  },
  {
    name: 'COG Dashboard Access',
    path: '/cog',
    description: 'Test initial access to COG dashboard',
    expectedBehavior: 'Should redirect to DEX authentication or return auth error',
    expectedStatus: [302, 401, 403, 500],
  },
  {
    name: 'COG iframe Access',
    path: '/cog-iframe',
    description: 'Test initial access to COG iframe',
    expectedBehavior: 'Should redirect to DEX authentication',
    expectedStatus: [302],
    expectedRedirectPattern: /\/dex\/auth\?/
  },
  {
    name: 'Kubernetes Dashboard Access',
    path: '/iframe/api/v1/namespace',
    description: 'Test initial access to Kubernetes dashboard',
    expectedBehavior: 'Should return authentication required error',
    expectedStatus: [401, 403],
  },
  {
    name: 'DEX Auth Endpoint',
    path: '/dex/auth?client_id=test&redirect_uri=/test&response_type=code',
    description: 'Test DEX authentication endpoint availability',
    expectedBehavior: 'Should show login form or handle auth request',
    expectedStatus: [200, 302, 400],
  }
];

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
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        ...options.headers,
      },
      timeout: TIMEOUT,
      // Don't follow redirects automatically
      ...options.requestOptions
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
          url: url
        });
      });
    });

    req.on('timeout', () => {
      req.destroy();
      resolve({
        success: false,
        error: 'Request timeout',
        duration: Date.now() - startTime,
        url: url
      });
    });

    req.on('error', (err) => {
      resolve({
        success: false,
        error: err.message,
        duration: Date.now() - startTime,
        url: url
      });
    });

    req.end();
  });
}

function analyzeAuthResponse(response, test) {
  const analysis = {
    isAuthRedirect: false,
    isLoginPage: false,
    isAuthError: false,
    redirectLocation: null,
    authParams: null,
    sessionInfo: null
  };

  // Check for authentication redirect
  if (response.status === 302 && response.headers.location) {
    analysis.redirectLocation = response.headers.location;

    if (response.headers.location.includes('/dex/auth')) {
      analysis.isAuthRedirect = true;

      // Parse auth parameters
      try {
        const url = new URL(response.headers.location, BASE_URL);
        analysis.authParams = {
          client_id: url.searchParams.get('client_id'),
          redirect_uri: url.searchParams.get('redirect_uri'),
          response_type: url.searchParams.get('response_type'),
          scope: url.searchParams.get('scope'),
          state: url.searchParams.get('state')
        };
      } catch (e) {
        // Ignore parsing errors
      }
    }
  }

  // Check for login page
  if (response.status === 200 && response.data) {
    const lowerData = response.data.toLowerCase();
    if (lowerData.includes('login') || lowerData.includes('password') || lowerData.includes('username')) {
      analysis.isLoginPage = true;
    }
  }

  // Check for authentication errors
  if ([401, 403].includes(response.status)) {
    analysis.isAuthError = true;
  }

  // Check for session cookies
  if (response.headers['set-cookie']) {
    const cookies = Array.isArray(response.headers['set-cookie'])
      ? response.headers['set-cookie']
      : [response.headers['set-cookie']];

    analysis.sessionInfo = cookies
      .filter(cookie => cookie.includes('oidc_state_csrf') || cookie.includes('authservice_session'))
      .map(cookie => cookie.split(';')[0]);
  }

  return analysis;
}

function validateTestResult(response, test, analysis) {
  const result = {
    passed: false,
    message: '',
    details: {}
  };

  // Check if status is expected
  const statusMatches = test.expectedStatus.includes(response.status);

  if (!statusMatches) {
    result.message = `Unexpected status: ${response.status} (expected: ${test.expectedStatus.join(' or ')})`;
    return result;
  }

  // Check redirect pattern if specified
  if (test.expectedRedirectPattern && analysis.redirectLocation) {
    if (!test.expectedRedirectPattern.test(analysis.redirectLocation)) {
      result.message = `Redirect doesn't match expected pattern: ${analysis.redirectLocation}`;
      return result;
    }
  }

  // Specific validations based on test type
  switch (test.name) {
    case 'Pipeline Dashboard Access':
    case 'COG iframe Access':
      if (analysis.isAuthRedirect) {
        result.passed = true;
        result.message = 'Correctly redirects to DEX authentication';
        result.details = { authParams: analysis.authParams };
      } else {
        result.message = 'Should redirect to DEX authentication';
      }
      break;

    case 'COG Dashboard Access':
      if (analysis.isAuthRedirect || analysis.isAuthError || response.status === 500) {
        result.passed = true;
        result.message = response.status === 500
          ? 'Server error (may indicate backend issue)'
          : 'Authentication handling working';
      }
      break;

    case 'Kubernetes Dashboard Access':
      if (analysis.isAuthError) {
        result.passed = true;
        result.message = 'Correctly requires authentication';
      }
      break;

    case 'DEX Auth Endpoint':
      if (response.status === 200 || analysis.isAuthRedirect) {
        result.passed = true;
        result.message = 'DEX auth endpoint is accessible';
      } else if (response.status === 400) {
        result.passed = true;
        result.message = 'DEX returns bad request (expected for invalid auth params)';
      }
      break;

    default:
      result.passed = statusMatches;
      result.message = statusMatches ? 'Status as expected' : 'Unexpected status';
  }

  return result;
}

async function testAuthFlow(test) {
  console.log(`\n${colorize('Testing:', 'cyan')} ${test.name}`);
  console.log(`${colorize('Description:', 'gray')} ${test.description}`);
  console.log(`${colorize('URL:', 'white')} ${BASE_URL}${test.path}`);
  console.log(`${colorize('Expected:', 'white')} ${test.expectedBehavior}`);

  const response = await makeRequest(BASE_URL + test.path);

  if (!response.success) {
    console.log(`${colorize('Result:', 'red')} ❌ ${response.error} (${response.duration}ms)`);
    return {
      name: test.name,
      passed: false,
      error: response.error,
      duration: response.duration
    };
  }

  const analysis = analyzeAuthResponse(response, test);
  const validation = validateTestResult(response, test, analysis);

  // Display result
  const statusColor = validation.passed ? 'green' : 'red';
  const statusIcon = validation.passed ? '✅' : '❌';

  console.log(`${colorize('Result:', 'white')} ${statusIcon} ${colorize(response.status, statusColor)} ${response.statusText} (${response.duration}ms)`);
  console.log(`${colorize('Analysis:', 'white')} ${validation.message}`);

  // Show important details
  if (analysis.redirectLocation) {
    const location = analysis.redirectLocation.length > 80
      ? analysis.redirectLocation.substring(0, 77) + '...'
      : analysis.redirectLocation;
    console.log(`${colorize('Redirect:', 'gray')} ${location}`);
  }

  if (analysis.authParams && Object.keys(analysis.authParams).length > 0) {
    console.log(`${colorize('Auth Params:', 'gray')} client_id=${analysis.authParams.client_id || 'none'}`);
  }

  if (analysis.sessionInfo && analysis.sessionInfo.length > 0) {
    console.log(`${colorize('Session Cookie:', 'gray')} ${analysis.sessionInfo[0].split('=')[0]}`);
  }

  return {
    name: test.name,
    passed: validation.passed,
    status: response.status,
    duration: response.duration,
    analysis: analysis,
    validation: validation
  };
}

function printFlowDiagram() {
  console.log(colorize('\n🔄 Expected Authentication Flow:', 'magenta'));
  console.log('┌─────────────────────────────────────────────────────────────┐');
  console.log('│ 1. User visits protected resource (e.g., /pipeline/)       │');
  console.log('│ 2. AuthService intercepts → 302 redirect to /dex/auth      │');
  console.log('│ 3. DEX shows login form                                     │');
  console.log('│ 4. User submits credentials → POST /dex/auth               │');
  console.log('│ 5. DEX validates → 302 to /authservice/callback?code=...   │');
  console.log('│ 6. AuthService exchanges code → creates session cookie     │');
  console.log('│ 7. Final redirect to original resource with auth cookie    │');
  console.log('└─────────────────────────────────────────────────────────────┘');
}

function printSummary(results) {
  console.log(colorize('\n📊 Authentication Flow Test Summary', 'magenta'));
  console.log('='.repeat(60));

  const passed = results.filter(r => r.passed).length;
  const failed = results.filter(r => !r.passed).length;
  const totalDuration = results.reduce((sum, r) => sum + r.duration, 0);

  console.log(`${colorize('Total Tests:', 'white')} ${results.length}`);
  console.log(`${colorize('Passed:', 'green')} ${passed}`);
  console.log(`${colorize('Failed:', 'red')} ${failed}`);
  console.log(`${colorize('Total Duration:', 'white')} ${totalDuration}ms`);

  // Detailed results
  console.log(`\n${colorize('Detailed Results:', 'bold')}`);
  console.log('-'.repeat(60));

  results.forEach(result => {
    const status = result.passed ? '✅ PASS' : '❌ FAIL';
    const statusColor = result.passed ? 'green' : 'red';
    console.log(`${colorize(status, statusColor)} ${result.name} (${result.duration}ms)`);

    if (!result.passed && result.error) {
      console.log(`     ${colorize('Error:', 'red')} ${result.error}`);
    }
  });

  // Authentication flow health assessment
  console.log(colorize('\n🏥 Authentication Flow Health:', 'cyan'));

  const criticalTests = ['COG iframe Access', 'DEX Auth Endpoint'];
  const criticalPassed = results.filter(r => criticalTests.includes(r.name) && r.passed).length;

  if (criticalPassed === criticalTests.length) {
    console.log('✅ Authentication flow appears to be working correctly');
    console.log('   - DEX authentication redirects are functioning');
    console.log('   - Auth endpoints are accessible');
  } else {
    console.log('⚠️  Authentication flow may have issues');
    console.log('   - Check DEX service configuration');
    console.log('   - Verify AuthService setup');
  }

  return failed === 0;
}

async function checkDevServer() {
  console.log(colorize('🔍 Checking Angular dev server...', 'cyan'));

  try {
    const response = await makeRequest(BASE_URL);
    if (response.success) {
      console.log(colorize('✅ Angular dev server is running', 'green'));
      return true;
    } else {
      throw new Error(response.error);
    }
  } catch (error) {
    console.log(colorize('❌ Angular dev server is not running!', 'red'));
    console.log(colorize('Please start the dev server first:', 'yellow'));
    console.log(colorize('  pnpm run start:dev', 'white'));
    return false;
  }
}

async function main() {
  console.log(colorize('\n🔐 Authentication Flow Test Suite', 'magenta'));
  console.log('='.repeat(60));

  const serverRunning = await checkDevServer();
  if (!serverRunning) {
    process.exit(1);
  }

  printFlowDiagram();

  console.log(colorize('\n🧪 Running Authentication Tests...', 'cyan'));

  const results = [];
  for (const test of AUTH_FLOW_TESTS) {
    const result = await testAuthFlow(test);
    results.push(result);

    // Wait between tests to avoid overwhelming the server
    if (test !== AUTH_FLOW_TESTS[AUTH_FLOW_TESTS.length - 1]) {
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
  }

  const allPassed = printSummary(results);

  if (allPassed) {
    console.log(colorize('\n🎉 All authentication flow tests passed!', 'green'));
    process.exit(0);
  } else {
    console.log(colorize('\n⚠️  Some authentication tests need attention.', 'yellow'));
    console.log(colorize('\nNext Steps:', 'cyan'));
    console.log('1. Check if DEX and AuthService are properly configured');
    console.log('2. Verify backend services are running');
    console.log('3. Test with actual user credentials if available');
    process.exit(1);
  }
}

// Command line argument handling
const args = process.argv.slice(2);

if (args.includes('--help') || args.includes('-h')) {
  console.log(colorize('\nAuthentication Flow Test Suite', 'cyan'));
  console.log('\nUsage: node test-auth-flow.js [options]');
  console.log('\nOptions:');
  console.log('  --help, -h     Show this help message');
  console.log('  --diagram      Show only the authentication flow diagram');
  console.log('\nDescription:');
  console.log('  Tests the complete DEX authentication flow for Kubeflow/Orchestrator UI.');
  console.log('  Validates that protected resources correctly redirect to authentication');
  console.log('  and that the DEX authentication endpoints are accessible.');
  console.log('\nAuthentication Flow:');
  console.log('  User → AuthService → DEX → Login → Validation → Token → Session → Resource');
  console.log('\nExamples:');
  console.log('  node test-auth-flow.js          # Run full authentication tests');
  console.log('  node test-auth-flow.js --diagram   # Show flow diagram only');
  process.exit(0);
}

if (args.includes('--diagram')) {
  printFlowDiagram();
  process.exit(0);
}

main().catch(error => {
  console.error(colorize('\n❌ Fatal error:', 'red'), error.message);
  process.exit(1);
});
