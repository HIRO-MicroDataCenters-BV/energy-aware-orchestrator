/**
 * Unauthorized Component
 * Error page for 401 unauthorized access attempts
 */

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';

import { TranslocoModule } from '@jsverse/transloco';

@Component({
  selector: 'app-unauthorized',
  standalone: true,
  imports: [CommonModule, TranslocoModule],
  template: `
    <div
      class="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 p-4"
    >
      <div class="w-full max-w-md">
        <div
          class="bg-card text-card-foreground shadow-sm rounded-lg border p-6"
        >
          <div class="text-center space-y-6">
            <!-- Icon -->
            <div
              class="inline-flex items-center justify-center w-16 h-16 bg-amber-100 rounded-full"
            >
              <svg
                class="w-8 h-8 text-amber-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.314 16.5c-.77.833.192 2.5 1.732 2.5z"
                />
              </svg>
            </div>

            <!-- Content -->
            <div>
              <h1 class="text-2xl font-bold text-foreground">
                {{ 'error.unauthorized.title' | transloco }}
              </h1>
              <p class="text-muted-foreground mt-2">
                {{ 'error.unauthorized.message' | transloco }}
              </p>
            </div>

            <!-- Error Code -->
            <div class="text-6xl font-bold text-muted-foreground/20">401</div>

            <!-- Actions -->
            <div class="space-y-3">
              <!-- Login Button -->
              <button
                type="button"
                class="inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2 w-full"
                (click)="goToLogin()"
              >
                Login
              </button>

              <!-- Back to Home Button -->
              <button
                type="button"
                class="inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-10 px-4 py-2 w-full"
                (click)="goToHome()"
              >
                {{ 'error.unauthorized.back_home' | transloco }}
              </button>
            </div>

            <!-- Additional Info -->
            <div class="text-xs text-muted-foreground">
              If you believe this is an error, please contact your
              administrator.
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div class="text-center mt-8 text-xs text-muted-foreground">
          {{ 'app.footer' | transloco }}
        </div>
      </div>
    </div>
  `,
  styles: [],
})
export class UnauthorizedComponent {
  private readonly router = inject(Router);

  /**
   * Navigate to login page
   */
  goToLogin(): void {
    this.router.navigate(['/auth/login']);
  }

  /**
   * Navigate to home page
   */
  goToHome(): void {
    this.router.navigate(['/']);
  }
}
