# Energy Metric Service

A comprehensive energy monitoring service that integrates with Prometheus, Kepler, and Kubernetes to provide real-time energy consumption metrics, forecasting, and pod management capabilities.

## Features

- **Energy Metrics Collection**: Fetches energy consumption data from Kepler via Prometheus
- **Resource Monitoring**: CPU and memory utilization tracking
- **Energy Forecasting**: ML-powered energy consumption predictions
- **Kubernetes Integration**: Pod and namespace management
- **Time Series Analysis**: Historical data analysis and trend monitoring

## API Endpoints

### Energy & Metrics APIs

- **Prometheus Metrics V2**: `/api/metrics/prometheus/metrics-v2/`
  - `GET /latest` - Latest energy and resource metrics
  - `GET /timeseries` - Historical time series data

- **Energy Forecasting**: `/energy-forecast/`
  - `POST /predict` - Single prediction
  - `POST /forecast-day` - 24-hour forecasting
  - `GET /metrics-with-forecast` - Enhanced metrics with predictions

### Kubernetes APIs

- **Connection & Health**: `/api/kubernetes/`
  - `GET /test` - Test Kubernetes API connection
  - `GET /namespaces` - List all namespaces

- **Pod Management**: `/api/kubernetes/pods`
  - `GET /` - Get pods by namespace
  - `GET /all` - Get pods from all namespaces
  - `GET /summary` - Cluster-wide pod statistics
  - `GET /by-node/{node_name}` - Pods on specific node

## Environment Variables

### Kubernetes Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_KUBECTL_PROXY` | `true` | Use kubectl proxy for local development |
| `KUBERNETES_SERVICE_HOST` | `localhost` | Kubernetes API server host |
| `KUBERNETES_SERVICE_PORT` | `8080` / `8443` | Kubernetes API server port |

### Application Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_METRICS_SCHEDULER` | `false` | Enable automatic metrics collection |
| `NODE_MAPPINGS` | - | Map IP addresses to node names (format: `ip1:name1,ip2:name2`) |

## Deployment Scenarios

### 1. Local Development with Minikube

**Prerequisites:**
- Minikube running
- kubectl configured

**Setup:**
```bash
# Start Minikube
minikube start

# Start kubectl proxy
kubectl proxy --port=8080

# Set environment variables
export USE_KUBECTL_PROXY=true
export KUBERNETES_SERVICE_HOST=localhost
export KUBERNETES_SERVICE_PORT=8080

# Run the service
python -m uvicorn app.main:app --host 0.0.0.0 --port 8086
```

**Test Connection:**
```bash
curl http://localhost:8086/api/kubernetes/test
curl http://localhost:8086/api/kubernetes/namespaces
curl http://localhost:8086/api/kubernetes/pods?namespace=default
```

### 2. In-Cluster Deployment

**Prerequisites:**
- Kubernetes cluster
- Service account with appropriate permissions

**Create RBAC:**
```yaml
# rbac.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: energy-metrics-sa
  namespace: default
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: energy-metrics-reader
rules:
- apiGroups: [""]
  resources: ["pods", "namespaces"]
  verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: energy-metrics-binding
subjects:
- kind: ServiceAccount
  name: energy-metrics-sa
  namespace: default
roleRef:
  kind: ClusterRole
  name: energy-metrics-reader
  apiGroup: rbac.authorization.k8s.io
```

**Deploy Service:**
```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: energy-metric-service
spec:
  replicas: 1
  selector:
    matchLabels:
      app: energy-metric-service
  template:
    metadata:
      labels:
        app: energy-metric-service
    spec:
      serviceAccountName: energy-metrics-sa
      containers:
      - name: energy-metric-service
        image: your-registry/energy-metric-service:latest
        ports:
        - containerPort: 8086
        env:
        - name: USE_KUBECTL_PROXY
          value: "false"
        - name: ENABLE_METRICS_SCHEDULER
          value: "true"
```

**Apply:**
```bash
kubectl apply -f rbac.yaml
kubectl apply -f deployment.yaml
```

### 3. External Cluster Access

**Setup:**
```bash
# Get cluster info
kubectl cluster-info

# Create service account token
kubectl create token energy-metrics-sa

# Set environment variables
export USE_KUBECTL_PROXY=false
export KUBERNETES_SERVICE_HOST=<cluster-ip>
export KUBERNETES_SERVICE_PORT=6443
export K8S_TOKEN=<service-account-token>

# Run service
python -m uvicorn app.main:app --host 0.0.0.0 --port 8086
```

