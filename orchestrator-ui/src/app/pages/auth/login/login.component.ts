import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  FormBuilder,
  FormGroup,
  Validators,
  ReactiveFormsModule,
} from '@angular/forms';
import { Router } from '@angular/router';
import { finalize } from 'rxjs/operators';

import { TranslocoModule } from '@jsverse/transloco';
import { NgIcon, provideIcons } from '@ng-icons/core';
import {
  lucideEye,
  lucideEyeOff,
  lucideLoader,
  lucideLock,
  lucideMail,
} from '@ng-icons/lucide';

// Spartan UI Components
import { HlmCardImports } from '@spartan-ng/ui-card-helm';
import { HlmButtonDirective } from '@spartan-ng/ui-button-helm';
import { HlmInputDirective } from '@spartan-ng/ui-input-helm';
import { HlmLabelDirective } from '@spartan-ng/ui-label-helm';

import { AuthService } from '../../../core/services/auth/auth.service';
import { MockAuthService } from '../../../mock/auth.mock';
import { AUTH_CONSTANTS } from '../../../shared/constants/app.constants';
import {
  LoginCredentials,
  AuthError,
} from '../../../shared/models/auth.models';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    TranslocoModule,
    NgIcon,
    ...HlmCardImports,
    HlmButtonDirective,
    HlmInputDirective,
    HlmLabelDirective,
  ],
  providers: [
    provideIcons({
      lucideEye,
      lucideEyeOff,
      lucideLoader,
      lucideLock,
      lucideMail,
    }),
  ],
  templateUrl: './login.component.html',
  styleUrls: [],
})
export class LoginComponent {
  private readonly fb = inject(FormBuilder);
  private readonly router = inject(Router);
  private readonly authService = inject(AuthService);
  private readonly mockAuthService = inject(MockAuthService);

  private readonly _isLoading = signal(false);
  private readonly _showPassword = signal(false);

  loginForm: FormGroup;

  isLoading = this._isLoading.asReadonly();
  showPassword = this._showPassword.asReadonly();

  constructor() {
    this.loginForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(6)]],
    });

    if (this.mockAuthService.isMockAuthEnabled()) {
      this.loginForm.patchValue({
        email: 'admin@admin.com',
        password: 'password',
      });
    }
  }

  togglePasswordVisibility(): void {
    this._showPassword.update((show) => !show);
  }

  /**
   * Initiate OIDC login flow
   */
  onOidcLogin(): void {
    console.log('Initiating OIDC Authorization Code Flow');
    this.authService.initiateOidcLogin();
  }

  onLogin(): void {
    if (this.loginForm.invalid) {
      this.markAllFieldsAsTouched();
      return;
    }

    this._isLoading.set(true);

    const credentials: LoginCredentials = {
      email: this.loginForm.value.email,
      password: this.loginForm.value.password,
    };

    // Проверяем, совпадают ли credentials с mock данными
    const isMockCredentials =
      credentials.email === 'admin@admin.com' &&
      credentials.password === 'password';

    console.log('=== Login Flow Decision ===');
    console.log('Is mock credentials?', isMockCredentials);
    console.log('Form values:', {
      email: credentials.email,
      password: '[HIDDEN]',
    });

    if (isMockCredentials) {
      console.log('Using MOCK authentication flow');
      // Используем mock аутентификацию
      this.authService
        .login(credentials)
        .pipe(finalize(() => this._isLoading.set(false)))
        .subscribe({
          next: (response) => {
            console.log('Mock login response:', response);
            if (response.success) {
              const returnUrl =
                this.authService.getReturnUrl() ||
                AUTH_CONSTANTS.ROUTES.AFTER_LOGIN;
              this.authService.clearReturnUrl();
              this.router.navigateByUrl(returnUrl);
            }
          },
          error: (error: AuthError) => {
            console.error('Mock login error:', error);
          },
        });
    } else {
      console.log('Using OIDC authentication flow with credentials');
      // Use OIDC authentication with real credentials
      this.authService
        .login(credentials)
        .pipe(finalize(() => this._isLoading.set(false)))
        .subscribe({
          next: (response) => {
            console.log('OIDC login response:', response);
            if (response.success) {
              const returnUrl =
                this.authService.getReturnUrl() ||
                AUTH_CONSTANTS.ROUTES.AFTER_LOGIN;
              this.authService.clearReturnUrl();
              this.router.navigateByUrl(returnUrl);
            }
          },
          error: (error: AuthError) => {
            console.error('OIDC login error:', error);
          },
        });
    }
  }

  private markAllFieldsAsTouched(): void {
    Object.keys(this.loginForm.controls).forEach((key) => {
      this.loginForm.get(key)?.markAsTouched();
    });
  }
}
