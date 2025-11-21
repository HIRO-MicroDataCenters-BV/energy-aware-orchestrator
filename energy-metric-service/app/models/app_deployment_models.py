"""
Pydantic models for Application Deployment API endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

from app.models.ApplicationDeployment import ApplicationDeployment


class ApplicationDeploymentRequestModel(BaseModel):
    app_definition_id: UUID = Field(..., description="UUID of the app definition to deploy")
    estimated_energy_watts: Optional[float] = Field(None, description="Estimated energy consumption")
    schedule_at: Optional[datetime] = Field(None, description="Scheduled deployment time in ISO format (e.g., 2025-11-21T10:43:00)")


class ApplicationDeploymentUpdateModel(BaseModel):
    status: str = Field(..., description="New status - Currently only 'Scheduled' is allowed")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "Scheduled"
            }
        }


class ApplicationDeploymentResponse(BaseModel):
    id: UUID
    app_definition_id: UUID
    status: str
    estimated_energy_watts: Optional[float]
    created_at: datetime
    deployed_at: Optional[datetime]
    schedule_at: Optional[datetime]
    error_message: Optional[str]

    # App definition details (from the relationship)
    app_name: Optional[str] = None
    app_namespace: Optional[str] = None
    workload_type: Optional[str] = None
    app_description: Optional[str] = None
    manifest: Optional[str] = None


class EnergyCheckResponse(BaseModel):
    sufficient: bool
    current_energy_watts: Optional[float]
    required_energy_watts: Optional[float]
    available_capacity_watts: Optional[float]
    reason: str


class ClusterCapacityResponse(BaseModel):
    total_namespaces: int
    total_pods: int
    running_pods: int
    current_energy_watts: Optional[float]
    available_energy_watts: Optional[float]
    energy_utilization_percent: float


def build_deployment_response(application_deployment: ApplicationDeployment) -> ApplicationDeploymentResponse:
    """Helper function to build ApplicationDeploymentResponse from ApplicationDeployment with app definition."""
    application = application_deployment.application_definition
    return ApplicationDeploymentResponse(
        id=application_deployment.id,
        app_definition_id=application_deployment.app_definition_id,
        status=application_deployment.status,
        estimated_energy_watts=application_deployment.estimated_energy_watts,
        created_at=application_deployment.created_at,
        deployed_at=application_deployment.deployed_at,
        schedule_at=application_deployment.schedule_at,
        error_message=application_deployment.error_message,
        # Include app definition details if available
        app_name=application.name if application else None,
        app_namespace=application.namespace if application else None,
        workload_type=application.workload_type if application else None,
        app_description=application.description if application else None,
        manifest=application.manifest if application else None
    )