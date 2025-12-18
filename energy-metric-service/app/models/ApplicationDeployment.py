import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, Float, func, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, selectinload
from app.db.database import Base

class RequestStatus(str, enum.Enum):
    CREATED = "Created" # when first workload is created
    SCHEDULE = "Schedule" # Schedule to be deployed, may be waiting because energy is not available
    DEPLOYED = "Deployed" # Deployed in k8s and running
    FAILED = "Failed" # Failed or not deployed after when it is scheduled for deployment

class WorkloadType(str, enum.Enum):
    CRITICAL = "Critical"
    PREFERRED = "Preferred"
    OPTIONAL = "Optional"

class DeploymentType(str, enum.Enum):
    KUBERNETES = "kubernetes"  # Native K8s YAML manifests (Deployment, Service, ConfigMap, etc.)
    HELM = "helm"              # Helm chart definitions
    CUSTOM = "custom"          # Custom Resources (CRDs)

class ApplicationDeployment(Base):
    __tablename__ = "app_deployments_request"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    app_definition_id = Column(UUID(as_uuid=True), ForeignKey("app_definitions.id"), nullable=False)
    status = Column(String, default=RequestStatus.CREATED.value)
    error_message = Column(Text, nullable=True)
    estimated_energy_watts = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    deployed_at = Column(DateTime, nullable=True)
    schedule_at = Column(DateTime, nullable=True)  # Scheduled deployment time

    # Relationship to ApplicationDefinition
    application_definition = relationship("ApplicationDefinition", back_populates="application_deployments")