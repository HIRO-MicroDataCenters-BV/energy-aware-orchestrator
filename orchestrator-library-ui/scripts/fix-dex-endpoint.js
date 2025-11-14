#!/usr/bin/env node

/**
 * Quick Fix Script for DEX OIDC Discovery Endpoint
 * Automatically detects and fixes the correct OIDC discovery path
 */

const fs = require('fs');
const path = require('path');
const http = require('http');
const { URL } = require('url');

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
  bold: '\x1b[1m',
};

function colorize(text, color) {
  return `${colors[color]}${text}${colors.reset}`;
}

// Test paths for OIDC discovery
const OIDC_TEST_PATHS = [
  '/.well-known/openid_configuration',
  '/dex/.well-known/openid_configuration',
  '/auth/.well-known/openid_configuration',
  '/oidc/.well-known/openid_configuration',
  '/authservice/.well-known/openid_configuration'
];

const TARGET_SERVER = 'http://51.44.28.47:30080';
const PROXY_CONFIG_PATH = path.join(__dirname, '..', 'proxy.conf.js');
const BACKUP_PATH = PROXY_CONFIG_PATH + '.backup';

async function testEndpoint(url) {
  return new Promise((resolve) => {
    const urlObj = new URL(url);

    const options = {
      hostname: urlObj.hostname,
      port: urlObj.port,
      path: urlObj.pathname,
      method: 'GET',
      timeout: 5000,
      headers: {
        'User-Agent': 'DEX-Fix-Script/1.0',
        'Accept': 'application/json'
      }
    };

    const req = http.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        resolve({
          success: res.statusCode === 200,
          status: res.statusCode,
          statusText: res.statusMessage,
          data: data,
          contentType: res.headers['content-type']
        });
      });
    });

    req.on('timeout', () => {
      req.destroy();
      resolve({ success: false, error: 'Timeout' });
    });

    req.on('error', (err) => {
      resolve({ success: false, error: err.message });
    });

    req.end();
  });
}

async function findWorkingOIDCPath() {
  console.log(colorize('\n🔍 Testing OIDC discovery endpoints...', 'cyan'));

  for (const testPath of OIDC_TEST_PATHS) {
    const testUrl = TARGET_SERVER + testPath;
    console.log(`  Testing: ${testPath}`);

    const result = await testEndpoint(testUrl);

    if (result.success) {
      // Verify it's actually an OIDC discovery document
      try {
        const oidcData = JSON.parse(result.data);
        if (oidcData.issuer && oidcData.authorization_endpoint) {
          console.log(colorize(`  ✅ Found working OIDC endpoint: ${testPath}`, 'green'));
          return testPath;
        }
      } catch (e) {
        // Not valid JSON, continue
      }
    } else if (result.status) {
      console.log(`  ❌ ${result.status} ${result.statusText}`);
    } else {
      console.log(`  ❌ ${result.error}`);
    }
  }

  console.log(colorize('  ❌ No working OIDC discovery endpoint found', 'red'));
  return null;
}

function backupProxyConfig() {
  if (fs.existsSync(PROXY_CONFIG_PATH)) {
    fs.copyFileSync(PROXY_CONFIG_PATH, BACKUP_PATH);
    console.log(colorize(`📄 Backup created: ${BACKUP_PATH}`, 'blue'));
    return true;
  }
  return false;
}

function updateProxyConfig(correctPath) {
  try {
    let content = fs.readFileSync(PROXY_CONFIG_PATH, 'utf8');

    // Find the DEX proxy configuration
    const dexConfigRegex = /\/dex\/\*\*.*?pathRewrite:\s*\{[^}]*\}/s;
    const currentMatch = content.match(dexConfigRegex);

    if (!currentMatch) {
      console.log(colorize('❌ Could not find DEX proxy configuration', 'red'));
      return false;
    }

    // Create new pathRewrite configuration
    const newPathRewrite = `pathRewrite: {
      '^/dex': '${correctPath.replace('/.well-known/openid_configuration', '')}'
    }`;

    // If the correct path is at root level, we need special handling
    if (correctPath === '/.well-known/openid_configuration') {
      newPathRewrite = `pathRewrite: {
      '^/dex/.well-known/openid_configuration': '/.well-known/openid_configuration'
    }`;
    }

    // Replace the pathRewrite section
    const updatedContent = content.replace(
      /pathRewrite:\s*\{[^}]*\}/,
      newPathRewrite
    );

    fs.writeFileSync(PROXY_CONFIG_PATH, updatedContent);
    console.log(colorize('✅ Proxy configuration updated successfully', 'green'));
    return true;

  } catch (error) {
    console.log(colorize(`❌ Error updating proxy config: ${error.message}`, 'red'));
    return false;
  }
}

function restoreBackup() {
  if (fs.existsSync(BACKUP_PATH)) {
    fs.copyFileSync(BACKUP_PATH, PROXY_CONFIG_PATH);
    fs.unlinkSync(BACKUP_PATH);
    console.log(colorize('🔄 Proxy configuration restored from backup', 'yellow'));
  }
}

async function testProxyAfterFix() {
  console.log(colorize('\n🧪 Testing proxy after fix...', 'cyan'));

  // Give a moment for any caching to clear
  await new Promise(resolve => setTimeout(resolve, 1000));

  const testUrl = 'http://localhost:4200/dex/.well-known/openid_configuration';
  const result = await testEndpoint(testUrl);

  if (result.success) {
    try {
      const oidcData = JSON.parse(result.data);
      if (oidcData.issuer) {
        console.log(colorize('✅ Proxy test successful! OIDC discovery working.', 'green'));
        console.log(`   Issuer: ${oidcData.issuer}`);
        return true;
      }
    } catch (e) {
      // Continue to failure case
    }
  }

  console.log(colorize('❌ Proxy test failed - fix may need manual adjustment', 'red'));
  return false;
}

