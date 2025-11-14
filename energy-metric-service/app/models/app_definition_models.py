"""
Pydantic models for Application Definition API endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional
import uuid

from app.models.ApplicationDeployment import WorkloadType


class AppDefinitionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    namespace: str = Field("default", min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    manifest: str = Field(..., min_length=1)
    workload_type: WorkloadType = Field(WorkloadType.OPTIONAL)
    estimated_energy_required: Optional[float] = Field(None, ge=0)


class AppDefinitionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    namespace: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    manifest: Optional[str] = Field(None, min_length=1)
    workload_type: Optional[WorkloadType] = None
    estimated_energy_required: Optional[float] = Field(None, ge=0)


class AppDefinitionResponse(BaseModel):
    id: uuid.UUID
    name: str
    namespace: str
    description: Optional[str]
    manifest: str
    workload_type: str
    estimated_energy_required: Optional[float]