"""
Deployment service for managing Kubernetes deployments with energy constraints.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession

from app.servicesv2.kubernetes_pods_service import KubernetesPodService
from app.servicesv2.prometheus_metrics_service_v2 import PrometheusMetricsServiceV2
from app.servicesv2.energy_availability_service import EnergyAvailabilityService
from app.services.energy_forecasting_service import EnergyForecastingService


class DeploymentStatus(Enum):
    CREATED = "Created"
    SCHEDULED = "Scheduled"
    DEPLOYED = "Deployed"
    FAILED = "Failed"


class KubernetesDeploymentService:
    """Service to manage Kubernetes deployments with energy awareness."""

    def __init__(self, db_session: Optional[AsyncSession] = None):
        self.k8s_service = KubernetesPodService()
        self.metrics_service = PrometheusMetricsServiceV2()
        self.energy_availability_service = EnergyAvailabilityService(db_session)
        self.forecasting_service = None
        self._forecasting_service_initialized = False

    def _init_forecasting_service(self):
        """Initialize forecasting service lazily to avoid async context issues."""
        if not self._forecasting_service_initialized:
            try:
                # Temporarily disable forecasting service to isolate the issue
                # self.forecasting_service = EnergyForecastingService.get_instance()
                self.forecasting_service = None
                logging.info("Forecasting service temporarily disabled")
            except Exception as e:
                logging.warning(f"Energy forecasting service not available: {e}")
            self._forecasting_service_initialized = True

    async def check_energy_availability(
        self,
        required_energy_watts: float = None,
        db_session: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Check if cluster has sufficient energy for deployment using EnergyAvailabilityService.

        This method now uses the current time slot's available energy from EnergyAvailabilityRepository
        and subtracts the current K8s container energy consumption to get actual available energy.

        Args:
            required_energy_watts: Estimated energy requirement for the deployment
            db_session: Database session for accessing energy availability data

        Returns:
            Dict with availability status and current energy metrics
        """
        try:
            # Default required energy if not specified
            if required_energy_watts is None:
                required_energy_watts = 50.0  # Default estimate for small deployment

            # Use EnergyAvailabilityService to check energy sufficiency
            energy_check = await self.energy_availability_service.check_energy_sufficient_for_deployment(
                required_energy_watts=required_energy_watts,
                db_session=db_session
            )

            # Return the result from the energy availability service
            return energy_check

        except Exception as e:
            logging.error(f"Error checking energy availability: {e}")
            return {
                "sufficient": False,
                "reason": f"Error checking energy: {str(e)}",
                "total_available_watts": None,
                "slot_energy_watts": None,
                "current_consumption_watts": None
            }

    async def deploy_to_kubernetes(self, manifest: str, namespace: str = "default", custom_labels: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Deploy a Kubernetes manifest to the cluster.

        Args:
            manifest: YAML manifest content
            namespace: Target namespace
            custom_labels: Optional custom labels to add to all resources

        Returns:
            Dict with deployment result
        """
        try:
            import yaml
            import json
            import aiohttp

            # Parse the YAML manifest
            try:
                manifest_docs = list(yaml.safe_load_all(manifest))
            except yaml.YAMLError as e:
                return {
                    "success": False,
                    "error": f"Invalid YAML manifest: {str(e)}",
                    "status": "failed"
                }

            deployed_resources = []

            for doc in manifest_docs:
                if not doc:
                    continue

                try:
                    # Inject custom labels if provided
                    if custom_labels:
                        self._inject_custom_labels(doc, custom_labels)

                    # Extract resource information
                    api_version = doc.get('apiVersion', '')
                    kind = doc.get('kind', '')
                    metadata = doc.get('metadata', {})
                    resource_name = metadata.get('name', '')

                    # Construct the API URL based on resource type
                    if api_version == 'v1':
                        if kind.lower() == 'service':
                            api_url = f"/api/v1/namespaces/{namespace}/services"
                        elif kind.lower() == 'pod':
                            api_url = f"/api/v1/namespaces/{namespace}/pods"
                        elif kind.lower() == 'configmap':
                            api_url = f"/api/v1/namespaces/{namespace}/configmaps"
                        else:
                            # Fallback for other v1 resources
                            api_url = f"/api/v1/namespaces/{namespace}/{kind.lower()}s"
                    elif api_version == 'apps/v1':
                        if kind.lower() == 'deployment':
                            api_url = f"/apis/apps/v1/namespaces/{namespace}/deployments"
                        elif kind.lower() == 'daemonset':
                            api_url = f"/apis/apps/v1/namespaces/{namespace}/daemonsets"
                        elif kind.lower() == 'statefulset':
                            api_url = f"/apis/apps/v1/namespaces/{namespace}/statefulsets"
                        else:
                            api_url = f"/apis/apps/v1/namespaces/{namespace}/{kind.lower()}s"
                    else:
                        # Generic approach for other API versions
                        api_group = api_version.split('/')[0] if '/' in api_version else ''
                        version = api_version.split('/')[-1]
                        if api_group and api_group != 'v1':
                            api_url = f"/apis/{api_version}/namespaces/{namespace}/{kind.lower()}s"
                        else:
                            api_url = f"/api/{version}/namespaces/{namespace}/{kind.lower()}s"

                    # Get K8s service auth headers
                    headers = await self.k8s_service._get_auth_headers()

                    # Create the resource
                    url = f"{self.k8s_service.k8s_base_url}{api_url}"

                    # Use default SSL verification (can be configured later)
                    connector = aiohttp.TCPConnector(ssl=False)  # Disable SSL verification for now
                    timeout = aiohttp.ClientTimeout(total=30)

                    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                        # First, try to create the resource
                        async with session.post(url, headers=headers, json=doc) as response:
                            if response.status in [200, 201]:
                                result = await response.json()
                                deployed_resources.append({
                                    "kind": kind,
                                    "name": resource_name,
                                    "namespace": namespace,
                                    "status": "created"
                                })
                                logging.info(f"Successfully created {kind}/{resource_name} in namespace {namespace}")
                            elif response.status == 409:  # Conflict - resource already exists
                                logging.info(f"{kind}/{resource_name} already exists, attempting to update...")

                                # Try to update the existing resource
                                update_url = f"{url}/{resource_name}"
                                async with session.put(update_url, headers=headers, json=doc) as update_response:
                                    if update_response.status in [200, 201]:
                                        result = await update_response.json()
                                        deployed_resources.append({
                                            "kind": kind,
                                            "name": resource_name,
                                            "namespace": namespace,
                                            "status": "updated"
                                        })
                                        logging.info(f"Successfully updated {kind}/{resource_name} in namespace {namespace}")
                                    else:
                                        error_text = await update_response.text()
                                        return {
                                            "success": False,
                                            "error": f"Failed to update {kind}/{resource_name}: {error_text}",
                                            "status": "failed"
                                        }
                            else:
                                error_text = await response.text()
                                return {
                                    "success": False,
                                    "error": f"Failed to create {kind}/{resource_name}: {error_text}",
                                    "status": "failed"
                                }

                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Failed to deploy resource: {str(e)}",
                        "status": "failed"
                    }

            # Return success with deployed resources
            return {
                "success": True,
                "namespace": namespace,
                "deployed_resources": deployed_resources,
                "deployed_at": datetime.utcnow().isoformat(),
                "status": "deployed"
            }

        except Exception as e:
            logging.error(f"Deployment failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "status": "failed"
            }

    async def validate_manifest(self, manifest: str) -> Dict[str, Any]:
        """
        Validate Kubernetes manifest before deployment.

        Args:
            manifest: YAML manifest content

        Returns:
            Dict with validation result
        """
        try:
            import yaml

            # Basic YAML validation
            try:
                yaml_docs = list(yaml.safe_load_all(manifest))
            except yaml.YAMLError as e:
                return {
                    "valid": False,
                    "error": f"Invalid YAML: {str(e)}"
                }

            # Basic Kubernetes manifest validation
            errors = []
            warnings = []

            for doc in yaml_docs:
                if not doc:
                    continue

                # Check required fields
                if 'apiVersion' not in doc:
                    errors.append("Missing 'apiVersion' field")
                if 'kind' not in doc:
                    errors.append("Missing 'kind' field")
                if 'metadata' not in doc:
                    errors.append("Missing 'metadata' field")
                elif 'name' not in doc.get('metadata', {}):
                    errors.append("Missing 'metadata.name' field")

                # Check for common issues
                if doc.get('kind') == 'Deployment':
                    spec = doc.get('spec', {})
                    if 'selector' not in spec:
                        errors.append("Deployment missing 'spec.selector'")
                    if 'template' not in spec:
                        errors.append("Deployment missing 'spec.template'")

            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "document_count": len([doc for doc in yaml_docs if doc])
            }

        except Exception as e:
            return {
                "valid": False,
                "error": f"Validation error: {str(e)}"
            }

    async def estimate_deployment_energy(self, manifest: str) -> float:
        """
        Estimate energy consumption for a deployment based on resource requests.

        Args:
            manifest: YAML manifest content

        Returns:
            Estimated energy consumption in watts
        """
        try:
            import yaml

            total_estimated_watts = 0.0

            yaml_docs = list(yaml.safe_load_all(manifest))

            for doc in yaml_docs:
                if not doc or doc.get('kind') != 'Deployment':
                    continue

                spec = doc.get('spec', {})
                template = spec.get('template', {})
                pod_spec = template.get('spec', {})
                containers = pod_spec.get('containers', [])

                replicas = spec.get('replicas', 1)

                for container in containers:
                    resources = container.get('resources', {})
                    requests = resources.get('requests', {})

                    # Estimate based on CPU and memory requests
                    cpu_request = requests.get('cpu', '100m')
                    memory_request = requests.get('memory', '128Mi')

                    # Parse CPU (convert millicores to cores)
                    if cpu_request.endswith('m'):
                        cpu_cores = float(cpu_request[:-1]) / 1000
                    else:
                        cpu_cores = float(cpu_request)

                    # Parse memory (convert to GB)
                    memory_gb = 0.128  # default 128Mi
                    if memory_request.endswith('Mi'):
                        memory_gb = float(memory_request[:-2]) / 1024
                    elif memory_request.endswith('Gi'):
                        memory_gb = float(memory_request[:-2])

                    # Rough estimation:
                    # ~20W per CPU core + ~5W per GB RAM
                    container_watts = (cpu_cores * 20) + (memory_gb * 5)
                    total_estimated_watts += container_watts * replicas

            # Minimum estimate for any deployment
            return max(total_estimated_watts, 10.0)

        except Exception as e:
            logging.warning(f"Could not estimate energy consumption: {e}")
            return 50.0  # Default estimate

    async def get_cluster_capacity(self) -> Dict[str, Any]:
        """Get current cluster capacity and utilization."""
        try:
            # Get all pods to understand current utilization
            pods_by_namespace = await self.k8s_service.get_pods_all_namespaces()

            total_pods = sum(len(pods) for pods in pods_by_namespace.values())
            running_pods = 0

            for namespace_pods in pods_by_namespace.values():
                running_pods += sum(1 for pod in namespace_pods if pod.get('phase') == 'Running')

            # Get current energy metrics
            energy_check = await self.check_energy_availability()

            return {
                "total_namespaces": len(pods_by_namespace),
                "total_pods": total_pods,
                "running_pods": running_pods,
                "current_energy_watts": energy_check.get('current_energy_watts'),
                "available_energy_watts": energy_check.get('available_capacity_watts'),
                "energy_utilization_percent": round(
                    (energy_check.get('current_energy_watts', 0) / 1000) * 100, 2
                ) if energy_check.get('current_energy_watts') else 0
            }

        except Exception as e:
            logging.error(f"Error getting cluster capacity: {e}")
            return {
                "total_namespaces": 0,
                "total_pods": 0,
                "running_pods": 0,
                "current_energy_watts": 0,
                "available_energy_watts": 0,
                "energy_utilization_percent": 0,
                "error": str(e)
            }

    async def check_deployment_exists(self, deployment_name: str, namespace: str = "default") -> bool:
        """
        Check if a deployment exists in Kubernetes cluster.

        Args:
            deployment_name: Name of the deployment
            namespace: Kubernetes namespace

        Returns:
            True if deployment exists, False otherwise
        """
        try:
            # Get deployments from the specified namespace
            deployments = await self.k8s_service.get_pods_by_namespace(namespace)

            # Check if any pod belongs to the deployment
            for pod in deployments:
                pod_name = pod.get('name', '')
                # Check if pod name starts with deployment name (K8s convention)
                if pod_name.startswith(f"{deployment_name}-"):
                    return True

            return False

        except Exception as e:
            logging.error(f"Error checking if deployment {deployment_name} exists in namespace {namespace}: {e}")
            # If we can't check, assume it might exist to be safe
            return True

    def _inject_custom_labels(self, resource_doc: Dict[str, Any], custom_labels: Dict[str, str]) -> None:
        """
        Inject custom labels into a Kubernetes resource document.

        Args:
            resource_doc: The Kubernetes resource document (dict)
            custom_labels: Custom labels to inject
        """
        try:
            # Ensure metadata exists
            if 'metadata' not in resource_doc:
                resource_doc['metadata'] = {}

            # Ensure labels exists in metadata
            if 'labels' not in resource_doc['metadata']:
                resource_doc['metadata']['labels'] = {}

            # Sanitize and add custom labels to metadata
            sanitized_labels = self._sanitize_labels(custom_labels)
            resource_doc['metadata']['labels'].update(sanitized_labels)

            # For Deployments, also add labels to pod template metadata
            if resource_doc.get('kind') == 'Deployment':
                spec = resource_doc.get('spec', {})
                template = spec.get('template', {})

                # Ensure template metadata exists
                if 'metadata' not in template:
                    template['metadata'] = {}
                    spec['template'] = template

                # Ensure template labels exist
                if 'labels' not in template['metadata']:
                    template['metadata']['labels'] = {}

                # Add sanitized custom labels to pod template
                template['metadata']['labels'].update(sanitized_labels)

            logging.debug(f"Injected custom labels {custom_labels} into {resource_doc.get('kind', 'Unknown')}/{resource_doc.get('metadata', {}).get('name', 'unnamed')}")

        except Exception as e:
            logging.warning(f"Failed to inject custom labels into resource: {e}")

    def _sanitize_labels(self, labels: Dict[str, str]) -> Dict[str, str]:
        """
        Sanitize label values to comply with Kubernetes naming rules.

        Kubernetes label values must:
        - Be empty or consist of alphanumeric characters, '-', '_', or '.'
        - Start and end with an alphanumeric character
        - Be at most 63 characters long

        Args:
            labels: Dictionary of labels to sanitize

        Returns:
            Dictionary of sanitized labels
        """
        import re

        sanitized = {}

        for key, value in labels.items():
            if not value:
                sanitized[key] = value
                continue

            # Replace spaces and other invalid characters with hyphens
            sanitized_value = re.sub(r'[^a-zA-Z0-9\-_.]', '-', str(value))

            # Remove leading and trailing non-alphanumeric characters
            sanitized_value = re.sub(r'^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$', '', sanitized_value)

            # Ensure it doesn't start or end with hyphen, underscore, or dot
            sanitized_value = re.sub(r'^[-_.]+|[-_.]+$', '', sanitized_value)

            # If empty after sanitization, use a default value
            if not sanitized_value:
                sanitized_value = 'sanitized-value'

            # Truncate to 63 characters if necessary
            if len(sanitized_value) > 63:
                sanitized_value = sanitized_value[:63]
                # Ensure it doesn't end with a special character after truncation
                sanitized_value = re.sub(r'[-_.]+$', '', sanitized_value)

            sanitized[key] = sanitized_value

            if sanitized_value != value:
                logging.debug(f"Sanitized label value: '{value}' -> '{sanitized_value}'")

        return sanitized