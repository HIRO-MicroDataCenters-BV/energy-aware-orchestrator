#!/bin/bash

# Master monitoring script for all workload applications
# Provides comprehensive monitoring for all three workload types

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NAMESPACE="workspace"

echo "======================================"
echo "    ALL WORKLOADS MONITORING SCRIPT"
echo "======================================"
echo ""

# Check prerequisites
if ! command -v kubectl &> /dev/null; then
    echo "❌ Error: kubectl is not installed or not in PATH"
    exit 1
fi

if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Error: Cannot connect to Kubernetes cluster"
    exit 1
fi

# Function to get node IP
get_node_ip() {
    if command -v minikube &> /dev/null && minikube status &> /dev/null; then
        minikube ip
    else
        kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}' 2>/dev/null || echo "<node-ip>"
    fi
}

NODE_IP=$(get_node_ip)

echo "Node IP: $NODE_IP"
echo ""

# Function to check if a workload is deployed
check_workload_status() {
    local workload_name=$1
    local port=$2
    
    echo "----------------------------------------"
    echo "$workload_name Status"
    echo "----------------------------------------"
    
    # Check if namespace exists
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        echo "❌ Namespace '$NAMESPACE' not found - workloads not deployed"
        return 1
    fi
    
    # Check pod status
    echo "Pod Status:"
    if kubectl get pods -n "$NAMESPACE" -l app="$workload_name" &> /dev/null; then
        kubectl get pods -n "$NAMESPACE" -l app="$workload_name" -o wide
        
        # Check if pod is running
        POD_STATUS=$(kubectl get pods -n "$NAMESPACE" -l app="$workload_name" -o jsonpath='{.items[0].status.phase}' 2>/dev/null || echo "NotFound")
        if [ "$POD_STATUS" = "Running" ]; then
            echo "✅ Pod is running"
            
            # Try to get application status
            echo ""
            echo "Application Status:"
            if curl -s --connect-timeout 5 "http://$NODE_IP:$port/status" > /dev/null 2>&1; then
                echo "✅ API is responding"
                curl -s "http://$NODE_IP:$port/status" | jq -r '
                    if .current_phase then
                        "Current Phase: " + .current_phase
                    else
                        empty
                    end,
                    if .is_running then
                        "Is Running: " + (.is_running | tostring)
                    else
                        empty
                    end,
                    if .current_intensity then
                        "Current Intensity: " + (.current_intensity | tostring)
                    else
                        empty
                    end,
                    if .total_runs then
                        "Total Runs: " + (.total_runs | tostring)
                    else
                        empty
                    end,
                    if .cpu_usage then
                        "CPU Usage: " + (.cpu_usage | tostring) + "%"
                    else
                        empty
                    end,
                    if .memory_usage then
                        "Memory Usage: " + (.memory_usage | tostring) + "%"
                    else
                        empty
                    end
                ' 2>/dev/null || echo "Status endpoint available but response parsing failed"
            else
                echo "⚠️  API not responding (service may still be starting)"
            fi
        else
            echo "⚠️  Pod status: $POD_STATUS"
        fi
    else
        echo "❌ No pods found"
    fi
    
    echo ""
}

# Function to show resource usage
show_resource_usage() {
    echo "----------------------------------------"
    echo "Resource Usage (All Workloads)"
    echo "----------------------------------------"
    
    if kubectl top pods -n "$NAMESPACE" -l component=workload &> /dev/null; then
        kubectl top pods -n "$NAMESPACE" -l component=workload
    else
        echo "⚠️  Resource metrics not available (metrics-server may not be installed)"
    fi
    echo ""
}

# Function to show all workload services
show_services() {
    echo "----------------------------------------"
    echo "Services and Access URLs"
    echo "----------------------------------------"
    
    echo "External Access URLs:"
    echo "  Type-1 (Daily): http://$NODE_IP:32003"
    echo "  Type-2 (Periodic): http://$NODE_IP:32002"
    echo "  Type-3 (Random): http://$NODE_IP:32004"
    echo ""
    
    echo "Service Status:"
    if kubectl get namespace "$NAMESPACE" &> /dev/null; then
        kubectl get services -n "$NAMESPACE" 2>/dev/null || echo "  No services in $NAMESPACE"
    else
        echo "  Workspace namespace not found"
    fi
    echo ""
}

# Function to show quick health check
show_health_status() {
    echo "----------------------------------------"
    echo "Health Check (All Workloads)"
    echo "----------------------------------------"
    
    local ports=(32003 32002 32004)
    local names=("Type-1" "Type-2" "Type-3")
    
    for i in "${!ports[@]}"; do
        local port="${ports[$i]}"
        local name="${names[$i]}"
        
        printf "%-8s " "$name:"
        if curl -s --connect-timeout 3 "http://$NODE_IP:$port/health" > /dev/null 2>&1; then
            echo "✅ Healthy"
        else
            echo "❌ Not responding"
        fi
    done
    echo ""
}

