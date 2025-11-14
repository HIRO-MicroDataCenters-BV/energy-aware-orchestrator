/**
 * Mock Authentication Service
 * Provides mock authentication functionality for development and testing
 */

import { Injectable } from '@angular/core';
import { Observable, of, throwError } from 'rxjs';
import { delay, map } from 'rxjs/operators';
import {
  User,
  LoginCredentials,
  LoginResponse,
  AuthTokens,
  MockUser,
  AuthError,
  AuthErrorType,
} from '../shared/models/auth.models';
import { AUTH_CONSTANTS } from '../shared/constants/app.constants';

@Injectable({
  providedIn: 'root',
})
export class MockAuthService {
  private readonly mockUsers: MockUser[] = AUTH_CONSTANTS.MOCK_AUTH.USERS.map(
    (user) => ({
      email: user.email,
      password: user.password,
      user: {
        ...user.user,
        roles: [...user.user.roles],
        permissions: user.user.permissions ? [...user.user.permissions] : [],
      },
    })
  );
  private readonly mockDelay = AUTH_CONSTANTS.MOCK_AUTH.DELAY;

  /**
   * Mock login with email and password
   */
  login(credentials: LoginCredentials): Observable<LoginResponse> {
    return of(credentials).pipe(
      delay(this.mockDelay),
      map((creds) => {
        const mockUser = this.findUserByCredentials(
          creds.email,
          creds.password
        );

        if (!mockUser) {
          const error = this.createAuthError(
            AuthErrorType.INVALID_CREDENTIALS,
            'INVALID_CREDENTIALS',
            AUTH_CONSTANTS.ERRORS.INVALID_CREDENTIALS
          );
          throw error;
        }

        const tokens = this.generateMockTokens(mockUser.user);

        return {
          success: true,
          user: mockUser.user,
          tokens,
          message: AUTH_CONSTANTS.MESSAGES.LOGIN_SUCCESS,
        };
      })
    );
  }

  /**
   * Mock logout
   */
  logout(): Observable<{ success: boolean; message: string }> {
    return of({
      success: true,
      message: AUTH_CONSTANTS.MESSAGES.LOGOUT_SUCCESS,
    }).pipe(delay(this.mockDelay / 2));
  }

  /**
   * Mock token refresh
   */
  refreshToken(refreshToken: string): Observable<AuthTokens> {
    return of(refreshToken).pipe(
      delay(this.mockDelay / 2),
      map(() => {
        if (!refreshToken || refreshToken === 'invalid') {
          const error = this.createAuthError(
            AuthErrorType.TOKEN_EXPIRED,
            'TOKEN_EXPIRED',
            AUTH_CONSTANTS.ERRORS.TOKEN_EXPIRED
          );
          throw error;
        }

        // For mock, we'll just generate new tokens
        // In real implementation, we'd validate the refresh token
        const mockUser = this.mockUsers[0].user; // Default to first user
        return this.generateMockTokens(mockUser);
      })
    );
  }

  /**
   * Mock user profile retrieval
   */
  getUserProfile(accessToken: string): Observable<User> {
    return of(accessToken).pipe(
      delay(this.mockDelay / 2),
      map(() => {
        if (!accessToken || accessToken === 'invalid') {
          const error = this.createAuthError(
            AuthErrorType.UNAUTHORIZED,
            'UNAUTHORIZED',
            AUTH_CONSTANTS.ERRORS.UNAUTHORIZED
          );
          throw error;
        }

        // For mock, extract user info from token (in real implementation, call API)
        const userId = this.extractUserIdFromToken(accessToken);
        const user = this.findUserById(userId);

        if (!user) {
          throw this.createAuthError(
            AuthErrorType.UNAUTHORIZED,
            'USER_NOT_FOUND',
            'User not found'
          );
        }

        return user;
      })
    );
  }

  /**
   * Mock token validation
   */
  validateToken(accessToken: string): Observable<boolean> {
    return of(accessToken).pipe(
      delay(this.mockDelay / 4),
      map(() => {
        if (!accessToken) {
          return false;
        }

        try {
          const payload = this.parseJWT(accessToken) as any;
          const now = Math.floor(Date.now() / 1000);
          return payload.exp > now;
        } catch {
          return false;
        }
      })
    );
  }

