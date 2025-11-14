"""
Repository for node power metrics data operations.
"""

from typing import List, Optional
from datetime import datetime
from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.node_metrics import NodeMetrics
from app.schemas.node_metrics import NodePowerMetricsCreate
import time

class NodePowerMetricsRepository:
    """Repository for node power metrics operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_batch(self, metrics: List[NodePowerMetricsCreate]) -> List[NodeMetrics]:
        """Create multiple node power metrics records in batch"""
        db_metrics = []
        for metric in metrics:
            db_metric = NodeMetrics(**metric.model_dump())
            db_metrics.append(db_metric)
            self.session.add(db_metric)
        
        await self.session.commit()
        return db_metrics
    
    async def create(self, metric: NodePowerMetricsCreate) -> NodeMetrics:
        """Create a single node power metrics record"""
        db_metric = NodeMetrics(**metric.model_dump())
        self.session.add(db_metric)
        await self.session.commit()
        await self.session.refresh(db_metric)
        return db_metric
    
    async def get_all(
        self,
        node_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[NodeMetrics]:
        """Get all node power metrics with optional filtering"""
        query = select(NodeMetrics)
        
        # Apply filters
        if node_name:
            query = query.where(NodeMetrics.node_name == node_name)
        if start_time:
            # Convert datetime to Unix timestamp for comparison
            start_timestamp = int(start_time.timestamp())
            query = query.where(NodeMetrics.timestamp >= start_timestamp)
        if end_time:
            # Convert datetime to Unix timestamp for comparison
            end_timestamp = int(end_time.timestamp())
            query = query.where(NodeMetrics.timestamp <= end_timestamp)
        
        # Order by timestamp descending (most recent first)
        query = query.order_by(desc(NodeMetrics.timestamp))
        
        # Apply limit
        query = query.limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()