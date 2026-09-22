# Energy Metrics Monitoring with Kepler, Prometheus, and Grafana

This Helm chart deploys a complete energy monitoring stack for Kubernetes clusters using Kepler, Prometheus, and Grafana to collect, store, and visualize energy consumption metrics.

## 🎯 Overview

This setup provides real-time energy consumption monitoring for:
- **Pod-level energy consumption**
- **Node-level energy consumption** 
- **CPU and Memory utilization**
- **Energy efficiency insights**

## 🏗️ Architecture

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌─────────────┐
│   Kepler    │───▶│  Prometheus  │───▶│   Grafana   │───▶│   Dashboard │
│ (Energy     │    │ (Metrics     │    │ (Visualize) │    │ (Monitor)   │
│  Collector) │    │  Storage)    │    │             │    │             │
└─────────────┘    └──────────────┘    └─────────────┘    └─────────────┘
```

## 📦 Components

### 1. **Kepler (v0.8.0)**
- **Purpose:** Energy metrics collection
- **Port:** 9102
- **Features:**
  - Container-level energy monitoring
  - Node-level energy aggregation
  - eBPF-based metrics collection
  - ML-powered energy estimation

### 2. **Prometheus (v25.21.0)**
- **Purpose:** Metrics storage and querying
- **Port:** 9090 (internal), 32001 (NodePort)
- **Features:**
  - Time-series database
  - PromQL query language
  - Service discovery
  - Alerting capabilities

### 3. **Grafana (v7.3.9)**
- **Purpose:** Visualization and dashboards
- **Port:** 3000 (internal), 32000 (NodePort)
- **Features:**
  - Interactive dashboards
  - Multiple data sources
  - Alerting and notifications
  - Custom queries

## 🔧 Installation

### Prerequisites
- Kubernetes cluster (tested with Minikube)
- Helm 3.x
- kubectl configured

### Quick Start
```bash
# 1. Clone or navigate to the chart directory
cd energy-monitoring-helm-stack

# 2. Update dependencies
helm dependency update

# 3. Install the chart - "energy-metrics" below is the Helm RELEASE name,
#    not the namespace. Deploy into the same namespace as the rest of this
#    repo's stack (default: "default") - see the note under Configuration.
helm upgrade --install energy-metrics . --namespace default

# 4. Wait for all pods to be ready
kubectl get pods -n default
```
Alternatively, you can use the provided scripts for cleanup and deployment:

```bash
# Clean up all resources
bash scripts/cleanup.sh

# Deploy the energy monitoring stack
bash scripts/deploy.sh
```


## 🌐 Access URLs

### Grafana Dashboard
- **URL:** `http://<NODE_IP>:32000`
- **Username:** `admin`
- **Password:** `admin`

### Prometheus
- **URL:** `http://<NODE_IP>:32001`

### Direct Kepler Metrics
- **URL:** `http://localhost:9102/metrics` (with port-forward)

## 📊 Available Dashboards

### 1. **Pod & Node Energy Dashboard** (`pod-node-energy-dashboard.json`)
Comprehensive dashboard with:
- **Energy Metrics:**
  - Pod Energy Consumption (Joules)
  - Pod Energy Consumption Rate (Joules/sec)
  - Node Energy Consumption (Joules)
- **Resource Utilization:**
  - Pod CPU Utilization (%)
  - Pod Memory Utilization (%)
  - Node CPU Utilization (%)
  - Node Memory Utilization (%)
- **Summary:**
  - Top 5 Energy Consumers

### 2. **Simple Test Dashboard** (`simple-kepler-dashboard.json`)
Basic dashboard for testing:
- Energy Consumption (Joules)
- Current Energy Values

## 🔍 How Kepler Collects Energy Metrics

### Real Hardware Mode (When Available)
Kepler can collect real energy measurements using:
- **RAPL (Running Average Power Limit):** Direct CPU power via MSR registers
- **ACPI Power Meters:** System-level power consumption
- **Redfish API:** Server management interface
- **Hardware Counters:** CPU performance counters via eBPF

### Estimation Mode (Current Setup)
In virtualized environments (like Minikube), Kepler uses:
- **Machine Learning Models:** Trained on real hardware data
- **CPU Usage Correlation:** Energy estimates based on CPU utilization
- **Statistical Models:** Patterns from historical data
- **BPF Data:** CPU time and metrics via eBPF

### Accuracy Levels
- **Real Hardware:** 95-99% accurate
- **Estimation (Virtual):** 70-85% accurate (good approximation)

## 📈 Key Metrics

### Energy Metrics
```promql
# Total energy consumption per container
kepler_container_joules_total

# Energy consumption rate
rate(kepler_container_joules_total[5m])

# Energy by namespace
kepler_container_joules_total{container_namespace="energy-metrics"}

# Top energy consumers
topk(5, kepler_container_joules_total)
```

### Resource Metrics
```promql
# CPU utilization
100 * (rate(container_cpu_usage_seconds_total[5m]) / scalar(machine_cpu_cores))

# Memory utilization
100 * (container_memory_usage_bytes / container_spec_memory_limit_bytes)

# Node CPU utilization
100 * (1 - avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])))

# Node memory utilization
100 * (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes))
```

