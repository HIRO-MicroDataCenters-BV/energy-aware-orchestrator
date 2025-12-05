# PostgreSQL Chart Deployment Guide

Your custom PostgreSQL Helm chart with StatefulSet, ConfigMap, and Service.

## Chart Structure

```
charts/
├── Chart.yaml                           # Chart metadata
├── values.yaml                          # Configuration values
└── templates/
    ├── postgres-statefulset.yaml        # PostgreSQL StatefulSet
    ├── postgres-service.yaml            # PostgreSQL Service
    └── postgres-configmap.yaml          # ConfigMaps (DB URL + Init Script)
```

## Quick Deploy

### 1. From Project Root

```bash
# Install with default values
helm install postgres ./charts

# Or with custom release name
helm install my-postgres ./charts
```

### 2. With Custom Values

```bash
# Create custom values file
cat > my-postgres-values.yaml <<EOF
postgres:
  name: my-postgres
  credentials:
    username: myuser
    password: mypassword
    database: mydb
  persistence:
    size: 20Gi
EOF

# Install
helm install postgres ./charts -f my-postgres-values.yaml
```

## Configuration

### Default Values

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

### Customize via Command Line

```bash
# Change database name
helm install postgres ./charts \
  --set postgres.credentials.database=energy_db

# Change storage size
helm install postgres ./charts \
  --set postgres.persistence.size=20Gi

# Change credentials
helm install postgres ./charts \
  --set postgres.credentials.username=myuser \
  --set postgres.credentials.password=mypassword

# Change all at once
helm install postgres ./charts \
  --set postgres.name=my-postgres \
  --set postgres.credentials.database=mydb \
  --set postgres.credentials.username=myuser \
  --set postgres.credentials.password=mypass \
  --set postgres.persistence.size=50Gi
```

## Deployment Steps

### Step 1: Review Configuration

Edit `charts/values.yaml` or create your own values file:

```yaml
postgres:
  name: eao-postgres               # Service name
  image:
    repository: postgres
    tag: "14"                      # PostgreSQL version
    pullPolicy: Always
  replicaCount: 1
  service:
    type: ClusterIP
    port: 5432
  persistence:
    enabled: true
    size: 8Gi                      # Storage size
  credentials:
    username: postgres             # Database user
    password: postgres             # ⚠️ Change this!
    database: orchestration_db     # Database name
```

### Step 2: Install Chart

```bash
# Install with default values
helm install postgres ./charts

# Or with custom values file
helm install postgres ./charts -f my-values.yaml

# Or with inline overrides
helm install postgres ./charts \
  --set postgres.credentials.password=secure-password
```

### Step 3: Verify Deployment

```bash
# Check pods
kubectl get pods -l app=eao-postgres

# Check service
kubectl get svc eao-postgres

# Check PVC
kubectl get pvc

# Check configmaps
kubectl get configmap
```

### Step 4: Wait for Ready

```bash
# Wait for pod to be ready
kubectl wait --for=condition=ready pod \
  -l app=eao-postgres \
  --timeout=300s
```

## Accessing PostgreSQL

### Connection Details

After deployment, PostgreSQL is accessible at:

```
Host: eao-postgres (or your custom name from values.yaml)
Port: 5432
Database: orchestration_db (or your custom database name)
Username: postgres (or your custom username)
Password: postgres (or your custom password)
```

### Connection String

The chart automatically creates a ConfigMap with the connection string:

```bash
# Get the connection string
kubectl get configmap orchestration-api-config -o jsonpath='{.data.databaseURL}'
```

Output:
```
postgresql+asyncpg://postgres:postgres@eao-postgres:5432/orchestration_db
```

### Connect from Another Pod

```bash
# Run psql client
kubectl run psql-client --rm -it --restart=Never \
  --image=postgres:14 \
  --env="PGPASSWORD=postgres" \
  -- psql -h eao-postgres -U postgres -d orchestration_db

# Test connection
psql> SELECT version();
psql> \l
psql> \q
```

### Port Forward to Local Machine

```bash
# Forward PostgreSQL port
kubectl port-forward svc/eao-postgres 5432:5432

# Connect from local machine
psql -h localhost -U postgres -d orchestration_db
# Password: postgres
```

## Using with Energy Metric Service

### Get Connection Details

The ConfigMap `orchestration-api-config` contains the full DATABASE_URL:

```yaml
# In your application deployment
env:
  - name: DATABASE_URL
    valueFrom:
      configMapKeyRef:
        name: orchestration-api-config
        key: databaseURL
```

Or construct it:

```yaml
env:
  - name: POSTGRES_HOST
    value: eao-postgres
  - name: POSTGRES_PORT
    value: "5432"
  - name: POSTGRES_DB
    value: orchestration_db
  - name: POSTGRES_USER
    value: postgres
  - name: POSTGRES_PASSWORD
    value: postgres
```

## Management

### Upgrade

```bash
# Upgrade with new values
helm upgrade postgres ./charts -f new-values.yaml

# Or with inline changes
helm upgrade postgres ./charts \
  --set postgres.persistence.size=20Gi \
  --reuse-values
```

### Check Status

```bash
# Helm release status
helm status postgres

# Get all resources
kubectl get all -l app=eao-postgres

# View logs
kubectl logs -l app=eao-postgres -f
```

