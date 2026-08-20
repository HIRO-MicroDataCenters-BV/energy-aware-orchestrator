"""
Container power metrics repository.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy import select, update, delete, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.container_power_metrics import ContainerPowerMetrics
from app.schemas.container_power_metrics import ContainerPowerMetricsCreate, ContainerPowerMetricsUpdate
import logging

class ContainerPowerMetricsRepository:
    """Repository for container power metrics operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, metrics: ContainerPowerMetricsCreate) -> ContainerPowerMetrics:
        # Exclude container_id as it's not stored in database, only used for internal processing
        metrics_data = metrics.model_dump(exclude={'container_id'})
        db_metrics = ContainerPowerMetrics(**metrics_data)
        self.db.add(db_metrics)
        await self.db.commit()
        await self.db.refresh(db_metrics)
        logging.debug(f"DB CREATE: {db_metrics}")
        return db_metrics

    async def get_by_pk(self, timestamp: datetime, container_name: str, pod_name: str) -> Optional[ContainerPowerMetrics]:
        query = select(ContainerPowerMetrics).where(
            and_(
                ContainerPowerMetrics.timestamp == timestamp,
                ContainerPowerMetrics.container_name == container_name,
                ContainerPowerMetrics.pod_name == pod_name
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        container_name: Optional[str] = None,
        pod_name: Optional[str] = None,
        namespace: Optional[str] = None,
        node_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[ContainerPowerMetrics]:
        query = select(ContainerPowerMetrics)
        if container_name:
            query = query.where(ContainerPowerMetrics.container_name == container_name)
        if pod_name:
            query = query.where(ContainerPowerMetrics.pod_name == pod_name)
        if namespace:
            query = query.where(ContainerPowerMetrics.namespace == namespace)
        if node_name:
            query = query.where(ContainerPowerMetrics.node_name == node_name)
        if start_time:
            query = query.where(ContainerPowerMetrics.timestamp >= start_time)
        if end_time:
            query = query.where(ContainerPowerMetrics.timestamp <= end_time)
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update(self, timestamp: datetime, container_name: str, pod_name: str, metrics_update: ContainerPowerMetricsUpdate) -> Optional[ContainerPowerMetrics]:
        update_data = metrics_update.model_dump(exclude_unset=True)
        if not update_data:
            logging.debug(f"DB UPDATE: No update data for {timestamp}, {container_name}, {pod_name}")
            return None
        query = (
            update(ContainerPowerMetrics)
            .where(
                and_(
                    ContainerPowerMetrics.timestamp == timestamp,
                    ContainerPowerMetrics.container_name == container_name,
                    ContainerPowerMetrics.pod_name == pod_name
                )
            )
            .values(**update_data)
            .returning(ContainerPowerMetrics)
        )
        result = await self.db.execute(query)
        await self.db.commit()
        updated = result.scalar_one_or_none()
        if updated:
            logging.debug(f"DB UPDATE: Updated {timestamp}, {container_name}, {pod_name}")
        else:
            logging.debug(f"DB UPDATE: No row found for {timestamp}, {container_name}, {pod_name}")
        return updated

    async def delete(self, timestamp: datetime, container_name: str, pod_name: str) -> bool:
        query = delete(ContainerPowerMetrics).where(
            and_(
                ContainerPowerMetrics.timestamp == timestamp,
                ContainerPowerMetrics.container_name == container_name,
                ContainerPowerMetrics.pod_name == pod_name
            )
        )
        result = await self.db.execute(query)
        await self.db.commit()
        return result.rowcount > 0

    async def get_by_container_name(self, container_name: str, skip: int = 0, limit: int = 100) -> List[ContainerPowerMetrics]:
        query = (
            select(ContainerPowerMetrics)
            .where(ContainerPowerMetrics.container_name == container_name)
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def _latest_rows_per_pod_for_app(
        self,
        application_name: str,
        namespace: str,
        max_age_minutes: int,
    ) -> List[ContainerPowerMetrics]:
        """One most-recent row per pod belonging to `application_name` (pod
        names are prefixed by their owning Deployment's name) in `namespace`,
        within the last `max_age_minutes`. Empty list if nothing recent.

        `timestamp` is a naive DateTime column (no timezone), so the cutoff
        must be naive UTC too - comparing it against an aware datetime would
        silently match nothing, the same bug already fixed once in
        energy_availability.py.
        """
        cutoff = datetime.utcnow() - timedelta(minutes=max_age_minutes)
        query = (
            select(ContainerPowerMetrics)
            .where(
                ContainerPowerMetrics.namespace == namespace,
                ContainerPowerMetrics.pod_name.like(f"{application_name}-%"),
                ContainerPowerMetrics.timestamp >= cutoff,
            )
            .order_by(desc(ContainerPowerMetrics.timestamp))
        )
        result = await self.db.execute(query)

        latest_per_pod: Dict[str, ContainerPowerMetrics] = {}
        for row in result.scalars().all():
            if row.pod_name not in latest_per_pod:
                latest_per_pod[row.pod_name] = row  # DESC order: first seen is latest
        return list(latest_per_pod.values())

    async def get_latest_measured_watts(
        self,
        application_name: str,
        namespace: str,
        max_age_minutes: int = 30,
    ) -> Optional[float]:
        """Sum of the most recent measured watts across all pods for this
        application. Package watts already includes core watts (Kepler
        convention - see prometheus_metrics_service.py), so core is excluded
        here too to avoid double-counting. None if nothing recent."""
        rows = await self._latest_rows_per_pod_for_app(application_name, namespace, max_age_minutes)
        if not rows:
            return None
        return sum(
            (row.cpu_package_watts or 0)
            + (row.memory_power_watts or 0)
            + (row.platform_watts or 0)
            + (row.other_watts or 0)
            for row in rows
        )

    async def get_latest_utilization(
        self,
        application_name: str,
        namespace: str,
        max_age_minutes: int = 30,
    ) -> Optional[Dict[str, float]]:
        """Average CPU/memory utilization across the most recent reading per
        pod for this application - fallback input for the ML consumption
        model when direct wattage measurement isn't available. None if
        nothing recent."""
        rows = await self._latest_rows_per_pod_for_app(application_name, namespace, max_age_minutes)
        if not rows:
            return None
        cpu_values = [row.cpu_utilization_percent for row in rows if row.cpu_utilization_percent is not None]
        memory_values = [row.memory_utilization_percent for row in rows if row.memory_utilization_percent is not None]
        if not cpu_values or not memory_values:
            return None
        return {
            "cpu_utilization_percent": sum(cpu_values) / len(cpu_values),
            "memory_utilization_percent": sum(memory_values) / len(memory_values),
        }

    async def get_by_pod(self, pod_name: str, namespace: str, skip: int = 0, limit: int = 100) -> List[ContainerPowerMetrics]:
        query = (
            select(ContainerPowerMetrics)
            .where(
                ContainerPowerMetrics.pod_name == pod_name,
                ContainerPowerMetrics.namespace == namespace
            )
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().all() 