import { Component, OnInit, inject, signal, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../core/services/auth/auth.service';
import { LoginCredentials } from '../../shared/models/auth.models';

interface ProxyTestResult {
  endpoint: string;
  status: 'pending' | 'success' | 'error';
  response?: any;
  error?: string;
  duration?: number;
}

@Component({
  selector: 'app-proxy-test',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="proxy-test-page">
      <div class="proxy-test-container">
        <h1 class="text-2xl font-bold mb-6">Proxy Test Dashboard</h1>

        <div class="mb-6">
          <button
            (click)="runAllTests()"
            [disabled]="isRunning"
            class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded mr-4"
          >
            {{ isRunning ? 'Running Tests...' : 'Run All Tests' }}
          </button>

          <button
            (click)="clearResults()"
            class="bg-gray-500 hover:bg-gray-700 text-white font-bold py-2 px-4 rounded mr-4"
          >
            Clear Results
          </button>

          <button
            (click)="testOpenIDFlow()"
            [disabled]="isRunning"
            class="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded"
          >
            Test OpenID Flow
          </button>
        </div>

        <div class="mb-6 p-4 bg-blue-50 rounded">
          <h2 class="font-semibold mb-2">OpenID Connect Test</h2>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium mb-1">Email:</label>
              <input
                [(ngModel)]="testCredentials.email"
                type="email"
                class="w-full px-3 py-2 border rounded"
                placeholder="test@example.com"
              />
            </div>
            <div>
              <label class="block text-sm font-medium mb-1">Password:</label>
              <input
                [(ngModel)]="testCredentials.password"
                type="password"
                class="w-full px-3 py-2 border rounded"
                placeholder="password"
              />
            </div>
          </div>
          <button
            (click)="testOpenIDLogin()"
            [disabled]="
              isRunning || !testCredentials.email || !testCredentials.password
            "
            class="mt-3 bg-purple-500 hover:bg-purple-700 text-white font-bold py-2 px-4 rounded"
          >
            Test OpenID Login
          </button>
          <div
            *ngIf="openidTestResult"
            class="mt-3 p-3 rounded"
            [ngClass]="{
              'bg-green-100 text-green-800': openidTestResult.success,
              'bg-red-100 text-red-800': !openidTestResult.success
            }"
          >
            {{ openidTestResult.message }}
          </div>
        </div>

        <div class="test-results-container">
          <div class="grid gap-4">
            <div *ngFor="let test of testResults" class="border rounded-lg p-4">
              <div class="flex items-center justify-between mb-2">
                <h3 class="font-semibold">{{ test.endpoint }}</h3>

                <div class="flex items-center">
                  <span
                    *ngIf="test.duration"
                    class="text-sm text-gray-500 mr-2"
                  >
                    {{ test.duration }}ms
                  </span>

                  <span
                    [ngClass]="{
                      'bg-yellow-100 text-yellow-800':
                        test.status === 'pending',
                      'bg-green-100 text-green-800': test.status === 'success',
                      'bg-red-100 text-red-800': test.status === 'error'
                    }"
                    class="px-2 py-1 rounded text-sm"
                  >
                    {{ test.status.toUpperCase() }}
                  </span>
                </div>
              </div>

              <div *ngIf="test.status === 'pending'" class="text-gray-500">
                Testing proxy connection...
              </div>

              <div *ngIf="test.status === 'success'" class="text-green-600">
                <p class="text-sm mb-2">✅ Proxy working correctly</p>
                <details class="text-xs">
                  <summary class="cursor-pointer">View Response</summary>
                  <pre
                    class="mt-2 bg-gray-100 p-2 rounded overflow-x-auto max-h-40 overflow-y-auto"
                    >{{ formatResponse(test.response) }}</pre
                  >
                </details>
              </div>

              <div *ngIf="test.status === 'error'" class="text-red-600">
                <p class="text-sm">❌ {{ test.error }}</p>
              </div>
            </div>
          </div>
        </div>

        <div class="mt-8 p-4 bg-gray-50 rounded">
          <h2 class="font-semibold mb-2">Authentication Status</h2>
          <p>
            <strong>Session Available:</strong> {{ hasToken ? 'Yes' : 'No' }}
          </p>
          <p *ngIf="hasToken">
            <strong>Session Type:</strong> {{ tokenPreview }}
          </p>
          <p>
            <strong>User Authenticated:</strong>
            {{ isAuthenticated ? 'Yes' : 'No' }}
          </p>
          <div class="mt-2 text-sm text-gray-600">
            <p>
              <strong>Note:</strong> Authentication is managed by AuthService
              via cookies
            </p>
            <p>
              <strong>Cookie:</strong>
              {{ getSessionCookie() || 'No session cookie' }}
            </p>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [
    `
      .proxy-test-page {
        height: 100vh;
        overflow-y: auto;
        background-color: #f9fafb;
      }

      .proxy-test-container {
        max-width: 1000px;
        margin: 0 auto;
        padding: 1.5rem;
        min-height: 100%;
      }

      .test-results-container {
        max-height: 60vh;
        overflow-y: auto;
        padding-right: 0.5rem;
      }

      .test-results-container::-webkit-scrollbar {
        width: 6px;
      }

      .test-results-container::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 3px;
      }

      .test-results-container::-webkit-scrollbar-thumb {
        background: #c1c1c1;
        border-radius: 3px;
      }

      .test-results-container::-webkit-scrollbar-thumb:hover {
        background: #a8a8a8;
      }

      :host {
        display: block;
        height: 100%;
      }
    `,
  ],
})
export class ProxyTestComponent implements OnInit {
  protected readonly http = inject(HttpClient);
  private readonly authService = inject(AuthService);
  private readonly platformId = inject(PLATFORM_ID);
  private readonly isBrowser = isPlatformBrowser(this.platformId);

