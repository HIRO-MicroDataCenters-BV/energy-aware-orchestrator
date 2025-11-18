#!/usr/bin/env node

const axios = require('axios');

const DEX_URL =
  process.env.DEX_URL || 'https://dashboard.cog.hiro-develop.nl/apidev';
const LOGIN = process.env.DEX_LOGIN || 'admin@kubeflow.org';
const PASSWORD = process.env.DEX_PASSWORD || '12341234';

async function testDexAuth() {
  console.log('🔐 Testing DEX Authentication Flow');
  console.log(`📍 Target: ${DEX_URL}`);
  console.log(`👤 User: ${LOGIN}\n`);

  let state, req, code, sessionCookie;

  try {
    // Step 1: Get STATE
    console.log('📋 Step 1: Getting STATE...');
    const stateResponse = await axios.get(DEX_URL, {
      maxRedirects: 0,
      validateStatus: () => true,
    });

    if (process.env.DEBUG) {
      console.log(`Response status: ${stateResponse.status}`);
      console.log(`Response headers:`, stateResponse.headers);
      console.log(
        `Response data (first 500 chars):`,
        typeof stateResponse.data === 'string'
          ? stateResponse.data.substring(0, 500)
          : JSON.stringify(stateResponse.data).substring(0, 500)
      );
    }

    // Extract STATE from location header for redirect response
    let stateMatch;
    if (stateResponse.status === 302 && stateResponse.headers.location) {
      stateMatch = stateResponse.headers.location.match(/state=([^&]+)/);
    } else {
      // Fallback to body parsing
      stateMatch = stateResponse.data.match(/STATE=([A-Za-z0-9_-]+)/);
    }

    if (!stateMatch) {
      throw new Error('Could not extract STATE from response');
    }
    state = stateMatch[1];
    console.log(`✅ STATE: ${state}\n`);

    // Step 2: Get REQ
    console.log('📋 Step 2: Getting REQ...');
    const authUrl = `${DEX_URL}/dex/auth?client_id=kubeflow-oidc-authservice&redirect_uri=%2Flogin%2Foidc&response_type=code&scope=profile+email+groups+openid&state=${state}`;
    const reqResponse = await axios.get(authUrl, {
      maxRedirects: 5,
      validateStatus: () => true,
    });

    if (process.env.DEBUG) {
      console.log(`REQ Response status: ${reqResponse.status}`);
      console.log(
        `REQ Response data (first 2000 chars):`,
        typeof reqResponse.data === 'string'
          ? reqResponse.data.substring(0, 2000)
          : JSON.stringify(reqResponse.data).substring(0, 2000)
      );
    }

    // Extract auth state from form action (this DEX version uses state instead of req)
    let authStateMatch = reqResponse.data.match(
      /action="[^"]*[?&](?:amp;)?state=([^"&]+)"/
    );
    if (!authStateMatch) {
      // Fallback patterns
      authStateMatch = reqResponse.data.match(/name="req"\s+value="([^"]+)"/);
    }
    if (!authStateMatch) {
      authStateMatch = reqResponse.data.match(/REQ=([A-Za-z0-9_-]+)/);
    }

    if (!authStateMatch) {
      throw new Error('Could not extract auth state from response');
    }
    req = authStateMatch[1];
    console.log(`✅ Auth State (REQ): ${req}\n`);

    // Step 3: Submit credentials
    console.log('📋 Step 3: Submitting credentials...');
    const credentialsUrl = `${DEX_URL}/dex/auth/local/login?back=&state=${req}`;
    const credentialsData = `login=${encodeURIComponent(
      LOGIN
    )}&password=${encodeURIComponent(PASSWORD)}`;

    await axios.post(credentialsUrl, credentialsData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      maxRedirects: 0,
      validateStatus: () => true,
    });
    console.log('✅ Credentials submitted\n');

    // Step 4: Get approval and CODE
    console.log('📋 Step 4: Getting approval and CODE...');
    const approvalUrl = `${DEX_URL}/dex/approval?req=${req}`;
    const approvalResponse = await axios.get(approvalUrl, {
      maxRedirects: 5,
      validateStatus: () => true,
    });

    if (process.env.DEBUG) {
      console.log(`Approval Response status: ${approvalResponse.status}`);
      console.log(
        `Approval Response data (first 500 chars):`,
        typeof approvalResponse.data === 'string'
          ? approvalResponse.data.substring(0, 500)
          : JSON.stringify(approvalResponse.data).substring(0, 500)
      );
    }

    // Extract CODE from location header for redirect response or from response body
    let codeMatch;
    if (
      (approvalResponse.status === 302 || approvalResponse.status === 303) &&
      approvalResponse.headers.location
    ) {
      codeMatch = approvalResponse.headers.location.match(/code=([^&]+)/);
    }

    if (!codeMatch) {
      // Look for CODE in response body or redirected page
      codeMatch = approvalResponse.data.match(/code=([^&"]+)/);
    }

    if (!codeMatch) {
      codeMatch = approvalResponse.data.match(/CODE=([A-Za-z0-9_-]+)/);
    }

    if (!codeMatch) {
      throw new Error('Could not extract CODE from response');
    }
    code = codeMatch[1];
    console.log(`✅ CODE: ${code}\n`);

    // Step 5: Get session cookie
    console.log('📋 Step 5: Getting session cookie...');
    const sessionUrl = `${DEX_URL}/login/oidc?code=${code}&state=${state}`;
    const sessionResponse = await axios.get(sessionUrl, {
      maxRedirects: 0,
      validateStatus: () => true,
    });

    const setCookieHeader = sessionResponse.headers['set-cookie'];
    if (!setCookieHeader) {
      throw new Error('No Set-Cookie header found');
    }

    const sessionMatch = setCookieHeader
      .find((cookie) => cookie.includes('authservice_session='))
      ?.match(/authservice_session=([^;\s]+)/);

    if (!sessionMatch) {
      throw new Error('Could not extract session cookie');
    }
    sessionCookie = sessionMatch[1];
    console.log(`✅ Session cookie: ${sessionCookie}\n`);

    // Step 6: Test authenticated request
    console.log('📋 Step 6: Testing authenticated request...');
    const apiUrl = `${DEX_URL}/pipeline/apis/v1beta1/pipelines`;
    const apiResponse = await axios.get(apiUrl, {
      headers: { Cookie: `authservice_session=${sessionCookie}` },
      validateStatus: () => true,
    });

    if (apiResponse.status === 200) {
      console.log('✅ Authenticated request successful');
      if (process.env.DEBUG) {
        console.log(
          `📊 Response: ${JSON.stringify(apiResponse.data, null, 2).substring(
            0,
            200
          )}...`
        );
      }
    } else {
      console.log(`⚠️  API request returned status: ${apiResponse.status}`);
    }

    console.log('\n🎉 DEX Authentication test completed successfully!');
  } catch (error) {
    console.error('\n❌ DEX Authentication test failed:');
    console.error(`Error: ${error.message}`);

    if (error.response && process.env.DEBUG) {
      console.error(`Status: ${error.response.status}`);
      console.error(
        `Headers: ${JSON.stringify(error.response.headers, null, 2)}`
      );
      console.error(
        `Data: ${
          typeof error.response.data === 'string'
            ? error.response.data.substring(0, 500)
            : JSON.stringify(error.response.data, null, 2).substring(0, 500)
        }...`
      );
    }

    console.log('\n📊 Current state:');
    console.log(`STATE: ${state || 'not set'}`);
    console.log(`REQ: ${req || 'not set'}`);
    console.log(`CODE: ${code || 'not set'}`);
    console.log(`SESSION: ${sessionCookie || 'not set'}`);

    process.exit(1);
  }
}

if (require.main === module) {
  testDexAuth();
}

module.exports = testDexAuth;
