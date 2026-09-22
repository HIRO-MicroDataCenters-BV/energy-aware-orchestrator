"""
Kubernetes API endpoints for pod and namespace management.
"""

from datetime import datetime
from typing import Optional, Dict
from fastapi import APIRouter, HTTPException, Query
from app.services.kubernetes_service import KubernetesService
from app.models.kubernetes_models import (
    PodInfo,
    PodsResponse,
    NamespacesResponse,
    AllPodsResponse,
    AppPodsInfo,
    AppPodsResponse,
    AppPodsInfoV2,
    AppPodsResponseV2,
    ConnectionTestResponse
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/kubernetes", tags=["Kubernetes APIs"])


def get_kubernetes_service():
    """Get KubernetesService instance."""
    return KubernetesService()


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


@router.get("/pods/by-app/v2", response_model=AppPodsResponseV2)
async def get_pods_by_app_v2(
    app_name: Optional[str] = Query(None, description="Filter by app name (works with standard, custom labels, and CR names)"),
    app_type: Optional[str] = Query(None, description="Filter by app type: 'standard', 'custom', or 'custom-resource'"),
    workload_type: Optional[str] = Query(None, description="Filter by workload type (Critical, Preferred, Optional)"),
    namespace: Optional[str] = Query(None, description="Filter by specific namespace")
):
    """
    V2 API: Get all pods grouped by application with enhanced identification including Custom Resources.
    
    This endpoint intelligently detects:
    
    **Standard Kubernetes Apps** (detected by):
    - `app.kubernetes.io/name` (preferred)
    - `app` (common standard label)
    
    **Custom Apps** (detected by):
    - `app-name` (energy-metric-service custom label)
    
    **Custom Resources** (EnergyAwareOrchestration CRs):
    - Fetched from Kubernetes API
    - Shows CR metadata and target application reference
    
    Additional metadata extracted:
    - Standard apps: instance, version, component, managed-by
    - Custom apps: app-definition-id, workload-type
    - Custom resources: priority, phase, decision, target application
    
    **Query Parameters:**
    - **app_name**: Filter by app name (searches across all types including CR names)
    - **app_type**: Filter by type ('standard', 'custom', or 'custom-resource')
    - **workload_type**: Filter by workload type/priority (works for custom apps and CRs)
    - **namespace**: Filter by specific namespace
    
    **Response includes:**
    - App name and type (standard/custom/custom-resource)
    - Label source or "EnergyAwareOrchestration CR"
    - All relevant metadata
    - Pod list with full details
    - Namespace list where app is deployed or CR is located
    """
    try:
        k8s_service = get_kubernetes_service()

        # Get pods from all namespaces or specific namespace
        if namespace:
            all_pods = {namespace: await k8s_service.get_pods_by_namespace(namespace)}
        else:
            all_pods = await k8s_service.get_pods_all_namespaces()

        # Get custom resources
        try:
            custom_resources = await k8s_service.get_custom_resources(namespace=namespace)
        except Exception as e:
            logger.warning(f"Could not fetch custom resources: {e}")
            custom_resources = []

        # Group pods by app with enhanced detection
        apps = {}
        total_pods = 0
        standard_apps_count = 0
        custom_apps_count = 0
        custom_resource_count = 0

        for ns, pods in all_pods.items():
            for pod in pods:
                pod_labels = pod.get('labels', {})

                # Detect app name and type from various label sources
                detected_app = _detect_app_from_labels(pod_labels)
                
                if not detected_app:
                    # Skip pods without recognizable app labels
                    continue

                detected_app_name = detected_app['app_name']
                detected_app_type = detected_app['app_type']
                label_source = detected_app['label_source']

                # Apply filters
                if app_name and detected_app_name != app_name:
                    continue

                if app_type and detected_app_type != app_type:
                    continue

                if workload_type:
                    pod_workload_type = pod_labels.get('workload-type')
                    if pod_workload_type != workload_type:
                        continue

                # Create app key (app_name + app_type to avoid conflicts)
                app_key = f"{detected_app_type}:{detected_app_name}"

                # Initialize app entry if not exists
                if app_key not in apps:
                    app_entry = {
                        "app_name": detected_app_name,
                        "app_type": detected_app_type,
                        "label_source": label_source,
                        "pods": [],
                        "namespaces": set(),
                        # Capture app-name label value (present in both standard and custom apps)
                        "app_name_label": pod_labels.get('app-name')
                    }

                    # Add standard k8s metadata
                    if detected_app_type == "standard":
                        app_entry["app_instance"] = pod_labels.get('app.kubernetes.io/instance')
                        app_entry["app_version"] = pod_labels.get('app.kubernetes.io/version')
                        app_entry["app_component"] = pod_labels.get('app.kubernetes.io/component')
                        app_entry["managed_by"] = pod_labels.get('app.kubernetes.io/managed-by')
                        app_entry["app_definition_id"] = None
                        app_entry["workload_type"] = pod_labels.get('workload-type')  # Capture workload-type for standard apps too
                    # Add custom app metadata
                    else:
                        app_entry["app_instance"] = None
                        app_entry["app_version"] = None
                        app_entry["app_component"] = None
                        app_entry["managed_by"] = None
                        app_entry["app_definition_id"] = pod_labels.get('app-definition-id')
                        app_entry["workload_type"] = pod_labels.get('workload-type')

                    apps[app_key] = app_entry

                # Add namespace to the set
                apps[app_key]["namespaces"].add(ns)

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

        # Add custom resources to apps
        for cr in custom_resources:
            cr_name = cr.get('name', '')
            cr_namespace = cr.get('namespace', '')
            cr_spec = cr.get('spec', {})
            cr_status = cr.get('status', {})
            cr_labels = cr.get('labels', {})
            
            # Get priority from spec
            cr_priority = cr_spec.get('priority', '')
            
            # Apply filters for custom resources
            if app_name and cr_name != app_name:
                continue
            
            if app_type and app_type != 'custom-resource':
                continue
            
            if workload_type and cr_priority != workload_type:
                continue

            # Get target application reference
            app_ref = cr_spec.get('application_ref', {})
            target_app_name = app_ref.get('name', '')
            target_app_kind = app_ref.get('kind', '')
            target_app_namespace = app_ref.get('namespace', cr_namespace)
            
            # Get status information
            cr_phase = cr_status.get('phase') if cr_status else None
            cr_decision = cr_status.get('decision', {}).get('action') if cr_status else None

            # Get app-name label directly from CR's own labels
            cr_app_name_label = cr_labels.get('app-name')
            
            if cr_app_name_label:
                logger.debug(f"CR '{cr_name}' has app-name label: {cr_app_name_label}")
            else:
                logger.debug(f"CR '{cr_name}' does not have app-name label")

            # Create app key for CR
            app_key = f"custom-resource:{cr_name}:{cr_namespace}"

            # Add CR as an app entry (no pods, just CR metadata)
            apps[app_key] = {
                "app_name": cr_name,
                "app_type": "custom-resource",
                "label_source": "EnergyAwareOrchestration CR",
                "pods": [],
                "namespaces": {cr_namespace},
                "app_name_label": cr_app_name_label,  # Get from target application's pods
                "app_instance": None,
                "app_version": None,
                "app_component": None,
                "managed_by": None,
                "app_definition_id": None,
                "workload_type": cr_priority,
                "custom_resource_name": cr_name,
                "custom_resource_namespace": cr_namespace,
                "custom_resource_priority": cr_priority,
                "custom_resource_phase": cr_phase,
                "custom_resource_decision": cr_decision,
                "target_app_name": target_app_name,
                "target_app_kind": target_app_kind,
                "target_app_namespace": target_app_namespace
            }

        # Convert to response format
        app_list = []
        for app_data in apps.values():
            app_info = AppPodsInfoV2(
                app_name=app_data["app_name"],
                app_type=app_data["app_type"],
                label_source=app_data["label_source"],
                app_name_label=app_data.get("app_name_label"),
                app_instance=app_data.get("app_instance"),
                app_version=app_data.get("app_version"),
                app_component=app_data.get("app_component"),
                app_definition_id=app_data.get("app_definition_id"),
                workload_type=app_data.get("workload_type"),
                managed_by=app_data.get("managed_by"),
                custom_resource_name=app_data.get("custom_resource_name"),
                custom_resource_namespace=app_data.get("custom_resource_namespace"),
                custom_resource_priority=app_data.get("custom_resource_priority"),
                custom_resource_phase=app_data.get("custom_resource_phase"),
                custom_resource_decision=app_data.get("custom_resource_decision"),
                target_app_name=app_data.get("target_app_name"),
                target_app_kind=app_data.get("target_app_kind"),
                target_app_namespace=app_data.get("target_app_namespace"),
                pods=app_data["pods"],
                pod_count=len(app_data["pods"]),
                namespaces=sorted(list(app_data["namespaces"]))
            )
            app_list.append(app_info)

            # Count by type
            if app_info.app_type == "standard":
                standard_apps_count += 1
            elif app_info.app_type == "custom":
                custom_apps_count += 1
            elif app_info.app_type == "custom-resource":
                custom_resource_count += 1

        # Sort by app type first, then app name
        app_list.sort(key=lambda x: (x.app_type, x.app_name))

        return AppPodsResponseV2(
            status="success",
            apps=app_list,
            total_apps=len(app_list),
            total_pods=total_pods,
            standard_apps_count=standard_apps_count,
            custom_apps_count=custom_apps_count,
            custom_resource_count=custom_resource_count,
            timestamp=datetime.utcnow().isoformat()
        )

    except Exception as e:
        logger.error(f"Error fetching pods by app (v2): {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch pods by app: {str(e)}")


def _detect_app_from_labels(labels: Dict[str, str]) -> Optional[Dict[str, str]]:
    """
    Detect app name and type from pod labels.
    
    Priority order:
    1. app.kubernetes.io/name (standard Kubernetes label)
    2. app (common standard label)
    3. app-name (custom label for energy-metric-service)
    
    Returns:
        Dict with app_name, app_type ('standard' or 'custom'), and label_source
        None if no app labels found
    """
    # Check for standard Kubernetes labels (preferred)
    if 'app.kubernetes.io/name' in labels:
        return {
            'app_name': labels['app.kubernetes.io/name'],
            'app_type': 'standard',
            'label_source': 'app.kubernetes.io/name'
        }
    
    # Check for common 'app' label (also considered standard)
    if 'app' in labels:
        return {
            'app_name': labels['app'],
            'app_type': 'standard',
            'label_source': 'app'
        }
    
    # Check for custom 'app-name' label (energy-metric-service custom)
    if 'app-name' in labels:
        return {
            'app_name': labels['app-name'],
            'app_type': 'custom',
            'label_source': 'app-name'
        }
    
    # No recognizable app label found
    return None


# ============================================================================
# Custom Resource Endpoints (EnergyAwareOrchestration)
# ============================================================================

@router.get("/custom-resources", response_model=dict)
async def get_custom_resources(
    namespace: Optional[str] = Query(None, description="Filter by specific namespace (if not specified, gets from all namespaces)"),
    priority: Optional[str] = Query(None, description="Filter by priority (Critical, Preferred, Optional)"),
    phase: Optional[str] = Query(None, description="Filter by phase (Pending, Scheduled, Running, Completed, Failed)")
):
    """
    Get all EnergyAwareOrchestration custom resources.

    This endpoint retrieves all energy-aware orchestration custom resources from the cluster.
    
    - **namespace**: Optional filter by specific namespace (if not specified, searches all namespaces)
    - **priority**: Optional filter by priority level (Critical, Preferred, Optional)
    - **phase**: Optional filter by status phase (Pending, Scheduled, Running, Completed, Failed)

    Returns all custom resources with their spec and status information.
    """
    try:
        k8s_service = get_kubernetes_service()
        
        # Get custom resources
        custom_resources = await k8s_service.get_custom_resources(
            namespace=namespace
        )

        # Apply additional filters
        filtered_crs = custom_resources

        if priority:
            filtered_crs = [
                cr for cr in filtered_crs
                if cr.get("spec", {}).get("priority") == priority
            ]

        if phase:
            filtered_crs = [
                cr for cr in filtered_crs
                if cr.get("status", {}) and cr.get("status", {}).get("phase") == phase
            ]

        return {
            "status": "success",
            "namespace": namespace if namespace else "all",
            "custom_resources": filtered_crs,
            "count": len(filtered_crs),
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error fetching custom resources: {e}")
        
        if "Unauthorized" in str(e):
            raise HTTPException(status_code=401, detail="Unauthorized access to Kubernetes API")
        elif "Forbidden" in str(e):
            raise HTTPException(status_code=403, detail="Forbidden access to custom resources")
        else:
            raise HTTPException(status_code=500, detail=f"Failed to fetch custom resources: {str(e)}")