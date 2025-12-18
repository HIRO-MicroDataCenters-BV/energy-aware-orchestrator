import uuid

from sqlalchemy import Column, String, Text, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.database import Base


class ApplicationDefinition(Base):
    __tablename__ = "app_definitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    namespace = Column(String(255), nullable=False, default="default")
    description = Column(Text, nullable=True)
    manifest = Column(Text, nullable=False)
    workload_type = Column(String(20), nullable=False, default="Optional")
    deployment_type = Column(String(20), nullable=False, default="kubernetes")
    estimated_energy_required = Column(Float, nullable=True)

    # Relationship to ApplicationDeployment
    application_deployments = relationship("ApplicationDeployment", back_populates="application_definition")


