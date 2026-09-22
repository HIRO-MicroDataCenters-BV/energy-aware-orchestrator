"""
Node metrics model - updated to match new database schema.
"""

from sqlalchemy import Column, String, Float, BigInteger, Integer, PrimaryKeyConstraint, DateTime, func
from app.db.database import Base

class NodeMetrics(Base):
    """Database model for node metrics with CPU, memory, and power data"""
    __tablename__ = "node_metrics"

    # Primary key components  
    timestamp = Column(BigInteger, nullable=False)
    node_name = Column(String(255))

    # Additional metadata
    metric_source = Column(String(255))

    # Resource utilization metrics
    cpu_utilization_percent = Column(Float)
    total_cpu_assigned = Column(Integer)
    machine_cpu_cores = Column(Integer)
    memory_utilization_percent = Column(Float)
    memory_utilization_bytes = Column(Float)
    memory_assigned_bytes = Column(Float)
    machine_memory_total_bytes = Column(Float)

    # Power metrics (from Kepler) - total power = package + memory + platform + uncore (NOT core, as it's included in package)
    cpu_core_watts = Column(Float)
    cpu_package_watts = Column(Float)
    memory_power_watts = Column(Float)
    platform_watts = Column(Float)
    energy_watts = Column(Float)
    
    # Auto-generated timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        PrimaryKeyConstraint('timestamp', 'node_name'),
    )

    def __repr__(self):
        return (f"<NodeMetrics("
                f"timestamp={self.timestamp}, "
                f"node={self.node_name}, "
                f"metric_source={self.metric_source})>")

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'timestamp': self.timestamp,
            'node_name': self.node_name,
            'metric_source': self.metric_source,
            # Resource utilization
            'cpu_utilization_percent': self.cpu_utilization_percent,
            'total_cpu_assigned': self.total_cpu_assigned,
            'machine_cpu_cores': self.machine_cpu_cores,
            'memory_utilization_percent': self.memory_utilization_percent,
            'memory_utilization_bytes': self.memory_utilization_bytes,
            'memory_assigned_bytes': self.memory_assigned_bytes,
            'machine_memory_total_bytes': self.machine_memory_total_bytes,
            # Power metrics
            'cpu_core_watts': self.cpu_core_watts,
            'cpu_package_watts': self.cpu_package_watts,
            'memory_power_watts': self.memory_power_watts,
            'platform_watts': self.platform_watts,
            'energy_watts': self.energy_watts,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }