# Orchestration Library UI

Angular 20 + Nx frontend for Energy-Aware Orchestrator.

This README reflects the current state of the app:

- Authentication is disabled in UI routes/guards/interceptors.
- Legacy tabs/pages (overview, COG, monitoring, k8s root, alerts/actions/request decisions) were removed.
- Default landing page is `energy-metrics`.

## Current App Routes

- `/energy-metrics` (default page)
- `/emdc/workloads/system-utilization`
- `/emdc/workloads/workload-deployment`
- `/emdc/workloads/register-workload`
- `/test/proxy` (manual proxy endpoint test page)
- `/error/404`, `/error/403`, `/error/500`

## Environment Configuration

Environment files:

- `src/environments/environment.ts`
- `src/environments/environment.development.ts`
- `src/environments/environment.prod.ts`

Current `Environment` shape:

```ts
export interface Environment {
  production: boolean;
  apiUrl: string;
  backendBaseUrl: string;
  tokenKey: string;
  refreshTokenKey: string;
  userKey: string;
}
```

Notes:

- `apiUrl` and `backendBaseUrl` are used for backend endpoint construction.
- `dashboardUrl` has been removed.
- OIDC/auth environment config has been removed.

## Local Development

Prerequisites:

- Node.js (LTS)
- `pnpm`

Install:

```bash
pnpm install
```

Run dev server:

```bash
pnpm start
```

Build:

```bash
pnpm build
pnpm run build:prod
```

Run SSR bundle:

```bash
pnpm run start:prod
```

## Scripts

### `scripts/deploy.sh`

Main Kubernetes deployment utility for UI and optional k8s-proxy.

It can:

- build Docker image (fast mode with `Dockerfile.prebuilt` when `dist/` exists, else full build with `Dockerfile`)
- load image into local cluster (`minikube`/`kind` when available)
- run `helm upgrade --install` using `charts/orchestrator-library-ui`
- wait for pods and set up local port forwarding
- show `status` and `logs`
- perform `cleanup`

Usage examples:

```bash
./scripts/deploy.sh
./scripts/deploy.sh --no-build
./scripts/deploy.sh status
./scripts/deploy.sh logs
./scripts/deploy.sh cleanup
```

### `scripts/cleanup.sh`

Focused cleanup helper.

It:

- stops matching port-forward processes
- uninstalls Helm release (`orchestrator-ui` by default)
- deletes UI and k8s-proxy resources by labels
- optionally deletes namespace when namespace is not `default`
- can optionally reinstall via `--reinstall`

Usage examples:

```bash
./scripts/cleanup.sh
./scripts/cleanup.sh -n <namespace>
./scripts/cleanup.sh --reinstall
```

## Helm Chart

UI Helm chart path:

- `charts/orchestrator-library-ui`

Main chart files:

- `Chart.yaml`: chart metadata
- `values.yaml`: deploy-time config (image, service, ingress, proxy settings)
- `templates/deployment.yaml`: UI deployment
- `templates/service.yaml`: UI service
- `templates/ingress.yaml`: UI ingress
- `templates/configmap.yaml`: runtime `env.js` generation
- `templates/k8s-proxy-*`: optional k8s-proxy resources

## Testing

```bash
pnpm test
```

## References

- [Angular](https://angular.dev/)
- [Nx](https://nx.dev/)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [Helm](https://helm.sh/docs/)