function printSummary(workingPath, fixApplied, testPassed) {
  console.log(colorize('\n📊 SUMMARY', 'magenta'));
  console.log('='.repeat(50));

  if (workingPath) {
    console.log(`${colorize('Working OIDC path:', 'white')} ${workingPath}`);
  } else {
    console.log(colorize('Working OIDC path: None found', 'red'));
  }

  console.log(`${colorize('Configuration updated:', 'white')} ${fixApplied ? '✅ Yes' : '❌ No'}`);
  console.log(`${colorize('Proxy test passed:', 'white')} ${testPassed ? '✅ Yes' : '❌ No'}`);

  if (fixApplied && testPassed) {
    console.log(colorize('\n🎉 DEX OIDC discovery endpoint fixed successfully!', 'green'));
    console.log('You can now test with: curl http://localhost:4200/dex/.well-known/openid_configuration');
  } else if (fixApplied && !testPassed) {
    console.log(colorize('\n⚠️  Configuration updated but proxy test failed.', 'yellow'));
    console.log('You may need to restart your Angular dev server:');
    console.log(colorize('  pnpm run start:dev', 'white'));
  } else if (!workingPath) {
    console.log(colorize('\n❌ No working OIDC endpoint found on target server.', 'red'));
    console.log('This indicates the DEX service may not be running or configured properly.');
  }

  if (fs.existsSync(BACKUP_PATH)) {
    console.log(colorize(`\n💾 Backup available at: ${BACKUP_PATH}`, 'blue'));
    console.log('Run with --restore to revert changes');
  }
}

async function main() {
  console.log(colorize('\n🔧 DEX OIDC Discovery Endpoint Fix Tool', 'magenta'));
  console.log('='.repeat(50));

  // Check if proxy config exists
  if (!fs.existsSync(PROXY_CONFIG_PATH)) {
    console.log(colorize(`❌ Proxy configuration not found: ${PROXY_CONFIG_PATH}`, 'red'));
    process.exit(1);
  }

  // Find working OIDC path
  const workingPath = await findWorkingOIDCPath();

  if (!workingPath) {
    printSummary(null, false, false);
    console.log(colorize('\n💡 Recommendations:', 'cyan'));
    console.log('1. Check if DEX service is running on the target server');
    console.log('2. Verify the target server URL in proxy.conf.js');
    console.log('3. Contact your infrastructure team for DEX configuration');
    process.exit(1);
  }

  // Create backup
  const backupCreated = backupProxyConfig();
  if (!backupCreated) {
    console.log(colorize('⚠️  Could not create backup, proceeding anyway...', 'yellow'));
  }

  // Update proxy configuration
  console.log(colorize('\n🔧 Updating proxy configuration...', 'cyan'));
  const fixApplied = updateProxyConfig(workingPath);

  if (!fixApplied) {
    printSummary(workingPath, false, false);
    process.exit(1);
  }

  // Test the fix (only if Angular dev server might be running)
  const testPassed = await testProxyAfterFix();

  printSummary(workingPath, fixApplied, testPassed);

  if (!testPassed) {
    console.log(colorize('\n🔄 Next steps:', 'cyan'));
    console.log('1. Restart your Angular dev server: pnpm run start:dev');
    console.log('2. Test the endpoint: pnpm run test:proxy:endpoint "DEX OIDC Discovery"');
    console.log('3. Or test manually: curl http://localhost:4200/dex/.well-known/openid_configuration');
  }
}

// Handle command line arguments
const args = process.argv.slice(2);

if (args.includes('--help') || args.includes('-h')) {
  console.log(colorize('\nDEX OIDC Discovery Endpoint Fix Tool', 'cyan'));
  console.log('\nUsage: node fix-dex-endpoint.js [options]');
  console.log('\nOptions:');
  console.log('  --help, -h    Show this help message');
  console.log('  --restore     Restore proxy configuration from backup');
  console.log('  --test-only   Only test endpoints, don\'t modify configuration');
  console.log('\nDescription:');
  console.log('  Automatically detects the correct OIDC discovery path and updates');
  console.log('  the proxy configuration accordingly. Creates a backup before making changes.');
  console.log('\nExamples:');
  console.log('  node fix-dex-endpoint.js           # Auto-fix DEX endpoint');
  console.log('  node fix-dex-endpoint.js --test-only   # Test only, no changes');
  console.log('  node fix-dex-endpoint.js --restore     # Restore from backup');
  process.exit(0);
}

if (args.includes('--restore')) {
  if (fs.existsSync(BACKUP_PATH)) {
    restoreBackup();
    console.log(colorize('✅ Configuration restored successfully', 'green'));
  } else {
    console.log(colorize('❌ No backup file found', 'red'));
  }
  process.exit(0);
}

if (args.includes('--test-only')) {
  console.log(colorize('\n🧪 Test-only mode enabled', 'cyan'));
  findWorkingOIDCPath().then(workingPath => {
    if (workingPath) {
      console.log(colorize(`\n✅ Found working path: ${workingPath}`, 'green'));
      console.log('Run without --test-only to apply the fix.');
    } else {
      console.log(colorize('\n❌ No working OIDC endpoint found', 'red'));
    }
  });
} else {
  main().catch(error => {
    console.error(colorize('\n❌ Fatal error:', 'red'), error.message);

    // Try to restore backup on error
    if (fs.existsSync(BACKUP_PATH)) {
      restoreBackup();
    }

    process.exit(1);
  });
}
