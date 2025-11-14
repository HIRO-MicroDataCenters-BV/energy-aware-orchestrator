from typing import List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.ApplicationDefinition import ApplicationDefinition


class ApplicationDefinitionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, wd: ApplicationDefinition) -> ApplicationDefinition:
        self.session.add(wd)
        await self.session.flush()
        return wd

    async def get_by_id(self, workload_id: uuid.UUID) -> Optional[ApplicationDefinition]:
        stmt = select(ApplicationDefinition).where(ApplicationDefinition.id == workload_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str, namespace: Optional[str] = None) -> Optional[ApplicationDefinition]:
        stmt = select(ApplicationDefinition).where(ApplicationDefinition.name == name)
        if namespace:
            stmt = stmt.where(ApplicationDefinition.namespace == namespace)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        namespace: Optional[str] = None,
        workload_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ApplicationDefinition]:
        stmt = select(ApplicationDefinition)
        if namespace:
            stmt = stmt.where(ApplicationDefinition.namespace == namespace)
        if workload_type:
            stmt = stmt.where(ApplicationDefinition.workload_type == workload_type)
        stmt = stmt.order_by(ApplicationDefinition.id.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update(
        self,
        workload_id: uuid.UUID,
        name: Optional[str] = None,
        namespace: Optional[str] = None,
        description: Optional[str] = None,
        manifest: Optional[str] = None,
        workload_type: Optional[str] = None,
        estimated_energy_required: Optional[float] = None,
    ) -> bool:
        values = {}
        if name is not None:
            values["name"] = name
        if namespace is not None:
            values["namespace"] = namespace
        if description is not None:
            values["description"] = description
        if manifest is not None:
            values["manifest"] = manifest
        if workload_type is not None:
            values["workload_type"] = workload_type
        if estimated_energy_required is not None:
            values["estimated_energy_required"] = estimated_energy_required

        if not values:
            return False

        stmt = update(ApplicationDefinition).where(ApplicationDefinition.id == workload_id).values(**values)
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def delete(self, workload_id: uuid.UUID) -> bool:
        wd = await self.get_by_id(workload_id)
        if wd:
            await self.session.delete(wd)
            return True
        return False


