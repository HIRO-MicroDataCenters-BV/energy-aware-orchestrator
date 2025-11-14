#!/usr/bin/env node

/**
 * Enhanced Proxy Diagnostic Script
 * Comprehensive testing of proxy endpoints with detailed connectivity analysis
 */

const http = require('http');
const https = require('https');
const { URL } = require('url');
const dns = require('dns').promises;

// Test configuration
const BASE_URL = 'http://localhost:4200';
const TIMEOUT = 15000; // 15 seconds
const USER_AGENT = 'Enhanced-Proxy-Test/1.0';

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

// Enhanced test configuration with target server details
const TEST_ENDPOINTS = [
  {
    name: 'API Health Check',
    path: '/api/health',
    target: 'http://51.44.28.47:30015',
    targetPath: '/health',
    method: 'GET',
    expectedStatus: [200, 404],
    description: 'Backend API health endpoint',
  },
  {
    name: 'DEX OIDC Discovery',
    path: '/dex/.well-known/openid_configuration',
    target: 'http://51.44.28.47:30080',
    targetPath: '/dex/.well-known/openid_configuration',
    method: 'GET',
    expectedStatus: [200],
    description: 'OIDC discovery document',
    knownIssue: 'Target server returns 404 - endpoint may not exist',
  },
  {
    name: 'COG Dashboard Proxy (Dev)',
    path: '/cog',
    target: 'https://dashboard.cog.hiro-develop.nl',
    targetPath: '/cogui',
    method: 'GET',
    expectedStatus: [200, 401, 403, 302],
    description: 'COG dashboard development environment',
    headers: {
      Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    },
    knownIssue: 'SSL/TLS connection issues with target server',
  },
  {
    name: 'COG iframe Proxy (Production)',
    path: '/cog-iframe',
    target: 'http://51.44.28.47:30080',
    targetPath: '/cogui',
    method: 'GET',
    expectedStatus: [200, 401, 403, 302],
    description: 'COG dashboard production environment',
    headers: {
      Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    },
  },
  {
    name: 'Kubernetes Dashboard Proxy',
    path: '/iframe/api/v1/namespace',
    target: 'http://51.44.28.47:30016',
    targetPath: '/api/v1/namespace',
    method: 'GET',
    expectedStatus: [200, 401, 403],
    description: 'Kubernetes API server namespaces',
  },
];

async function checkDNSResolution(hostname) {
  try {
    const addresses = await dns.lookup(hostname, { all: true });
    return {
      success: true,
      addresses: addresses.map(addr => addr.address),
    };
  } catch (error) {
    return {
      success: false,
      error: error.message,
    };
  }
}

