"""
EnergyAwareOrchestration Kubernetes Operator

This operator watches EnergyAwareOrchestration custom resources and:
1. Calculates execution schedules based on priority and energy availability
2. Updates CR status with scheduling decisions
3. Posts Kubernetes events for observability

Scheduling Logic:
- Critical: Deploy immediately (24/7 operation)
- Preferred: If energy insufficient, delay by 6 hours
- Optional: Find best slot in next 24 hours based on energy availability
"""

import logging
from typing import Any, Dict

import kopf
from kubernetes import config

from app.crd.handlers import (
    EventHandler,
    SchedulerHandler,
    StatusHandler,
    ValidationHandler,
    get_event_handler,
    get_scheduler_handler,
    get_status_handler,
    get_validation_handler,
)
from app.crd.handlers.validation_handler import ValidationError

API_GROUP = "eas.hiro.io"
API_VERSION = "v1"
PLURAL = "energyawareorchestrations"

logger = logging.getLogger(__name__)

# Handler instances - initialized at module load time
# These are pure Python objects and don't require Kubernetes config
validation_handler: ValidationHandler = get_validation_handler()
scheduler_handler: SchedulerHandler = get_scheduler_handler()
status_handler: StatusHandler = get_status_handler()
event_handler: EventHandler = get_event_handler()


def _load_kube_config() -> None:
    """
    Load Kubernetes configuration.

    - In-cluster: use ServiceAccount credentials.
    - Local development: fall back to ~/.kube/config.
    """
    try:
        config.load_incluster_config()
        logger.info("Loaded in-cluster Kubernetes configuration.")
    except config.ConfigException:
        config.load_kube_config()
        logger.info("Loaded local kubeconfig.")


@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **_: Any) -> None:
    """
    Global operator configuration hook.

    This runs once when the operator starts and:
    - Loads Kubernetes configuration
    - Configures Kopf settings

    Note: Handlers are already initialized at module load time.
    """
    _load_kube_config()

    # Tune Kopf settings for production use.
    settings.posting.level = logging.INFO
    settings.posting.enabled = True
    settings.persistence.progress_storage = kopf.AnnotationsProgressStorage(
        prefix="eas.hiro.io"
    )

    logger.info("EAO Operator configured with energy-aware scheduling")
    logger.info(
        f"Handlers ready: {type(validation_handler).__name__}, "
        f"{type(scheduler_handler).__name__}, "
        f"{type(status_handler).__name__}, "
        f"{type(event_handler).__name__}"
    )


@kopf.on.create(API_GROUP, API_VERSION, PLURAL)
@kopf.on.update(API_GROUP, API_VERSION, PLURAL)
async def reconcile_handler(
    spec: Dict[str, Any],
    status: Dict[str, Any],
    name: str,
    namespace: str,
    body: Dict[str, Any],
    logger: kopf.Logger,
    patch: kopf.Patch,
    **_: Any,
) -> Dict[str, Any]:
    """
    Main reconciliation handler for EnergyAwareOrchestration resources.

    This handler:
    1. Extracts spec fields (priority, energy consumption, etc.)
    2. Calls the scheduler service to calculate the execution schedule
    3. Updates CR status with the scheduling decision
    4. Posts Kubernetes events for observability
    """
    logger.info(f"Reconciling EnergyAwareOrchestration '{name}' in namespace '{namespace}'")

    # Validate and extract spec fields
    try:
        validated_spec = validation_handler.validate_and_extract_spec(spec, namespace)
    except ValidationError as e:
        logger.error(f"Validation failed for '{name}': {e.message}")

        # Post validation failure event
        event_handler.post_validation_failed(body, e.message)

        # Update status with validation error
        failure_status = status_handler.build_validation_failure_status(
            field=e.field or "unknown",
            message=e.message
        )
        status_handler.apply_status_patch(patch, failure_status)

        raise kopf.PermanentError(e.message)

    # Extract validated fields
    energy_consumption = validated_spec["energy_consumption"]
    priority = validated_spec["priority"]
    app_name = validated_spec["app_name"]
    app_namespace = validated_spec["app_namespace"]

    logger.info(
        f"Processing: priority={priority}, energy={energy_consumption}W, "
        f"app={app_name}, namespace={app_namespace}"
    )

    # Post event: Processing started
    event_handler.post_scheduling_started(body, name, priority, energy_consumption)

    # Calculate schedule using async scheduler (Kopf handles the event loop)
    try:
        schedule_result = await scheduler_handler.calculate_schedule(
            priority, energy_consumption
        )

        if schedule_result:
            # Build status patch
            status_update = status_handler.build_status_from_schedule(schedule_result)

            # Apply to patch
            status_handler.apply_status_patch(patch, status_update)

            # Log decision
            status_handler.log_schedule_decision(name, schedule_result)

            # Post event: Schedule calculated
            event_handler.post_scheduling_completed(body, schedule_result)

            return {"scheduled": True, "action": schedule_result.decision.action.value}
        else:
            # Scheduling failed
            failure_status = status_handler.build_failure_status(
                reason="Failed to calculate schedule"
            )
            status_handler.apply_status_patch(patch, failure_status)

            event_handler.post_scheduling_failed(body)

            return {"scheduled": False, "error": "Scheduling failed"}

    except Exception as e:
        logger.error(f"Error during scheduling for '{name}': {e}", exc_info=True)

        failure_status = status_handler.build_failure_status(
            reason=f"Scheduling error: {str(e)}",
            error=str(e)
        )
        status_handler.apply_status_patch(patch, failure_status)

        event_handler.post_error(body, str(e))

        raise kopf.TemporaryError(f"Scheduling failed: {e}", delay=60)