# Main menu function
show_menu() {
    echo "Select monitoring option:"
    echo "  1) Quick overview (all workloads)"
    echo "  2) Detailed status (individual workloads)"
    echo "  3) Resource usage monitoring"
    echo "  4) Health check"
    echo "  5) Live log streaming"
    echo "  6) Service information"
    echo "  7) API testing"
    echo "  8) Continuous monitoring (updates every 10s)"
    echo "  q) Quit"
    echo ""
    read -p "Choose an option [1-8,q]: " -n 1 -r
    echo
}

# Function for continuous monitoring
continuous_monitoring() {
    echo "Starting continuous monitoring (Press Ctrl+C to stop)..."
    echo ""
    
    while true; do
        clear
        echo "======================================"
        echo "CONTINUOUS WORKLOAD MONITORING"
        echo "$(date)"
        echo "======================================"
        echo ""
        
        show_health_status
        show_resource_usage
        
        echo "Waiting 10 seconds for next update..."
        sleep 10
    done
}

# Function for API testing
api_testing() {
    echo "----------------------------------------"
    echo "API Testing (All Workloads)"
    echo "----------------------------------------"
    
    local ports=(32003 32002 32004)
    local names=("Type-1" "Type-2" "Type-3")
    
    for i in "${!ports[@]}"; do
        local port="${ports[$i]}"
        local name="${names[$i]}"
        
        echo "Testing $name (port $port):"
        
        # Test health endpoint
        if curl -s --connect-timeout 5 "http://$NODE_IP:$port/health" > /dev/null 2>&1; then
            echo "  ✅ /health - OK"
        else
            echo "  ❌ /health - FAILED"
        fi
        
        # Test status endpoint
        if curl -s --connect-timeout 5 "http://$NODE_IP:$port/status" > /dev/null 2>&1; then
            echo "  ✅ /status - OK"
        else
            echo "  ❌ /status - FAILED"
        fi
        
        # Test metrics endpoint
        if curl -s --connect-timeout 5 "http://$NODE_IP:$port/metrics" > /dev/null 2>&1; then
            echo "  ✅ /metrics - OK"
        else
            echo "  ❌ /metrics - FAILED"
        fi
        
        echo ""
    done
}

# Main execution
if [ "$1" = "--quick" ] || [ "$1" = "-q" ]; then
    # Quick mode
    show_health_status
    show_resource_usage
    exit 0
elif [ "$1" = "--continuous" ] || [ "$1" = "-c" ]; then
    # Continuous monitoring mode
    continuous_monitoring
    exit 0
fi

# Interactive mode
while true; do
    show_menu
    case $REPLY in
        1)
            clear
            echo "QUICK OVERVIEW - ALL WORKLOADS"
            echo "======================================"
            show_health_status
            show_resource_usage
            echo ""
            read -p "Press Enter to continue..."
            ;;
        2)
            clear
            echo "DETAILED STATUS - INDIVIDUAL WORKLOADS"
            echo "======================================"
            check_workload_status "workload-type-1" "32003"
            check_workload_status "workload-type-2" "32002"
            check_workload_status "workload-type-3" "32004"
            read -p "Press Enter to continue..."
            ;;
        3)
            clear
            echo "RESOURCE USAGE MONITORING"
            echo "======================================"
            show_resource_usage
            echo "Node resource usage:"
            kubectl top nodes 2>/dev/null || echo "Node metrics not available"
            echo ""
            read -p "Press Enter to continue..."
            ;;
        4)
            clear
            echo "HEALTH CHECK"
            echo "======================================"
            show_health_status
            read -p "Press Enter to continue..."
            ;;
        5)
            clear
            echo "Starting live log streaming for all workloads..."
            echo "Press Ctrl+C to stop"
            echo ""
            kubectl logs -f -l component=workload -n "$NAMESPACE" --prefix=true
            ;;
        6)
            clear
            echo "SERVICE INFORMATION"
            echo "======================================"
            show_services
            read -p "Press Enter to continue..."
            ;;
        7)
            clear
            echo "API TESTING"
            echo "======================================"
            api_testing
            read -p "Press Enter to continue..."
            ;;
        8)
            continuous_monitoring
            ;;
        q|Q)
            echo "Goodbye!"
            exit 0
            ;;
        *)
            echo "Invalid option. Please try again."
            sleep 1
            ;;
    esac
    clear
done