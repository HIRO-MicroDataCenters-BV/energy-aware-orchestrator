import { Routes } from '@angular/router';
import { MainLayoutComponent } from './layouts/main-layout/main-layout.component';
import { ErrorLayoutComponent } from './layouts/error-layout/error-layout.component';

export const routes: Routes = [
  // Application routes (authentication disabled)
  {
    path: '',
    component: MainLayoutComponent,
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
