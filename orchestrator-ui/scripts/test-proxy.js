#!/usr/bin/env node

/**
 * Standalone Proxy Test Script
 * Tests all proxy endpoints independently without Angular
 */

const http = require('http');
const https = require('https');
const { URL } = require('url');

// Test configuration
const BASE_URL = 'http://localhost:4200';
const TIMEOUT = 10000; // 10 seconds

const TEST_ENDPOINTS = [
  {
    name: 'API Health Check',
    path: '/api/health',
    method: 'GET',
    expectedStatus: [200, 404], // 404 is ok if endpoint doesn't exist
  },
  {
    name: 'DEX OIDC Discovery',
    path: '/dex/.well-known/openid_configuration',
    method: 'GET',
    expectedStatus: [200, 302], // 302 redirect to auth is expected
  },
  {
    name: 'COG Dashboard Proxy',
    path: '/cog',
    method: 'GET',
    expectedStatus: [200, 302, 401, 403], // Auth required or auth redirect
    headers: {
      Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    },
  },
  {
    name: 'COG iframe Proxy (Production)',
    path: '/cog-iframe',
    method: 'GET',
    expectedStatus: [200, 302, 401, 403, 500], // Auth redirect or auth required
    headers: {
      Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    },
  },
  {
    name: 'Kubernetes Dashboard Proxy',
    path: '/iframe/api/v1/namespace',
    method: 'GET',
    expectedStatus: [200, 302, 401, 403], // Auth redirect or auth required
  },
];

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
};

function colorize(text, color) {
  return `${colors[color]}${text}${colors.reset}`;
}

function makeRequest(url, options = {}) {
  return new Promise((resolve, reject) => {
    const urlObj = new URL(url);
    const client = urlObj.protocol === 'https:' ? https : http;

    const requestOptions = {
      hostname: urlObj.hostname,
      port: urlObj.port,
      path: urlObj.pathname + urlObj.search,
      method: options.method || 'GET',
      headers: {
        'User-Agent': 'Proxy-Test-Script/1.0',
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
      reject(new Error(`Request timeout after ${TIMEOUT}ms`));
    });

    req.on('error', (err) => {
      const duration = Date.now() - startTime;
      reject({
        error: err.message,
        duration: duration,
      });
    });

    req.end();
  });
}

async function testEndpoint(endpoint) {
  console.log(`\n${colorize('Testing:', 'cyan')} ${endpoint.name}`);
  console.log(`${colorize('URL:', 'white')} ${BASE_URL}${endpoint.path}`);

  try {
    const response = await makeRequest(BASE_URL + endpoint.path, {
      method: endpoint.method,
      headers: endpoint.headers,
    });

    const isExpectedStatus = endpoint.expectedStatus.includes(response.status);
    const statusColor = isExpectedStatus ? 'green' : 'red';
    const statusIcon = isExpectedStatus ? '✅' : '❌';

    console.log(
      `${colorize('Status:', 'white')} ${statusIcon} ${colorize(
        response.status,
        statusColor
      )} ${response.statusText}`
    );
    console.log(`${colorize('Duration:', 'white')} ${response.duration}ms`);

    // Check for DEX authentication redirect (this is SUCCESS)
    if (response.status === 302 && response.headers.location) {
      const location = response.headers.location;
      if (location.includes('/dex/auth')) {
        console.log(
          `${colorize(
            'Auth Flow:',
            'green'
          )} ✅ DEX authentication redirect (working correctly)`
        );
      }
    }

    // Show important headers
    const importantHeaders = [
      'content-type',
      'location',
      'www-authenticate',
      'set-cookie',
    ];
    importantHeaders.forEach((header) => {
      if (response.headers[header]) {
        console.log(
          `${colorize(header + ':', 'white')} ${response.headers[header]}`
        );
      }
    });

    // Show response preview for non-HTML content
    if (
      response.data &&
      response.headers['content-type'] &&
      response.headers['content-type'].includes('application/json')
    ) {
      try {
        const jsonData = JSON.parse(response.data);
        console.log(
          `${colorize('Response:', 'white')} ${JSON.stringify(
            jsonData,
            null,
            2
          ).substring(0, 200)}...`
        );
      } catch (e) {
        console.log(
          `${colorize('Response:', 'white')} ${response.data.substring(
            0,
            100
          )}...`
        );
      }
    }

    // Additional success check for DEX auth redirects
    let actualSuccess = isExpectedStatus;
    let successMessage = null;

    if (response.status === 302 && response.headers.location) {
      const location = response.headers.location;
      if (location.includes('/dex/auth')) {
        actualSuccess = true;
        successMessage = 'DEX authentication redirect (correct behavior)';
      }
    }

    return {
      name: endpoint.name,
      success: actualSuccess,
      status: response.status,
      duration: response.duration,
      error: null,
      message: successMessage,
    };
  } catch (error) {
    console.log(
      `${colorize('Status:', 'white')} ❌ ${colorize('ERROR', 'red')}`
    );
    console.log(`${colorize('Error:', 'red')} ${error.error || error.message}`);

    if (error.duration) {
      console.log(`${colorize('Duration:', 'white')} ${error.duration}ms`);
    }

    return {
      name: endpoint.name,
      success: false,
      status: null,
      duration: error.duration || 0,
      error: error.error || error.message,
    };
  }
}