## 🛠️ Configuration

### Values.yaml Customization
```yaml
grafana:
  service:
    type: NodePort
    nodePort: 32000
  adminPassword: admin

prometheus:
  server:
    service:
      type: NodePort
      nodePort: 32001

kepler:
  image:
    repository: quay.io/sustainable_computing_io/kepler
    tag: "release-0.8.0"
  resources:
    requests:
      memory: "128Mi"
      cpu: "250m"
    limits:
      memory: "512Mi"
      cpu: "500m"
```

> **Namespace gotcha:** `prometheus.extraScrapeConfigs` in `values.yaml` hardcodes the namespace its `kepler`/`node-exporter` scrape jobs look for pods in (currently `default`, matching this repo's deploy convention). This is the **Kubernetes namespace**, not the Helm release/chart name (`energy-metrics`) — confusing the two silently breaks both scrape jobs (zero targets discovered, no error). If you deploy this chart into a different namespace, update `prometheus.extraScrapeConfigs` to match. (Container CPU/memory metrics come from Prometheus's own built-in `kubernetes-nodes-cadvisor` job, not from an `extraScrapeConfigs` entry — see [Container Metrics Collection](../energy-metric-service/README.md#-container-metrics-collection) in the service README.)

## 🔧 Troubleshooting

### Common Issues

#### 1. **No Metrics in Grafana**
```bash
# Check Prometheus actually has kepler/node-exporter/kubernetes-nodes-cadvisor
# as active, healthy scrape targets - this is the most direct check and will
# catch a namespace mismatch in extraScrapeConfigs (see Configuration note
# above), which fails silently otherwise (no error, just zero targets)
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.scrapePool | test("kepler|node-exporter|cadvisor")) | {scrapePool, health}'

# Verify Kepler is running
kubectl get pods -n default -l app.kubernetes.io/name=kepler

# Check Kepler logs
kubectl logs -n default -l app.kubernetes.io/name=kepler
```

#### 2. **Port Forwarding Issues**
```bash
# Kill existing port forwards
pkill -f "kubectl port-forward"

# Restart port forwarding
kubectl port-forward -n default svc/energy-metrics-grafana 3000:80 &
kubectl port-forward -n default svc/energy-metrics-prometheus-server 9090:80 &
```

#### 3. **Kepler Image Pull Issues**
```bash
# Check image compatibility
docker manifest inspect quay.io/sustainable_computing_io/kepler:release-0.8.0

# For ARM64 systems, ensure using compatible image
```

### Health Checks
```bash
# Check all components
kubectl get pods -n default

# Test Kepler metrics
curl -s http://localhost:9102/metrics | grep kepler_container_joules_total

# Test Prometheus
curl -s "http://localhost:9090/api/v1/query?query=up" | jq

# Test Grafana
curl -s http://localhost:3000/api/health
```

## 📋 Importing Dashboards

### Method 1: File Upload
1. Open Grafana: `http://localhost:3000`
2. Go to **Dashboards** → **Import**
3. Upload the JSON file:
   - `pod-node-energy-dashboard.json`
   - `simple-kepler-dashboard.json`
4. Set data source to `prometheus`
5. Click **Import**

### Method 2: Manual Creation
1. Create new dashboard in Grafana
2. Add panels with PromQL queries
3. Configure data source as `prometheus`

## 🎛️ Dashboard Variables

The main dashboard includes:
- **Pod:** Filter by specific pods
- **Namespace:** Filter by namespace

## 🔄 Updating the Deployment

> **If your change only touched a ConfigMap-backed value** (e.g. `prometheus.extraScrapeConfigs`, Grafana dashboards/datasources), `helm upgrade` updates the ConfigMap but does **not** restart the pod that mounts it - this chart has no checksum annotation to trigger that automatically. Follow up with a manual restart of the affected deployment, e.g. `kubectl rollout restart deployment/energy-metrics-prometheus-server -n default`, or the old config keeps running until the pod restarts for some other reason.

```bash
# Update dependencies
helm dependency update

# Upgrade deployment
helm upgrade energy-metrics . -n default

# Rollback if needed
helm rollback energy-metrics -n default
```

## 🗑️ Cleanup

```bash
# Uninstall the chart
helm uninstall energy-metrics -n default

# Delete namespace
kubectl delete namespace energy-metrics

# Clean up port forwarding
pkill -f "kubectl port-forward"
```

## 📚 Additional Resources

- [Kepler Documentation](https://sustainable-computing.io/kepler/)
- [Prometheus Query Language](https://prometheus.io/docs/prometheus/latest/querying/)
- [Grafana Dashboard Documentation](https://grafana.com/docs/grafana/latest/dashboards/)

## 🤝 Contributing

To contribute to this setup:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Note:** Energy metrics in virtualized environments are estimates based on ML models. For production deployments on bare metal, Kepler can provide real hardware measurements with higher accuracy. 