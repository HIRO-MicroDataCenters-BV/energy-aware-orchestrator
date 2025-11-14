"""
Unified node metrics service that combines cAdvisor and Kepler node-level metrics.
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from app.services.cadvisor_node_metrics_service import CadvisorNodeMetricsService
from app.services.kepler_node_metrics_service import KeplerNodeMetricsService
from app.schemas.node_metrics import NodePowerMetricsCreate
from app.repositories.node_power_metrics import NodePowerMetricsRepository
from app.db.database import get_async_db
import logging

class UnifiedNodeMetricsService:
    """
    Service that combines metrics from both cAdvisor (CPU/memory usage) 
    and Kepler (energy consumption) into unified node power metrics.
    """
    
    def __init__(self):
        self.cadvisor_node_service = CadvisorNodeMetricsService()
        self.kepler_node_service = KeplerNodeMetricsService()
        
    async def collect_and_store_metrics(self) -> int:
        """
        Collect node metrics from both cAdvisor and Kepler, merge them, and store in database.
        Returns the number of records stored.
        """
        try:
            # Collect metrics from both sources concurrently
            cadvisor_task = asyncio.create_task(self.cadvisor_node_service.scrape_and_transform())
            kepler_task = asyncio.create_task(self.kepler_node_service.scrape_and_transform())
            
            cadvisor_node_metrics, kepler_node_metrics = await asyncio.gather(
                cadvisor_task, kepler_task, return_exceptions=True
            )
            
            # Handle potential exceptions
            if isinstance(cadvisor_node_metrics, Exception):
                logging.error(f"Failed to collect cAdvisor node metrics: {cadvisor_node_metrics}")
                cadvisor_node_metrics = []
            else:
                logging.info(f"Successfully collected {len(cadvisor_node_metrics)} cAdvisor node metrics")
                
            if isinstance(kepler_node_metrics, Exception):
                logging.error(f"Failed to collect Kepler node metrics: {kepler_node_metrics}")
                kepler_node_metrics = []
            else:
                logging.info(f"Successfully collected {len(kepler_node_metrics)} Kepler node metrics")
                
            # Merge metrics from both sources
            unified_node_metrics = self._merge_node_metrics(cadvisor_node_metrics, kepler_node_metrics)
            
            # Store in database
            stored_count = await self._store_metrics(unified_node_metrics)
            
            logging.info(f"UnifiedNodeMetricsService: Stored {stored_count} unified node power metrics")
            return stored_count
            
        except Exception as e:
            logging.error(f"Error in collect_and_store_node_metrics: {e}")
            return 0

    def _merge_node_metrics(
        self, 
        cadvisor_node_metrics: List[NodePowerMetricsCreate], 
        kepler_node_metrics: List[NodePowerMetricsCreate]
    ) -> List[NodePowerMetricsCreate]:
        """
        Merge cAdvisor and Kepler node metrics based on node_name.
        Logic: For each Kepler metric, find matching cAdvisor metric by node_name,
        then add CPU and memory utilization data from cAdvisor to the Kepler metric.
        """
        merged_metrics = []
        
        # Create lookup dict for cAdvisor node metrics by node_name
        cadvisor_lookup = {}
        for metric in cadvisor_node_metrics:
            if metric.node_name:
                cadvisor_lookup[metric.node_name] = metric
        
        # Process each Kepler node metric
        for kepler_metric in kepler_node_metrics:
            if not kepler_metric.node_name:
                # Skip Kepler metrics without node_name
                continue
                
            # Find matching cAdvisor metric by node_name
            cadvisor_metric = cadvisor_lookup.get(kepler_metric.node_name)
            
            # Create unified metric by enhancing Kepler metric with cAdvisor CPU/memory data
            unified_metric = self._create_unified_node_metric_from_kepler(kepler_metric, cadvisor_metric)
            if unified_metric:
                merged_metrics.append(unified_metric)
        
        logging.info(f"Merged {len(kepler_node_metrics)} Kepler node metrics with cAdvisor CPU/memory data = {len(merged_metrics)} unified node metrics")
        return merged_metrics

    def _create_unified_node_metric_from_kepler(
        self, 
        kepler_metric: NodePowerMetricsCreate,
        cadvisor_metric: Optional[NodePowerMetricsCreate]
    ) -> Optional[NodePowerMetricsCreate]:
        """
        Create a unified node metric by enhancing Kepler metric with cAdvisor CPU/memory data.
        Keep all Kepler data unchanged, only add CPU and memory metrics from cAdvisor.
        """
        # Use current timestamp
        timestamp = datetime.utcnow()
        
        # Determine metric source
        metric_source = "kepler"
        if cadvisor_metric:
            metric_source = "kepler+cadvisor"
        
        # Helper function to round float values to 4 decimal places
        def round_float(value):
            return round(value, 4) if value is not None else None
        
        # Create unified metric keeping all Kepler data and adding cAdvisor CPU/memory
        return NodePowerMetricsCreate(
            timestamp=timestamp,
            node_name=kepler_metric.node_name,
            metric_source=metric_source,
            
            # Keep all Kepler energy data unchanged but rounded to 4 decimal places
            cpu_core_watts=round_float(kepler_metric.cpu_core_watts),
            cpu_package_watts=round_float(kepler_metric.cpu_package_watts),
            memory_power_watts=round_float(kepler_metric.memory_power_watts),
            platform_watts=round_float(kepler_metric.platform_watts),
            
            # Add CPU and memory utilization data from cAdvisor (if available) - rounded to 4 decimal places
            cpu_utilization_percent=round_float(cadvisor_metric.cpu_utilization_percent) if cadvisor_metric else None,
            memory_utilization_percent=round_float(cadvisor_metric.memory_utilization_percent) if cadvisor_metric else None,
            memory_usage_bytes=cadvisor_metric.memory_usage_bytes if cadvisor_metric else None,  # Keep bytes as integer
        )

    async def _store_metrics(self, metrics: List[NodePowerMetricsCreate]) -> int:
        """Store node metrics in the database."""
        if not metrics:
            return 0
            
        stored_count = 0
        async for session in get_async_db():
            try:
                repository = NodePowerMetricsRepository(session)
                
                for metric in metrics:
                    try:
                        await repository.create(metric)
                        stored_count += 1
                    except Exception as e:
                        logging.warning(f"Failed to store node metric for {metric.node_name}: {e}")
                        
                await session.commit()
                
            except Exception as e:
                logging.error(f"Database error storing node metrics: {e}")
                await session.rollback()
                
        return stored_count

    async def get_latest_metrics(
        self,
        node_name: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get latest node metrics from database."""
        async for session in get_async_db():
            try:
                # TODO: Implement repository method to get node metrics
                # repository = NodePowerMetricsRepository(session)
                # metrics = await repository.get_all(node_name=node_name, limit=limit)
                # return [metric.to_dict() for metric in metrics]
                return []
            except Exception as e:
                logging.error(f"Error retrieving node metrics: {e}")
                return []
        return []  # Fallback if no session is available