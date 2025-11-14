/**
 * OIDC Callback Component
 * Handles the callback from OpenID Connect provider after authentication
 */

import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, ActivatedRoute } from '@angular/router';
import { finalize } from 'rxjs/operators';

import { TranslocoModule } from '@jsverse/transloco';
import { environment } from '../../../../environments/environment';

import { AuthService } from '../../../core/services/auth/auth.service';
import { AUTH_CONSTANTS } from '../../../shared/constants/app.constants';
import { AuthError, AuthErrorType } from '../../../shared/models/auth.models';

@Component({
  selector: 'app-auth-callback',
  standalone: true,
  imports: [CommonModule, TranslocoModule],
  templateUrl: './callback.component.html',
  styles: [],
})
export class CallbackComponent implements OnInit {
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly authService = inject(AuthService);

  // State signals
  private readonly _isProcessing = signal(true);
  private readonly _isSuccess = signal(false);
  private readonly _error = signal<AuthError | null>(null);

  // Public readonly signals
  isProcessing = this._isProcessing.asReadonly();
  isSuccess = this._isSuccess.asReadonly();
  error = this._error.asReadonly();

  // Show detailed error information in development
  showErrorDetails(): boolean {
    return !environment.production;
  }

  ngOnInit(): void {
    this.handleCallback();
  }

  /**
   * Handle the OIDC callback
   */
  private handleCallback(): void {
    this._isProcessing.set(true);
    this._error.set(null);

    // Get authorization code and state from URL parameters
    const code = this.route.snapshot.queryParams['code'];
    const state = this.route.snapshot.queryParams['state'];
    const error = this.route.snapshot.queryParams['error'];
    const errorDescription =
      this.route.snapshot.queryParams['error_description'];

    console.log('=== OIDC Callback Parameters ===');
    console.log('Code:', code ? 'received' : 'missing');
    console.log('State:', state ? 'received' : 'missing');
    console.log('Error:', error);
    console.log('Error Description:', errorDescription);

    // Handle OIDC error response
    if (error) {
      const authError: AuthError = {
        type: AuthErrorType.OIDC_ERROR,
        code: error,
        message: errorDescription || `OIDC authentication failed: ${error}`,
        timestamp: new Date(),
      };
      this._error.set(authError);
      this._isProcessing.set(false);
      return;
    }

    // Handle Authorization Code Flow
    if (code && state) {
      console.log('Processing Authorization Code Flow...');

      this.authService
        .exchangeCodeForTokens(code, state)
        .pipe(finalize(() => this._isProcessing.set(false)))
        .subscribe({
          next: (result) => {
            if (result.success) {
              this._isSuccess.set(true);
              console.log('Authorization code exchange successful');

              // Add a small delay to show success state
              setTimeout(() => {
                const returnUrl =
                  this.authService.getReturnUrl() ||
                  AUTH_CONSTANTS.ROUTES.AFTER_LOGIN;
                this.authService.clearReturnUrl();
                this.router.navigateByUrl(returnUrl);
              }, 1500);
            }
          },
          error: (error: AuthError) => {
            this._error.set(error);
            console.error('Auth callback error:', error);
          },
        });
    } else {
      // Fallback to original cookie-based callback handling
      console.log('No authorization code found, using cookie-based flow...');

      this.authService
        .handleAuthCallback()
        .pipe(finalize(() => this._isProcessing.set(false)))
        .subscribe({
          next: (success) => {
            if (success) {
              this._isSuccess.set(true);
              setTimeout(() => {
                const returnUrl =
                  this.authService.getReturnUrl() ||
                  AUTH_CONSTANTS.ROUTES.AFTER_LOGIN;
                this.authService.clearReturnUrl();
                this.router.navigateByUrl(returnUrl);
              }, 1500);
            }
          },
          error: (error: AuthError) => {
            this._error.set(error);
            console.error('Auth callback error:', error);
          },
        });
    }
  }

  /**
   * Retry authentication process
   */
  retry(): void {
    this._error.set(null);
    this._isProcessing.set(true);
    this.handleCallback();
  }

  /**
   * Navigate back to login page
   */
  backToLogin(): void {
    this.router.navigate([AUTH_CONSTANTS.ROUTES.LOGIN]);
  }

  /**
   * Retry authentication by redirecting to login
   */
  retryAuthentication(): void {
    this.backToLogin();
  }

  /**
   * Navigate to login page
   */
  goToLogin(): void {
    this.router.navigate([AUTH_CONSTANTS.ROUTES.LOGIN]);
  }
}
