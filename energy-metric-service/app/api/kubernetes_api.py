"""
Kubernetes API endpoints for pod and namespace management.
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from app.servicesv2.kubernetes_pods_service import KubernetesPodService
from app.models.kubernetes_models import (
    PodInfo,
    PodsResponse,
    NamespacesResponse,
    AllPodsResponse,
    AppPodsInfo,
    AppPodsResponse,
    ConnectionTestResponse
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/kubernetes", tags=["Kubernetes"])


def get_kubernetes_service():
    """Get KubernetesPodService instance."""
    return KubernetesPodService()


@router.get("/status", response_model=ConnectionTestResponse)
async def test_kubernetes_connection():
    """
    Test connection to Kubernetes API server.
    to test the connection to the Kubernetes API server use command 'kubectl proxy --port=8080'
    Returns connection status, authentication status, and cluster version information.
    Returns HTTP 503 if connection fails, HTTP 200 if connected.
    """
    try:
        k8s_service = get_kubernetes_service()
        connection_info = await k8s_service.test_connection()

        # If status is error, return 503 Service Unavailable
        if connection_info.get("status") == "error":
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "error",
                    "api_server": connection_info.get("api_server"),
                    "authenticated": connection_info.get("authenticated", False),
                    "error": connection_info.get("error")
                }
            )

        return ConnectionTestResponse(**connection_info)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing Kubernetes connection: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to test Kubernetes connection: {str(e)}")


@router.get("/namespaces", response_model=NamespacesResponse)
async def get_namespaces():
    """
    Get all available namespaces in the Kubernetes cluster.

    Returns a list of all namespaces with their metadata.
    """
    try:
        k8s_service = get_kubernetes_service()
        namespaces = await k8s_service.get_all_namespaces()

        return NamespacesResponse(
            status="success",
            namespaces=namespaces,
            count=len(namespaces),
            timestamp=datetime.utcnow().isoformat()
        )

    except Exception as e:
        logger.error(f"Error fetching namespaces: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch namespaces: {str(e)}")


@router.get("/pods", response_model=PodsResponse)
async def get_pods_by_namespace(
    namespace: str = Query("default", description="Kubernetes namespace to query"),
    phase: Optional[str] = Query(None, description="Filter by pod phase (Running, Pending, Succeeded, Failed, Unknown)"),
    node_name: Optional[str] = Query(None, description="Filter by node name")
):
    """
    Get all pods in a specific namespace.

    - **namespace**: The Kubernetes namespace to query (default: "default")
    - **phase**: Optional filter by pod phase
    - **node_name**: Optional filter by node name

    Returns detailed information about all pods in the specified namespace.
    """
    try:
        k8s_service = get_kubernetes_service()
        pods = await k8s_service.get_pods_by_namespace(namespace)

        # Apply additional filters if specified
        filtered_pods = pods

        if phase:
            filtered_pods = [pod for pod in filtered_pods if pod.get("phase") == phase]

        if node_name:
            filtered_pods = [pod for pod in filtered_pods if pod.get("node_name") == node_name]

        return PodsResponse(
            status="success",
            namespace=namespace,
            pods=filtered_pods,
            count=len(filtered_pods),
            timestamp=datetime.utcnow().isoformat()
        )

    except Exception as e:
        logger.error(f"Error fetching pods from namespace '{namespace}': {e}")

        if "Unauthorized" in str(e):
            raise HTTPException(status_code=401, detail="Unauthorized access to Kubernetes API")
        elif "Forbidden" in str(e):
            raise HTTPException(status_code=403, detail=f"Forbidden access to namespace '{namespace}'")
        elif "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Namespace '{namespace}' not found")
        else:
            raise HTTPException(status_code=500, detail=f"Failed to fetch pods: {str(e)}")


@router.get("/pods/all", response_model=AllPodsResponse)
async def get_all_pods(
    include_system: bool = Query(False, description="Include system namespaces (kube-system, kube-public, etc.)"),
    phase: Optional[str] = Query(None, description="Filter by pod phase"),
    node_name: Optional[str] = Query(None, description="Filter by node name")
):
    """
    Get all pods from all namespaces.

    - **include_system**: Whether to include system namespaces (default: False)
    - **phase**: Optional filter by pod phase
    - **node_name**: Optional filter by node name

    Returns pods organized by namespace.
    """
    try:
        k8s_service = get_kubernetes_service()
        pods_by_namespace = await k8s_service.get_pods_all_namespaces()

        # Filter out system namespaces if not requested
        if not include_system:
            system_namespaces = {
                "kube-system", "kube-public", "kube-node-lease",
                "local-path-storage", "ingress-nginx", "metallb-system"
            }
            pods_by_namespace = {
                ns: pods for ns, pods in pods_by_namespace.items()
                if ns not in system_namespaces
            }

        # Apply additional filters
        if phase or node_name:
            filtered_pods_by_namespace = {}
            for namespace, pods in pods_by_namespace.items():
                filtered_pods = pods

                if phase:
                    filtered_pods = [pod for pod in filtered_pods if pod.get("phase") == phase]

                if node_name:
                    filtered_pods = [pod for pod in filtered_pods if pod.get("node_name") == node_name]

                if filtered_pods:  # Only include namespaces with matching pods
                    filtered_pods_by_namespace[namespace] = filtered_pods

            pods_by_namespace = filtered_pods_by_namespace

        total_pods = sum(len(pods) for pods in pods_by_namespace.values())

        return AllPodsResponse(
            status="success",
            pods_by_namespace=pods_by_namespace,
            total_pods=total_pods,
            namespace_count=len(pods_by_namespace),
            timestamp=datetime.utcnow().isoformat()
        )

    except Exception as e:
        logger.error(f"Error fetching all pods: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch all pods: {str(e)}")


@router.get("/pods/summary")
async def get_pods_summary(
    include_system: bool = Query(False, description="Include system namespaces")
):
    """
    Get a summary of pods across all namespaces.

    Returns aggregated statistics about pods in the cluster.
    """
    try:
        k8s_service = get_kubernetes_service()
        pods_by_namespace = await k8s_service.get_pods_all_namespaces()

        # Filter out system namespaces if not requested
        if not include_system:
            system_namespaces = {
                "kube-system", "kube-public", "kube-node-lease",
                "local-path-storage", "ingress-nginx", "metallb-system"
            }
            pods_by_namespace = {
                ns: pods for ns, pods in pods_by_namespace.items()
                if ns not in system_namespaces
            }

        # Calculate summary statistics
        total_pods = 0
        phase_counts = {}
        node_counts = {}
        namespace_stats = {}

        for namespace, pods in pods_by_namespace.items():
            namespace_pod_count = len(pods)
            total_pods += namespace_pod_count

            namespace_phases = {}
            for pod in pods:
                phase = pod.get("phase", "Unknown")
                phase_counts[phase] = phase_counts.get(phase, 0) + 1
                namespace_phases[phase] = namespace_phases.get(phase, 0) + 1

                node_name = pod.get("node_name", "unassigned")
                if node_name:
                    node_counts[node_name] = node_counts.get(node_name, 0) + 1

            namespace_stats[namespace] = {
                "total_pods": namespace_pod_count,
                "phases": namespace_phases
            }

        return {
            "status": "success",
            "summary": {
                "total_pods": total_pods,
                "namespace_count": len(pods_by_namespace),
                "phase_distribution": phase_counts,
                "node_distribution": node_counts,
                "namespace_details": namespace_stats
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error generating pods summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate pods summary: {str(e)}")


@router.get("/pods/by-node/{node_name}")
async def get_pods_by_node(
    node_name: str,
    include_system: bool = Query(False, description="Include system namespaces")
):
    """
    Get all pods running on a specific node.

    - **node_name**: The name of the node to query
    - **include_system**: Whether to include system namespaces

    Returns all pods scheduled on the specified node.
    """
    try:
        k8s_service = get_kubernetes_service()
        pods_by_namespace = await k8s_service.get_pods_all_namespaces()

        # Filter by node and optionally exclude system namespaces
        node_pods = {}
        system_namespaces = {
            "kube-system", "kube-public", "kube-node-lease",
            "local-path-storage", "ingress-nginx", "metallb-system"
        }

        for namespace, pods in pods_by_namespace.items():
            if not include_system and namespace in system_namespaces:
                continue

            namespace_node_pods = [
                pod for pod in pods
                if pod.get("node_name") == node_name
            ]

            if namespace_node_pods:
                node_pods[namespace] = namespace_node_pods

        total_pods = sum(len(pods) for pods in node_pods.values())

        return {
            "status": "success",
            "node_name": node_name,
            "pods_by_namespace": node_pods,
            "total_pods": total_pods,
            "namespace_count": len(node_pods),
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error fetching pods for node '{node_name}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch pods for node: {str(e)}")


@router.get("/pods/by-app", response_model=AppPodsResponse)
async def get_pods_by_app_labels(
    app_name: Optional[str] = Query(None, description="Filter by app-name label"),
    workload_type: Optional[str] = Query(None, description="Filter by workload-type label"),
    namespace: Optional[str] = Query(None, description="Filter by specific namespace")
):
    """
    Get all pods grouped by application using custom labels.

    This endpoint retrieves pods based on their app-name labels and groups them
    by application. When no filters are provided, it returns all applications and their pods.

    - **app_name**: Optional filter by specific app-name label
    - **workload_type**: Optional filter by workload-type label (Critical, Preferred, Optional)
    - **namespace**: Optional filter by specific namespace (if not specified, searches all namespaces)

    Returns applications grouped with their associated pods. If no filters are provided,
    returns all apps that have the app-name label.
    """
    try:
        k8s_service = get_kubernetes_service()

        # Get pods from all namespaces or specific namespace
        if namespace:
            all_pods = {namespace: await k8s_service.get_pods_by_namespace(namespace)}
        else:
            all_pods = await k8s_service.get_pods_all_namespaces()

        # Group pods by app based on custom labels
        apps = {}
        total_pods = 0

        for ns, pods in all_pods.items():
            for pod in pods:
                pod_labels = pod.get('labels', {})

                # Get pod labels for filtering and grouping
                pod_app_name = pod_labels.get('app-name')
                pod_workload_type = pod_labels.get('workload-type')

                # If no filters are provided, include all pods that have an app-name label
                # If filters are provided, apply them
                if app_name and pod_app_name != app_name:
                    continue

                if workload_type and pod_workload_type != workload_type:
                    continue

                # Skip pods without app-name label
                # (either not managed by energy-metric-service or missing labels)
                if not pod_app_name:
                    continue

                # Create app key
                app_key = pod_app_name

                # Initialize app entry if not exists
                if app_key not in apps:
                    apps[app_key] = {
                        "app_name": pod_app_name,
                        "app_definition_id": pod_labels.get('app-definition-id'),
                        "workload_type": pod_workload_type,
                        "pods": []
                    }

                # Convert pod to PodInfo format
                pod_info = PodInfo(
                    name=pod.get('name', ''),
                    namespace=pod.get('namespace', ''),
                    uid=pod.get('uid', ''),
                    node_name=pod.get('node_name'),
                    phase=pod.get('phase', ''),
                    pod_ip=pod.get('pod_ip'),
                    host_ip=pod.get('host_ip'),
                    start_time=pod.get('start_time'),
                    created_at=pod.get('created_at', ''),
                    labels=pod_labels,
                    annotations=pod.get('annotations', {}),
                    containers=pod.get('containers', []),
                    container_statuses=pod.get('container_statuses', []),
                    restart_policy=pod.get('restart_policy'),
                    service_account=pod.get('service_account'),
                    conditions=pod.get('conditions', [])
                )

                apps[app_key]["pods"].append(pod_info)
                total_pods += 1

        # Convert to response format
        app_list = []
        for app_data in apps.values():
            app_list.append(AppPodsInfo(
                app_name=app_data["app_name"],
                app_definition_id=app_data["app_definition_id"],
                workload_type=app_data["workload_type"],
                pods=app_data["pods"],
                pod_count=len(app_data["pods"])
            ))

        # Sort by app name
        app_list.sort(key=lambda x: x.app_name)

        return AppPodsResponse(
            status="success",
            apps=app_list,
            total_apps=len(app_list),
            total_pods=total_pods,
            timestamp=datetime.utcnow().isoformat()
        )

    except Exception as e:
        logger.error(f"Error fetching pods by app labels: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch pods by app labels: {str(e)}")