#!/bin/bash

# Master cleanup script for all workload applications
# Removes workload-type-1, workload-type-2, and workload-type-3

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKLOAD_DIRS=("workload-type-1" "workload-type-2" "workload-type-3")
NAMESPACE="workspace"
FAILED_CLEANUPS=()

echo "======================================"
echo "    ALL WORKLOADS CLEANUP SCRIPT"
echo "======================================"
echo ""
echo "This script will remove all three workload applications from the '$NAMESPACE' namespace:"
echo "  - workload-type-1 (Daily scheduled workload)"
echo "  - workload-type-2 (Regular periodic workload)"
echo "  - workload-type-3 (Random burst workload)"
echo ""

# Check prerequisites
echo "Checking prerequisites..."

# Check kubectl
if ! command -v kubectl &> /dev/null; then
    echo "❌ Error: kubectl is not installed or not in PATH"
    exit 1
fi

# Check Kubernetes cluster connection
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Error: Cannot connect to Kubernetes cluster"
    exit 1
fi

echo "✅ kubectl found and cluster connection verified"
echo ""

# Confirmation prompt
read -p "Are you sure you want to remove ALL workload applications? [y/N]: " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cleanup cancelled."
    exit 0
fi

echo ""
echo "======================================"
echo "Starting cleanup process..."
echo "======================================"

# Function to cleanup a workload
cleanup_workload() {
    local workload_dir=$1
    local workload_name=$(basename "$workload_dir")
    
    echo ""
    echo "----------------------------------------"
    echo "Cleaning up: $workload_name"
    echo "----------------------------------------"
    
    if [ ! -d "$SCRIPT_DIR/$workload_dir" ]; then
        echo "⚠️  Directory $workload_dir not found, skipping..."
        return 0
    fi
    
    cd "$SCRIPT_DIR/$workload_dir"
    
    # Check if cleanup.sh exists
    if [ ! -f "cleanup.sh" ]; then
        echo "⚠️  cleanup.sh not found in $workload_dir, trying manual cleanup..."
        
        # Try manual cleanup of resources in workspace namespace
        echo "Attempting manual cleanup of $workload_name resources in $NAMESPACE namespace..."
        kubectl delete deployment "$workload_name" -n "$NAMESPACE" --ignore-not-found=true
        kubectl delete service "${workload_name}-service" -n "$NAMESPACE" --ignore-not-found=true
        kubectl delete configmap "${workload_name}-config" -n "$NAMESPACE" --ignore-not-found=true
        echo "✅ Manual cleanup attempted for $workload_name"
        return 0
    fi
    
    if [ ! -x "cleanup.sh" ]; then
        echo "Making cleanup.sh executable..."
        chmod +x cleanup.sh
    fi
    
    # Run cleanup script
    echo "🧹 Running cleanup for $workload_name..."
    if ./cleanup.sh; then
        echo "✅ $workload_name cleaned up successfully"
    else
        echo "❌ Failed to cleanup $workload_name"
        FAILED_CLEANUPS+=("$workload_name: Cleanup failed")
        return 1
    fi
    
    cd "$SCRIPT_DIR"
    return 0
}

# Cleanup each workload
for workload in "${WORKLOAD_DIRS[@]}"; do
    cleanup_workload "$workload"
done

# Additional cleanup - remove workspace namespace and any remaining resources
echo ""
echo "----------------------------------------"
echo "Final cleanup of workspace namespace..."
echo "----------------------------------------"

# Check if workspace namespace exists and has resources
if kubectl get namespace "$NAMESPACE" &> /dev/null; then
    echo "Checking for remaining resources in $NAMESPACE namespace..."
    
    # List any remaining resources
    REMAINING_RESOURCES=$(kubectl get all -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l || echo "0")
    if [ "$REMAINING_RESOURCES" -gt 0 ]; then
        echo "Found $REMAINING_RESOURCES remaining resources in $NAMESPACE:"
        kubectl get all -n "$NAMESPACE"
        echo ""
        echo "Deleting remaining resources..."
        kubectl delete all --all -n "$NAMESPACE" --timeout=120s || echo "Some resources failed to delete"
    fi
    
    echo "Deleting workspace namespace..."
    kubectl delete namespace "$NAMESPACE" --timeout=180s
    echo "✅ Workspace namespace deleted"
else
    echo "✅ Workspace namespace already removed"
fi

# Check for any remaining workload pods in other namespaces
WORKLOAD_PODS=$(kubectl get pods --all-namespaces -l component=workload -o name 2>/dev/null || true)
if [ -n "$WORKLOAD_PODS" ]; then
    echo "⚠️  Found remaining workload pods in other namespaces:"
    kubectl get pods --all-namespaces -l component=workload
else
    echo "✅ No remaining workload pods found"
fi

echo ""
echo "======================================"
echo "CLEANUP SUMMARY"
echo "======================================"

if [ ${#FAILED_CLEANUPS[@]} -eq 0 ]; then
    echo "🎉 ALL WORKLOADS CLEANED UP SUCCESSFULLY!"
    echo ""
    echo "Removed Applications:"
    echo "  🗑️  workload-type-1 (Daily scheduled)"
    echo "  🗑️  workload-type-2 (Regular periodic)"
    echo "  🗑️  workload-type-3 (Random bursts)"
    echo ""
else
    echo "⚠️  CLEANUP COMPLETED WITH SOME FAILURES:"
    for failure in "${FAILED_CLEANUPS[@]}"; do
        echo "  ❌ $failure"
    done
    echo ""
fi

echo "Docker Images Status:"
echo "The following Docker images are still available locally:"
if docker images | grep -E "workload-type-[123]" > /dev/null 2>&1; then
    docker images | grep -E "workload-type-[123]"
    echo ""
    echo "To remove Docker images:"
    echo "  docker rmi workload-type-1:v1"
    echo "  docker rmi workload-type-2:v1"
    echo "  docker rmi workload-type-3:v1"
else
    echo "  No workload Docker images found locally"
fi

echo ""
echo "Verification Commands:"
echo "  Check for any remaining workload resources:"
echo "    kubectl get all -n $NAMESPACE -l component=workload"
echo ""
echo "  Check if workspace namespace exists:"
echo "    kubectl get namespace $NAMESPACE"

echo ""
echo "======================================"
echo "Cleanup script completed!"
echo "======================================"