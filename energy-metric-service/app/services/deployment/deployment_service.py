"""
Deployment service for managing Kubernetes deployments with energy constraints.
"""

import logging
from typing import Dict, Any, Optional
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.kubernetes_service import KubernetesService
from app.services.prometheus_metrics_service_v2 import PrometheusMetricsServiceV2
from app.services.energy_availability_service import EnergyAvailabilityService
from app.services.deployment.kubernetes_native_deployment_service import KubernetesNativeDeploymentService
from app.services.deployment.helm_deployment_service import HelmDeploymentService
from app.services.deployment.custom_resource_deployment_service import CustomResourceDeploymentService


class DeploymentStatus(Enum):
    CREATED = "Created"
    SCHEDULED = "Scheduled"
    DEPLOYED = "Deployed"
    FAILED = "Failed"


class DeploymentHelperService:
    """
    Helper service for deployment operations.

    Provides common utilities for deployments including:
    - Energy availability checking
    - Deployment orchestration and delegation
    - Manifest validation
    - Energy estimation
    - Cluster capacity monitoring
    """

    def __init__(self, db_session: Optional[AsyncSession] = None):
        self.k8s_service = KubernetesService()
        self.metrics_service = PrometheusMetricsServiceV2()
        self.energy_availability_service = EnergyAvailabilityService(db_session)
        self.forecasting_service = None
        self._forecasting_service_initialized = False

        # Specialized deployment services
        self.kubernetes_native_service = KubernetesNativeDeploymentService()
        self.helm_service = HelmDeploymentService()
        self.custom_resource_service = CustomResourceDeploymentService()

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