### Backup Database

```bash
# Create backup
kubectl exec -it eao-postgres-0 -- \
  pg_dump -U postgres orchestration_db > backup.sql

# Or backup all databases
kubectl exec -it eao-postgres-0 -- \
  pg_dumpall -U postgres > full-backup.sql
```

### Restore Database

```bash
# Restore from backup
cat backup.sql | kubectl exec -i eao-postgres-0 -- \
  psql -U postgres orchestration_db
```

### Uninstall

```bash
# Remove Helm release
helm uninstall postgres

# Delete PVC (optional - data will be lost!)
kubectl delete pvc postgres-data-eao-postgres-0
```

## Environment-Specific Deployments

### Development

```yaml
# dev-values.yaml
postgres:
  name: postgres-dev
  credentials:
    username: dev_user
    password: dev_password
    database: dev_db
  persistence:
    size: 5Gi
```

```bash
helm install postgres-dev ./charts -f dev-values.yaml
```

### Staging

```yaml
# staging-values.yaml
postgres:
  name: postgres-staging
  credentials:
    username: staging_user
    password: staging_secure_password
    database: staging_db
  persistence:
    size: 20Gi
```

```bash
helm install postgres-staging ./charts \
  -f staging-values.yaml \
  --namespace staging \
  --create-namespace
```

### Production

```yaml
# production-values.yaml
postgres:
  name: postgres-prod
  image:
    tag: "14"
  credentials:
    username: prod_user
    password: very-secure-production-password
    database: production_db
  persistence:
    enabled: true
    size: 100Gi
  service:
    type: ClusterIP
```

```bash
# Install in production namespace
helm install postgres-prod ./charts \
  -f production-values.yaml \
  --namespace production \
  --create-namespace
```

## Custom Init Scripts

Edit the ConfigMap in `charts/templates/postgres-configmap.yaml`:

```yaml
data:
  init.sql: |
    -- Create extensions
    CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

    -- Create custom tables
    CREATE TABLE IF NOT EXISTS energy_metrics (
      id SERIAL PRIMARY KEY,
      timestamp TIMESTAMPTZ NOT NULL,
      value FLOAT NOT NULL
    );

    -- Create indexes
    CREATE INDEX idx_energy_timestamp ON energy_metrics(timestamp);
```

Then upgrade:

```bash
helm upgrade postgres ./charts
```

## Troubleshooting

### Pod Won't Start

```bash
# Check pod events
kubectl describe pod eao-postgres-0

# Check logs
kubectl logs eao-postgres-0

# Common issues:
# - PVC not bound
# - Storage class not available
# - Resource limits too low
```

### PVC Issues

```bash
# Check PVC status
kubectl get pvc

# Check storage classes
kubectl get storageclass

# If PVC pending, check events
kubectl describe pvc postgres-data-eao-postgres-0
```

### Connection Issues

```bash
# Check service
kubectl get svc eao-postgres
kubectl describe svc eao-postgres

# Test connection from another pod
kubectl run test --rm -it --restart=Never \
  --image=busybox \
  -- nc -zv eao-postgres 5432
```

### Reset Database

```bash
# Delete pod (StatefulSet will recreate it)
kubectl delete pod eao-postgres-0

# Or delete PVC to start fresh (⚠️ DATA LOSS!)
helm uninstall postgres
kubectl delete pvc postgres-data-eao-postgres-0
helm install postgres ./charts
```

## ConfigMaps Created

### orchestration-api-config
Contains the DATABASE_URL connection string for your application:
```
postgresql+asyncpg://postgres:postgres@eao-postgres:5432/orchestration_db
```

### db-init-script
Contains SQL initialization script that runs on first startup.

## Examples

### Example 1: Quick Dev Setup

```bash
helm install postgres ./charts
kubectl wait --for=condition=ready pod -l app=eao-postgres --timeout=300s
kubectl port-forward svc/eao-postgres 5432:5432
```

### Example 2: Production with Custom Settings

```bash
helm install postgres-prod ./charts \
  --namespace production \
  --create-namespace \
  --set postgres.name=postgres-prod \
  --set postgres.credentials.username=prod_user \
  --set postgres.credentials.password="$(openssl rand -base64 32)" \
  --set postgres.credentials.database=prod_db \
  --set postgres.persistence.size=100Gi
```

### Example 3: Multiple Environments

```bash
# Dev
helm install postgres-dev ./charts \
  --namespace dev \
  --create-namespace \
  --set postgres.name=postgres-dev \
  --set postgres.persistence.size=5Gi

# Staging
helm install postgres-staging ./charts \
  --namespace staging \
  --create-namespace \
  --set postgres.name=postgres-staging \
  --set postgres.persistence.size=20Gi

# Production
helm install postgres-prod ./charts \
  --namespace production \
  --create-namespace \
  --set postgres.name=postgres-prod \
  --set postgres.persistence.size=100Gi
```

## Summary

Your chart includes:
- ✅ StatefulSet for PostgreSQL
- ✅ Service for networking
- ✅ ConfigMaps for DB URL and init scripts
- ✅ PersistentVolumeClaim for data storage
- ✅ Configurable via values.yaml

Deploy with:
```bash
helm install postgres ./charts
```

That's it! Your PostgreSQL is ready to use.
