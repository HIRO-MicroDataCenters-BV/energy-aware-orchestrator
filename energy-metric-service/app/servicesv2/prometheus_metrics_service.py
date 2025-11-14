import aiohttp
import asyncio
import time
from typing import List, Dict, Any
from app.schemas.node_metrics import NodeMetricsCreate
from app.repositories.node_metrics_repository import NodeMetricsRepository
from app.db.database import get_async_db
from app.utils.constants import PROMETHEUS_METRICS_URL
import logging


class PrometheusMetricsService:

    def __init__(self):
        self._previous_metrics = {}


    async def fetch_all_container_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Fetch all container and Kepler energy metrics in a single optimized call to Prometheus."""
        
        # All queries we need
        queries = {
            # Container Metrics (cAdvisor)
            # / "/ root will export node level metric" node CPU usage as percentage
            "cpu_utilization": 'sum(rate(container_cpu_usage_seconds_total{id="/"}[5m])) by (instance) * 100',
            "cpu_quota": 'container_spec_cpu_quota{id="/"} / container_spec_cpu_period{id="/"}',
            "memory_utilization": '(sum(container_memory_usage_bytes{id="/"}) by (instance) / sum(container_spec_memory_limit_bytes{id="/"}) by (instance)) * 100',
            "memory_limit": 'sum(container_spec_memory_limit_bytes{id="/"}) by (instance)',

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
                    self._execute_single_query(session, query, metric_name)
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

    async def _execute_single_query(self, session: aiohttp.ClientSession, query: str, metric_name: str) -> Dict[str, Any]:
        """Execute a single Prometheus query."""
        try:
            async with session.get(
                PROMETHEUS_METRICS_URL,
                params={"query": query}
            ) as resp:
                resp.raise_for_status()
                return await resp.json()
        except Exception as e:
            logging.error(f"Error executing query for {metric_name}: {e}")
            raise

    def parse_prometheus_response(self, response_data: Dict[str, Any]) -> Dict[str, float]:
        """Parse Prometheus API response and extract metric values by instance."""
        metrics = {}
        
        if response_data.get("status") == "success" and "data" in response_data:
            result = response_data["data"].get("result", [])
            
            for item in result:
                if "metric" in item and "value" in item:
                    # Extract instance (node) name
                    instance = item["metric"].get("instance", "unknown")
                    # Clean instance name (remove port if present)
                    node_name = instance.split(":")[0] if ":" in instance else instance
                    
                    # Get the metric value (normalization will happen later in scrape_and_transform)
                    value = float(item["value"][1])
                    metrics[node_name] = value
                    
        return metrics
    
    def _normalize_node_name(self, node_name: str) -> str:
        """
        Normalize node names to handle multiple network identities for the same physical node.
        
        Strategy:
        1. Check for explicit NODE_MAPPINGS environment variable first
        2. Auto-detect common single-node environments (minikube, kind, etc.)
        3. Default: treat each unique IP/hostname as separate node
        
        Examples:
        - Explicit: NODE_MAPPINGS="192.168.1.10:worker1,10.244.1.10:worker1"
        - Auto-detect: minikube environment automatically consolidates IPs to "minikube"
        - Default: Each IP treated as separate node (correct for multi-node clusters)
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
        
        This helps avoid configuration for common development setups like minikube, kind, etc.
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

    async def scrape_and_transform(self) -> List[NodeMetricsCreate]:
        """Scrape container and Kepler energy metrics from Prometheus and transform to NodeMetricsCreate objects."""
        results = []
        current_timestamp = int(time.time())  # Unix timestamp for BigInt
        
        try:
            # Fetch all metrics in a single optimized call
            metric_responses = await self.fetch_all_container_metrics()
            
            # Parse all responses
            parsed_metrics = {}
            for metric_name, response in metric_responses.items():
                parsed_metrics[metric_name] = self.parse_prometheus_response(response)
            
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
                    metric_source="prometheus-kepler",
                    
                    # Resource utilization metrics from Prometheus
                    cpu_utilization_percent=round(cpu_utilization, 2),
                    total_cpu_assigned=int(cpu_quota) if cpu_quota else None,
                    machine_cpu_cores=int(machine_cpu_cores) if machine_cpu_cores else None,
                    memory_utilization_percent=round(memory_utilization_percent, 2),
                    memory_utilization_bytes=round(memory_utilization_bytes, 2),
                    memory_assigned_bytes=round(memory_limit_bytes, 2) if memory_limit_bytes else None,
                    machine_memory_total_bytes=round(machine_memory_total, 2) if machine_memory_total else None,
                    
                    # Kepler energy metrics from Prometheus (watts)
                    cpu_core_watts=round(kepler_cpu_core_watts, 4) if kepler_cpu_core_watts is not None else None,
                    cpu_package_watts=round(kepler_cpu_package_watts, 4) if kepler_cpu_package_watts is not None else None,
                    memory_power_watts=round(kepler_memory_watts, 4) if kepler_memory_watts is not None else None,
                    platform_watts=round(kepler_platform_watts, 4) if kepler_platform_watts is not None else None,
                    energy_watts=round(total_energy_watts, 4) if total_energy_watts is not None else None
                ))
                
            logging.info(f"PrometheusMetricsService: Parsed {len(results)} node metrics with energy data from Prometheus.")
            return results
            
        except Exception as e:
            logging.error(f"Error scraping Prometheus container metrics: {e}")
            return []

    async def collect_and_store_metrics(self) -> int:
        """
        Collect container and Kepler energy metrics from Prometheus and store in node_metrics table.
        Returns the number of records stored.
        """
        try:
            # Fetch container and energy metrics
            results = await self.scrape_and_transform()
            
            if not results:
                logging.warning("No node metrics collected from Prometheus")
                return 0
            
            # Store in database
            stored_count = await self._store_metrics(results)
            
            logging.info(f"PrometheusMetricsService: Stored {stored_count} node metrics with energy data to node_metrics table")
            return stored_count
            
        except Exception as e:
            logging.error(f"Error in collect_and_store_metrics: {e}")
            return 0

    async def _store_metrics(self, metrics: List[NodeMetricsCreate]) -> int:
        """Store container metrics in the node_metrics database table."""
        if not metrics:
            return 0
            
        stored_count = 0
        async for session in get_async_db():
            try:
                repository = NodeMetricsRepository(session)
                
                for metric in metrics:
                    try:
                        await repository.create(metric)
                        stored_count += 1
                    except Exception as e:
                        logging.warning(f"Failed to store container metric for {metric.node_name}: {e}")
                        
                await session.commit()
                
            except Exception as e:
                logging.error(f"Database error storing container metrics: {e}")
                await session.rollback()
                
        return stored_count


