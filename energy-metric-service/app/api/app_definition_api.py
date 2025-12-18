from typing import Optional, List
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.db.database import get_async_db
from app.servicesv2.workload_definition_service import ApplicationDefinitionService
from app.models.ApplicationDeployment import WorkloadType, DeploymentType
from app.models.app_definition_models import (
    AppDefinitionCreate,
    AppDefinitionResponse
)


router = APIRouter(prefix="/app/definitions", tags=["Workload Definitions"])



@router.post("/", response_model=AppDefinitionResponse)
async def create_workload_definition(
    payload: AppDefinitionCreate,
    db: AsyncSession = Depends(get_async_db),
):
    service = ApplicationDefinitionService(db)

    # Check duplicate name within namespace
    existing = await service.get_by_name(payload.name, payload.namespace)
    if existing:
        raise HTTPException(status_code=400, detail="Workload definition with this name already exists in the namespace")

    wd = await service.create_workload_definition(
        name=payload.name,
        namespace=payload.namespace,
        description=payload.description,
        manifest=payload.manifest,
        workload_type=payload.workload_type.value,
        deployment_type=payload.deployment_type.value,
        estimated_energy_required=payload.estimated_energy_required,
    )
    await db.commit()
    await db.refresh(wd)
    return AppDefinitionResponse(
        id=wd.id,
        name=wd.name,
        namespace=wd.namespace,
        description=wd.description,
        manifest=wd.manifest,
        workload_type=wd.workload_type,
        deployment_type=wd.deployment_type,
        estimated_energy_required=wd.estimated_energy_required,
    )


@router.post("/upload", response_model=AppDefinitionResponse)
async def create_workload_definition_from_yaml(
    file: UploadFile = File(..., description="YAML manifest file"),
    name: str = Form(..., description="Workload definition name"),
    namespace: str = Form("default", description="Kubernetes namespace"),
    workload_type: str = Form("Optional", description="Workload type: Critical, Preferred, Optional"),
    deployment_type: str = Form("kubernetes", description="Deployment type: kubernetes, helm, custom"),
    description: Optional[str] = Form(None, description="Description of the workload"),
    estimated_energy_required: Optional[float] = Form(None, description="Estimated energy required in watts"),
    db: AsyncSession = Depends(get_async_db),
):
    # Validate file extension
    if not file.filename.endswith((".yaml", ".yml")):
        raise HTTPException(status_code=400, detail="File must be a YAML file (.yaml or .yml)")

    # Read YAML content
    content_bytes = await file.read()
    try:
        manifest = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be valid UTF-8 text")

    # Validate workload type
    try:
        workload_type_enum = WorkloadType(workload_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid workload_type. Must be one of: Critical, Preferred, Optional")

    # Validate deployment type
    try:
        deployment_type_enum = DeploymentType(deployment_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid deployment_type. Must be one of: kubernetes, helm, custom")

    service = ApplicationDefinitionService(db)

    # Check duplicate name in namespace (note: DB unique is on name)
    existing = await service.get_by_name(name, namespace)
    if existing:
        raise HTTPException(status_code=400, detail="Workload definition with this name already exists in the namespace")

    wd = await service.create_workload_definition(
        name=name,
        namespace=namespace,
        description=description,
        manifest=manifest,
        workload_type=workload_type_enum.value,
        deployment_type=deployment_type_enum.value,
        estimated_energy_required=estimated_energy_required,
    )
    await db.commit()
    await db.refresh(wd)

    return AppDefinitionResponse(
        id=wd.id,
        name=wd.name,
        namespace=wd.namespace,
        description=wd.description,
        manifest=wd.manifest,
        workload_type=wd.workload_type,
        deployment_type=wd.deployment_type,
        estimated_energy_required=wd.estimated_energy_required,
    )


@router.get("/", response_model=List[AppDefinitionResponse])
async def list_workload_definitions(
    namespace: Optional[str] = Query(None),
    workload_type: Optional[WorkloadType] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_async_db),
):
    service = ApplicationDefinitionService(db)
    items = await service.list_workload_definitions(
        namespace=namespace,
        workload_type=workload_type.value if workload_type else None,
        limit=limit,
        offset=offset,
    )
    return [
        AppDefinitionResponse(
            id=i.id,
            name=i.name,
            namespace=i.namespace,
            description=i.description,
            manifest=i.manifest,
            workload_type=i.workload_type,
            deployment_type=i.deployment_type,
            estimated_energy_required=i.estimated_energy_required,
        )
        for i in items
    ]


@router.get("/{definition_id}", response_model=AppDefinitionResponse)
async def get_workload_definition(
    definition_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
):
    service = ApplicationDefinitionService(db)

    workload_def = await service.get_workload_definition(definition_id)
    if not workload_def:
        raise HTTPException(status_code=404, detail="Workload definition not found")

    return AppDefinitionResponse(
        id=workload_def.id,
        name=workload_def.name,
        namespace=workload_def.namespace,
        description=workload_def.description,
        manifest=workload_def.manifest,
        workload_type=workload_def.workload_type,
        deployment_type=workload_def.deployment_type,
        estimated_energy_required=workload_def.estimated_energy_required,
    )


@router.delete("/{definition_id}")
async def delete_workload_definition(
    definition_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
):
    service = ApplicationDefinitionService(db)

    existing = await service.get_workload_definition(definition_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Workload definition not found")

    try:
        success = await service.delete_workload_definition(definition_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete workload definition")

        await db.commit()
        return {"message": "Workload definition deleted successfully"}
    except IntegrityError as e:
        await db.rollback()
        if "app_definition_id" in str(e) and "app_deployments_request" in str(e):
            raise HTTPException(
                status_code=400,
                detail="Cannot delete workload definition: There are active deployment requests associated with this definition. Please remove all deployment requests first."
            )
        else:
            raise HTTPException(status_code=400, detail=f"Cannot delete workload definition due to database constraints: {str(e)}")