  /**
   * Mock password change
   */
  changePassword(
    oldPassword: string,
    newPassword: string,
    accessToken: string
  ): Observable<{ success: boolean; message: string }> {
    return of({ oldPassword, newPassword, accessToken }).pipe(
      delay(this.mockDelay),
      map(({ oldPassword, accessToken }) => {
        if (!accessToken) {
          throw this.createAuthError(
            AuthErrorType.UNAUTHORIZED,
            'UNAUTHORIZED',
            AUTH_CONSTANTS.ERRORS.UNAUTHORIZED
          );
        }

        const userId = this.extractUserIdFromToken(accessToken);
        const mockUser = this.mockUsers.find((u) => u.user.id === userId);

        if (!mockUser) {
          throw this.createAuthError(
            AuthErrorType.UNAUTHORIZED,
            'USER_NOT_FOUND',
            'User not found'
          );
        }

        if (mockUser.password !== oldPassword) {
          throw this.createAuthError(
            AuthErrorType.INVALID_CREDENTIALS,
            'INVALID_OLD_PASSWORD',
            'Current password is incorrect'
          );
        }

        // In a real implementation, we'd update the password in the database
        return {
          success: true,
          message: 'Password changed successfully',
        };
      })
    );
  }

  /**
   * Get available mock users (for development purposes)
   */
  getMockUsers(): MockUser[] {
    return this.mockUsers.map((user) => ({
      ...user,
      password: '***', // Don't expose actual passwords
    }));
  }

  /**
   * Check if mock auth is enabled
   */
  isMockAuthEnabled(): boolean {
    return AUTH_CONSTANTS.MOCK_AUTH.ENABLED;
  }

  // Private helper methods

  private findUserByCredentials(
    email: string,
    password: string
  ): MockUser | undefined {
    return this.mockUsers.find(
      (user) => user.email === email && user.password === password
    );
  }

  private findUserById(userId: string): User | undefined {
    const mockUser = this.mockUsers.find((user) => user.user.id === userId);
    return mockUser?.user;
  }

  private generateMockTokens(user: User): AuthTokens {
    const now = Math.floor(Date.now() / 1000);
    const expiresIn = 3600; // 1 hour
    const refreshExpiresIn = 86400; // 24 hours

    const accessToken = this.createMockJWT({
      sub: user.id,
      email: user.email,
      name: user.name,
      roles: user.roles,
      permissions: user.permissions || [],
      iat: now,
      exp: now + expiresIn,
    });

    const refreshToken = this.createMockJWT({
      sub: user.id,
      type: 'refresh',
      iat: now,
      exp: now + refreshExpiresIn,
    });

    const idToken = this.createMockJWT({
      sub: user.id,
      email: user.email,
      name: user.name,
      given_name: user.firstName,
      family_name: user.lastName,
      picture: user.avatar,
      email_verified: user.isEmailVerified,
      iat: now,
      exp: now + expiresIn,
    });

    return {
      accessToken,
      refreshToken,
      idToken,
      expiresAt: (now + expiresIn) * 1000, // Convert to milliseconds
      scope: AUTH_CONSTANTS.OIDC.SCOPE,
    };
  }

  private createMockJWT(payload: unknown): string {
    // This is a mock JWT - in real implementation, use proper JWT library
    const header = { alg: 'HS256', typ: 'JWT' };
    const encodedHeader = btoa(JSON.stringify(header));
    const encodedPayload = btoa(JSON.stringify(payload));
    const signature = 'mock-signature';

    return `${encodedHeader}.${encodedPayload}.${signature}`;
  }

  private parseJWT(token: string): unknown {
    try {
      const parts = token.split('.');
      if (parts.length !== 3) {
        throw new Error('Invalid token format');
      }

      const payload = parts[1];
      return JSON.parse(atob(payload));
    } catch (error) {
      throw new Error('Invalid token');
    }
  }

  private extractUserIdFromToken(token: string): string {
    try {
      const payload = this.parseJWT(token) as any;
      return payload.sub;
    } catch {
      throw this.createAuthError(
        AuthErrorType.UNAUTHORIZED,
        'INVALID_TOKEN',
        'Invalid access token'
      );
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
   * Simulate network errors for testing
   */
  simulateNetworkError(): Observable<never> {
    return throwError(() =>
      this.createAuthError(
        AuthErrorType.NETWORK_ERROR,
        'NETWORK_ERROR',
        AUTH_CONSTANTS.ERRORS.NETWORK_ERROR
      )
    ).pipe(delay(this.mockDelay));
  }

  /**
   * Simulate OIDC errors for testing
   */
  simulateOidcError(): Observable<never> {
    return throwError(() =>
      this.createAuthError(
        AuthErrorType.OIDC_ERROR,
        'OIDC_ERROR',
        AUTH_CONSTANTS.ERRORS.OIDC_ERROR
      )
    ).pipe(delay(this.mockDelay));
  }
}
