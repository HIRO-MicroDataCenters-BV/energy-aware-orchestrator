"""
Kubernetes Native Deployment Service
Handles deployment of standard Kubernetes resources (Deployment, Service, ConfigMap, etc.)
"""

import logging
from datetime import datetime
from typing import Dict, Any
import yaml
import json
import aiohttp
import re

from app.servicesv2.kubernetes_service import KubernetesService

logger = logging.getLogger(__name__)


class KubernetesNativeDeploymentService:
    """Service to handle deployment of native Kubernetes resources."""

    def __init__(self):
        self.k8s_service = KubernetesService()

    async def deploy_kubernetes_resources(
        self,
        manifest: str,
        namespace: str = "default",
        custom_labels: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Deploy native Kubernetes resources to the cluster.

        Args:
            manifest: YAML manifest content
            namespace: Target namespace
            custom_labels: Optional custom labels to add to all resources

        Returns:
            Dict with deployment result
        """
        try:
            # Parse the YAML manifest
            try:
                manifest_docs = list(yaml.safe_load_all(manifest))
            except yaml.YAMLError as e:
                logger.error(f"Invalid YAML manifest: {e}")
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

                    logger.info(f"Deploying resource: {kind}/{resource_name} (apiVersion: {api_version})")

                    # Construct the API URL based on resource type
                    api_url = self._construct_api_url(
                        api_version=api_version,
                        kind=kind,
                        namespace=namespace
                    )

                    if not api_url:
                        logger.error(f"Could not construct API URL for {kind} with apiVersion {api_version}")
                        return {
                            "success": False,
                            "error": f"Unsupported resource type: {kind} ({api_version})",
                            "status": "failed"
                        }

                    # Get K8s service auth headers
                    headers = await self.k8s_service._get_auth_headers()

                    # Create the resource
                    url = f"{self.k8s_service.k8s_base_url}{api_url}"

                    logger.info(f"Applying resource to URL: {url}")

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
                                logger.info(f"Successfully created {kind}/{resource_name} in namespace {namespace}")
                            elif response.status == 409:  # Conflict - resource already exists
                                logger.info(f"{kind}/{resource_name} already exists, attempting to update...")

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
                                        logger.info(f"Successfully updated {kind}/{resource_name} in namespace {namespace}")
                                    else:
                                        error_text = await update_response.text()
                                        logger.error(f"Failed to update {kind}/{resource_name}: {error_text}")
                                        return {
                                            "success": False,
                                            "error": f"Failed to update {kind}/{resource_name}: {error_text}",
                                            "status": "failed"
                                        }
                            else:
                                error_text = await response.text()
                                logger.error(f"Failed to create {kind}/{resource_name}: {error_text}")
                                return {
                                    "success": False,
                                    "error": f"Failed to create {kind}/{resource_name}: {error_text}",
                                    "status": "failed"
                                }

                except Exception as e:
                    logger.error(f"Failed to deploy resource: {e}")
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
            logger.error(f"Kubernetes deployment failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "status": "failed"
            }

    def _construct_api_url(
        self,
        api_version: str,
        kind: str,
        namespace: str
    ) -> str:
        """
        Construct the Kubernetes API URL for a resource.

        Args:
            api_version: API version (e.g., 'v1', 'apps/v1')
            kind: Resource kind (e.g., 'Deployment', 'Service')
            namespace: Target namespace

        Returns:
            API URL path or None if cannot be constructed
        """
        try:
            # Construct API URL based on resource type
            if api_version == 'v1':
                if kind.lower() == 'service':
                    api_url = f"/api/v1/namespaces/{namespace}/services"
                elif kind.lower() == 'pod':
                    api_url = f"/api/v1/namespaces/{namespace}/pods"
                elif kind.lower() == 'configmap':
                    api_url = f"/api/v1/namespaces/{namespace}/configmaps"
                elif kind.lower() == 'secret':
                    api_url = f"/api/v1/namespaces/{namespace}/secrets"
                elif kind.lower() == 'persistentvolumeclaim':
                    api_url = f"/api/v1/namespaces/{namespace}/persistentvolumeclaims"
                elif kind.lower() == 'serviceaccount':
                    api_url = f"/api/v1/namespaces/{namespace}/serviceaccounts"
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
                elif kind.lower() == 'replicaset':
                    api_url = f"/apis/apps/v1/namespaces/{namespace}/replicasets"
                else:
                    api_url = f"/apis/apps/v1/namespaces/{namespace}/{kind.lower()}s"
            elif api_version == 'batch/v1':
                if kind.lower() == 'job':
                    api_url = f"/apis/batch/v1/namespaces/{namespace}/jobs"
                elif kind.lower() == 'cronjob':
                    api_url = f"/apis/batch/v1/namespaces/{namespace}/cronjobs"
                else:
                    api_url = f"/apis/batch/v1/namespaces/{namespace}/{kind.lower()}s"
            elif api_version == 'networking.k8s.io/v1':
                if kind.lower() == 'ingress':
                    api_url = f"/apis/networking.k8s.io/v1/namespaces/{namespace}/ingresses"
                elif kind.lower() == 'networkpolicy':
                    api_url = f"/apis/networking.k8s.io/v1/namespaces/{namespace}/networkpolicies"
                else:
                    api_url = f"/apis/networking.k8s.io/v1/namespaces/{namespace}/{kind.lower()}es"
            else:
                # Generic approach for other API versions
                api_group = api_version.split('/')[0] if '/' in api_version else ''
                version = api_version.split('/')[-1]
                if api_group and api_group != 'v1':
                    api_url = f"/apis/{api_version}/namespaces/{namespace}/{kind.lower()}s"
                else:
                    api_url = f"/api/{version}/namespaces/{namespace}/{kind.lower()}s"

            logger.debug(f"Constructed API URL: {api_url} for {kind} ({api_version})")
            return api_url

        except Exception as e:
            logger.error(f"Error constructing API URL: {e}")
            return None

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

            logger.debug(f"Injected custom labels into {resource_doc.get('kind', 'Unknown')}/{resource_doc.get('metadata', {}).get('name', 'unnamed')}")

        except Exception as e:
            logger.warning(f"Failed to inject custom labels into resource: {e}")

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
                logger.debug(f"Sanitized label value: '{value}' -> '{sanitized_value}'")

        return sanitized
