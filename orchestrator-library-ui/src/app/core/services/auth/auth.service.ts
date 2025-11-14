/**
 * Authentication Service
 * Main service for handling authentication with OpenID Connect and mock fallback
 */

import {
  Injectable,
  inject,
  signal,
  computed,
  PLATFORM_ID,
} from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { Observable, of, throwError, from } from 'rxjs';
import { map, catchError, tap, switchMap, finalize } from 'rxjs/operators';

import {
  User,
  AuthState,
  LoginCredentials,
  LoginResponse,
  AuthTokens,
  AuthError,
  AuthErrorType,
  UserProfile,
} from '../../../shared/models/auth.models';
import { AUTH_CONSTANTS } from '../../../shared/constants/app.constants';
import { MockAuthService } from '../../../mock/auth.mock';

// OIDC-specific interfaces
interface OidcAuthResult {
  isAuthenticated: boolean;
  userData?: UserProfile;
  accessToken?: string;
  refreshToken?: string;
  idToken?: string;
  expiresAt?: number;
}

interface OidcCheckAuthResult {
  isAuthenticated: boolean;
  userData?: UserProfile;
  accessToken?: string;
  refreshToken?: string;
  idToken?: string;
  expiresAt?: number;
}

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private readonly router = inject(Router);
  private readonly http = inject(HttpClient);
  private readonly platformId = inject(PLATFORM_ID);

  private readonly mockAuthService = inject(MockAuthService);
  private readonly isBrowser = isPlatformBrowser(this.platformId);

  // Auth state management
  private readonly authState = signal<AuthState>({
    isAuthenticated: false,
    isLoading: false,
    user: null,
    tokens: null,
    error: null,
  });

  private readonly currentUser = signal<User | null>(null);
  private readonly isAuthenticated = signal<boolean>(false);
  private readonly isLoading = signal<boolean>(false);

  // Public readonly signals
  public readonly state = this.authState.asReadonly();
  public readonly user = this.currentUser.asReadonly();
  public readonly authenticated = this.isAuthenticated.asReadonly();
  public readonly loading = this.isLoading.asReadonly();

  // Computed properties
  public readonly userHasRole = computed(() => (role: string) => {
    const user = this.currentUser();
    return user?.roles?.includes(role) ?? false;
  });

  public readonly userHasPermission = computed(() => (permission: string) => {
    const user = this.currentUser();
    return user?.permissions?.includes(permission) ?? false;
  });

  public readonly isAdmin = computed(() => {
    return this.userHasRole()(AUTH_CONSTANTS.ROLES.ADMIN);
  });

  constructor() {
    // Set initial state without async initialization
    this.setAuthState({
      isAuthenticated: false,
      isLoading: false,
      user: null,
      tokens: null,
      error: null,
    });

    // Only initialize auth in browser environment
    if (this.isBrowser) {
      // Check for stored auth data immediately
      this.checkStoredAuth();
    }
  }

  /**
   * Check stored authentication data synchronously
   */
  private checkStoredAuth(): void {
    try {
      const storedUser = this.getStoredUser();
      const storedTokens = this.getStoredTokens();

      // Also check for authservice_session cookie
      const sessionCookie = document.cookie
        .split('; ')
        .find((row) => row.startsWith('authservice_session='));

      if ((storedUser && storedTokens) || sessionCookie) {
        console.log('Found existing authentication session');
        this.setAuthState({
          isAuthenticated: true,
          isLoading: false,
          user: storedUser,
          tokens: storedTokens,
          error: null,
        });
      } else {
        console.log('No existing authentication found');
      }
    } catch (error) {
      console.error('Error checking stored auth:', error);
      this.clearStoredAuthData();
    }
  }

  /**
   * Check for existing authentication session
   */
  private checkExistingSession(): void {
    console.log('=== checkExistingSession ===');
    console.log('Is browser:', this.isBrowser);

    if (!this.isBrowser) {
      console.log('Skipping session check - not browser');
      return;
    }

    // Check for authservice_session cookie
    const sessionCookie = document.cookie
      .split('; ')
      .find((row) => row.startsWith('authservice_session='));

    if (sessionCookie) {
      console.log('Found authservice_session cookie');
      // Could validate session here by making a test request
      this.setAuthState({
        isAuthenticated: true,
        isLoading: false,
        user: null,
        tokens: null,
        error: null,
      });
    } else {
      console.log('No authservice_session cookie found');
      this.setAuthState({
        isAuthenticated: false,
        isLoading: false,
        user: null,
        tokens: null,
        error: null,
      });
    }
  }

  /**
   * Login with email and password (mock) or redirect to OIDC provider
   */
  login(credentials?: LoginCredentials): Observable<LoginResponse> {
    console.log('=== AuthService.login() called ===');
    console.log('Credentials provided:', !!credentials);
    console.log('Mock auth enabled:', this.mockAuthService.isMockAuthEnabled());
    console.log('Is browser:', this.isBrowser);

    this.setLoading(true);

    // Check if credentials match mock credentials specifically
    const isMockCredentials =
      credentials &&
      credentials.email === 'admin@admin.com' &&
      credentials.password === 'password';

    if (this.mockAuthService.isMockAuthEnabled() && isMockCredentials) {
      console.log('Using mock authentication');
      return this.mockAuthService.login(credentials).pipe(
        tap((response) => {
          if (response.success && response.user && response.tokens) {
            this.setAuthState({
              isAuthenticated: true,
              isLoading: false,
              user: response.user,
              tokens: response.tokens,
              error: null,
            });
            this.storeAuthData(response.user, response.tokens);
          }
        }),
        catchError((_error) => {
          const authError = this.createAuthError(
            AuthErrorType.UNKNOWN,
            'MOCK_LOGIN_ERROR',
            'Failed to perform mock login'
          );
          this.setAuthState({
            ...this.authState(),
            isLoading: false,
            error: authError.message,
          });
          return throwError(() => authError);
        }),
        finalize(() => this.setLoading(false))
      );
    }

    // For real authentication, redirect to protected resource
    // AuthService will intercept and start the DEX flow
    if (!this.isBrowser) {
      console.error('Login attempted in SSR environment');
      this.setLoading(false);
      return throwError(() =>
        this.createAuthError(
          AuthErrorType.OIDC_ERROR,
          'SSR_ERROR',
          'Authentication not available in server environment'
        )
      );
    }

    console.log('=== Starting OIDC Password Flow ===');
    console.log('Using credentials for OIDC authentication...');
    console.log('Credentials object:', credentials);
    console.log('Email:', credentials?.email);
    console.log('Password length:', credentials?.password?.length);

    if (!credentials) {
      console.error('No credentials provided');
      this.setLoading(false);
      return throwError(() =>
        this.createAuthError(
          AuthErrorType.OIDC_ERROR,
          'NO_CREDENTIALS',
          'No credentials provided for authentication'
        )
      );
    }

    console.log('Credentials validated, proceeding with OIDC request...');

    try {
      // Use OIDC Resource Owner Password Credentials Grant
      const tokenUrl = AUTH_CONSTANTS.ROUTES.DEX_TOKEN;
      console.log('Token URL:', tokenUrl);

      const body = new URLSearchParams({
        grant_type: 'password',
        username: credentials.email,
        password: credentials.password,
        client_id: AUTH_CONSTANTS.OIDC.CLIENT_ID,
        client_secret: AUTH_CONSTANTS.OIDC.CLIENT_SECRET,
        scope: AUTH_CONSTANTS.OIDC.SCOPE,
      });

      console.log('Request body params:', {
        grant_type: 'password',
        username: credentials.email,
        password: '[HIDDEN]',
        client_id: AUTH_CONSTANTS.OIDC.CLIENT_ID,
        client_secret: '[HIDDEN]',
        scope: AUTH_CONSTANTS.OIDC.SCOPE,
      });

      console.log('Making HTTP POST request to:', tokenUrl);

      return this.http
        .post<any>(tokenUrl, body.toString(), {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
        })
        .pipe(
          map((tokenResponse) => {
            console.log('=== OIDC Token Response ===');
            console.log('Full response:', tokenResponse);
            console.log('Token received successfully');

            // Set authenticated state
            this.setAuthState({
              isAuthenticated: true,
              isLoading: false,
              user: null, // Will be populated from token if needed
              tokens: {
                accessToken: tokenResponse.access_token,
                refreshToken: tokenResponse.refresh_token,
                idToken: tokenResponse.id_token,
                expiresAt: Date.now() + tokenResponse.expires_in * 1000,
              },
              error: null,
            });

            console.log('Auth state updated successfully');

            return {
              success: true,
              message: 'Authentication successful',
            };
          }),
          catchError((error) => {
            console.error('=== OIDC Token Error ===');
            console.error('Full error object:', error);
            console.error('Error status:', error.status);
            console.error('Error statusText:', error.statusText);
            console.error('Error message:', error.message);
            console.error('Error url:', error.url);
            console.error('Error body:', error.error);

            const errorMessage =
              error.error?.error_description ||
              error.error?.error ||
              error.statusText ||
              'Invalid credentials';

            console.error('Parsed error message:', errorMessage);

            const authError = this.createAuthError(
              AuthErrorType.OIDC_ERROR,
              'CREDENTIALS_ERROR',
              errorMessage
            );

            this.setAuthState({
              ...this.authState(),
              isLoading: false,
              error: authError.message,
            });

            return throwError(() => authError);
          }),
          finalize(() => {
            console.log('OIDC request finalized, setting loading to false');
            this.setLoading(false);
          })
        );
    } catch (error) {
      console.error('=== OIDC Authentication Error (Synchronous) ===');
      console.error('Error object:', error);

      const errorMessage =
        (error as any)?.message || 'Unknown authentication error';
      const authError = this.createAuthError(
        AuthErrorType.OIDC_ERROR,
        'AUTH_ERROR',
        `Authentication failed: ${errorMessage}`
      );

      this.setAuthState({
        ...this.authState(),
        isLoading: false,
        error: authError.message,
      });

      this.setLoading(false);
      return throwError(() => authError);
    }
  }

  /**
   * Handle authentication callback after successful login
   */
  handleAuthCallback(): Observable<boolean> {
    console.log('=== handleAuthCallback ===');
    this.setLoading(true);

    if (!this.isBrowser) {
      this.setLoading(false);
      return throwError(() =>
        this.createAuthError(
          AuthErrorType.OIDC_ERROR,
          'SSR_ERROR',
          'Auth callback not available in server environment'
        )
      );
    }

    // Check for authservice_session cookie
    const sessionCookie = document.cookie
      .split('; ')
      .find((row) => row.startsWith('authservice_session='));

    if (sessionCookie) {
      console.log('Found authservice_session cookie after callback');

      this.setAuthState({
        isAuthenticated: true,
        isLoading: false,
        user: null, // Will be populated later if needed
        tokens: null,
        error: null,
      });

      // Navigate to the intended route or default
      const returnUrl =
        this.getReturnUrl() || AUTH_CONSTANTS.ROUTES.AFTER_LOGIN;
      this.clearReturnUrl();
      this.router.navigateByUrl(returnUrl);

      this.setLoading(false);
      return of(true);
    } else {
      console.log('No authservice_session cookie found after callback');
      const authError = this.createAuthError(
        AuthErrorType.OIDC_ERROR,
        'CALLBACK_ERROR',
        'Authentication session not found after callback'
      );
      this.setAuthState({
        ...this.authState(),
        isLoading: false,
        error: authError.message,
      });
      this.setLoading(false);
      return throwError(() => authError);
    }
  }

  /**
   * Logout user
   */
  logout(): Observable<boolean> {
    this.setLoading(true);

    // Clear stored data immediately
    this.clearStoredAuthData();
    this.setAuthState({
      isAuthenticated: false,
      isLoading: false,
      user: null,
      tokens: null,
      error: null,
    });

    // If mock auth was used, just redirect
    if (this.mockAuthService.isMockAuthEnabled()) {
      this.router.navigate([AUTH_CONSTANTS.ROUTES.AFTER_LOGOUT]);
      this.setLoading(false);
      return of(true);
    }

    // Clear authservice_session cookie if it exists
    if (this.isBrowser) {
      document.cookie =
        'authservice_session=; Path=/; Expires=Thu, 01 Jan 1970 00:00:01 GMT;';
      console.log('Cleared authservice_session cookie');
    }

    // Navigate to logout page
    this.router.navigate([AUTH_CONSTANTS.ROUTES.AFTER_LOGOUT]);
    this.setLoading(false);
    return of(true);
  }

  /**
   * Refresh authentication tokens
   */
  refreshTokens(): Observable<AuthTokens> {
    const currentTokens = this.authState().tokens;

    if (!currentTokens?.refreshToken) {
      return throwError(() =>
        this.createAuthError(
          AuthErrorType.TOKEN_EXPIRED,
          'NO_REFRESH_TOKEN',
          'No refresh token available'
        )
      );
    }

    // Use mock refresh if mock auth is enabled
    if (this.mockAuthService.isMockAuthEnabled()) {
      return this.mockAuthService.refreshToken(currentTokens.refreshToken).pipe(
        tap((tokens) => {
          this.setAuthState({
            ...this.authState(),
            tokens,
          });
          this.storeTokens(tokens);
        })
      );
    }

    // For AuthService-managed sessions, tokens are managed by the service
    // Check if we still have a valid session cookie
    const sessionCookie = document.cookie
      .split('; ')
      .find((row) => row.startsWith('authservice_session='));

    if (sessionCookie) {
      // Session is still valid, return dummy tokens
      const tokens: AuthTokens = {
        accessToken: 'managed-by-authservice',
        refreshToken: 'managed-by-authservice',
        expiresAt: Date.now() + 3600 * 1000, // 1 hour
      };

      this.setAuthState({
        ...this.authState(),
        tokens,
      });

      return of(tokens);
    }

    // SSR fallback
    return throwError(() =>
      this.createAuthError(
        AuthErrorType.TOKEN_EXPIRED,
        'SSR_ERROR',
        'Token refresh not available in server environment'
      )
    );
  }

  /**
   * Get current access token
   */
  getAccessToken(): string | null {
    return this.authState().tokens?.accessToken || null;
  }

  /**
   * Check if user has specific role
   */
  hasRole(role: string): boolean {
    return this.userHasRole()(role);
  }

  /**
   * Check if user has specific permission
   */
  hasPermission(permission: string): boolean {
    return this.userHasPermission()(permission);
  }

  /**
   * Set return URL for post-login navigation
   */
  setReturnUrl(url: string): void {
    if (this.isBrowser && typeof localStorage !== 'undefined') {
      localStorage.setItem(AUTH_CONSTANTS.TOKENS.RETURN_URL_KEY, url);
    }
  }

  /**
   * Get return URL for post-login navigation
   */
  getReturnUrl(): string | null {
    if (this.isBrowser && typeof localStorage !== 'undefined') {
      return localStorage.getItem(AUTH_CONSTANTS.TOKENS.RETURN_URL_KEY);
    }
    return null;
  }

  /**
   * Clear return URL
   */
  clearReturnUrl(): void {
    if (this.isBrowser && typeof localStorage !== 'undefined') {
      localStorage.removeItem(AUTH_CONSTANTS.TOKENS.RETURN_URL_KEY);
    }
  }

  // Private helper methods

  private setLoading(loading: boolean): void {
    this.isLoading.set(loading);
    this.setAuthState({
      ...this.authState(),
      isLoading: loading,
    });
  }

  private setAuthState(state: AuthState): void {
    this.authState.set(state);
    this.currentUser.set(state.user);
    this.isAuthenticated.set(state.isAuthenticated);
    this.isLoading.set(state.isLoading);
  }

  private mapOidcUserToUser(oidcUser: UserProfile): User {
    return {
      id: oidcUser.sub,
      email: oidcUser.email,
      name:
        oidcUser.name ||
        `${oidcUser.given_name || ''} ${oidcUser.family_name || ''}`.trim(),
      firstName: oidcUser.given_name,
      lastName: oidcUser.family_name,
      roles: oidcUser.roles || [AUTH_CONSTANTS.ROLES.USER],
      permissions: [AUTH_CONSTANTS.PERMISSIONS.READ],
      avatar: oidcUser.picture,
      isEmailVerified: oidcUser.email_verified,
      lastLoginAt: new Date(),
    };
  }

  private createDefaultTokens(): AuthTokens {
    return {
      accessToken: 'managed-by-authservice',
      refreshToken: 'managed-by-authservice',
      expiresAt: Date.now() + 3600000, // 1 hour from now
    };
  }

  private isTokenValid(tokens: AuthTokens): boolean {
    return tokens.expiresAt > Date.now();
  }

  private storeAuthData(user: User, tokens: AuthTokens): void {
    this.storeUser(user);
    this.storeTokens(tokens);
  }

  private storeUser(user: User): void {
    if (this.isBrowser && typeof localStorage !== 'undefined') {
      localStorage.setItem(
        AUTH_CONSTANTS.TOKENS.USER_KEY,
        JSON.stringify(user)
      );
    }
  }

  private storeTokens(tokens: AuthTokens): void {
    if (this.isBrowser && typeof localStorage !== 'undefined') {
      localStorage.setItem(
        AUTH_CONSTANTS.TOKENS.ACCESS_TOKEN_KEY,
        tokens.accessToken
      );
      if (tokens.refreshToken) {
        localStorage.setItem(
          AUTH_CONSTANTS.TOKENS.REFRESH_TOKEN_KEY,
          tokens.refreshToken
        );
      }
      if (tokens.idToken) {
        localStorage.setItem(
          AUTH_CONSTANTS.TOKENS.ID_TOKEN_KEY,
          tokens.idToken
        );
      }
      localStorage.setItem(
        AUTH_CONSTANTS.TOKENS.EXPIRES_AT_KEY,
        tokens.expiresAt.toString()
      );
    }
  }

  private getStoredUser(): User | null {
    if (!this.isBrowser || typeof localStorage === 'undefined') {
      return null;
    }
    try {
      const stored = localStorage.getItem(AUTH_CONSTANTS.TOKENS.USER_KEY);
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  }

  private getStoredTokens(): AuthTokens | null {
    if (!this.isBrowser || typeof localStorage === 'undefined') {
      return null;
    }
    try {
      const accessToken = localStorage.getItem(
        AUTH_CONSTANTS.TOKENS.ACCESS_TOKEN_KEY
      );
      const refreshToken = localStorage.getItem(
        AUTH_CONSTANTS.TOKENS.REFRESH_TOKEN_KEY
      );
      const idToken = localStorage.getItem(AUTH_CONSTANTS.TOKENS.ID_TOKEN_KEY);
      const expiresAt = localStorage.getItem(
        AUTH_CONSTANTS.TOKENS.EXPIRES_AT_KEY
      );

      if (!accessToken || !expiresAt) {
        return null;
      }

      return {
        accessToken,
        refreshToken: refreshToken || undefined,
        idToken: idToken || undefined,
        expiresAt: parseInt(expiresAt, 10),
      };
    } catch {
      return null;
    }
  }

  private clearStoredAuthData(): void {
    if (this.isBrowser && typeof localStorage !== 'undefined') {
      localStorage.removeItem(AUTH_CONSTANTS.TOKENS.ACCESS_TOKEN_KEY);
      localStorage.removeItem(AUTH_CONSTANTS.TOKENS.REFRESH_TOKEN_KEY);
      localStorage.removeItem(AUTH_CONSTANTS.TOKENS.ID_TOKEN_KEY);
      localStorage.removeItem(AUTH_CONSTANTS.TOKENS.EXPIRES_AT_KEY);
      localStorage.removeItem(AUTH_CONSTANTS.TOKENS.USER_KEY);
      localStorage.removeItem(AUTH_CONSTANTS.TOKENS.STATE_KEY);
      localStorage.removeItem(AUTH_CONSTANTS.TOKENS.RETURN_URL_KEY);
      localStorage.removeItem('oidc_state');
    }
  }

  private createAuthError(
    type: AuthErrorType,
    code: string,
    message: string
  ): AuthError {
    return {
      type,
      code,
      message,
      timestamp: new Date(),
    };
  }

  /**
   * Initiate OIDC Authorization Code Flow
   * Redirects user to OIDC provider for authentication
   */
  initiateOidcLogin(): void {
    if (!this.isBrowser) {
      console.warn('OIDC login not available in server environment');
      return;
    }

    console.log('=== Initiating OIDC Authorization Code Flow ===');

    // Store current URL as return URL
    const currentUrl = window.location.pathname + window.location.search;
    this.setReturnUrl(currentUrl);

    // Generate state parameter for security
    const state = this.generateRandomState();
    if (this.isBrowser && typeof localStorage !== 'undefined') {
      localStorage.setItem('oidc_state', state);
    }

    // Build authorization URL
    const authUrl = new URL(
      AUTH_CONSTANTS.OIDC.AUTHORIZATION_ENDPOINT,
      AUTH_CONSTANTS.OIDC.AUTHORITY
    );
    authUrl.searchParams.set('client_id', AUTH_CONSTANTS.OIDC.CLIENT_ID);
    authUrl.searchParams.set(
      'response_type',
      AUTH_CONSTANTS.OIDC.RESPONSE_TYPE
    );
    authUrl.searchParams.set('scope', AUTH_CONSTANTS.OIDC.SCOPE);
    authUrl.searchParams.set('redirect_uri', AUTH_CONSTANTS.OIDC.REDIRECT_URI);
    authUrl.searchParams.set('state', state);

    console.log('Redirecting to authorization URL:', authUrl.toString());

    // Redirect to OIDC provider
    window.location.href = authUrl.toString();
  }

  /**
   * Generate random state parameter for OIDC security
   */
  private generateRandomState(): string {
    if (!this.isBrowser || typeof crypto === 'undefined') {
      // Fallback for SSR
      return Math.random().toString(36).substring(2) + Date.now().toString(36);
    }
    const array = new Uint8Array(32);
    crypto.getRandomValues(array);
    return Array.from(array, (byte) => byte.toString(16).padStart(2, '0')).join(
      ''
    );
  }

  /**
   * Exchange authorization code for tokens
   */
  exchangeCodeForTokens(code: string, state: string): Observable<any> {
    console.log('=== Exchanging authorization code for tokens ===');

    // Verify state parameter
    if (!this.isBrowser || typeof localStorage === 'undefined') {
      // Skip state verification in SSR
      console.warn('State verification skipped in SSR environment');
    } else {
      const storedState = localStorage.getItem('oidc_state');
      if (!storedState || storedState !== state) {
        const error = this.createAuthError(
          AuthErrorType.OIDC_ERROR,
          'INVALID_STATE',
          'Invalid state parameter'
        );
        return throwError(() => error);
      }

      // Clear stored state
      localStorage.removeItem('oidc_state');
    }

    const body = new URLSearchParams({
      grant_type: 'authorization_code',
      code: code,
      redirect_uri: AUTH_CONSTANTS.OIDC.REDIRECT_URI,
      client_id: AUTH_CONSTANTS.OIDC.CLIENT_ID,
      client_secret: AUTH_CONSTANTS.OIDC.CLIENT_SECRET,
    });

    return this.http
      .post<any>(AUTH_CONSTANTS.ROUTES.DEX_TOKEN, body.toString(), {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      })
      .pipe(
        map((tokenResponse) => {
          console.log('=== Token Exchange Successful ===');
          console.log('Token received successfully');

          const tokens: AuthTokens = {
            accessToken: tokenResponse.access_token,
            refreshToken: tokenResponse.refresh_token,
            idToken: tokenResponse.id_token,
            expiresAt: Date.now() + tokenResponse.expires_in * 1000,
          };

          // Set authenticated state
          this.setAuthState({
            isAuthenticated: true,
            isLoading: false,
            user: null,
            tokens: tokens,
            error: null,
          });

          this.storeTokens(tokens);

          return {
            success: true,
            user: null,
            tokens: tokens,
          };
        }),
        catchError((error) => {
          console.error('=== Token Exchange Error ===');
          console.error('Error:', error);

          const errorMessage =
            error.error?.error_description || 'Token exchange failed';
          const authError = this.createAuthError(
            AuthErrorType.OIDC_ERROR,
            'TOKEN_EXCHANGE_ERROR',
            errorMessage
          );

          this.setAuthState({
            ...this.authState(),
            isLoading: false,
            error: authError.message,
          });

          return throwError(() => authError);
        })
      );
  }
}
