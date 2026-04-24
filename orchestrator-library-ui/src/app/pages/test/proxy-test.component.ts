import { Component, OnInit, inject, signal, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

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
              <strong>Note:</strong> Proxy endpoints can be checked here.
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
  private readonly platformId = inject(PLATFORM_ID);
  private readonly isBrowser = isPlatformBrowser(this.platformId);

  testResults: ProxyTestResult[] = [];
  isRunning = false;
  hasToken = false;
  tokenPreview = '';
  isAuthenticated = false;

  private testEndpoints = [
    {
      name: '/dex/.well-known/openid_configuration',
      url: '/dex/.well-known/openid_configuration',
      method: 'GET',
      description: 'DEX discovery endpoint',
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
    this.isAuthenticated = false;
    this.hasToken = false;

    // Check for authservice_session cookie as well
    let sessionCookie = null;
    if (this.isBrowser && typeof document !== 'undefined') {
      sessionCookie = document.cookie
        .split('; ')
        .find((row) => row.startsWith('authservice_session='));
    }

    if (sessionCookie) {
      this.hasToken = true;
      this.tokenPreview = 'Session Cookie';
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

      // Prepare headers
      const headers: any = {};

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

}
