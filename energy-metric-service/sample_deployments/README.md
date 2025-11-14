# Sample Deployment JSON Files

This directory contains sample JSON files for testing the energy-aware Kubernetes deployment API.

## Available Samples

### 1. **nginx-simple.json** - Low Energy (15.5W)
- Simple NGINX web server
- 1 replica with minimal resources
- Good for testing basic deployment functionality

**Usage:**
```bash
curl -X POST http://localhost:8086/api/deployment/deploy \
  -H "Content-Type: application/json" \
  -d @sample_deployments/nginx-simple.json
```

### 2. **microservice-low-energy.json** - Very Low Energy (8.3W)
- Lightweight API microservice
- 2 replicas with minimal CPU/memory
- Includes HPA for auto-scaling
- Good for microservices architecture testing

### 3. **web-app-high-cpu.json** - Medium Energy (75.2W)
- Production web application
- 3 replicas with higher resource requests
- Includes health checks and secrets
- Good for testing medium energy consumption

### 4. **database-deployment.json** - Medium Energy (45.8W)
- PostgreSQL database deployment
- Persistent storage
- Database-specific configuration
- Good for testing stateful workloads

### 5. **ml-workload-high-energy.json** - High Energy (180.5W)
- Machine Learning training job
- GPU requirements
- High CPU and memory demands
- Good for testing energy constraint scenarios

## Energy Estimation Guide

| Deployment Type | Estimated Energy | Use Case |
|----------------|------------------|----------|
| Microservice | 5-15W | API services, small apps |
| Web Application | 20-80W | Frontend apps, mid-tier services |
| Database | 30-60W | Persistent data services |
| ML/AI Workload | 100-300W+ | Training, inference, GPU workloads |

## Testing Scenarios

### Scenario 1: Successful Deployment
Use low-energy deployments when cluster has sufficient energy:
```bash
# Check energy first
curl http://localhost:8086/api/deployment/energy-check

# Deploy if sufficient
curl -X POST http://localhost:8086/api/deployment/deploy \
  -H "Content-Type: application/json" \
  -d @sample_deployments/nginx-simple.json
```

### Scenario 2: Energy Constraint Testing
Deploy high-energy workload to test queueing:
```bash
curl -X POST http://localhost:8086/api/deployment/deploy \
  -H "Content-Type: application/json" \
  -d @sample_deployments/ml-workload-high-energy.json
```

### Scenario 3: Multiple Deployments
Deploy several workloads to test cumulative energy tracking:
```bash
# Deploy multiple services
for file in nginx-simple.json microservice-low-energy.json web-app-high-cpu.json; do
  curl -X POST http://localhost:8086/api/deployment/deploy \
    -H "Content-Type: application/json" \
    -d @sample_deployments/$file
  echo "Deployed $file"
  sleep 2
done
```

## API Testing Commands

### Check Cluster Status
```bash
# Current energy availability
curl http://localhost:8086/api/deployment/energy-check

# Cluster capacity and utilization
curl http://localhost:8086/api/deployment/cluster-capacity

# Deployment statistics
curl http://localhost:8086/api/deployment/stats
```

### Manage Deployments
```bash
# List all deployment requests
curl http://localhost:8086/api/deployment/requests

# Get specific deployment
curl http://localhost:8086/api/deployment/requests/1

# Retry failed deployment
curl -X POST http://localhost:8086/api/deployment/requests/1/retry

# Filter by status
curl "http://localhost:8086/api/deployment/requests?status=pending"

# Filter by namespace
curl "http://localhost:8086/api/deployment/requests?namespace=production"
```

## Customizing Samples

To create your own deployment JSON:

```json
{
  "name": "your-app-name",
  "namespace": "your-namespace",
  "estimated_energy_watts": 25.0,
  "manifest": "your-kubernetes-yaml-here"
}
```

### Energy Estimation Formula
Rough estimation based on resource requests:
- **CPU**: ~20W per core
- **Memory**: ~5W per GB
- **GPU**: ~100-200W per GPU
- **Base overhead**: ~10W minimum

### Example Calculation
For a deployment with:
- CPU: 500m (0.5 cores) = 10W
- Memory: 1Gi = 5W
- Base overhead = 10W
- **Total**: ~25W

## Environment Setup

Ensure your Minikube/cluster has the required namespaces:
```bash
kubectl create namespace production
kubectl create namespace microservices
kubectl create namespace database
kubectl create namespace ml-workloads
```

## Notes

- All samples use realistic resource requests and limits
- Energy estimates are based on typical hardware consumption
- High-energy samples may be queued if cluster energy is insufficient
- Adjust `estimated_energy_watts` based on your actual hardware