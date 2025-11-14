"""
Node metrics schemas for API and service layer - updated to match new database schema.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class NodeMetricsCreate(BaseModel):
    """Schema for creating node metrics with CPU, memory, and power data"""
    timestamp: int  # BigInt timestamp
    node_name: str
    metric_source: str
    
    # Resource utilization metrics
    cpu_utilization_percent: Optional[float] = None
    total_cpu_assigned: Optional[int] = None
    machine_cpu_cores: Optional[int] = None
    memory_utilization_percent: Optional[float] = None
    memory_utilization_bytes: Optional[float] = None
    memory_assigned_bytes: Optional[float] = None
    machine_memory_total_bytes: Optional[float] = None
    
    # Power metrics (from Kepler)
    cpu_core_watts: Optional[float] = None
    cpu_package_watts: Optional[float] = None
    memory_power_watts: Optional[float] = None
    platform_watts: Optional[float] = None
    energy_watts: Optional[float] = None

class NodeMetricsResponse(BaseModel):
    """Schema for node metrics API response"""
    timestamp: int
    node_name: str
    metric_source: str
    
    # Resource utilization metrics
    cpu_utilization_percent: Optional[float] = None
    total_cpu_assigned: Optional[int] = None
    machine_cpu_cores: Optional[int] = None
    memory_utilization_percent: Optional[float] = None
    memory_utilization_bytes: Optional[float] = None
    memory_assigned_bytes: Optional[float] = None
    machine_memory_total_bytes: Optional[float] = None
    
    # Power metrics (from Kepler)
    cpu_core_watts: Optional[float] = None
    cpu_package_watts: Optional[float] = None
    memory_power_watts: Optional[float] = None
    platform_watts: Optional[float] = None
    energy_watts: Optional[float] = None
    
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Keep backward compatibility
NodePowerMetricsCreate = NodeMetricsCreate
NodePowerMetricsResponse = NodeMetricsResponse