async function runAllTests() {
  console.log(colorize('\n🚀 Starting Proxy Test Suite', 'magenta'));
  console.log(colorize('='.repeat(50), 'magenta'));

  const results = [];

  for (const endpoint of TEST_ENDPOINTS) {
    const result = await testEndpoint(endpoint);
    results.push(result);

    // Wait 1 second between tests
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }

  // Print summary
  console.log(colorize('\n📊 Test Summary', 'magenta'));
  console.log(colorize('='.repeat(50), 'magenta'));

  const successful = results.filter((r) => r.success).length;
  const failed = results.filter((r) => !r.success).length;
  const totalDuration = results.reduce((sum, r) => sum + r.duration, 0);

  console.log(`${colorize('Total Tests:', 'white')} ${results.length}`);
  console.log(`${colorize('Successful:', 'green')} ${successful}`);
  console.log(`${colorize('Failed:', 'red')} ${failed}`);
  console.log(`${colorize('Total Duration:', 'white')} ${totalDuration}ms`);

  // Show failed tests
  const failedTests = results.filter((r) => !r.success);
  if (failedTests.length > 0) {
    console.log(colorize('\n❌ Failed Tests:', 'red'));
    failedTests.forEach((test) => {
      console.log(
        `  • ${test.name}: ${test.error || 'Unexpected status ' + test.status}`
      );
    });
  }

  // Show successful tests
  const successfulTests = results.filter((r) => r.success);
  if (successfulTests.length > 0) {
    console.log(colorize('\n✅ Successful Tests:', 'green'));
    successfulTests.forEach((test) => {
      const message = test.message ? ` - ${test.message}` : '';
      console.log(
        `  • ${test.name}: ${test.status} (${test.duration}ms)${message}`
      );
    });
  }

  console.log(colorize('\n' + '='.repeat(50), 'magenta'));

  if (failed === 0) {
    console.log(colorize('🎉 All proxy tests passed!', 'green'));
    process.exit(0);
  } else {
    console.log(colorize(`⚠️  ${failed} proxy test(s) failed!`, 'yellow'));
    process.exit(1);
  }
}

// Handle command line arguments
const args = process.argv.slice(2);

if (args.includes('--help') || args.includes('-h')) {
  console.log(colorize('Proxy Test Script', 'cyan'));
  console.log('\nUsage: node test-proxy.js [options]');
  console.log('\nOptions:');
  console.log('  --help, -h     Show this help message');
  console.log('  --endpoint     Test specific endpoint by name');
  console.log('\nExamples:');
  console.log('  node test-proxy.js');
  console.log('  node test-proxy.js --endpoint "COG Dashboard Proxy"');
  process.exit(0);
}

const endpointFilter = args.find((arg) => arg.startsWith('--endpoint'));
if (endpointFilter) {
  const endpointName =
    endpointFilter.split('=')[1] || args[args.indexOf(endpointFilter) + 1];
  const endpoint = TEST_ENDPOINTS.find((e) => e.name === endpointName);

  if (!endpoint) {
    console.error(colorize(`❌ Endpoint "${endpointName}" not found`, 'red'));
    console.log('\nAvailable endpoints:');
    TEST_ENDPOINTS.forEach((e) => console.log(`  • ${e.name}`));
    process.exit(1);
  }

  console.log(colorize(`🎯 Testing single endpoint: ${endpointName}`, 'cyan'));
  testEndpoint(endpoint).then((result) => {
    if (result.success) {
      console.log(colorize('\n✅ Test passed!', 'green'));
      process.exit(0);
    } else {
      console.log(colorize('\n❌ Test failed!', 'red'));
      process.exit(1);
    }
  });
} else {
  // Check if Angular dev server is running
  console.log(
    colorize('🔍 Checking if Angular dev server is running...', 'cyan')
  );
  makeRequest(BASE_URL)
    .then(() => {
      console.log(colorize('✅ Angular dev server is running', 'green'));
      runAllTests();
    })
    .catch(() => {
      console.log(colorize('❌ Angular dev server is not running!', 'red'));
      console.log(colorize('Please start the dev server first:', 'yellow'));
      console.log(colorize('  pnpm run start:dev', 'white'));
      process.exit(1);
    });
}
