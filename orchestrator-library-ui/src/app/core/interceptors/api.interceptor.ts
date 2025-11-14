import { Injectable, inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import {
  HttpInterceptor,
  HttpRequest,
  HttpHandler,
  HttpEvent,
  HttpResponse,
  HttpErrorResponse,
} from '@angular/common/http';
import { Observable, throwError, timer } from 'rxjs';
import { catchError, retry, tap, timeout } from 'rxjs/operators';
import { LoggerService } from '../services/logger.service';
import { API_CONFIG } from '../config/api.config';

@Injectable()
export class ApiInterceptor implements HttpInterceptor {
  private readonly logger = inject(LoggerService);
  private readonly apiConfig = inject(API_CONFIG);
  private readonly platformId = inject(PLATFORM_ID);
  private readonly isBrowser = isPlatformBrowser(this.platformId);

  intercept(
    req: HttpRequest<unknown>,
    next: HttpHandler
  ): Observable<HttpEvent<unknown>> {
    if (!this.isBrowser) {
      return next.handle(req);
    }

    const startTime = Date.now();

    const modifiedReq = req.clone({
      setHeaders: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
      },
    });

    this.logger.debug(
      `HTTP ${req.method} ${req.url}`,
      {
        body: req.body,
        headers: req.headers,
      },
      'ApiInterceptor'
    );

    return next.handle(modifiedReq).pipe(
      timeout(this.apiConfig.timeout),
      retry({
        count: this.apiConfig.retryAttempts,
        delay: (error, retryCount) => {
          if (this.shouldRetry(error)) {
            const delay = Math.min(1000 * Math.pow(2, retryCount), 10000);
            this.logger.warn(
              `Retrying request (${retryCount}/${this.apiConfig.retryAttempts}) after ${delay}ms`,
              error,
              'ApiInterceptor'
            );
            return timer(delay);
          }
          return throwError(() => error);
        },
      }),
      tap({
        next: (event) => {
          if (event instanceof HttpResponse) {
            const duration = Date.now() - startTime;
            this.logger.info(
              `HTTP ${req.method} ${req.url} completed in ${duration}ms`,
              {
                status: event.status,
                statusText: event.statusText,
                duration,
              },
              'ApiInterceptor'
            );
          }
        },
      }),
      catchError((error: HttpErrorResponse) => {
        const duration = Date.now() - startTime;

        this.logger.error(
          `HTTP ${req.method} ${req.url} failed after ${duration}ms`,
          {
            status: error.status,
            statusText: error.statusText,
            message: error.message,
            error: error.error,
            duration,
          },
          'ApiInterceptor'
        );

        return throwError(() => this.formatError(error));
      })
    );
  }

  private shouldRetry(error: HttpErrorResponse): boolean {
    return !error.status || (error.status >= 500 && error.status < 600);
  }

  private formatError(error: HttpErrorResponse): {
    userMessage: string;
    timestamp: string;
  } & HttpErrorResponse {
    let errorMessage = 'An unexpected error occurred';

    if (error.error?.message) {
      errorMessage = error.error.message;
    } else if (error.message) {
      errorMessage = error.message;
    }

    switch (error.status) {
      case 0:
        errorMessage = 'Network error. Please check your connection.';
        break;
      case 400:
        errorMessage = 'Bad request. Please check your input.';
        break;
      case 401:
        errorMessage = 'Unauthorized. Please log in again.';
        break;
      case 403:
        errorMessage = 'Access denied. You do not have permission.';
        break;
      case 404:
        errorMessage = 'Resource not found.';
        break;
      case 408:
        errorMessage = 'Request timeout. Please try again.';
        break;
      case 429:
        errorMessage = 'Too many requests. Please wait before trying again.';
        break;
      case 500:
        errorMessage = 'Server error. Please try again later.';
        break;
      case 502:
      case 503:
      case 504:
        errorMessage =
          'Service temporarily unavailable. Please try again later.';
        break;
    }

    return {
      ...error,
      userMessage: errorMessage,
      timestamp: new Date().toISOString(),
    };
  }
}