@kopf.on.delete(API_GROUP, API_VERSION, PLURAL, optional=True)
def deletion_handler(
    name: str,
    namespace: str,
    body: Dict[str, Any],
    logger: kopf.Logger,
    **_: Any,
) -> None:
    """
    Cleanup hook for CR deletion.

    Note: optional=True prevents the finalizer from blocking deletion
    if the operator is not running or can't process the delete event.
    """
    logger.info(f"DELETE handler triggered for '{name}' in namespace '{namespace}'")

    # Post Kubernetes event: Resource being deleted
    event_handler.post_deletion(body, name)

    # Add any cleanup logic here (e.g., delete associated deployments)
    logger.info(f"EnergyAwareOrchestration '{name}' cleanup completed.")


@kopf.timer(API_GROUP, API_VERSION, PLURAL, interval=3600.0)  # Re-evaluate every hour
async def periodic_reconcile(
    spec: Dict[str, Any],
    status: Dict[str, Any],
    name: str,
    namespace: str,
    body: Dict[str, Any],
    logger: kopf.Logger,
    patch: kopf.Patch,
    **_: Any,
) -> Dict[str, Any]:
    """
    Periodic timer to re-evaluate schedules.

    This runs every hour to:
    - Re-calculate schedules based on updated energy availability
    - Update CR status if scheduling decision changes
    """
    # Get current phase
    current_phase = status.get("phase", "Pending")

    # Only re-evaluate if not already completed or failed permanently
    if current_phase in ["Completed"]:
        logger.debug(f"Skipping re-evaluation for '{name}': phase is {current_phase}")
        return {"skipped": True, "reason": f"Phase is {current_phase}"}

    logger.info(f"Periodic re-evaluation for '{name}'")

    # Extract spec fields (skip validation as it was already validated on create/update)
    energy_consumption = int(
        validation_handler.extract_spec_field(spec, "energyConsumption", 0)
    )
    priority = validation_handler.extract_spec_field(spec, "priority", "Preferred")

    # Post re-evaluation event
    event_handler.post_periodic_reevaluation(body, name)

    try:
        schedule_result = await scheduler_handler.calculate_schedule(
            priority, energy_consumption
        )

        if schedule_result:
            status_update = status_handler.build_status_from_schedule(schedule_result)
            status_handler.apply_status_patch(patch, status_update)

            logger.info(f"Re-evaluated '{name}': {schedule_result.decision.action.value}")

            return {"re_evaluated": True, "action": schedule_result.decision.action.value}

    except Exception as e:
        logger.warning(f"Error during periodic re-evaluation for '{name}': {e}")

    return {"re_evaluated": False}
