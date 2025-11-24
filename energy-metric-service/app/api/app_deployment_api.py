"""
Kubernetes Deployment API endpoints with energy awareness
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
import logging

from app.models.ApplicationDeployment import ApplicationDeployment, RequestStatus
from app.models.app_deployment_models import (
    ApplicationDeploymentRequestModel,
    ApplicationDeploymentUpdateModel,
    ApplicationDeploymentResponse,
    build_deployment_response
)
from app.servicesv2.deployment_service import KubernetesDeploymentService
from app.repositories.application_deployment_repository import ApplicationDeploymentRepository
from app.repositories.application_definition_repository import ApplicationDefinitionRepository
from app.db.database import get_async_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/app/deployment-request", tags=["Application Deployment Request"])

@router.post("/deploy", response_model=ApplicationDeploymentResponse)
async def request_deployment(
    deployment_request: ApplicationDeploymentRequestModel,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Request a new Kubernetes deployment.

    This endpoint:
    1. Retrieves the workload definition by ID
    2. Validates the Kubernetes manifest from workload definition
    3. Estimates energy consumption
    4. Creates a deployment request with status 'CREATED'
    5. Returns the request details

    Note: The actual deployment will be handled by the deployment scheduler
    which runs every 10 seconds and processes pending deployments based on energy availability.
    """
    try:
        logger.info("Starting deployment request processing")
        repository = ApplicationDeploymentRepository(db)
        application_repository = ApplicationDefinitionRepository(db)

        logger.info("Repositories initialized")

        # Get the app definition
        logger.info(f"Fetching app definition with ID: {deployment_request.app_definition_id}")
        app_definition = await application_repository.get_by_id(deployment_request.app_definition_id)
        if not app_definition:
            raise HTTPException(
                status_code=404,
                detail=f"App definition with ID {deployment_request.app_definition_id} not found"
            )

        logger.info(f"App definition found: {app_definition.name}")

        # Check if app is already deployed or has a pending deployment request
        existing_deployment = await repository.get_by_app_definition_id(deployment_request.app_definition_id)
        if existing_deployment:
            if existing_deployment.status == RequestStatus.DEPLOYED.value:
                # App is already deployed
                logger.info(f"App '{app_definition.name}' is already deployed")
                raise HTTPException(
                    status_code=409,
                    detail={
                        "message": f"Application '{app_definition.name}' is already deployed",
                        "deployment_id": str(existing_deployment.id),
                        "deployed_at": existing_deployment.deployed_at.isoformat() if existing_deployment.deployed_at else None,
                        "status": existing_deployment.status
                    }
                )
            elif existing_deployment.status == RequestStatus.CREATED.value:
                # There's already a pending deployment request
                logger.info(f"App '{app_definition.name}' already has a pending deployment request")
                raise HTTPException(
                    status_code=409,
                    detail={
                        "message": f"Application '{app_definition.name}' already has a pending deployment request",
                        "deployment_id": str(existing_deployment.id),
                        "created_at": existing_deployment.created_at.isoformat() if existing_deployment.created_at else None,
                        "status": existing_deployment.status,
                        "note": "The deployment scheduler will process this request shortly"
                    }
                )

        # Initialize deployment service for validation only
        deployment_service = KubernetesDeploymentService()
        logger.info("Deployment service initialized")

        # Validate manifest from application definition
        validation = await deployment_service.validate_manifest(app_definition.manifest)
        if not validation["valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid manifest in application definition: {validation.get('error', 'Unknown validation error')}"
            )

        # Estimate energy consumption
        estimated_energy = deployment_request.estimated_energy_watts
        if not estimated_energy:
            estimated_energy = app_definition.estimated_energy_required
        if not estimated_energy:
            estimated_energy = await deployment_service.estimate_deployment_energy(app_definition.manifest)

        # Create application deployment record with status CREATED
        # The deployment scheduler will pick this up and deploy it
        db_request = ApplicationDeployment(
            app_definition_id=deployment_request.app_definition_id,
            estimated_energy_watts=estimated_energy,
            status=RequestStatus.SCHEDULE.value,
            schedule_at=deployment_request.schedule_at
        )

        logger.info(f"Created deployment request for '{app_definition.name}' - will be processed by scheduler")

        # Save to database
        try:
            saved_request = await repository.create(db_request)
            await db.commit()
            # Refresh the object to get server-generated values
            await db.refresh(saved_request)
        except IntegrityError as e:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Database integrity error: {str(e)}"
            )
        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Database error: {str(e)}"
            )

        # Store app definition details before returning response
        app_name = app_definition.name
        app_namespace = app_definition.namespace
        workload_type = app_definition.workload_type
        app_description = app_definition.description
        manifest = app_definition.manifest

        return ApplicationDeploymentResponse(
            id=saved_request.id,
            app_definition_id=saved_request.app_definition_id,
            status=saved_request.status,
            estimated_energy_watts=saved_request.estimated_energy_watts,
            created_at=saved_request.created_at,
            deployed_at=saved_request.deployed_at,
            schedule_at=saved_request.schedule_at,
            error_message=saved_request.error_message,
            # Include application definition details
            app_name=app_name,
            app_namespace=app_namespace,
            workload_type=workload_type,
            app_description=app_description,
            manifest=manifest
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing deployment request: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")



@router.get("/requests", response_model=List[ApplicationDeploymentResponse])
async def get_deployment_requests(
    status: Optional[str] = Query(None, description="Filter by status"),
    app_definition_id: Optional[UUID] = Query(None, description="Filter by application definition ID"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get application deployments with optional filtering.

    Returns a list of application deployments matching the specified criteria.
    """
    try:
        repository = ApplicationDeploymentRepository(db)
        requests = await repository.get_all(
            status=status,
            app_definition_id=app_definition_id,
            limit=limit,
            offset=offset
        )

        return [build_deployment_response(req) for req in requests]

    except Exception as e:
        logger.error(f"Error retrieving application deployments: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve application deployments: {str(e)}")


@router.patch("/requests/{request_id}", response_model=ApplicationDeploymentResponse)
async def update_deployment_request(
    request_id: UUID,
    update_data: ApplicationDeploymentUpdateModel,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Update a deployment request's status to 'Scheduled'.

    This endpoint updates the deployment status to 'Scheduled' only.

    Note: Currently, only 'Scheduled' status is allowed for manual updates.
    This will be expanded in the future to support other status transitions.

    Returns the updated deployment request with application definition details.
    """
    try:
        repository = ApplicationDeploymentRepository(db)

        # Check if the deployment request exists
        existing_request = await repository.get_by_id(request_id)
        if not existing_request:
            raise HTTPException(status_code=404, detail="Deployment request not found")

        # Validate status - Currently only allow 'Scheduled' status
        # TODO: In the future, expand this to allow other status transitions
        allowed_statuses = [RequestStatus.SCHEDULED.value]

        if update_data.status not in allowed_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Currently, only 'Scheduled' status is allowed. Provided: {update_data.status}"
            )

        # Update only the status field
        updated_request = await repository.update_deployment_request(
            request_id=request_id,
            status=update_data.status
        )

        if not updated_request:
            raise HTTPException(status_code=500, detail="Failed to update deployment request")

        await db.commit()
        await db.refresh(updated_request)

        # Return the updated request with app definition details
        return build_deployment_response(updated_request)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating deployment request: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update deployment request: {str(e)}")


@router.patch("/requests/{request_id}/schedule")
async def update_deployment_schedule(
    request_id: UUID,
    schedule_at: datetime = Query(..., description="Scheduled deployment time in ISO format (e.g., 2025-11-21T10:43:00)"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Update the scheduled deployment time for a deployment request.
    """
    try:
        repository = ApplicationDeploymentRepository(db)

        existing_request = await repository.get_by_id(request_id)
        if not existing_request:
            raise HTTPException(status_code=404, detail="Deployment request not found")

        existing_request.schedule_at = schedule_at
        await db.commit()
        await db.refresh(existing_request)

        return build_deployment_response(existing_request)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating deployment schedule: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update deployment schedule: {str(e)}")


@router.delete("/requests/{request_id}")
async def delete_deployment_request(
    request_id: UUID,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Delete a deployment request by ID.

    This will remove the deployment request from the database.
    Note: This does not undeploy the application from Kubernetes if it was already deployed.
    """
    try:
        repository = ApplicationDeploymentRepository(db)

        # Check if the deployment request exists
        existing_request = await repository.get_by_id(request_id)
        if not existing_request:
            raise HTTPException(status_code=404, detail="Deployment request not found")

        # Delete the deployment request
        success = await repository.delete(request_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete deployment request")

        await db.commit()
        return {"message": "Deployment request deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting deployment request: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete deployment request: {str(e)}")

