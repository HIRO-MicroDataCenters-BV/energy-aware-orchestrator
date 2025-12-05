# PostgreSQL Helm Chart

Custom PostgreSQL chart with StatefulSet, Service, and ConfigMaps.

## Quick Start

### Option 1: Using the Script (Easiest)

```bash
cd charts
./deploy-postgres.sh
```

### Option 2: Using Helm Directly

```bash
# Install with defaults
helm install postgres ./charts

# Install with custom values
helm install postgres ./charts \
  --set postgres.credentials.database=mydb \
  --set postgres.credentials.username=myuser \
  --set postgres.credentials.password=mypass \
  --set postgres.persistence.size=20Gi
```

## What's Included

```
charts/
├── Chart.yaml                    # Chart metadata
├── values.yaml                   # Default configuration
├── deploy-postgres.sh            # Deployment script
├── DEPLOY.md                     # Full deployment guide
└── templates/
    ├── postgres-statefulset.yaml # PostgreSQL StatefulSet
    ├── postgres-service.yaml     # Service
    └── postgres-configmap.yaml   # ConfigMaps
```

## Chart Components

### StatefulSet
- PostgreSQL 14
- Persistent storage (8Gi default)
- Init scripts support via ConfigMap
- Health checks

### Service
- ClusterIP (default)
- Port 5432
- Internal cluster access

### ConfigMaps
1. **orchestration-api-config** - Contains DATABASE_URL
2. **db-init-script** - SQL initialization scripts

## Default Configuration

```yaml
postgres:
  name: eao-postgres
  image: postgres:14
  credentials:
    username: postgres
    password: postgres           # ⚠️ Change in production!
    database: orchestration_db
  persistence:
    size: 8Gi
  service:
    type: ClusterIP
    port: 5432
```

## Deployment Examples

### Example 1: Development

```bash
./deploy-postgres.sh
```

### Example 2: Production

```bash
./deploy-postgres.sh \
  --namespace production \
  --release postgres-prod \
  --db production_db \
  --user prod_user \
  --password "$(openssl rand -base64 32)" \
  --storage 100Gi
```

### Example 3: With Values File

Create `prod-values.yaml`:
```yaml
postgres:
  name: postgres-prod
  credentials:
    username: prod_user
    password: very-secure-password
    database: prod_db
  persistence:
    size: 50Gi
```

Deploy:
```bash
./deploy-postgres.sh -f prod-values.yaml --namespace production
```

## Connection Details

After deployment, PostgreSQL is accessible at:

```
Host: eao-postgres (or your custom name)
Port: 5432
Database: orchestration_db (or your custom database)
Username: postgres (or your custom username)
Password: postgres (or your custom password)
```

### Get Connection String

```bash
# From ConfigMap
kubectl get configmap orchestration-api-config -o jsonpath='{.data.databaseURL}'

# Output:
# postgresql+asyncpg://postgres:postgres@eao-postgres:5432/orchestration_db
```

### Connect from Pod

```bash
kubectl run psql-client --rm -it --restart=Never \
  --image=postgres:14 \
  --env="PGPASSWORD=postgres" \
  -- psql -h eao-postgres -U postgres -d orchestration_db
```

### Port Forward

```bash
kubectl port-forward svc/eao-postgres 5432:5432
psql -h localhost -U postgres -d orchestration_db
```

## Management

### Upgrade

```bash
# With script
./deploy-postgres.sh --db newdb --storage 20Gi

# With helm
helm upgrade postgres ./charts --reuse-values
```

### Logs

```bash
kubectl logs -l app=eao-postgres -f
```

### Backup

```bash
kubectl exec eao-postgres-0 -- pg_dump -U postgres orchestration_db > backup.sql
```

### Uninstall

```bash
# With script
./deploy-postgres.sh --uninstall

# With helm
helm uninstall postgres
kubectl delete pvc postgres-data-eao-postgres-0
```

## Customization

### Change Database Credentials

```bash
helm install postgres ./charts \
  --set postgres.credentials.username=myuser \
  --set postgres.credentials.password=mypassword \
  --set postgres.credentials.database=mydb
```

### Change Storage Size

```bash
helm install postgres ./charts \
  --set postgres.persistence.size=50Gi
```

### Add Custom Init Script

Edit `templates/postgres-configmap.yaml`:

```yaml
data:
  init.sql: |
    CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

    CREATE TABLE IF NOT EXISTS my_table (
      id SERIAL PRIMARY KEY,
      name VARCHAR(255)
    );
```

## Environment Variables for Application

Your application can use these environment variables:

```yaml
env:
  - name: DATABASE_URL
    valueFrom:
      configMapKeyRef:
        name: orchestration-api-config
        key: databaseURL

# Or construct manually:
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

## Troubleshooting

### Pod Not Starting

```bash
# Check events
kubectl describe pod eao-postgres-0

# Check logs
kubectl logs eao-postgres-0

# Check PVC
kubectl get pvc
```

### Connection Issues

```bash
# Check service
kubectl get svc eao-postgres

# Test connection
kubectl run test --rm -it --image=busybox -- nc -zv eao-postgres 5432
```

## Documentation

- [DEPLOY.md](DEPLOY.md) - Full deployment guide with all options
- [deploy-postgres.sh](deploy-postgres.sh) - Automated deployment script

## Support

```bash
# Script help
./deploy-postgres.sh --help

# Check chart
helm template postgres ./charts

# Validate
helm lint ./charts
```

## Summary

✅ StatefulSet with persistent storage
✅ Service for cluster access
✅ ConfigMaps for connection strings
✅ Easy deployment script
✅ Customizable via values or CLI

Deploy now:
```bash
./deploy-postgres.sh
```
