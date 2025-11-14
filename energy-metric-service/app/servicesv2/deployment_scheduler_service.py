"""
Deployment Scheduler Service
Processes pending deployment requests based on energy availability
"""

import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.models.ApplicationDeployment import ApplicationDeployment, RequestStatus, WorkloadType
from app.repositories.application_deployment_repository import ApplicationDeploymentRepository
from app.repositories.application_definition_repository import ApplicationDefinitionRepository
from app.servicesv2.deployment_service import KubernetesDeploymentService
from app.db.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


class DeploymentSchedulerService:
    """Service to process pending deployments based on energy availability"""

    def __init__(self):
        self.deployment_service = KubernetesDeploymentService()

    async def process_pending_deployments(self) -> int:
        """
        Process all pending deployment requests (status = 'Created').

        Returns:
            Number of deployments processed
        """
        processed_count = 0

        async with AsyncSessionLocal() as db:
            try:
                deployment_repo = ApplicationDeploymentRepository(db)
                app_definition_repo = ApplicationDefinitionRepository(db)

                # Get all pending deployments (status = 'Created')
                pending_deployments = await deployment_repo.get_all(
                    status=RequestStatus.CREATED.value,
                    limit=100
                )

                if not pending_deployments:
                    logger.debug("No pending deployments found")
                    return 0

                logger.info(f"Found {len(pending_deployments)} pending deployment(s) to process")

                for deployment in pending_deployments:
                    try:
                        await self._process_single_deployment(
                            deployment,
                            app_definition_repo,
                            deployment_repo,
                            db
                        )
                        processed_count += 1
                    except Exception as e:
                        logger.error(f"Failed to process deployment {deployment.id}: {e}")
                        # Mark as failed
                        await deployment_repo.update_deployment_request(
                            request_id=deployment.id,
                            status=RequestStatus.FAILED.value,
                            error_message=f"Scheduler processing error: {str(e)}"
                        )
                        await db.commit()

                logger.info(f"Processed {processed_count} pending deployment(s)")
                return processed_count

            except Exception as e:
                logger.error(f"Error in process_pending_deployments: {e}")
                await db.rollback()
                raise

    async def _process_single_deployment(
            self,
            deployment: ApplicationDeployment,
            app_definition_repo: ApplicationDefinitionRepository,
            deployment_repo: ApplicationDeploymentRepository,
            db: AsyncSession
    ):
        """
        Process a single pending deployment request.

        Args:
            deployment: The deployment request to process
            app_definition_repo: Repository for app definitions
            deployment_repo: Repository for deployments
            db: Database session
        """
        logger.info(f"Processing deployment request {deployment.id}")

        # Get app definition
        app_definition = await app_definition_repo.get_by_id(deployment.app_definition_id)
        if not app_definition:
            logger.error(f"App definition {deployment.app_definition_id} not found for deployment {deployment.id}")
            await deployment_repo.update_deployment_request(
                request_id=deployment.id,
                status=RequestStatus.FAILED.value,
                error_message="App definition not found"
            )
            await db.commit()
            return

        logger.info(
            f"Processing deployment for app '{app_definition.name}' (workload type: {app_definition.workload_type})")

        # Get estimated energy
        estimated_energy = deployment.estimated_energy_watts
        if not estimated_energy:
            estimated_energy = app_definition.estimated_energy_required
        if not estimated_energy:
            estimated_energy = await self.deployment_service.estimate_deployment_energy(app_definition.manifest)

        # Check energy availability based on workload type
        if app_definition.workload_type == WorkloadType.CRITICAL.value:
            # Critical workloads bypass energy checks
            logger.info(f"Critical workload '{app_definition.name}' - bypassing energy check")
            energy_check = {"sufficient": True, "reason": "Critical workload - energy check bypassed"}
        else:
            # For Preferred and Optional workloads, check energy availability
            # Use EnergyAvailabilityService to calculate available energy
            # Available energy = Energy available from current time slot - Current K8s consumption
            energy_check = await self.deployment_service.check_energy_availability(
                required_energy_watts=estimated_energy,
                db_session=db
            )
            logger.info(f"Energy check for '{app_definition.name}': {energy_check}")

        # If sufficient energy, deploy
        if energy_check["sufficient"]:
            try:
                # Add custom labels
                custom_labels = {
                    "app-name": app_definition.name,
                    "workload-type": app_definition.workload_type,
                    "deployed-by": "energy-scheduler"
                }

                logger.info(f"###### Deploying '{app_definition.name}' to namespace '{app_definition.namespace}' ######")
                deployment_result = await self.deployment_service.deploy_to_kubernetes(
                    app_definition.manifest,
                    app_definition.namespace,
                    custom_labels=custom_labels
                )

                if deployment_result["success"]:
                    await deployment_repo.update_deployment_request(
                        request_id=deployment.id,
                        status=RequestStatus.DEPLOYED.value,
                        deployed_at=datetime.utcnow(),
                        error_message=''
                    )
                    logger.info(f"Successfully deployed '{app_definition.name}' via scheduler")
                else:
                    await deployment_repo.update_deployment_request(
                        request_id=deployment.id,
                        # status=RequestStatus.FAILED.value,
                        error_message=deployment_result.get("error", "Deployment failed")
                    )
                    logger.error(
                        f"Deployment failed for '{app_definition.name}': {deployment_result.get('error', 'Deployment failed')}")

            except Exception as e:
                await deployment_repo.update_deployment_request(
                    request_id=deployment.id,
                    status=RequestStatus.FAILED.value,
                    error_message=f"Deployment exception: {str(e)}"
                )
                logger.error(f"Exception during deployment of '{app_definition.name}': {e}")

        else:
            # Still insufficient energy - keep as CREATED but update error message
            await deployment_repo.update_deployment_request(
                request_id=deployment.id,
                error_message=f"Waiting for sufficient energy: {energy_check['reason']}"
            )
            logger.info(f"Deployment '{app_definition.name}' still waiting: {energy_check['reason']}")

        # Commit the changes
        await db.commit()

        # Get updated deployment to log final status
        updated_deployment = await deployment_repo.get_by_id(deployment.id)
        if updated_deployment:
            logger.info(f"Updated deployment {deployment.id} with status: {updated_deployment.status}")
