"""
Repository for application deployment database operations.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from sqlalchemy.orm import joinedload
from datetime import datetime

from app.models.ApplicationDeployment import ApplicationDeployment
from app.servicesv2.deployment.deployment_service import DeploymentStatus


class ApplicationDeploymentRepository:
    """Repository for managing application deployments."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, application_deployment: ApplicationDeployment) -> ApplicationDeployment:
        """Create a new application deployment."""
        self.session.add(application_deployment)
        await self.session.flush()
        return application_deployment

    async def get_by_id(self, request_id: UUID) -> Optional[ApplicationDeployment]:
        """Get application deployment by ID with application definition."""
        stmt = select(ApplicationDeployment).options(
            joinedload(ApplicationDeployment.application_definition)
        ).where(ApplicationDeployment.id == request_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_app_definition_id(self, app_definition_id: UUID) -> Optional[ApplicationDeployment]:
        """Get application deployment by app definition ID."""
        stmt = select(ApplicationDeployment).where(ApplicationDeployment.app_definition_id == app_definition_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        status: Optional[str] = None,
        app_definition_id: Optional[UUID] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ApplicationDeployment]:
        """Get all application deployments with optional filtering and app definitions."""
        stmt = select(ApplicationDeployment).options(
            joinedload(ApplicationDeployment.application_definition)
        )

        if status:
            stmt = stmt.where(ApplicationDeployment.status == status)
        if app_definition_id:
            stmt = stmt.where(ApplicationDeployment.app_definition_id == app_definition_id)

        stmt = stmt.order_by(ApplicationDeployment.created_at.desc())
        stmt = stmt.limit(limit).offset(offset)

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_pending_requests(self) -> List[ApplicationDeployment]:
        """Get all pending application deployments."""
        return await self.get_all(status=DeploymentStatus.PENDING.value)

    async def get_by_statuses(
        self,
        statuses: List[str],
        limit: int = 100,
        offset: int = 0
    ) -> List[ApplicationDeployment]:
        """Get all application deployments with status in the provided list."""
        stmt = select(ApplicationDeployment).options(
            joinedload(ApplicationDeployment.application_definition)
        )

        if statuses:
            stmt = stmt.where(ApplicationDeployment.status.in_(statuses))

        stmt = stmt.order_by(ApplicationDeployment.created_at.desc())
        stmt = stmt.limit(limit).offset(offset)

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update_status(
        self,
        request_id: UUID,
        status: DeploymentStatus,
        error_message: Optional[str] = None,
        deployed_at: Optional[datetime] = None
    ) -> bool:
        """Update application deployment status."""
        update_data = {
            "status": status.value,
            "updated_at": datetime.utcnow()
        }

        if error_message:
            update_data["error_message"] = error_message

        if deployed_at:
            update_data["deployed_at"] = deployed_at

        stmt = (
            update(ApplicationDeployment)
            .where(ApplicationDeployment.id == request_id)
            .values(**update_data)
        )

        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def get_deployment_stats(self) -> Dict[str, Any]:
        """Get deployment statistics."""
        from sqlalchemy import func

        # Count by status
        status_counts_stmt = (
            select(
                ApplicationDeployment.status,
                func.count(ApplicationDeployment.id).label('count')
            )
            .group_by(ApplicationDeployment.status)
        )

        # Count by namespace
        namespace_counts_stmt = (
            select(
                ApplicationDeployment.namespace,
                func.count(ApplicationDeployment.id).label('count')
            )
            .group_by(ApplicationDeployment.namespace)
        )

        # Recent deployments (last 24 hours)
        from datetime import timedelta
        yesterday = datetime.utcnow() - timedelta(hours=24)
        recent_count_stmt = (
            select(func.count(ApplicationDeployment.id))
            .where(ApplicationDeployment.created_at >= yesterday)
        )

        # Execute queries
        status_result = await self.session.execute(status_counts_stmt)
        namespace_result = await self.session.execute(namespace_counts_stmt)
        recent_result = await self.session.execute(recent_count_stmt)

        # Process results
        status_counts = {row.status: row.count for row in status_result}
        namespace_counts = {row.namespace: row.count for row in namespace_result}
        recent_count = recent_result.scalar()

        return {
            "total_requests": sum(status_counts.values()),
            "status_distribution": status_counts,
            "namespace_distribution": namespace_counts,
            "recent_24h": recent_count or 0
        }

    async def delete(self, request_id: UUID) -> bool:
        """Delete a deployment request by ID."""
        stmt = select(ApplicationDeployment).where(ApplicationDeployment.id == request_id)
        result = await self.session.execute(stmt)
        deployment_request = result.scalar_one_or_none()

        if deployment_request:
            await self.session.delete(deployment_request)
            return True
        return False

    async def update_deployment_request(
        self,
        request_id: UUID,
        manifest: str = None,
        estimated_energy_watts: float = None,
        status: str = None,
        error_message: str = None,
        deployed_at: datetime = None
    ) -> Optional[ApplicationDeployment]:
        """Update a deployment request with new values."""
        stmt = select(ApplicationDeployment).where(ApplicationDeployment.id == request_id)
        result = await self.session.execute(stmt)
        deployment_request = result.scalar_one_or_none()

        if deployment_request:
            if manifest is not None:
                deployment_request.manifest = manifest
            if estimated_energy_watts is not None:
                deployment_request.estimated_energy_watts = estimated_energy_watts
            if status is not None:
                deployment_request.status = status
            if error_message is not None:
                deployment_request.error_message = error_message
            if deployed_at is not None:
                deployment_request.deployed_at = deployed_at

            return deployment_request
        return None