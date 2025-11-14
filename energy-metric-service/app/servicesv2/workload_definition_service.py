from typing import Optional, List
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ApplicationDefinition import ApplicationDefinition
from app.repositories.application_definition_repository import ApplicationDefinitionRepository


class ApplicationDefinitionService:
    def __init__(self, session: AsyncSession):
        self.repo = ApplicationDefinitionRepository(session)
        self.session = session

    async def create_workload_definition(
        self,
        name: str,
        namespace: str,
        description: Optional[str],
        manifest: str,
        workload_type: str,
        estimated_energy_required: Optional[float] = None,
    ) -> ApplicationDefinition:
        wd = ApplicationDefinition(
            name=name,
            namespace=namespace or "default",
            description=description,
            manifest=manifest,
            workload_type=workload_type,
            estimated_energy_required=estimated_energy_required,
        )
        created = await self.repo.create(wd)
        await self.session.flush()
        return created

    async def get_workload_definition(self, workload_id: uuid.UUID) -> Optional[ApplicationDefinition]:
        return await self.repo.get_by_id(workload_id)

    async def get_by_name(self, name: str, namespace: Optional[str]) -> Optional[ApplicationDefinition]:
        return await self.repo.get_by_name(name, namespace)

    async def list_workload_definitions(
        self,
        namespace: Optional[str],
        workload_type: Optional[str],
        limit: int,
        offset: int,
    ) -> List[ApplicationDefinition]:
        return await self.repo.list(namespace, workload_type, limit, offset)

    async def update_workload_definition(
        self,
        workload_id: uuid.UUID,
        name: Optional[str] = None,
        namespace: Optional[str] = None,
        description: Optional[str] = None,
        manifest: Optional[str] = None,
        workload_type: Optional[str] = None,
        estimated_energy_required: Optional[float] = None,
    ) -> bool:
        updated = await self.repo.update(
            workload_id,
            name=name,
            namespace=namespace,
            description=description,
            manifest=manifest,
            workload_type=workload_type,
            estimated_energy_required=estimated_energy_required,
        )
        return updated

    async def delete_workload_definition(self, workload_id: uuid.UUID) -> bool:
        return await self.repo.delete(workload_id)


