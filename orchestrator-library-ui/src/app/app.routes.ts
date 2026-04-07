import { Routes } from '@angular/router';
import { MainLayoutComponent } from './layouts/main-layout/main-layout.component';
import { ErrorLayoutComponent } from './layouts/error-layout/error-layout.component';
import { AuthLayoutComponent } from './layouts/auth-layout/auth-layout.component';
import { AuthGuard, GuestGuard } from './core/services/auth';

export const routes: Routes = [
  // Auth routes (public, for non-authenticated users)
  {
    path: 'auth',
    component: AuthLayoutComponent,
    canActivate: [GuestGuard],
    children: [
      {
        path: 'login',
        loadComponent: () =>
          import('./pages/auth/login/login.component').then(
            (m) => m.LoginComponent
          ),
        data: { title: 'Login' },
      },
      {
        path: 'callback',
        loadComponent: () =>
          import('./pages/auth/callback/callback.component').then(
            (m) => m.CallbackComponent
          ),
        data: { title: 'Authentication Callback' },
      },
      {
        path: '',
        redirectTo: 'login',
        pathMatch: 'full',
      },
    ],
  },

  // Ambassador Auth callback route (public)
  {
    path: 'authservice/oidc/callback',
    loadComponent: () =>
      import('./pages/auth/callback/callback.component').then(
        (m) => m.CallbackComponent
      ),
    data: { title: 'Authentication Callback' },
  },

  // Protected routes (require authentication)
  {
    path: '',
    component: MainLayoutComponent,
    canActivate: [AuthGuard],
    children: [
      {
        path: '',
        redirectTo: '/energy-metrics',
        pathMatch: 'full',
      },
      {
        path: 'energy-metrics',
        loadComponent: () =>
          import('./pages/k8s/energy-prediction-v2/energy-prediction-v2.component').then(
            (m) => m.EnergyPredictionV2Component
          ),
        data: { title: 'Energy Metrics' },
      },
      // Keep top-level path for backward-compatibility, redirect to nested
      {
        path: 'system-utilization',
        redirectTo: '/emdc/workloads/system-utilization',
        pathMatch: 'full',
      },
      // Keep top-level path for backward-compatibility, redirect to nested
      {
        path: 'workload-deployment',
        redirectTo: '/emdc/workloads/workload-deployment',
        pathMatch: 'full',
      },
      {
        path: 'emdc',
        children: [
          {
            path: 'workloads',
            children: [
              {
                path: 'system-utilization',
                loadComponent: () =>
                  import('./pages/k8s/system-utilization/system-utilization.component').then(
                    (m) => m.SystemUtilizationComponent
                  ),
                data: { title: 'System Utilization' },
              },
              {
                path: 'workload-deployment',
                loadComponent: () =>
                  import('./pages/k8s/workload-deployment/workload-deployment.component').then(
                    (m) => m.WorkloadDeploymentComponent
                  ),
                data: { title: 'Workload Deployment' },
              },
              {
                path: 'register-workload',
                loadComponent: () =>
                  import('./pages/k8s/register-workload/register-workload.component').then(
                    (m) => m.RegisterWorkloadComponent
                  ),
                data: { title: 'Register Workload' },
              },
            ],
          },
        ],
      },
    ],
  },

  // Error routes (public)
  {
    path: 'error',
    component: ErrorLayoutComponent,
    children: [
      {
        path: '404',
        loadComponent: () =>
          import('./pages/error/not-found/not-found.component').then(
            (m) => m.NotFoundComponent
          ),
        data: { title: '404 - Not Found' },
      },
      {
        path: '403',
        loadComponent: () =>
          import('./pages/error/forbidden/forbidden.component').then(
            (m) => m.ForbiddenComponent
          ),
        data: { title: '403 - Access Denied' },
      },
      {
        path: '500',
        loadComponent: () =>
          import('./pages/error/server-error/server-error.component').then(
            (m) => m.ServerErrorComponent
          ),
        data: { title: '500 - Server Error' },
      },
    ],
  },

  // Auth-specific error routes without layout guards
  {
    path: 'auth/unauthorized',
    loadComponent: () =>
      import('./pages/error/unauthorized/unauthorized.component').then(
        (m) => m.UnauthorizedComponent
      ),
    data: { title: 'Unauthorized' },
  },
  {
    path: 'auth/forbidden',
    loadComponent: () =>
      import('./pages/error/forbidden/forbidden.component').then(
        (m) => m.ForbiddenComponent
      ),
    data: { title: 'Access Denied' },
  },

  {
    path: 'test/proxy',
    loadComponent: () =>
      import('./pages/test/proxy-test.component').then(
        (m) => m.ProxyTestComponent
      ),
    data: { title: 'Proxy Test' },
  },

  // Fallback routes
  { path: '**', redirectTo: '/error/404' },
];
