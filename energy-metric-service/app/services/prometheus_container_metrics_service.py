import aiohttp
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Tuple
from app.schemas.container_power_metrics import ContainerPowerMetricsCreate
from app.repositories.container_power_metrics import ContainerPowerMetricsRepository
from app.db.database import get_async_db
from app.utils.constants import PROMETHEUS_METRICS_URL
import logging

ContainerKey = Tuple[str, str, str]  # (pod_name, namespace, container_name)


class PrometheusContainerMetricsService:
    """
    Per-container equivalent of PrometheusMetricsService: queries Kepler
    (energy) and cAdvisor (utilization) through Prometheus - rather than
    scraping the Kepler/cAdvisor DaemonSets directly, which only ever
    reaches one node's pod per Kubernetes Service - keyed by
    (pod_name, namespace, container_name) instead of node instance.

    cAdvisor utilization is read from job="kubernetes-nodes-cadvisor" (the
    built-in kubelet-proxied scrape), not the custom "cadvisor" job: the
    kubelet proxy enriches results with clean pod/namespace/container
    labels, while scraping the DaemonSet's own :8080/metrics directly only
    yields raw cgroup paths that would need manual pod-UID correlation.
    """

    async def fetch_all_metrics(self) -> Dict[str, Dict[ContainerKey, float]]:
        queries = {
            # Kepler container energy (joules/sec = watts via rate), summed
            # across dynamic+idle mode.
            "kepler_core_watts": 'sum(rate(kepler_container_core_joules_total[5m])) by (pod_name, container_namespace, container_name)',
            "kepler_package_watts": 'sum(rate(kepler_container_package_joules_total[5m])) by (pod_name, container_namespace, container_name)',
            "kepler_dram_watts": 'sum(rate(kepler_container_dram_joules_total[5m])) by (pod_name, container_namespace, container_name)',
            "kepler_platform_watts": 'sum(rate(kepler_container_platform_joules_total[5m])) by (pod_name, container_namespace, container_name)',
            "kepler_other_watts": 'sum(rate(kepler_container_other_joules_total[5m])) by (pod_name, container_namespace, container_name)',

            # cAdvisor utilization. cpu_cores_used follows the same
            # convention as the existing node-level query in
            # PrometheusMetricsService (cores actively used * 100, NOT
            # normalized to a limit - the ML model was trained on node
            # data using that same convention). Memory IS normalized to
            # the container's own limit, also matching the node-level query.
            "cpu_cores_used": 'sum(rate(container_cpu_usage_seconds_total{job="kubernetes-nodes-cadvisor", container!=""}[5m])) by (pod, namespace, container)',
            "memory_usage_bytes": 'max(container_memory_usage_bytes{job="kubernetes-nodes-cadvisor", container!=""}) by (pod, namespace, container)',
            "memory_limit_bytes": 'max(container_spec_memory_limit_bytes{job="kubernetes-nodes-cadvisor", container!=""}) by (pod, namespace, container)',
        }

        async with aiohttp.ClientSession() as session:
            tasks = [
                asyncio.create_task(self._execute_single_query(session, query, name))
                for name, query in queries.items()
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        responses: Dict[str, Dict[ContainerKey, float]] = {}
        for (metric_name, _), result in zip(queries.items(), results):
            if isinstance(result, Exception):
                logging.error(f"Error fetching {metric_name}: {result}")
                responses[metric_name] = {}
            else:
                responses[metric_name] = result
        return responses

    async def _execute_single_query(
        self, session: aiohttp.ClientSession, query: str, metric_name: str
    ) -> Dict[ContainerKey, float]:
        try:
            async with session.get(PROMETHEUS_METRICS_URL, params={"query": query}) as resp:
                resp.raise_for_status()
                data = await resp.json()
        except Exception as e:
            logging.error(f"Error executing query for {metric_name}: {e}")
            raise
        return self._parse_response(data)

    def _parse_response(self, response_data: Dict[str, Any]) -> Dict[ContainerKey, float]:
        """Extract {(pod, namespace, container): value}, normalizing the two
        different label naming schemes (Kepler's pod_name/container_namespace/
        container_name vs cAdvisor's pod/namespace/container) to one shape."""
        parsed: Dict[ContainerKey, float] = {}
        if response_data.get("status") != "success":
            return parsed

        for item in response_data.get("data", {}).get("result", []):
            labels = item.get("metric", {})
            pod = labels.get("pod_name") or labels.get("pod")
            namespace = labels.get("container_namespace") or labels.get("namespace")
            container = labels.get("container_name") or labels.get("container")
            if not pod or not container:
                continue
            key = (pod, namespace or "default", container)
            parsed[key] = float(item["value"][1])

        return parsed

    async def scrape_and_transform(self) -> List[ContainerPowerMetricsCreate]:
        results = []
        current_time = datetime.utcnow()

        try:
            metrics = await self.fetch_all_metrics()

            all_keys: set = set()
            for metric_dict in metrics.values():
                all_keys.update(metric_dict.keys())

            for pod_name, namespace, container_name in all_keys:
                key = (pod_name, namespace, container_name)
                core_w = metrics["kepler_core_watts"].get(key)
                package_w = metrics["kepler_package_watts"].get(key)
                dram_w = metrics["kepler_dram_watts"].get(key)
                platform_w = metrics["kepler_platform_watts"].get(key)
                other_w = metrics["kepler_other_watts"].get(key)

                cpu_cores_used = metrics["cpu_cores_used"].get(key)
                memory_bytes = metrics["memory_usage_bytes"].get(key)
                memory_limit_bytes = metrics["memory_limit_bytes"].get(key)

                energy_values = (core_w, package_w, dram_w, platform_w, other_w)
                has_energy = any(w is not None for w in energy_values)
                has_utilization = cpu_cores_used is not None or memory_bytes is not None
                if not has_energy and not has_utilization:
                    continue

                cpu_utilization_percent = round(cpu_cores_used * 100, 2) if cpu_cores_used is not None else None
                memory_utilization_percent = (
                    round((memory_bytes / memory_limit_bytes) * 100, 2)
                    if memory_bytes is not None and memory_limit_bytes
                    else None
                )

                if has_energy and has_utilization:
                    metric_source = "kepler+cadvisor"
                elif has_energy:
                    metric_source = "kepler"
                else:
                    metric_source = "cadvisor"

                results.append(ContainerPowerMetricsCreate(
                    timestamp=current_time,
                    container_name=container_name,
                    pod_name=pod_name,
                    namespace=namespace,
                    node_name=None,
                    metric_source=metric_source,
                    cpu_core_watts=round(core_w, 4) if core_w is not None else None,
                    cpu_package_watts=round(package_w, 4) if package_w is not None else None,
                    memory_power_watts=round(dram_w, 4) if dram_w is not None else None,
                    platform_watts=round(platform_w, 4) if platform_w is not None else None,
                    other_watts=round(other_w, 4) if other_w is not None else None,
                    cpu_utilization_percent=cpu_utilization_percent,
                    memory_utilization_percent=memory_utilization_percent,
                    memory_usage_bytes=int(memory_bytes) if memory_bytes is not None else None,
                    network_io_rate_bytes_per_sec=None,
                    disk_io_rate_bytes_per_sec=None,
                ))

            logging.info(f"PrometheusContainerMetricsService: Parsed {len(results)} container metrics from Prometheus.")
            return results

        except Exception as e:
            logging.error(f"Error scraping Prometheus container metrics: {e}")
            return []

    async def collect_and_store_metrics(self) -> int:
        """Collect per-container Kepler+cAdvisor metrics and store in
        container_power_metrics. Returns the number of records stored."""
        try:
            results = await self.scrape_and_transform()

            if not results:
                logging.warning("No container metrics collected from Prometheus")
                return 0

            stored_count = await self._store_metrics(results)
            logging.info(f"PrometheusContainerMetricsService: Stored {stored_count} container metrics to container_power_metrics table")
            return stored_count

        except Exception as e:
            logging.error(f"Error in collect_and_store_metrics: {e}")
            return 0

    async def _store_metrics(self, metrics: List[ContainerPowerMetricsCreate]) -> int:
        if not metrics:
            return 0

        stored_count = 0
        async for session in get_async_db():
            try:
                repository = ContainerPowerMetricsRepository(session)

                for metric in metrics:
                    try:
                        await repository.create(metric)
                        stored_count += 1
                    except Exception as e:
                        logging.warning(f"Failed to store container metric for {metric.pod_name}/{metric.container_name}: {e}")

                await session.commit()

            except Exception as e:
                logging.error(f"Database error storing container metrics: {e}")
                await session.rollback()

        return stored_count
