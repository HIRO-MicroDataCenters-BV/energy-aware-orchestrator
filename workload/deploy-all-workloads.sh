#!/bin/bash

# Master deployment script for all workload applications
# Builds and deploys workload-type-1, workload-type-2, and workload-type-3

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKLOAD_BASE_DIR="$SCRIPT_DIR"
ALL_WORKLOAD_DIRS=("workload-type-1" "workload-type-2" "workload-type-3")
NAMESPACE="workspace"
FAILED_DEPLOYMENTS=()

# Function to show usage
show_usage() {
    echo "Usage: $0 [workload_number|all]"
    echo ""
    echo "Options:"
    echo "  1        Deploy only workload-type-1 (Daily scheduled)"
    echo "  2        Deploy only workload-type-2 (Regular periodic)" 
    echo "  3        Deploy only workload-type-3 (Random bursts)"
    echo "  all      Deploy all three workloads (default)"
    echo "  -h|--help Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 1       # Deploy only workload-type-1"
    echo "  $0 all     # Deploy all workloads"
    echo "  $0         # Deploy all workloads (default)"
}

# Parse command line arguments
WORKLOAD_DIRS=()
if [ $# -eq 0 ] || [ "$1" = "all" ]; then
    WORKLOAD_DIRS=("${ALL_WORKLOAD_DIRS[@]}")
elif [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    show_usage
    exit 0
elif [ "$1" = "1" ]; then
    WORKLOAD_DIRS=("workload-type-1")
elif [ "$1" = "2" ]; then
    WORKLOAD_DIRS=("workload-type-2") 
elif [ "$1" = "3" ]; then
    WORKLOAD_DIRS=("workload-type-3")
else
    echo "❌ Error: Invalid option '$1'"
    echo ""
    show_usage
    exit 1
fi

echo "======================================"
echo "    WORKLOADS DEPLOYMENT SCRIPT"
echo "======================================"
echo ""
echo "Selected workloads to deploy in namespace '$NAMESPACE':"
for workload in "${WORKLOAD_DIRS[@]}"; do
    case $workload in
        "workload-type-1")
            echo "  ✓ workload-type-1: Daily scheduled (8-10 AM, 6-9 PM, 2 hours each)"
            ;;
        "workload-type-2")
            echo "  ✓ workload-type-2: Regular periodic (every 15 minutes, 30 seconds)"
            ;;
        "workload-type-3")
            echo "  ✓ workload-type-3: Random bursts (20min active, 60min idle cycles)"
            ;;
    esac
done
echo ""

# Check prerequisites
echo "Checking prerequisites..."

# Check kubectl
if ! command -v kubectl &> /dev/null; then
    echo "❌ Error: kubectl is not installed or not in PATH"
    exit 1
fi

# Check docker
if ! command -v docker &> /dev/null; then
    echo "❌ Error: docker is not installed or not in PATH"
    exit 1
fi

# Check Kubernetes cluster connection
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Error: Cannot connect to Kubernetes cluster"
    echo "Please ensure your kubectl is configured and cluster is accessible"
    exit 1
fi

echo "✅ kubectl found and cluster connection verified"
echo "✅ docker found"
echo ""

# Check if minikube is available
MINIKUBE_AVAILABLE=false
if command -v minikube &> /dev/null && minikube status &> /dev/null; then
    MINIKUBE_AVAILABLE=true
    echo "✅ Minikube detected and running"
else
    echo "⚠️  Minikube not detected or not running"
fi

echo ""
echo "======================================"
echo "Starting deployment process..."
echo "======================================"

# Create shared workspace namespace first
echo ""
echo "Creating shared workspace namespace..."
if kubectl apply -f ../workspace-namespace.yaml; then
    echo "✅ Workspace namespace created/updated"
else
    echo "❌ Failed to create workspace namespace"
    exit 1
fi

