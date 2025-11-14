"""
Repository for node metrics data operations.
"""

from typing import List, Optional
from datetime import datetime
from sqlalchemy import desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.node_metrics import NodeMetrics
from app.schemas.node_metrics import NodeMetricsCreate

class NodeMetricsRepository:
    """Repository for node metrics operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_batch(self, metrics: List[NodeMetricsCreate]) -> List[NodeMetrics]:
        """Create multiple node metrics records in batch"""
        db_metrics = []
        for metric in metrics:
            db_metric = NodeMetrics(
                **metric.model_dump(),
                created_at=func.now()
            )
            db_metrics.append(db_metric)
            self.session.add(db_metric)
        
        await self.session.commit()
        return db_metrics
    
    async def create(self, metric: NodeMetricsCreate) -> NodeMetrics:
        """Create a single node metrics record"""
        db_metric = NodeMetrics(
            **metric.model_dump(),
            created_at=func.now()
        )
        self.session.add(db_metric)
        await self.session.commit()
        await self.session.refresh(db_metric)
        return db_metric
    
    async def get_all(
        self,
        node_name: Optional[str] = None,
        metric_source: Optional[str] = None,
        start_timestamp: Optional[int] = None,
        end_timestamp: Optional[int] = None,
        limit: int = 100
    ) -> List[NodeMetrics]:
        """Get all node metrics with optional filtering"""
        query = select(NodeMetrics)
        
        # Apply filters
        if node_name:
            query = query.where(NodeMetrics.node_name == node_name)
        if metric_source:
            query = query.where(NodeMetrics.metric_source == metric_source)
        if start_timestamp:
            query = query.where(NodeMetrics.timestamp >= start_timestamp)
        if end_timestamp:
            query = query.where(NodeMetrics.timestamp <= end_timestamp)
        
        # Order by timestamp descending (most recent first)
        query = query.order_by(desc(NodeMetrics.timestamp))
        
        # Apply limit
        query = query.limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_latest_by_node(self, node_name: str) -> Optional[NodeMetrics]:
        """Get the most recent metrics for a specific node"""
        query = select(NodeMetrics).where(
            NodeMetrics.node_name == node_name
        ).order_by(desc(NodeMetrics.timestamp)).limit(1)
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_timestamp_range(
        self, 
        start_timestamp: int, 
        end_timestamp: int,
        node_name: Optional[str] = None
    ) -> List[NodeMetrics]:
        """Get metrics within a specific timestamp range"""
        query = select(NodeMetrics).where(
            NodeMetrics.timestamp >= start_timestamp,
            NodeMetrics.timestamp <= end_timestamp
        )
        
        if node_name:
            query = query.where(NodeMetrics.node_name == node_name)
        
        query = query.order_by(NodeMetrics.timestamp)
        
        result = await self.session.execute(query)
        return result.scalars().all()