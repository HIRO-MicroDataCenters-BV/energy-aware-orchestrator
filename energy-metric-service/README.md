# Energy Metric Service

A comprehensive energy monitoring and forecasting service for Kubernetes clusters. Integrates with Prometheus, Kepler, and Kubernetes to provide real-time energy consumption metrics, forecasting, and pod management. Includes both the FastAPI application and a custom PostgreSQL Helm chart for persistent storage.

---

## 📁 Project Structure

```
energy-metric-service/
├── app/                  # FastAPI application source code
│   ├── api/              # API routers (metrics, k8s, forecasting, etc.)
│   ├── db/               # Database connection logic
│   ├── models/           # ORM/data models
│   ├── repositories/     # Data access logic
│   ├── scheduler/        # Background schedulers
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Metrics, forecasting, and integration logic
│   ├── servicesv2/       # Newer service implementations
│   └── utils/            # Utilities and helpers
├── charts/
│   ├── app/              # Helm chart for FastAPI app
│   └── postgres/         # Helm chart for PostgreSQL
├── scripts/
│   ├── deploy-all.sh     # Deploys both PostgreSQL and app (recommended)
│   ├── deploy-app.sh     # Deploys only the FastAPI app
│   └── deploy-postgres.sh# Deploys only PostgreSQL
├── Dockerfile            # Container build for FastAPI app
├── docker-compose.yaml   # Local dev (optional)
├── README.md             # This file
└── ...
```

---

## 🚀 Features

- **Energy Metrics Collection:** Fetches energy data from Kepler via Prometheus
- **Resource Monitoring:** Tracks CPU and memory utilization
- **Energy Forecasting:** ML-powered predictions for energy consumption
- **Kubernetes Integration:** Pod and namespace management APIs
- **Time Series Analysis:** Historical data and trend monitoring
- **Custom PostgreSQL Helm Chart:** Easy, persistent storage setup

---

## ⚡ Quick Start (Recommended)

### 1. Prerequisites

- Kubernetes cluster (tested with Minikube)
- Helm 3.x
- kubectl configured
- Docker (for building the app image)

### 2. Deploy Everything (App + PostgreSQL)

From the `energy-metric-service/` directory:

```bash
./scripts/deploy-all.sh
```

- This script will:
  - Deploy PostgreSQL using the custom Helm chart
  - Build and deploy the FastAPI application
  - Wait for all pods to be ready

#### Options

- Deploy only DB: `./scripts/deploy-all.sh --db-only`
- Deploy only App: `./scripts/deploy-all.sh --app-only`
- Skip image build: `./scripts/deploy-all.sh --no-build`
- Specify namespace: `./scripts/deploy-all.sh -n my-namespace`

---

## 🛠️ Manual Installation

### 1. Deploy PostgreSQL Only

```bash
./scripts/deploy-postgres.sh
```

- Custom options:
  - `-n my-namespace` — set namespace
  - `--db mydb` — set database name
  - `--user myuser` — set username
  - `--password mypass` — set password
  - `--storage 20Gi` — set storage size
  - `-f my-values.yaml` — use custom values file

### 2. Deploy FastAPI App Only

```bash
./scripts/deploy-app.sh
```

- Options:
  - `-n my-namespace` — set namespace
  - `--no-build` — skip Docker image build

---

## 📦 Helm Installation (Advanced)

### Deploy PostgreSQL Chart Directly

```bash
cd charts
helm install postgres ./postgres
```

- With custom values:
  ```bash
  helm install postgres ./postgres \
    --set postgres.credentials.database=mydb \
    --set postgres.credentials.username=myuser \
    --set postgres.credentials.password=mypass \
    --set postgres.persistence.size=20Gi
  ```
- Or with a values file:
  ```bash
  helm install postgres ./postgres -f my-values.yaml
  ```

### Deploy App Chart Directly

```bash
cd charts
helm install energy-metric-service ./app
```

- Set image/tag or environment variables as needed.

---

## ⚙️ Configuration & Customization

### PostgreSQL Chart (`charts/postgres/values.yaml`)

```yaml
postgres:
  name: eao-postgres
  image:
    repository: postgres
    tag: "14"
  credentials:
    username: postgres
    password: postgres
    database: orchestration_db
  persistence:
    enabled: true
    size: 8Gi
  service:
    type: ClusterIP
    port: 5432
```

- **Override any value** via `--set` or a custom values file.
- **Init scripts:** Edit `charts/postgres/templates/postgres-configmap.yaml` to add custom SQL.

### App Chart (`charts/app/values.yaml`)

- Set image repository/tag, environment variables, and resource limits as needed.

---

## 🌐 Accessing the Service

- **API Docs:**  
  After deployment, port-forward the service:
  ```bash
  kubectl port-forward -n <namespace> svc/energy-metric-service 8000:8000
  ```
  Open: [http://localhost:8000/docs](http://localhost:8000/docs)

- **PostgreSQL Connection:**  
  Get the connection string:
  ```bash
  kubectl get configmap orchestration-api-config -o jsonpath='{.data.databaseURL}'
  ```

---

## 🧹 Uninstallation

### Remove Everything (App + DB)

```bash
# Remove app and DB using scripts
./scripts/deploy-postgres.sh --uninstall
helm uninstall energy-metric-service -n <namespace> || true

# Optionally delete PVC (data loss!)
kubectl delete pvc -n <namespace> -l app=eao-postgres
```

### Remove via Helm

```bash
helm uninstall postgres -n <namespace>
helm uninstall energy-metric-service -n <namespace>
kubectl delete pvc -n <namespace> -l app=eao-postgres
```

---

## 📝 API Endpoints

- **Prometheus Metrics:** `/api/metrics/prometheus/metrics-v2/`
- **Energy Forecasting:** `/energy-forecast/`
- **Kubernetes APIs:** `/api/kubernetes/`
- See [http://localhost:8000/docs](http://localhost:8000/docs) for full OpenAPI docs.

---

## 🐳 Local Development

- Use `docker-compose.yaml` for local dev (optional).
- For Minikube:  
  - Start Minikube  
  - Start `kubectl proxy`  
  - Set environment variables as needed  
  - Run the app locally with Uvicorn

---

## Dependencies

- **Python 3.8+**
- **FastAPI**: Web framework
- **aiohttp**: Async HTTP client
- **Prometheus**: Metrics collection
- **Kubernetes**: Container orchestration
- **Kepler**: Energy consumption monitoring

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with Minikube
5. Submit a pull request

---

## 📄 License

[Your License Here]