  testResults: ProxyTestResult[] = [];
  isRunning = false;
  hasToken = false;
  tokenPreview = '';
  isAuthenticated = false;
  testCredentials: LoginCredentials = { email: '', password: '' };
  openidTestResult: { success: boolean; message: string } | null = null;

  private testEndpoints = [
    {
      name: '/api/k8s_cluster_info/',
      url: '/api/k8s_cluster_info/',
      method: 'GET',
      description: 'API Backend Health Check',
    },
    {
      name: '/dex/.well-known/openid_configuration',
      url: '/dex/.well-known/openid_configuration',
      method: 'GET',
      description: 'DEX OIDC Discovery (May require auth)',
    },
    {
      name: '/dex/auth (Test Auth Endpoint)',
      url: '/dex/auth?client_id=authservice-oidc&redirect_uri=/authservice/oidc/callback&response_type=code&scope=openid+profile+email+groups',
      method: 'GET',
      description: 'DEX Authentication Endpoint',
    },
    {
      name: '/authservice/oidc/callback',
      url: '/authservice/oidc/callback',
      method: 'GET',
      description: 'AuthService OIDC Callback',
    },
    {
      name: '/cog (with token)',
      url: '/cog',
      method: 'GET',
      description: 'COG Dashboard Proxy',
      requiresAuth: true,
    },
    {
      name: '/cog-iframe (with token)',
      url: '/cog-iframe',
      method: 'GET',
      description: 'COG iframe Proxy (Production)',
      requiresAuth: true,
    },
    {
      name: '/iframe/api/v1/namespace',
      url: '/iframe/api/v1/namespace',
      method: 'GET',
      description: 'Kubernetes Dashboard Proxy',
    },
  ];

  ngOnInit(): void {
    this.checkAuthStatus();
    this.initializeTestResults();
  }

  private checkAuthStatus(): void {
    this.isAuthenticated = this.authService.authenticated();
    const token = this.authService.getAccessToken();
    this.hasToken = !!token;

    // Check for authservice_session cookie as well
    let sessionCookie = null;
    if (this.isBrowser && typeof document !== 'undefined') {
      sessionCookie = document.cookie
        .split('; ')
        .find((row) => row.startsWith('authservice_session='));
    }

    if (token && token !== 'managed-by-authservice') {
      // Show first and last 10 characters of token
      this.tokenPreview =
        token.length > 20
          ? `${token.substring(0, 10)}...${token.substring(token.length - 10)}`
          : token;
    } else if (sessionCookie) {
      this.hasToken = true;
      this.tokenPreview = 'AuthService Session Cookie';
    }
  }

  private initializeTestResults(): void {
    this.testResults = this.testEndpoints.map((endpoint) => ({
      endpoint: `${endpoint.method} ${endpoint.name}`,
      status: 'pending',
    }));
  }