## API Usage Examples

### Get Pod Information

```bash
# List all namespaces
curl http://localhost:8086/api/kubernetes/namespaces

# Get pods in specific namespace
curl "http://localhost:8086/api/kubernetes/pods?namespace=default"

# Filter running pods
curl "http://localhost:8086/api/kubernetes/pods?namespace=default&phase=Running"

# Get pods on specific node
curl "http://localhost:8086/api/kubernetes/pods?namespace=default&node_name=minikube"

# Get all pods (excluding system namespaces)
curl "http://localhost:8086/api/kubernetes/pods/all?include_system=false"

# Get cluster summary
curl http://localhost:8086/api/kubernetes/pods/summary

# Get pods by node
curl http://localhost:8086/api/kubernetes/pods/by-node/minikube
```

### Energy Metrics

```bash
# Get latest energy metrics (last 1 hour)
curl "http://localhost:8086/api/metrics/prometheus/metrics-v2/latest?hours_back=1"

# Get time series data
curl "http://localhost:8086/api/metrics/prometheus/metrics-v2/timeseries?hours_back=2"

# Filter by node
curl "http://localhost:8086/api/metrics/prometheus/metrics-v2/timeseries?hours_back=1&node_name=minikube"
```

## Response Formats

### Pod Information Response
```json
{
  "status": "success",
  "namespace": "default",
  "pods": [
    {
      "name": "my-pod",
      "namespace": "default",
      "node_name": "minikube",
      "phase": "Running",
      "pod_ip": "10.244.0.5",
      "host_ip": "192.168.49.2",
      "containers": [
        {
          "name": "app",
          "image": "nginx:latest",
          "resources": {}
        }
      ],
      "container_statuses": [
        {
          "name": "app",
          "ready": true,
          "restart_count": 0,
          "state": {}
        }
      ]
    }
  ],
  "count": 1,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Energy Metrics Response
```json
{
  "status": "success",
  "source": "prometheus-metrics-service-v2",
  "time_series": {
    "total_energy_watts": {
      "minikube": [
        {"timestamp": 1705320600, "value": 45.67},
        {"timestamp": 1705320660, "value": 46.12}
      ]
    },
    "cpu_utilization": {
      "minikube": [
        {"timestamp": 1705320600, "value": 25.5},
        {"timestamp": 1705320660, "value": 27.8}
      ]
    }
  }
}
```

## Troubleshooting

### Connection Issues

**Problem:** `Unauthorized access to Kubernetes API`
**Solution:**
- Check service account permissions
- Verify RBAC configuration
- Ensure token is valid

**Problem:** `Failed to fetch pods: Network error`
**Solution:**
- Verify kubectl proxy is running: `kubectl proxy --port=8080`
- Check Minikube status: `minikube status`
- Test direct API access: `curl http://localhost:8080/api/v1/namespaces`

**Problem:** `Namespace not found`
**Solution:**
- List available namespaces: `kubectl get namespaces`
- Use correct namespace name in API calls

### Development Tips

1. **Use kubectl proxy** for local development - it's the easiest setup
2. **Check logs** for detailed error information
3. **Test connection first** using `/api/kubernetes/test` endpoint
4. **Verify permissions** if getting 403 errors

## Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────┐
│   FastAPI App   │    │  Kubernetes  │    │ Prometheus  │
│                 │────│     API      │    │   Server    │
│ • REST APIs     │    │              │    │             │
│ • Pod Management│    │ • Pods       │    │ • Kepler    │
│ • Energy Data   │    │ • Namespaces │    │ • cAdvisor  │
└─────────────────┘    └──────────────┘    └─────────────┘
         │                       │                  │
         └───────────────────────┼──────────────────┘
                                 │
                    ┌─────────────────┐
                    │   kubectl       │
                    │   proxy         │
                    │  (development)  │
                    └─────────────────┘
```

## Dependencies

- **Python 3.8+**
- **FastAPI**: Web framework
- **aiohttp**: Async HTTP client
- **Prometheus**: Metrics collection
- **Kubernetes**: Container orchestration
- **Kepler**: Energy consumption monitoring

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with Minikube
5. Submit a pull request

## License

[Your License Here]