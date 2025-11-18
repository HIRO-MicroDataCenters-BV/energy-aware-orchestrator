import aiohttp
import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
from app.schemas.node_metrics import NodeMetricsCreate
from app.utils.constants import PROMETHEUS_QUERY_RANGE_URL
import logging


class PrometheusMetricsServiceV2:

    def __init__(self):
        self._previous_metrics = {}

    async def fetch_all_container_metrics_range(self, hours_back: float = 1.0) -> Dict[str, Dict[str, Any]]:
        """Fetch a recent time window of container and Kepler energy metrics using range queries.
        The window is specified in hours (supports fractional hours).
        """

        # Calculate time range
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours_back)

        # Convert to Unix timestamps
        start_timestamp = int(start_time.timestamp())
        end_timestamp = int(end_time.timestamp())
        step = "1m"  # 1  min resolution

        # Same queries as original service but exclude control-plane nodes and use only K8s built-in cAdvisor
        queries = {
            # Container Metrics (cAdvisor) - exclude control-plane nodes and use only metrics with kubernetes labels
            "cpu_utilization": 'sum(rate(container_cpu_usage_seconds_total{id="/",node_role_kubernetes_io_control_plane!="true",kubernetes_io_hostname!=""}[5m])) by (kubernetes_io_hostname) * 100',
            "cpu_quota": 'container_spec_cpu_quota{id="/",node_role_kubernetes_io_control_plane!="true",kubernetes_io_hostname!=""} / container_spec_cpu_period{id="/",node_role_kubernetes_io_control_plane!="true",kubernetes_io_hostname!=""}',
            "memory_utilization": '(sum(container_memory_usage_bytes{id="/",node_role_kubernetes_io_control_plane!="true",kubernetes_io_hostname!=""}) by (kubernetes_io_hostname) / sum(container_spec_memory_limit_bytes{id="/",node_role_kubernetes_io_control_plane!="true",kubernetes_io_hostname!=""}) by (kubernetes_io_hostname)) * 100',
            "memory_limit": 'sum(container_spec_memory_limit_bytes{id="/",node_role_kubernetes_io_control_plane!="true",kubernetes_io_hostname!=""}) by (kubernetes_io_hostname)',

            # Machine/Node Metrics (Node Exporter)
            "machine_cpu_cores": 'machine_cpu_cores',
            "machine_memory_total": 'machine_memory_bytes',

            # Kepler energy metrics - convert joules/second to watts using rate function
            "kepler_cpu_core_watts": 'rate(kepler_node_core_joules_total[5m])',
            "kepler_cpu_package_watts": 'rate(kepler_node_package_joules_total[5m])',
            "kepler_memory_watts": 'rate(kepler_node_dram_joules_total[5m])',
            "kepler_platform_watts": 'rate(kepler_node_platform_joules_total[5m])',
            "kepler_uncore_watts": 'rate(kepler_node_uncore_joules_total[5m])'
        }

        # Execute all queries concurrently
        async with aiohttp.ClientSession() as session:
            tasks = []
            for metric_name, query in queries.items():
                task = asyncio.create_task(
                    self._execute_range_query(session, query, metric_name, start_timestamp, end_timestamp, step)
                )
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

        # Organize results by metric name
        metric_responses = {}
        for i, (metric_name, _) in enumerate(queries.items()):
            if not isinstance(results[i], Exception):
                metric_responses[metric_name] = results[i]
            else:
                logging.error(f"Error fetching {metric_name}: {results[i]}")
                metric_responses[metric_name] = {"data": {"result": []}}

        return metric_responses

    async def _execute_range_query(self, session: aiohttp.ClientSession, query: str, metric_name: str,
                                 start: int, end: int, step: str) -> Dict[str, Any]:
        """Execute a single Prometheus range query."""
        try:
            params = {
                "query": query,
                "start": start,
                "end": end,
                "step": step
            }

            async with session.get(PROMETHEUS_QUERY_RANGE_URL, params=params) as resp:
                resp.raise_for_status()
                return await resp.json()
        except Exception as e:
            logging.error(f"Error executing range query for {metric_name}: {e}")
            raise

    def parse_prometheus_range_response(self, response_data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """Parse Prometheus range query response and extract time series data by instance."""
        metrics = {}

        if response_data.get("status") == "success" and "data" in response_data:
            result = response_data["data"].get("result", [])

            for item in result:
                if "metric" in item and "values" in item:
                    # Extract instance (node) name - prefer exported_instance for Kepler metrics
                    metric = item["metric"]
                    if "exported_instance" in metric:
                        # Kepler metrics use exported_instance for the actual node name
                        node_name = metric["exported_instance"]
                    elif "kubernetes_io_hostname" in metric:
                        # cAdvisor metrics grouped by kubernetes_io_hostname have it as the key
                        node_name = metric["kubernetes_io_hostname"]
                    else:
                        # Other metrics use instance
                        instance = metric.get("instance", "unknown")
                        # Clean instance name (remove port if present)
                        node_name = instance.split(":")[0] if ":" in instance else instance

                    # Get all time series values
                    values = []
                    for timestamp, value in item["values"]:
                        values.append({
                            "timestamp": int(timestamp),
                            "value": float(value)
                        })

                    metrics[node_name] = values

        return metrics

    def _normalize_node_name(self, node_name: str) -> str:
        """
        Normalize node names to handle multiple network identities for the same physical node.
        Same logic as original service.
        """
        import os

        # Check for environment variable mappings first
        env_mappings = os.getenv('NODE_MAPPINGS', '')
        if env_mappings:
            try:
                mappings = {}
                for mapping in env_mappings.split(','):
                    if ':' in mapping:
                        ip, hostname = mapping.strip().split(':', 1)
                        mappings[ip.strip()] = hostname.strip()

                if node_name in mappings:
                    mapped_name = mappings[node_name]
                    logging.debug(f"Node name mapped via environment: {node_name} -> {mapped_name}")
                    return mapped_name
            except Exception as e:
                logging.warning(f"Failed to parse NODE_MAPPINGS environment variable: {e}")

        # Auto-detect common single-node development environments
        auto_detected = self._auto_detect_single_node_mapping(node_name)
        if auto_detected != node_name:
            logging.debug(f"Node name auto-detected: {node_name} -> {auto_detected}")
            return auto_detected

        # Default: return original name (each IP/hostname is separate node)
        return node_name

    def _auto_detect_single_node_mapping(self, node_name: str) -> str:
        """
        Auto-detect common single-node development environments and map IPs to canonical names.
        Same logic as original service.
        """
        # Minikube detection: if we see "minikube" in the node names, map common IPs to it
        if hasattr(self, '_node_names_seen'):
            node_names = self._node_names_seen
        else:
            # We need to track seen node names across calls to detect patterns
            if not hasattr(self.__class__, '_global_node_names'):
                self.__class__._global_node_names = set()
            self._node_names_seen = self.__class__._global_node_names
            node_names = self._node_names_seen

        node_names.add(node_name)

        # If "minikube" is one of the node names, map ALL IPs to it (single-node environment)
        if "minikube" in node_names:
            # In minikube, all IPs should map to the single node
            if (node_name != "minikube" and  # Don't map minikube to itself
                (node_name.startswith("10.") or  # Any 10.x network
                 node_name.startswith("192.168.") or  # Any 192.168.x network
                 node_name.startswith("172.") or  # Any 172.x network
                 node_name.startswith("127.0.0.1"))):  # Localhost
                return "minikube"

        # If "kind-control-plane" is seen, map IPs to it (for kind clusters)
        if any("kind" in name for name in node_names):
            if (node_name.startswith("172.18.") or  # Kind network
                node_name.startswith("10.244.")):   # Pod network
                # Find the kind node name
                kind_node = next((name for name in node_names if "kind" in name), "kind-control-plane")
                return kind_node

        return node_name

    def get_latest_values_from_range(self, range_data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, float]:
        """Extract the latest values from time series range data."""
        latest_values = {}

        for node_name, time_series in range_data.items():
            if time_series:
                # Get the latest (last) value from the time series
                latest_point = max(time_series, key=lambda x: x["timestamp"])
                latest_values[node_name] = latest_point["value"]
            else:
                latest_values[node_name] = 0.0

        return latest_values

    async def scrape_and_transform_range(self, hours_back: float = 1.0) -> List[NodeMetricsCreate]:
        """Scrape a recent time window of container and Kepler energy metrics from Prometheus and transform to NodeMetricsCreate objects.
        The window is specified in hours (supports fractional hours).
        """
        results = []
        current_timestamp = int(time.time())  # Unix timestamp for BigInt

        try:
            # Fetch all metrics for the specified time range
            metric_responses = await self.fetch_all_container_metrics_range(hours_back)

            # Parse all range responses
            parsed_range_metrics = {}
            for metric_name, response in metric_responses.items():
                parsed_range_metrics[metric_name] = self.parse_prometheus_range_response(response)

            # Extract latest values from range data
            parsed_metrics = {}
            for metric_name, range_data in parsed_range_metrics.items():
                parsed_metrics[metric_name] = self.get_latest_values_from_range(range_data)

            # Get all unique node names (instances) BEFORE normalization
            raw_nodes = set()
            for metrics_dict in parsed_metrics.values():
                raw_nodes.update(metrics_dict.keys())

            # Pre-populate the node names for auto-detection to work correctly
            if not hasattr(self.__class__, '_global_node_names'):
                self.__class__._global_node_names = set()
            self._node_names_seen = self.__class__._global_node_names
            self._node_names_seen.update(raw_nodes)

            # Now normalize all node names
            all_nodes = set()
            for metrics_dict in parsed_metrics.values():
                normalized_dict = {}
                for node_name, value in metrics_dict.items():
                    normalized_name = self._normalize_node_name(node_name)
                    normalized_dict[normalized_name] = value
                # Replace the original dict with normalized names
                metrics_dict.clear()
                metrics_dict.update(normalized_dict)
                all_nodes.update(normalized_dict.keys())

            # Create NodeMetricsCreate objects for each normalized node
            for node_name in all_nodes:
                # Parse CPU metrics
                cpu_utilization = parsed_metrics.get("cpu_utilization", {}).get(node_name, 0.0)
                cpu_quota = parsed_metrics.get("cpu_quota", {}).get(node_name, 0.0)
                machine_cpu_cores = parsed_metrics.get("machine_cpu_cores", {}).get(node_name, 0.0)

                # Parse memory metrics
                memory_utilization_percent = parsed_metrics.get("memory_utilization", {}).get(node_name, 0.0)
                memory_limit_bytes = parsed_metrics.get("memory_limit", {}).get(node_name, 0.0)
                machine_memory_total = parsed_metrics.get("machine_memory_total", {}).get(node_name, 0.0)

                # Calculate memory utilization in bytes
                memory_utilization_bytes = (memory_utilization_percent / 100) * memory_limit_bytes if memory_utilization_percent and memory_limit_bytes else 0.0

                # Parse Kepler energy metrics (watts)
                kepler_cpu_core_watts = parsed_metrics.get("kepler_cpu_core_watts", {}).get(node_name, None)
                kepler_cpu_package_watts = parsed_metrics.get("kepler_cpu_package_watts", {}).get(node_name, None)
                kepler_memory_watts = parsed_metrics.get("kepler_memory_watts", {}).get(node_name, None)
                kepler_platform_watts = parsed_metrics.get("kepler_platform_watts", {}).get(node_name, None)
                kepler_uncore_watts = parsed_metrics.get("kepler_uncore_watts", {}).get(node_name, None)

                # Calculate total energy consumption (sum of components, excluding core watts as it's included in package watts)
                # NOTE: CPU core energy is already included in CPU package energy measurement
                # Total = Package + Memory + Platform + Uncore (NOT including Core)
                energy_components = [kepler_cpu_package_watts, kepler_memory_watts, kepler_platform_watts, kepler_uncore_watts]
                total_energy_watts = sum(w for w in energy_components if w is not None) if any(w is not None for w in energy_components) else None

                results.append(NodeMetricsCreate(
                    timestamp=current_timestamp,
                    node_name=node_name,
                    metric_source="prometheus-kepler-v2",

                    # Resource utilization metrics from Prometheus
                    cpu_utilization_percent=round(cpu_utilization, 2),
                    total_cpu_assigned=int(cpu_quota) if cpu_quota else None,
                    machine_cpu_cores=int(machine_cpu_cores) if machine_cpu_cores else None,
                    memory_utilization_percent=round(memory_utilization_percent, 2),
                    memory_utilization_bytes=round(memory_utilization_bytes, 2),
                    memory_assigned_bytes=round(memory_limit_bytes, 2) if memory_limit_bytes else None,
                    machine_memory_total_bytes=round(machine_memory_total, 2) if machine_memory_total else None,
                    # Kepler energy metrics from Prometheus (watts)
                    energy_watts=round(total_energy_watts, 4) if total_energy_watts is not None else None
                ))

            logging.info(f"PrometheusMetricsServiceV2: Parsed {len(results)} node metrics with energy data from Prometheus (last {hours_back} hour(s)).")
            return results

        except Exception as e:
            logging.error(f"Error scraping Prometheus container metrics range: {e}")
            return []

    async def get_time_series_data(self, hours_back: float = 1.0) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """
        Get full time series data for the specified recent window (in hours, supports fractional) instead of just latest values.
        Returns data organized by metric type and node name.
        """
        try:
            # Fetch all metrics for the specified time range
            metric_responses = await self.fetch_all_container_metrics_range(hours_back)


            # Parse all range responses (this returns full time series)
            parsed_range_metrics = {}
            for metric_name, response in metric_responses.items():
                parsed_range_metrics[metric_name] = self.parse_prometheus_range_response(response)


            # Normalize node names in the time series data
            normalized_metrics = {}
            for metric_name, range_data in parsed_range_metrics.items():
                normalized_range_data = {}
                for node_name, time_series in range_data.items():
                    normalized_name = self._normalize_node_name(node_name)
                    normalized_range_data[normalized_name] = time_series
                normalized_metrics[metric_name] = normalized_range_data


            logging.info(f"PrometheusMetricsServiceV2: Retrieved time series data for last {hours_back} hour(s).")
            return normalized_metrics

        except Exception as e:
            logging.error(f"Error getting time series data: {e}")
            return {}