import aiohttp
import asyncio
import json
import ssl
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging
import os


class KubernetesService:
    """Service to interact with Kubernetes API for various operations including pods, deployments, and resources."""

    def __init__(self):
        # Check if using kubectl proxy (common for local development)
        self.use_kubectl_proxy = os.getenv("USE_KUBECTL_PROXY", "true").lower() == "true"

        if self.use_kubectl_proxy:
            # kubectl proxy setup (for Minikube local testing)
            self.k8s_api_server = "localhost"
            self.k8s_api_port = "8080"
            self.k8s_base_url = f"http://{self.k8s_api_server}:{self.k8s_api_port}"
        else:
            # In-cluster setup
            self.k8s_api_server = os.getenv("KUBERNETES_SERVICE_HOST", "localhost")
            self.k8s_api_port = os.getenv("KUBERNETES_SERVICE_PORT", "8443")
            self.k8s_base_url = f"https://{self.k8s_api_server}:{self.k8s_api_port}"

        self.token_path = "/var/run/secrets/kubernetes.io/serviceaccount/token"
        self.ca_cert_path = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"

    async def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for Kubernetes API."""
        headers = {"Content-Type": "application/json"}

        # Skip authentication when using kubectl proxy
        if self.use_kubectl_proxy:
            logging.debug("Using kubectl proxy - no authentication needed")
            return headers

        # Try to read service account token for in-cluster setup
        try:
            if os.path.exists(self.token_path):
                with open(self.token_path, 'r') as f:
                    token = f.read().strip()
                headers["Authorization"] = f"Bearer {token}"
                logging.debug("Using service account token for K8s authentication")
            else:
                logging.warning("Service account token not found, using unauthenticated request")
        except Exception as e:
            logging.warning(f"Failed to read service account token: {e}")

        return headers

    async def _get_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Create SSL context for Kubernetes API calls."""
        # No SSL needed for kubectl proxy (uses HTTP)
        if self.use_kubectl_proxy:
            return None

        try:
            if os.path.exists(self.ca_cert_path):
                ssl_context = ssl.create_default_context(cafile=self.ca_cert_path)
                logging.debug("Using service account CA certificate")
                return ssl_context
            else:
                logging.warning("CA certificate not found, disabling SSL verification")
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                return ssl_context
        except Exception as e:
            logging.warning(f"Failed to create SSL context: {e}")
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            return ssl_context

    async def get_pods_by_namespace(self, namespace: str = "default") -> List[Dict[str, Any]]:
        """
        Get all pods in a specific namespace.

        Args:
            namespace: Kubernetes namespace (default: "default")

        Returns:
            List of pod information dictionaries
        """
        try:
            headers = await self._get_auth_headers()
            ssl_context = await self._get_ssl_context()

            url = f"{self.k8s_base_url}/api/v1/namespaces/{namespace}/pods"

            connector = aiohttp.TCPConnector(ssl=ssl_context) if ssl_context else aiohttp.TCPConnector()
            timeout = aiohttp.ClientTimeout(total=30)

            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_pods_response(data)
                    elif response.status == 401:
                        logging.error("Unauthorized access to Kubernetes API")
                        raise Exception("Unauthorized access to Kubernetes API")
                    elif response.status == 403:
                        logging.error(f"Forbidden access to namespace '{namespace}'")
                        raise Exception(f"Forbidden access to namespace '{namespace}'")
                    elif response.status == 404:
                        logging.warning(f"Namespace '{namespace}' not found")
                        return []
                    else:
                        error_text = await response.text()
                        logging.error(f"K8s API error {response.status}: {error_text}")
                        raise Exception(f"Kubernetes API error: {response.status}")

        except aiohttp.ClientError as e:
            logging.error(f"Network error accessing Kubernetes API: {e}")
            raise Exception(f"Network error: {str(e)}")
        except Exception as e:
            logging.error(f"Error fetching pods from namespace '{namespace}': {e}")
            raise

    async def get_all_namespaces(self) -> List[Dict[str, Any]]:
        """Get all available namespaces."""
        try:
            headers = await self._get_auth_headers()
            ssl_context = await self._get_ssl_context()

            url = f"{self.k8s_base_url}/api/v1/namespaces"

            connector = aiohttp.TCPConnector(ssl=ssl_context) if ssl_context else aiohttp.TCPConnector()
            timeout = aiohttp.ClientTimeout(total=30)

            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_namespaces_response(data)
                    else:
                        error_text = await response.text()
                        logging.error(f"K8s API error {response.status}: {error_text}")
                        raise Exception(f"Kubernetes API error: {response.status}")

        except Exception as e:
            logging.error(f"Error fetching namespaces: {e}")
            raise

    async def get_pods_all_namespaces(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all pods from all namespaces."""
        try:
            headers = await self._get_auth_headers()
            ssl_context = await self._get_ssl_context()

            url = f"{self.k8s_base_url}/api/v1/pods"

            connector = aiohttp.TCPConnector(ssl=ssl_context) if ssl_context else aiohttp.TCPConnector()
            timeout = aiohttp.ClientTimeout(total=30)

            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_pods_by_namespace(data)
                    else:
                        error_text = await response.text()
                        logging.error(f"K8s API error {response.status}: {error_text}")
                        raise Exception(f"Kubernetes API error: {response.status}")

        except Exception as e:
            logging.error(f"Error fetching pods from all namespaces: {e}")
            raise

    def _parse_pods_response(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse Kubernetes pods API response."""
        pods = []

        for item in data.get("items", []):
            try:
                metadata = item.get("metadata", {})
                spec = item.get("spec", {})
                status = item.get("status", {})

                # Extract container information
                containers = []
                for container in spec.get("containers", []):
                    container_info = {
                        "name": container.get("name"),
                        "image": container.get("image"),
                        "resources": container.get("resources", {})
                    }
                    containers.append(container_info)

                # Extract container status
                container_statuses = []
                for container_status in status.get("containerStatuses", []):
                    status_info = {
                        "name": container_status.get("name"),
                        "ready": container_status.get("ready", False),
                        "restart_count": container_status.get("restartCount", 0),
                        "image": container_status.get("image"),
                        "state": container_status.get("state", {})
                    }
                    container_statuses.append(status_info)

                pod_info = {
                    "name": metadata.get("name"),
                    "namespace": metadata.get("namespace"),
                    "uid": metadata.get("uid"),
                    "node_name": spec.get("nodeName"),
                    "phase": status.get("phase"),
                    "pod_ip": status.get("podIP"),
                    "host_ip": status.get("hostIP"),
                    "start_time": status.get("startTime"),
                    "created_at": metadata.get("creationTimestamp"),
                    "labels": metadata.get("labels", {}),
                    "annotations": metadata.get("annotations", {}),
                    "containers": containers,
                    "container_statuses": container_statuses,
                    "restart_policy": spec.get("restartPolicy"),
                    "service_account": spec.get("serviceAccountName"),
                    "conditions": status.get("conditions", [])
                }

                pods.append(pod_info)

            except Exception as e:
                logging.warning(f"Failed to parse pod item: {e}")
                continue

        return pods

    def _parse_namespaces_response(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse Kubernetes namespaces API response."""
        namespaces = []

        for item in data.get("items", []):
            try:
                metadata = item.get("metadata", {})
                status = item.get("status", {})

                namespace_info = {
                    "name": metadata.get("name"),
                    "uid": metadata.get("uid"),
                    "phase": status.get("phase"),
                    "created_at": metadata.get("creationTimestamp"),
                    "labels": metadata.get("labels", {}),
                    "annotations": metadata.get("annotations", {})
                }

                namespaces.append(namespace_info)

            except Exception as e:
                logging.warning(f"Failed to parse namespace item: {e}")
                continue

        return namespaces

    def _parse_pods_by_namespace(self, data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """Parse pods API response and group by namespace."""
        pods_by_namespace = {}

        all_pods = self._parse_pods_response(data)

        for pod in all_pods:
            namespace = pod.get("namespace", "unknown")
            if namespace not in pods_by_namespace:
                pods_by_namespace[namespace] = []
            pods_by_namespace[namespace].append(pod)

        return pods_by_namespace

    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to Kubernetes API."""
        try:
            headers = await self._get_auth_headers()
            ssl_context = await self._get_ssl_context()

            url = f"{self.k8s_base_url}/version"

            connector = aiohttp.TCPConnector(ssl=ssl_context)
            timeout = aiohttp.ClientTimeout(total=10)

            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        version_data = await response.json()
                        return {
                            "status": "connected",
                            "api_server": self.k8s_base_url,
                            "version": version_data,
                            "authenticated": "Authorization" in headers
                        }
                    else:
                        return {
                            "status": "error",
                            "api_server": self.k8s_base_url,
                            "error": f"HTTP {response.status}",
                            "authenticated": "Authorization" in headers
                        }

        except Exception as e:
            return {
                "status": "error",
                "api_server": self.k8s_base_url,
                "error": str(e),
                "authenticated": False
            }