  runAllTests(): void {
    if (this.isRunning) return;

    this.isRunning = true;
    this.initializeTestResults();

    // Run tests sequentially with delay
    this.runTestsSequentially(0);
  }

  private async runTestsSequentially(index: number): Promise<void> {
    if (index >= this.testEndpoints.length) {
      this.isRunning = false;
      return;
    }

    const endpoint = this.testEndpoints[index];
    await this.testEndpoint(endpoint, index);

    // Wait 500ms before next test
    setTimeout(() => {
      this.runTestsSequentially(index + 1);
    }, 500);
  }

  private async testEndpoint(endpoint: any, index: number): Promise<void> {
    const startTime = Date.now();

    try {
      // Skip auth-required endpoints if no token/session
      if (endpoint.requiresAuth && !this.hasToken) {
        throw new Error(
          'Authentication required but no token/session available'
        );
      }

      // Prepare headers - AuthService manages authentication via cookies
      const headers: any = {};
      // Note: AuthService uses cookies, so we don't need to manually add Authorization header
      // The authservice_session cookie will be automatically included

      // Make request
      const response = await this.http
        .get(endpoint.url, {
          headers,
          observe: 'response',
        })
        .toPromise();

      const duration = Date.now() - startTime;

      this.testResults[index] = {
        endpoint: `${endpoint.method} ${endpoint.name}`,
        status: 'success',
        response: {
          status: response?.status,
          statusText: response?.statusText,
          headers: this.extractHeaders(response?.headers),
          body: response?.body,
        },
        duration,
      };
    } catch (error: any) {
      const duration = Date.now() - startTime;

      this.testResults[index] = {
        endpoint: `${endpoint.method} ${endpoint.name}`,
        status: 'error',
        error: this.formatError(error),
        duration,
      };
    }
  }

  private extractHeaders(headers: any): any {
    if (!headers) return {};

    const result: any = {};
    headers.keys().forEach((key: string) => {
      result[key] = headers.get(key);
    });
    return result;
  }

  private formatError(error: any): string {
    if (error.status === 0) {
      return 'Network error - proxy might be down or CORS issue';
    }

    if (error.status >= 400 && error.status < 500) {
      return `Client error: ${error.status} ${
        error.statusText || error.message
      }`;
    }

    if (error.status >= 500) {
      return `Server error: ${error.status} ${
        error.statusText || error.message
      }`;
    }

    return error.message || 'Unknown error';
  }

  formatResponse(response: any): string {
    if (!response) return '';

    try {
      return JSON.stringify(response, null, 2);
    } catch {
      return String(response);
    }
  }

  clearResults(): void {
    this.initializeTestResults();
  }

  getSessionCookie(): string {
    if (!this.isBrowser || typeof document === 'undefined') {
      return 'SSR Environment';
    }

    const sessionCookie = document.cookie
      .split('; ')
      .find((row) => row.startsWith('authservice_session='));

    if (sessionCookie) {
      const value = sessionCookie.split('=')[1];
      return value.length > 20
        ? `${value.substring(0, 10)}...${value.substring(value.length - 10)}`
        : value;
    }
    return '';
  }

  testOpenIDFlow(): void {
    console.log('Testing OpenID Connect flow...');
    this.openidTestResult = {
      success: true,
      message:
        'OpenID Connect flow test: Check browser console for detailed logs and network tab for requests.',
    };
  }

  testOpenIDLogin(): void {
    if (!this.testCredentials.email || !this.testCredentials.password) {
      this.openidTestResult = {
        success: false,
        message: 'Please provide both email and password',
      };
      return;
    }

    console.log('Testing OpenID login with credentials:', {
      email: this.testCredentials.email,
      password: '[HIDDEN]',
    });

    this.openidTestResult = {
      success: true,
      message: 'Testing OpenID login... Check console and network tab.',
    };

    this.authService.login(this.testCredentials).subscribe({
      next: (response) => {
        console.log('OpenID login test response:', response);
        this.openidTestResult = {
          success: true,
          message: `OpenID login successful: ${response.message}`,
        };
        this.checkAuthStatus(); // Refresh auth status
      },
      error: (error) => {
        console.error('OpenID login test error:', error);
        this.openidTestResult = {
          success: false,
          message: `OpenID login failed: ${error.message}`,
        };
      },
    });
  }
}
