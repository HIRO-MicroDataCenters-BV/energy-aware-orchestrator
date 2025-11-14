import aiohttp
import re
from datetime import datetime
from typing import List, Dict, Any
from app.schemas.node_metrics import NodePowerMetricsCreate
import logging

class CadvisorNodeMetricsService:
    CADVISOR_METRICS_URL = "http://localhost:8080/metrics"

    def __init__(self):
        self._previous_metrics = {}

    async def fetch_metrics(self) -> str:
        """Fetch metrics from cAdvisor Prometheus endpoint."""
        async with aiohttp.ClientSession() as session:
            async with session.get(self.CADVISOR_METRICS_URL) as resp:
                resp.raise_for_status()
                return await resp.text()

    def parse_metrics(self, metrics_text: str) -> List[NodePowerMetricsCreate]:
        """
        Parse cAdvisor Prometheus metrics and extract node-level CPU and memory usage.
        Uses root container metrics (id="/") as node-level metrics.
        Returns a list of NodePowerMetricsCreate objects.
        """
        node_metrics = {}

        # Node-level metrics patterns from cAdvisor root container (id="/")
        metric_patterns = {
            'cpu_usage_seconds_total': r'container_cpu_usage_seconds_total\{cpu="total",id="/",([^}]*)\} ([0-9.eE+-]+)',
            'memory_usage_bytes': r'container_memory_usage_bytes\{id="/",([^}]*)\} ([0-9.eE+-]+)',
        }

        # Get total memory from machine metrics
        machine_memory_pattern = r'machine_memory_bytes\{([^}]*)\} ([0-9.eE+-]+)'
        machine_memory_match = re.search(machine_memory_pattern, metrics_text)
        total_memory = None
        if machine_memory_match:
            total_memory = float(machine_memory_match.group(2))

        # Extract metrics for each pattern
        for metric_type, pattern in metric_patterns.items():
            for match in re.finditer(pattern, metrics_text):
                labels_str, value = match.groups()
                labels = dict(re.findall(r'(\w+)="([^"]*)"', labels_str))

                # For node metrics, we'll try to match Kepler's node naming
                # Check for various possible node identifiers
                node_name = (labels.get("hostname") or
                             labels.get("instance") or
                             labels.get("node") or
                             "minikube")  # Default to minikube to match Kepler

                # Store the metric value and labels
                if node_name not in node_metrics:
                    node_metrics[node_name] = {'labels': labels, 'metrics': {}}

                node_metrics[node_name]['metrics'][metric_type] = float(value)

                # Add total memory for memory utilization calculation
                if total_memory:
                    node_metrics[node_name]['metrics']['memory_total_bytes'] = total_memory

        # Convert to NodePowerMetricsCreate objects
        results = []
        current_time = datetime.utcnow()

        for node_name, data in node_metrics.items():
            labels = data['labels']
            metrics = data['metrics']

            # Get previous metrics for this node if they exist
            previous_data = self._previous_metrics.get(node_name)

            # Calculate CPU utilization percentage
            cpu_utilization_percent = self._calculate_cpu_utilization(metrics, previous_data)

            # Calculate memory utilization percentage
            memory_utilization_percent = self._calculate_memory_utilization(metrics)

            # Get memory usage in bytes
            memory_usage_bytes = int(metrics.get('memory_usage_bytes', 0))

            # Store current metrics for next calculation
            self._previous_metrics[node_name] = {
                'timestamp': current_time,
                'metrics': metrics.copy()
            }

            results.append(NodePowerMetricsCreate(
                timestamp=int(current_time.timestamp()),
                node_name=node_name,
                metric_source="cadvisor",
                cpu_core_watts=None,  # Not available in cAdvisor
                cpu_package_watts=None,  # Not available in cAdvisor  
                memory_power_watts=None,  # Not available in cAdvisor
                platform_watts=None,  # Not available in cAdvisor
                cpu_utilization_percent=cpu_utilization_percent,
                memory_utilization_percent=memory_utilization_percent,
            ))

        logging.info(f"CadvisorNodeMetricsService: Parsed {len(results)} node metrics from cAdvisor.")
        return results

    def _calculate_cpu_utilization(self, current_metrics: Dict[str, float], previous_data: Dict[str, Any]) -> float:
        """
        Calculate CPU utilization percentage from machine_cpu_usage_seconds_total.
        CPU utilization = (delta_cpu_seconds / delta_time_seconds) * 100
        """
        cpu_usage_total = current_metrics.get('cpu_usage_seconds_total', 0)

        if not previous_data or 'cpu_usage_seconds_total' not in previous_data['metrics']:
            logging.debug(f"No previous CPU data - first measurement. Current: {cpu_usage_total}")
            return 0.0

        previous_cpu_usage = previous_data['metrics']['cpu_usage_seconds_total']
        time_diff = (datetime.utcnow() - previous_data['timestamp']).total_seconds()

        if time_diff > 0:
            cpu_usage_diff = cpu_usage_total - previous_cpu_usage
            cpu_utilization = (cpu_usage_diff / time_diff) * 100

            logging.info(f"Node CPU calculation: current={cpu_usage_total:.6f}, previous={previous_cpu_usage:.6f}, "
                         f"diff={cpu_usage_diff:.6f}, time={time_diff:.2f}s, utilization={cpu_utilization:.2f}%")

            return max(0.0, min(100.0, cpu_utilization))  # Clamp between 0-100%

        return 0.0

    def _calculate_memory_utilization(self, current_metrics: Dict[str, float]) -> float:
        """
        Calculate memory utilization percentage from memory usage and total.
        Memory utilization = (memory_usage_bytes / memory_total_bytes) * 100
        """
        memory_usage = current_metrics.get('memory_usage_bytes', 0)
        memory_total = current_metrics.get('memory_total_bytes', 0)

        if memory_total > 0:
            memory_utilization = (memory_usage / memory_total) * 100
            logging.info(f"Node Memory calculation: usage={memory_usage}, total={memory_total}, "
                         f"utilization={memory_utilization:.2f}%")
            return max(0.0, min(100.0, memory_utilization))  # Clamp between 0-100%

        return 0.0

    async def scrape_and_transform(self) -> List[NodePowerMetricsCreate]:
        """Scrape cAdvisor node metrics and transform to NodePowerMetricsCreate objects."""
        metrics_text = await self.fetch_metrics()
        logging.info("First 2 lines of cAdvisor node metrics:\n" + '\n'.join(metrics_text.splitlines()[:2]))
        return self.parse_metrics(metrics_text)