async function testDirectConnectivity(targetUrl, path) {
  return new Promise((resolve) => {
    const url = new URL(targetUrl);
    const client = url.protocol === 'https:' ? https : http;

    const options = {
      hostname: url.hostname,
      port: url.port || (url.protocol === 'https:' ? 443 : 80),
      path: path,
      method: 'GET',
      timeout: TIMEOUT,
      headers: {
        'User-Agent': USER_AGENT,
      },
      // Allow self-signed certificates for testing
      rejectUnauthorized: false,
    };

    const startTime = Date.now();

    const req = client.request(options, (res) => {
      const duration = Date.now() - startTime;
      res.on('data', () => {}); // Consume response data
      res.on('end', () => {
        resolve({
          success: true,
          status: res.statusCode,
          statusText: res.statusMessage,
          headers: res.headers,
          duration: duration,
        });
      });
    });

    req.on('timeout', () => {
      req.destroy();
      resolve({
        success: false,
        error: 'Connection timeout',
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

async function testProxyEndpoint(endpoint) {
  return new Promise((resolve) => {
    const url = new URL(BASE_URL + endpoint.path);

    const options = {
      hostname: url.hostname,
      port: url.port || 4200,
      path: url.pathname + url.search,
      method: endpoint.method,
      timeout: TIMEOUT,
      headers: {
        'User-Agent': USER_AGENT,
        ...endpoint.headers,
      },
    };

    const startTime = Date.now();

    const req = http.request(options, (res) => {
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

function printSeparator(char = '=', length = 60) {
  console.log(colorize(char.repeat(length), 'gray'));
}

function printHeader(text) {
  console.log(`\n${colorize(text, 'bold')}`);
  printSeparator();
}

async function performConnectivityDiagnostics() {
  printHeader('🔍 CONNECTIVITY DIAGNOSTICS');

  const targets = [...new Set(TEST_ENDPOINTS.map(e => e.target))];

  for (const target of targets) {
    const url = new URL(target);
    console.log(`\n${colorize('Target:', 'cyan')} ${target}`);

    // DNS Resolution
    console.log(`${colorize('DNS Resolution:', 'white')} `, '');
    const dnsResult = await checkDNSResolution(url.hostname);
    if (dnsResult.success) {
      console.log(`✅ ${dnsResult.addresses.join(', ')}`);
    } else {
      console.log(`❌ ${dnsResult.error}`);
    }

    // Port connectivity (simple test)
    console.log(`${colorize('Port Test:', 'white')} `, '');
    const connectTest = await testDirectConnectivity(target, '/');
    if (connectTest.success) {
      console.log(`✅ Connected (${connectTest.status} ${connectTest.statusText})`);
    } else {
      console.log(`❌ ${connectTest.error}`);
    }
  }
}

async function performEndpointTests() {
  printHeader('🚀 PROXY ENDPOINT TESTS');

  const results = [];

  for (const endpoint of TEST_ENDPOINTS) {
    console.log(`\n${colorize('Testing:', 'cyan')} ${endpoint.name}`);
    console.log(`${colorize('Description:', 'gray')} ${endpoint.description}`);
    console.log(`${colorize('Proxy URL:', 'white')} ${BASE_URL}${endpoint.path}`);
    console.log(`${colorize('Target:', 'white')} ${endpoint.target}${endpoint.targetPath}`);

    if (endpoint.knownIssue) {
      console.log(`${colorize('Known Issue:', 'yellow')} ${endpoint.knownIssue}`);
    }

    // Test direct connectivity to target
    console.log(`\n${colorize('Direct Target Test:', 'white')}`);
    const directTest = await testDirectConnectivity(endpoint.target, endpoint.targetPath);
    if (directTest.success) {
      console.log(`  ✅ ${directTest.status} ${directTest.statusText} (${directTest.duration}ms)`);
    } else {
      console.log(`  ❌ ${directTest.error} (${directTest.duration}ms)`);
    }

    // Test through proxy
    console.log(`${colorize('Proxy Test:', 'white')}`);
    const proxyTest = await testProxyEndpoint(endpoint);

    if (proxyTest.success) {
      const isExpectedStatus = endpoint.expectedStatus.includes(proxyTest.status);
      const statusColor = isExpectedStatus ? 'green' : 'red';
      const statusIcon = isExpectedStatus ? '✅' : '❌';

      console.log(`  ${statusIcon} ${colorize(proxyTest.status, statusColor)} ${proxyTest.statusText} (${proxyTest.duration}ms)`);

      // Show important headers
      const importantHeaders = ['content-type', 'location', 'www-authenticate', 'set-cookie'];
      importantHeaders.forEach((header) => {
        if (proxyTest.headers[header]) {
          const value = proxyTest.headers[header];
          const displayValue = value.length > 80 ? value.substring(0, 77) + '...' : value;
          console.log(`  ${colorize(header + ':', 'gray')} ${displayValue}`);
        }
      });

      results.push({
        name: endpoint.name,
        success: isExpectedStatus,
        status: proxyTest.status,
        duration: proxyTest.duration,
        directConnectivity: directTest.success,
        error: null,
      });
    } else {
      console.log(`  ❌ ${colorize('ERROR', 'red')}: ${proxyTest.error} (${proxyTest.duration}ms)`);

      results.push({
        name: endpoint.name,
        success: false,
        status: null,
        duration: proxyTest.duration,
        directConnectivity: directTest.success,
        error: proxyTest.error,
      });
    }

    // Wait between tests
    if (endpoint !== TEST_ENDPOINTS[TEST_ENDPOINTS.length - 1]) {
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
  }

  return results;
}

function printTestSummary(results) {
  printHeader('📊 TEST SUMMARY');

  const successful = results.filter(r => r.success).length;
  const failed = results.filter(r => !r.success).length;
  const totalDuration = results.reduce((sum, r) => sum + r.duration, 0);
  const avgDuration = Math.round(totalDuration / results.length);

  console.log(`${colorize('Total Tests:', 'white')} ${results.length}`);
  console.log(`${colorize('Successful:', 'green')} ${successful}`);
  console.log(`${colorize('Failed:', 'red')} ${failed}`);
  console.log(`${colorize('Total Duration:', 'white')} ${totalDuration}ms`);
  console.log(`${colorize('Average Duration:', 'white')} ${avgDuration}ms`);

  // Detailed results table
  console.log(`\n${colorize('Detailed Results:', 'bold')}`);
  printSeparator('-');

  const nameWidth = 30;
  const statusWidth = 15;
  const durationWidth = 10;
  const connectWidth = 10;

  // Header
  console.log(
    colorize('Endpoint'.padEnd(nameWidth), 'bold') +
    colorize('Status'.padEnd(statusWidth), 'bold') +
    colorize('Duration'.padEnd(durationWidth), 'bold') +
    colorize('Direct'.padEnd(connectWidth), 'bold') +
    colorize('Notes', 'bold')
  );
  printSeparator('-');

  // Results
  results.forEach(result => {
    const name = result.name.length > nameWidth - 2
      ? result.name.substring(0, nameWidth - 5) + '...'
      : result.name.padEnd(nameWidth);

    const statusText = result.status ? `${result.status}` : 'ERROR';
    const statusColor = result.success ? 'green' : 'red';
    const status = colorize(statusText.padEnd(statusWidth), statusColor);

    const duration = `${result.duration}ms`.padEnd(durationWidth);

    const directColor = result.directConnectivity ? 'green' : 'red';
    const direct = colorize((result.directConnectivity ? '✅' : '❌').padEnd(connectWidth), directColor);

    const notes = result.error || (result.success ? 'OK' : 'Unexpected status');

    console.log(name + status + duration + direct + notes);
  });

  printSeparator();
}

function printRecommendations(results) {
  printHeader('💡 RECOMMENDATIONS');

  const failedTests = results.filter(r => !r.success);
  const connectivityIssues = results.filter(r => !r.directConnectivity);

  if (failedTests.length === 0) {
    console.log(colorize('🎉 All proxy tests are working as expected!', 'green'));
    return;
  }

  console.log(colorize('Issues Found:', 'yellow'));

  if (connectivityIssues.length > 0) {
    console.log(`\n${colorize('Connectivity Issues:', 'red')}`);
    connectivityIssues.forEach(test => {
      console.log(`  • ${test.name}: Target server unreachable`);
    });
    console.log(`\n${colorize('Solutions:', 'cyan')}`);
    console.log('  - Check if target servers are running and accessible');
    console.log('  - Verify network connectivity and firewall rules');
    console.log('  - Check if URLs/ports in proxy.conf.js are correct');
  }

  const proxyOnlyIssues = results.filter(r => !r.success && r.directConnectivity);
  if (proxyOnlyIssues.length > 0) {
    console.log(`\n${colorize('Proxy Configuration Issues:', 'red')}`);
    proxyOnlyIssues.forEach(test => {
      console.log(`  • ${test.name}: Direct connection works, but proxy fails`);
    });
    console.log(`\n${colorize('Solutions:', 'cyan')}`);
    console.log('  - Check pathRewrite configuration in proxy.conf.js');
    console.log('  - Verify changeOrigin and secure settings');
    console.log('  - Check for CORS configuration issues');
    console.log('  - Review proxy headers and authentication handling');
  }

  // Specific recommendations
  const dexTest = results.find(r => r.name.includes('DEX'));
  if (dexTest && !dexTest.success) {
    console.log(`\n${colorize('DEX OIDC Discovery Issue:', 'yellow')}`);
    console.log('  - The OIDC discovery endpoint returns 404');
    console.log('  - Check if DEX is properly configured on the target server');
    console.log('  - Verify the correct path for OIDC discovery');
  }

  const cogTest = results.find(r => r.name.includes('COG Dashboard Proxy (Dev)'));
  if (cogTest && !cogTest.success) {
    console.log(`\n${colorize('COG HTTPS Issue:', 'yellow')}`);
    console.log('  - SSL/TLS connection problems with dashboard.cog.hiro-develop.nl');
    console.log('  - Certificate validation or network issues');
    console.log('  - Consider using the HTTP endpoint or fixing SSL configuration');
  }
}

async function checkDevServer() {
  console.log(colorize('🔍 Checking Angular dev server...', 'cyan'));

  try {
    const response = await testProxyEndpoint({ path: '', method: 'GET' });
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
  console.log(colorize('\n🔧 Enhanced Proxy Diagnostic Tool', 'magenta'));
  console.log(colorize('=====================================', 'magenta'));

  const serverRunning = await checkDevServer();
  if (!serverRunning) {
    process.exit(1);
  }

  await performConnectivityDiagnostics();
  const results = await performEndpointTests();
  printTestSummary(results);
  printRecommendations(results);

  const failed = results.filter(r => !r.success).length;
  if (failed === 0) {
    console.log(colorize('\n🎉 All tests completed successfully!', 'green'));
    process.exit(0);
  } else {
    console.log(colorize(`\n⚠️  ${failed} test(s) need attention.`, 'yellow'));
    process.exit(1);
  }
}

// Handle command line arguments
const args = process.argv.slice(2);

if (args.includes('--help') || args.includes('-h')) {
  console.log(colorize('\nEnhanced Proxy Diagnostic Tool', 'cyan'));
  console.log('\nUsage: node enhanced-proxy-test.js [options]');
  console.log('\nOptions:');
  console.log('  --help, -h     Show this help message');
  console.log('  --connectivity Test only connectivity (no proxy tests)');
  console.log('\nFeatures:');
  console.log('  • DNS resolution testing');
  console.log('  • Direct target server connectivity');
  console.log('  • Proxy endpoint testing');
  console.log('  • Detailed error analysis');
  console.log('  • Configuration recommendations');
  console.log('\nExamples:');
  console.log('  node enhanced-proxy-test.js');
  console.log('  node enhanced-proxy-test.js --connectivity');
  process.exit(0);
}

if (args.includes('--connectivity')) {
  performConnectivityDiagnostics().then(() => {
    console.log(colorize('\n✅ Connectivity diagnostics completed.', 'green'));
  });
} else {
  main().catch(error => {
    console.error(colorize('\n❌ Fatal error:', 'red'), error.message);
    process.exit(1);
  });
}