# Function to build and deploy a workload
deploy_workload() {
    local workload_dir=$1
    local workload_name=$(basename "$workload_dir")
    
    echo ""
    echo "----------------------------------------"
    echo "Processing: $workload_name"
    echo "----------------------------------------"
    
    if [ ! -d "$WORKLOAD_BASE_DIR/$workload_dir" ]; then
        echo "❌ Error: Directory $workload_dir not found"
        FAILED_DEPLOYMENTS+=("$workload_name: Directory not found")
        return 1
    fi
    
    cd "$WORKLOAD_BASE_DIR/$workload_dir"
    
    # Check if build.sh exists and is executable
    if [ ! -f "build.sh" ]; then
        echo "❌ Error: build.sh not found in $workload_dir"
        FAILED_DEPLOYMENTS+=("$workload_name: build.sh not found")
        return 1
    fi
    
    if [ ! -x "build.sh" ]; then
        echo "Making build.sh executable..."
        chmod +x build.sh
    fi
    
    # Check if deploy.sh exists and is executable
    if [ ! -f "deploy.sh" ]; then
        echo "❌ Error: deploy.sh not found in $workload_dir"
        FAILED_DEPLOYMENTS+=("$workload_name: deploy.sh not found")
        return 1
    fi
    
    if [ ! -x "deploy.sh" ]; then
        echo "Making deploy.sh executable..."
        chmod +x deploy.sh
    fi
    
    # Build the Docker image
    echo "🔨 Building $workload_name Docker image..."
    if ./build.sh; then
        echo "✅ $workload_name image built successfully"
        
        # Load image into minikube if available
        if $MINIKUBE_AVAILABLE; then
            echo "📦 Loading $workload_name image into minikube..."
            IMAGE_NAME="${workload_name}:v1"
            minikube image load "$IMAGE_NAME" || echo "⚠️  Failed to load image into minikube"
        fi
    else
        echo "❌ Failed to build $workload_name image"
        FAILED_DEPLOYMENTS+=("$workload_name: Build failed")
        return 1
    fi
    
    # Skip individual namespace creation (we already created workspace)
    echo "🚀 Deploying $workload_name to workspace namespace..."
    
    # Apply only the necessary manifests (skip namespace.yaml since we already created workspace)
    echo "  Creating ConfigMap..."
    kubectl apply -f k8s/configmap.yaml || { echo "❌ ConfigMap failed"; FAILED_DEPLOYMENTS+=("$workload_name: ConfigMap failed"); return 1; }
    
    echo "  Creating Service..."
    kubectl apply -f k8s/service.yaml || { echo "❌ Service failed"; FAILED_DEPLOYMENTS+=("$workload_name: Service failed"); return 1; }
    
    echo "  Creating Deployment..."
    kubectl apply -f k8s/deployment.yaml || { echo "❌ Deployment failed"; FAILED_DEPLOYMENTS+=("$workload_name: Deployment failed"); return 1; }
    
    echo "  Waiting for deployment to be ready..."
    kubectl rollout status deployment/$workload_name -n "$NAMESPACE" --timeout=300s || { echo "❌ Rollout failed"; FAILED_DEPLOYMENTS+=("$workload_name: Rollout timeout"); return 1; }
    
    echo "✅ $workload_name deployed successfully"
    
    cd "$SCRIPT_DIR"
    return 0
}

# Deploy each workload
for workload in "${WORKLOAD_DIRS[@]}"; do
    deploy_workload "$workload"
done

echo ""
echo "======================================"
echo "DEPLOYMENT SUMMARY"
echo "======================================"

if [ ${#FAILED_DEPLOYMENTS[@]} -eq 0 ]; then
    echo "🎉 SELECTED WORKLOADS DEPLOYED SUCCESSFULLY!"
    echo ""
    echo "Deployed Applications (in namespace: $NAMESPACE):"
    for workload in "${WORKLOAD_DIRS[@]}"; do
        case $workload in
            "workload-type-1")
                echo "  ✅ workload-type-1 → http://<node-ip>:32003"
                ;;
            "workload-type-2")
                echo "  ✅ workload-type-2 → http://<node-ip>:32002"
                ;;
            "workload-type-3")
                echo "  ✅ workload-type-3 → http://<node-ip>:32004"
                ;;
        esac
    done
    echo ""
    echo "Workload Patterns:"
    for workload in "${WORKLOAD_DIRS[@]}"; do
        case $workload in
            "workload-type-1")
                echo "  📅 Type-1: Daily windows (8-10 AM, 6-9 PM) - 2 hours each"
                ;;
            "workload-type-2")
                echo "  🔄 Type-2: Every 15 minutes - 30 seconds each"
                ;;
            "workload-type-3")
                echo "  🎲 Type-3: Random bursts - 20min active, 60min idle"
                ;;
        esac
    done
    echo ""
else
    echo "⚠️  DEPLOYMENT COMPLETED WITH SOME FAILURES:"
    for failure in "${FAILED_DEPLOYMENTS[@]}"; do
        echo "  ❌ $failure"
    done
    echo ""
fi

echo "Useful Commands:"
echo ""
echo "Check all workload pods:"
echo "  kubectl get pods -n $NAMESPACE -l component=workload"
echo ""
echo "Monitor resource usage:"
echo "  kubectl top pods -n $NAMESPACE -l component=workload"
echo ""
echo "Check workload status:"
for workload in "${WORKLOAD_DIRS[@]}"; do
    case $workload in
        "workload-type-1")
            if command -v minikube &> /dev/null; then
                echo "  curl http://\$(minikube ip):32003/status  # Type-1"
            else
                echo "  curl http://<node-ip>:32003/status  # Type-1"
            fi
            ;;
        "workload-type-2")
            if command -v minikube &> /dev/null; then
                echo "  curl http://\$(minikube ip):32002/status  # Type-2"
            else
                echo "  curl http://<node-ip>:32002/status  # Type-2"
            fi
            ;;
        "workload-type-3")
            if command -v minikube &> /dev/null; then
                echo "  curl http://\$(minikube ip):32004/status  # Type-3"
            else
                echo "  curl http://<node-ip>:32004/status  # Type-3"
            fi
            ;;
    esac
done
echo ""
echo "View logs for all workloads:"
echo "  kubectl logs -f -l component=workload -n $NAMESPACE"
echo ""
echo "Cleanup all workloads:"
echo "  ./cleanup-all-workloads.sh"

echo ""
echo "======================================"
echo "Deployment script completed!"
echo "======================================"