"""
Custom Resource Deployment Service
Handles direct deployment of custom Kubernetes resources (CRDs)
"""

import logging
from datetime import datetime
from typing import Dict, Any
import yaml
import aiohttp
import re

from app.servicesv2.kubernetes_service import KubernetesService

logger = logging.getLogger(__name__)


class CustomResourceDeploymentService:
    """Service to handle deployment of custom Kubernetes resources."""

    def __init__(self):
        self.k8s_service = KubernetesService()

    async def deploy_custom_resource(
        self,
        manifest: str,
        namespace: str = "default",
        custom_labels: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Deploy a custom Kubernetes resource directly to the cluster.

        Args:
            manifest: YAML manifest content for custom resource
            namespace: Target namespace
            custom_labels: Optional custom labels to add to the resource

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

                    logger.info(f"Deploying custom resource: {kind}/{resource_name} (apiVersion: {api_version})")

                    # Construct the API URL for custom resources
                    api_url = self._construct_custom_resource_url(
                        api_version=api_version,
                        kind=kind,
                        namespace=namespace
                    )

                    if not api_url:
                        logger.error(f"Could not construct API URL for {kind} with apiVersion {api_version}")
                        return {
                            "success": False,
                            "error": f"Unsupported custom resource type: {kind} ({api_version})",
                            "status": "failed"
                        }

                    # Get K8s service auth headers
                    headers = await self.k8s_service._get_auth_headers()

                    # Create the resource
                    url = f"{self.k8s_service.k8s_base_url}{api_url}"

                    logger.info(f"Applying custom resource to URL: {url}")

                    # Use default SSL verification (can be configured later)
                    connector = aiohttp.TCPConnector(ssl=False)  # Disable SSL verification for now
                    timeout = aiohttp.ClientTimeout(total=30)

                    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                        # Try to create the resource
                        async with session.post(url, headers=headers, json=doc) as response:
                            if response.status in [200, 201]:
                                result = await response.json()
                                deployed_resources.append({
                                    "kind": kind,
                                    "name": resource_name,
                                    "namespace": namespace,
                                    "apiVersion": api_version,
                                    "status": "created"
                                })
                                logger.info(f"Successfully created custom resource {kind}/{resource_name} in namespace {namespace}")
                            elif response.status == 409:  # Conflict - resource already exists
                                logger.info(f"Custom resource {kind}/{resource_name} already exists, attempting to update...")

                                # Try to update the existing resource
                                update_url = f"{url}/{resource_name}"
                                async with session.put(update_url, headers=headers, json=doc) as update_response:
                                    if update_response.status in [200, 201]:
                                        result = await update_response.json()
                                        deployed_resources.append({
                                            "kind": kind,
                                            "name": resource_name,
                                            "namespace": namespace,
                                            "apiVersion": api_version,
                                            "status": "updated"
                                        })
                                        logger.info(f"Successfully updated custom resource {kind}/{resource_name} in namespace {namespace}")
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
                    logger.error(f"Failed to deploy custom resource: {e}")
                    return {
                        "success": False,
                        "error": f"Failed to deploy custom resource: {str(e)}",
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
            logger.error(f"Custom resource deployment failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "status": "failed"
            }

    def _construct_custom_resource_url(
        self,
        api_version: str,
        kind: str,
        namespace: str
    ) -> str:
        """
        Construct the Kubernetes API URL for a custom resource.

        Args:
            api_version: API version (e.g., 'orchestrator.hiro.com/v1' or 'eas.hiro.io/v1')
            kind: Resource kind (e.g., 'EnergyAwareOrchestration')
            namespace: Target namespace

        Returns:
            API URL path or None if cannot be constructed
        """
        try:
            # Convert kind to lowercase plural form
            # Handle common pluralization patterns
            resource_plural = self._pluralize_resource_name(kind)

            # Parse the API version
            if '/' in api_version:
                # Custom API group (e.g., 'orchestrator.hiro.com/v1' or 'eas.hiro.io/v1')
                api_url = f"/apis/{api_version}/namespaces/{namespace}/{resource_plural}"
            else:
                # Core API (e.g., 'v1')
                api_url = f"/api/{api_version}/namespaces/{namespace}/{resource_plural}"

            logger.debug(f"Constructed API URL: {api_url} for {kind} ({api_version})")
            logger.info(f"Custom resource URL: {api_url}")
            return api_url

        except Exception as e:
            logger.error(f"Error constructing custom resource URL: {e}")
            return None

    def _pluralize_resource_name(self, kind: str) -> str:
        """
        Pluralize a Kubernetes resource kind name.

        Handles common patterns:
        - Words ending in 'y' (e.g., Policy -> policies)
        - Words ending in 's', 'x', 'ch', 'sh' (e.g., Status -> statuses)
        - Default: add 's'

        Args:
            kind: Resource kind name

        Returns:
            Pluralized lowercase resource name
        """
        kind_lower = kind.lower()

        # Already plural
        if kind_lower.endswith('s') or kind_lower.endswith('data') or kind_lower.endswith('metadata'):
            return kind_lower

        # Words ending in 'y' (preceded by consonant) -> 'ies'
        if kind_lower.endswith('y') and len(kind_lower) > 1:
            if kind_lower[-2] not in 'aeiou':
                return kind_lower[:-1] + 'ies'

        # Words ending in 's', 'x', 'z', 'ch', 'sh' -> add 'es'
        if (kind_lower.endswith(('s', 'x', 'z')) or
            kind_lower.endswith('ch') or
            kind_lower.endswith('sh')):
            return kind_lower + 'es'

        # Default: add 's'
        return kind_lower + 's'

    def _inject_custom_labels(self, resource_doc: Dict[str, Any], custom_labels: Dict[str, str]) -> None:
        """
        Inject custom labels into a custom resource document.

        Args:
            resource_doc: The custom resource document (dict)
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

            logger.debug(f"Injected custom labels into {resource_doc.get('kind', 'Unknown')}/{resource_doc.get('metadata', {}).get('name', 'unnamed')}")

        except Exception as e:
            logger.warning(f"Failed to inject custom labels into custom resource: {e}")

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

    async def validate_custom_resource(self, manifest: str) -> Dict[str, Any]:
        """
        Validate custom resource manifest before deployment.

        Args:
            manifest: YAML manifest content

        Returns:
            Dict with validation result
        """
        try:
            # Basic YAML validation
            try:
                yaml_docs = list(yaml.safe_load_all(manifest))
            except yaml.YAMLError as e:
                return {
                    "valid": False,
                    "error": f"Invalid YAML: {str(e)}"
                }

            # Basic custom resource validation
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

                # Check if it looks like a custom resource (has custom API group)
                api_version = doc.get('apiVersion', '')
                if '/' not in api_version or api_version.startswith('v1') or api_version.startswith('apps/'):
                    warnings.append(f"Resource {doc.get('kind')} may not be a custom resource (apiVersion: {api_version})")

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
