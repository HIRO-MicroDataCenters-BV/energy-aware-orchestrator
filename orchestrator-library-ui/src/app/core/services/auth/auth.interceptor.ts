/**
 * Authentication Interceptor
 * Automatically adds authentication tokens to HTTP requests and handles token refresh
 */

import { Injectable, inject } from '@angular/core';
import {
  HttpInterceptor,
  HttpRequest,
  HttpHandler,
  HttpEvent,
  HttpErrorResponse,
  HttpInterceptorFn,
  HttpHandlerFn,
} from '@angular/common/http';
import { Observable, throwError, BehaviorSubject } from 'rxjs';
import { catchError, filter, take, switchMap, finalize } from 'rxjs/operators';

import { AuthService } from './auth.service';
import { AUTH_CONSTANTS } from '../../../shared/constants/app.constants';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {
  private readonly authService = inject(AuthService);

  private isRefreshing = false;
  private refreshTokenSubject = new BehaviorSubject<string | null>(null);

  intercept(
    request: HttpRequest<any>,
    next: HttpHandler
  ): Observable<HttpEvent<any>> {
    // Skip authentication for certain URLs
    if (this.shouldSkipAuth(request.url)) {
      return next.handle(request);
    }

    // Add auth token to request
    const authRequest = this.addAuthToken(request);

    return next.handle(authRequest).pipe(
      catchError((error: any) => {
        if (error instanceof HttpErrorResponse && error.status === 401) {
          return this.handle401Error(authRequest, next);
        }
        return throwError(() => error);
      })
    );
  }

  /**
   * Add authentication token to request headers
   */
  private addAuthToken(request: HttpRequest<any>): HttpRequest<any> {
    const token = this.authService.getAccessToken();

    if (token) {
      return request.clone({
        setHeaders: {
          [AUTH_CONSTANTS.HEADERS
            .AUTHORIZATION]: `${AUTH_CONSTANTS.HEADERS.BEARER_PREFIX}${token}`,
        },
      });
    }

    return request;
  }

  /**
   * Handle 401 Unauthorized errors by attempting token refresh
   */
  private handle401Error(
    request: HttpRequest<any>,
    next: HttpHandler
  ): Observable<HttpEvent<any>> {
    if (!this.isRefreshing) {
      this.isRefreshing = true;
      this.refreshTokenSubject.next(null);

      return this.authService.refreshTokens().pipe(
        switchMap((tokens) => {
          this.isRefreshing = false;
          this.refreshTokenSubject.next(tokens.accessToken);

          // Retry the original request with new token
          const authRequest = this.addAuthToken(request);
          return next.handle(authRequest);
        }),
        catchError((error: any) => {
          this.isRefreshing = false;

          // Token refresh failed, logout user
          this.authService.logout().subscribe();

          return throwError(() => error);
        }),
        finalize(() => {
          this.isRefreshing = false;
        })
      );
    } else {
      // Wait for token refresh to complete
      return this.refreshTokenSubject.pipe(
        filter((token) => token !== null),
        take(1),
        switchMap(() => {
          const authRequest = this.addAuthToken(request);
          return next.handle(authRequest);
        })
      );
    }
  }

  /**
   * Check if authentication should be skipped for this URL
   */
  private shouldSkipAuth(url: string): boolean {
    const skipPatterns = [
      '/auth/',
      '/assets/',
      '/i18n/',
      '.json',
      'oauth2',
      'oidc',
      '.well-known',
    ];

    return skipPatterns.some((pattern) => url.includes(pattern));
  }
}

/**
 * Functional interceptor version for standalone apps
 */
export const authInterceptor: HttpInterceptorFn = (
  req: HttpRequest<unknown>,
  next: HttpHandlerFn
): Observable<HttpEvent<unknown>> => {
  const authService = inject(AuthService);

  // Skip authentication for certain URLs
  const skipPatterns = [
    '/auth/',
    '/assets/',
    '/i18n/',
    '.json',
    'oauth2',
    'oidc',
    '.well-known',
  ];

  if (skipPatterns.some((pattern) => req.url.includes(pattern))) {
    return next(req);
  }

  // Add auth token to request
  const token = authService.getAccessToken();
  let authReq = req;

  if (token) {
    authReq = req.clone({
      setHeaders: {
        [AUTH_CONSTANTS.HEADERS
          .AUTHORIZATION]: `${AUTH_CONSTANTS.HEADERS.BEARER_PREFIX}${token}`,
      },
    });
  }

  return next(authReq).pipe(
    catchError((error: any) => {
      if (error instanceof HttpErrorResponse && error.status === 401) {
        // For functional interceptor, we'll just logout on 401
        // More complex token refresh logic would require additional setup
        authService.logout().subscribe();
      }
      return throwError(() => error);
    })
  );
};
