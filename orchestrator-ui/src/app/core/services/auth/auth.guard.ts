/**
 * Authentication Guard
 * Protects routes by checking authentication status and user permissions
 */

import { Injectable, inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import {
  CanActivate,
  CanActivateChild,
  CanMatch,
  Router,
  ActivatedRouteSnapshot,
  RouterStateSnapshot,
  Route,
  UrlSegment,
} from '@angular/router';
import { Observable, of } from 'rxjs';
import { map } from 'rxjs/operators';

import { AuthService } from './auth.service';

@Injectable({
  providedIn: 'root',
})
export class AuthGuard implements CanActivate, CanActivateChild, CanMatch {
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  private readonly platformId = inject(PLATFORM_ID);
  private readonly isBrowser = isPlatformBrowser(this.platformId);

  /**
   * Check if route can be activated
   */
  canActivate(
    route: ActivatedRouteSnapshot,
    state: RouterStateSnapshot
  ): Observable<boolean> {
    return this.checkAuth(state.url, route.data);
  }

  /**
   * Check if child routes can be activated
   */
  canActivateChild(
    childRoute: ActivatedRouteSnapshot,
    state: RouterStateSnapshot
  ): Observable<boolean> {
    return this.checkAuth(state.url, childRoute.data);
  }

  /**
   * Check if route can be matched (for lazy loading)
   */
  canMatch(route: Route, segments: UrlSegment[]): Observable<boolean> {
    const url = segments.map((segment) => segment.path).join('/');
    return this.checkAuth(url, route.data);
  }

  /**
   * Main authentication check logic
   */
  private checkAuth(url: string, routeData?: any): Observable<boolean> {
    // For SSR, always allow access to prevent blocking
    if (!this.isBrowser) {
      return of(true);
    }

    try {
      const isAuthenticated = this.authService.authenticated();

      // If not authenticated, redirect to login
      if (!isAuthenticated) {
        this.authService.setReturnUrl(url);
        this.router.navigate(['/auth/login']);
        return of(false);
      }

      // If authenticated, check additional permissions if required
      if (routeData) {
        // Check required roles
        if (routeData['requiredRoles']) {
          const requiredRoles = Array.isArray(routeData['requiredRoles'])
            ? routeData['requiredRoles']
            : [routeData['requiredRoles']];

          const hasRequiredRole = requiredRoles.some((role: string) =>
            this.authService.hasRole(role)
          );

          if (!hasRequiredRole) {
            this.router.navigate(['/auth/forbidden']);
            return of(false);
          }
        }

        // Check required permissions
        if (routeData['requiredPermissions']) {
          const requiredPermissions = Array.isArray(
            routeData['requiredPermissions']
          )
            ? routeData['requiredPermissions']
            : [routeData['requiredPermissions']];

          const hasRequiredPermission = requiredPermissions.some(
            (permission: string) => this.authService.hasPermission(permission)
          );

          if (!hasRequiredPermission) {
            this.router.navigate(['/auth/forbidden']);
            return of(false);
          }
        }

        // Check if admin access is required
        if (routeData['requireAdmin'] === true) {
          if (!this.authService.isAdmin()) {
            this.router.navigate(['/auth/forbidden']);
            return of(false);
          }
        }
      }

      return of(true);
    } catch (error) {
      console.error('Auth guard error:', error);
      this.router.navigate(['/auth/login']);
      return of(false);
    }
  }
}

/**
 * Role-based guard for admin routes
 */
@Injectable({
  providedIn: 'root',
})
export class AdminGuard implements CanActivate, CanActivateChild {
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  private readonly platformId = inject(PLATFORM_ID);
  private readonly isBrowser = isPlatformBrowser(this.platformId);

  canActivate(
    route: ActivatedRouteSnapshot,
    state: RouterStateSnapshot
  ): Observable<boolean> {
    return this.checkAdminAccess(state.url);
  }

  canActivateChild(
    childRoute: ActivatedRouteSnapshot,
    state: RouterStateSnapshot
  ): Observable<boolean> {
    return this.checkAdminAccess(state.url);
  }

  private checkAdminAccess(url: string): Observable<boolean> {
    // For SSR, always allow access to prevent blocking
    if (!this.isBrowser) {
      return of(true);
    }

    try {
      const isAuthenticated = this.authService.authenticated();

      if (!isAuthenticated) {
        this.authService.setReturnUrl(url);
        this.router.navigate(['/auth/login']);
        return of(false);
      }

      if (!this.authService.isAdmin()) {
        this.router.navigate(['/auth/forbidden']);
        return of(false);
      }

      return of(true);
    } catch (error) {
      console.error('Admin guard error:', error);
      this.router.navigate(['/auth/login']);
      return of(false);
    }
  }
}

/**
 * Guest guard - redirects authenticated users away from auth pages
 */
@Injectable({
  providedIn: 'root',
})
export class GuestGuard implements CanActivate {
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  private readonly platformId = inject(PLATFORM_ID);
  private readonly isBrowser = isPlatformBrowser(this.platformId);

  canActivate(
    route: ActivatedRouteSnapshot,
    state: RouterStateSnapshot
  ): Observable<boolean> {
    // For SSR, always allow access to guest pages
    if (!this.isBrowser) {
      return of(true);
    }

    try {
      const isAuthenticated = this.authService.authenticated();

      if (isAuthenticated) {
        // Redirect authenticated users to main app
        this.router.navigate(['/overview']);
        return of(false);
      }

      return of(true);
    } catch (error) {
      console.error('Guest guard error:', error);
      return of(true);
    }
  }
}

/**
 * Permission-based guard factory
 */
export function createPermissionGuard(requiredPermission: string) {
  return class PermissionGuard implements CanActivate {
    private readonly authService = inject(AuthService);
    private readonly router = inject(Router);
    private readonly platformId = inject(PLATFORM_ID);
    private readonly isBrowser = isPlatformBrowser(this.platformId);

    canActivate(
      route: ActivatedRouteSnapshot,
      state: RouterStateSnapshot
    ): Observable<boolean> {
      // For SSR, always allow access to prevent blocking
      if (!this.isBrowser) {
        return of(true);
      }

      try {
        const isAuthenticated = this.authService.authenticated();

        if (!isAuthenticated) {
          this.authService.setReturnUrl(state.url);
          this.router.navigate(['/auth/login']);
          return of(false);
        }

        if (!this.authService.hasPermission(requiredPermission)) {
          this.router.navigate(['/auth/forbidden']);
          return of(false);
        }

        return of(true);
      } catch (error) {
        console.error('Permission guard error:', error);
        this.router.navigate(['/auth/login']);
        return of(false);
      }
    }
  };
}

/**
 * Role-based guard factory
 */
export function createRoleGuard(requiredRole: string) {
  return class RoleGuard implements CanActivate {
    private readonly authService = inject(AuthService);
    private readonly router = inject(Router);
    private readonly platformId = inject(PLATFORM_ID);
    private readonly isBrowser = isPlatformBrowser(this.platformId);

    canActivate(
      route: ActivatedRouteSnapshot,
      state: RouterStateSnapshot
    ): Observable<boolean> {
      // For SSR, always allow access to prevent blocking
      if (!this.isBrowser) {
        return of(true);
      }

      try {
        const isAuthenticated = this.authService.authenticated();

        if (!isAuthenticated) {
          this.authService.setReturnUrl(state.url);
          this.router.navigate(['/auth/login']);
          return of(false);
        }

        if (!this.authService.hasRole(requiredRole)) {
          this.router.navigate(['/auth/forbidden']);
          return of(false);
        }

        return of(true);
      } catch (error) {
        console.error('Role guard error:', error);
        this.router.navigate(['/auth/login']);
        return of(false);
      }
    }
  };
}
