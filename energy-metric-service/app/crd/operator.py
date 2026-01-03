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

from app.crd.config import (
    API_GROUP,
    API_VERSION,
    PLURAL,
    get_reevaluation_interval,
)
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

# Get configuration from environment
REEVALUATION_INTERVAL_SECONDS = get_reevaluation_interval()

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

    # Tune Kopf settings for production use
    settings.posting.enabled = True  # Disabled - we use EventHandler explicitly
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
    logger.info(
        f"Re-evaluation interval: {REEVALUATION_INTERVAL_SECONDS} seconds "
        f"({REEVALUATION_INTERVAL_SECONDS / 60:.1f} minutes)"
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
    logger.info("")
    logger.info("=" * 80)
    logger.info(f"RECONCILIATION STARTED: '{name}' (namespace: {namespace})")
    logger.info("=" * 80)

    # Validate and extract spec fields
    logger.info("")
    logger.info("STEP 1: Validating CR Specification")
    logger.info("-" * 80)
    try:
        validated_spec = validation_handler.validate_and_extract_spec(spec, namespace)
        logger.info("Validation successful")
    except ValidationError as e:
        logger.error("")
        logger.error("VALIDATION FAILED")
        logger.error(f"   Field: {e.field}")
        logger.error(f"   Error: {e.message}")
        logger.error("-" * 80)

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

    logger.info(f"   Priority: {priority}")
    logger.info(f"   Energy Required: {energy_consumption}W")
    logger.info(f"   Application: {app_name} (namespace: {app_namespace})")
    logger.info("-" * 80)

    # Post event: Processing started
    logger.info("")
    logger.info("STEP 2: Posting Kubernetes Event")
    logger.info("-" * 80)
    event_handler.post_scheduling_started(body, name, priority, energy_consumption)
    logger.info("Event posted: Scheduling started")
    logger.info("-" * 80)

    # Calculate schedule using async scheduler (Kopf handles the event loop)
    logger.info("")
    logger.info("STEP 3: Calculating Schedule")
    logger.info("-" * 80)
    try:
        schedule_result = await scheduler_handler.calculate_schedule(
            priority, energy_consumption
        )

        if schedule_result:
            logger.info("Schedule calculation successful")
            logger.info("-" * 80)
            # Build status patch
            logger.info("")
            logger.info("STEP 4: Updating CR Status")
            logger.info("-" * 80)
            status_update = status_handler.build_status_from_schedule(schedule_result)
            status_handler.apply_status_patch(patch, status_update)
            logger.info("Status patch applied")
            logger.info("-" * 80)

            # Log decision
            logger.info("")
            logger.info("STEP 5: Schedule Decision")
            logger.info("-" * 80)
            status_handler.log_schedule_decision(name, schedule_result)
            logger.info("-" * 80)

            # Post event: Schedule calculated
            logger.info("")
            logger.info("STEP 6: Posting Completion Event")
            logger.info("-" * 80)
            event_handler.post_scheduling_completed(body, schedule_result)
            logger.info("Event posted: Scheduled")
            logger.info("-" * 80)

            logger.info("")
            logger.info("=" * 80)
            logger.info(f"RECONCILIATION COMPLETED: '{name}'")
            logger.info(f"   Action: {schedule_result.decision.action.value}")
            logger.info("=" * 80)
            logger.info("")

            return {"scheduled": True, "action": schedule_result.decision.action.value}
        else:
            # Scheduling failed
            logger.error("")
            logger.error("SCHEDULING FAILED")
            logger.error("-" * 80)
            logger.error("   Reason: Failed to calculate schedule")

            failure_status = status_handler.build_failure_status(
                reason="Failed to calculate schedule"
            )
            status_handler.apply_status_patch(patch, failure_status)
            event_handler.post_scheduling_failed(body)

            logger.error("-" * 80)
            logger.error("=" * 80)
            logger.error("")

            return {"scheduled": False, "error": "Scheduling failed"}

    except Exception as e:
        logger.error("")
        logger.error("=" * 80)
        logger.error(f"EXCEPTION DURING RECONCILIATION: '{name}'")
        logger.error("=" * 80)
        logger.error(f"   Error Type: {type(e).__name__}")
        logger.error(f"   Error Message: {str(e)}")
        logger.error("-" * 80)

        failure_status = status_handler.build_failure_status(
            reason=f"Scheduling error: {str(e)}",
            error=str(e)
        )
        status_handler.apply_status_patch(patch, failure_status)
        event_handler.post_error(body, str(e))

        logger.error("=" * 80, exc_info=True)
        logger.error("")
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
    logger.info("")
    logger.info("=" * 80)
    logger.info(f"DELETION TRIGGERED: '{name}' (namespace: {namespace})")
    logger.info("=" * 80)

    # Post Kubernetes event: Resource being deleted
    logger.info("")
    logger.info("Posting deletion event")
    logger.info("-" * 80)
    event_handler.post_deletion(body, name)
    logger.info("Event posted: Deleting")
    logger.info("-" * 80)

    # Add any cleanup logic here (e.g., delete associated deployments)
    logger.info("")
    logger.info("Performing cleanup")
    logger.info("-" * 80)
    # TODO: Add cleanup logic here
    logger.info("Cleanup completed")
    logger.info("-" * 80)

    logger.info("")
    logger.info("=" * 80)
    logger.info(f"DELETION COMPLETED: '{name}'")
    logger.info("=" * 80)
    logger.info("")


@kopf.timer(API_GROUP, API_VERSION, PLURAL, interval=REEVALUATION_INTERVAL_SECONDS)
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

    logger.info("")
    logger.info("=" * 80)
    logger.info(f"PERIODIC RE-EVALUATION: '{name}' (namespace: {namespace})")
    logger.info(f"   Current Phase: {current_phase}")
    logger.info("=" * 80)

    # Extract spec fields (skip validation as it was already validated on create/update)
    logger.info("")
    logger.info("Extracting spec fields")
    logger.info("-" * 80)
    energy_consumption = int(
        validation_handler.extract_spec_field(spec, "energyConsumption", 0)
    )
    priority = validation_handler.extract_spec_field(spec, "priority", "Preferred")
    logger.info(f"   Priority: {priority}")
    logger.info(f"   Energy Required: {energy_consumption}W")
    logger.info("-" * 80)

    # Post re-evaluation event
    logger.info("")
    logger.info("Posting re-evaluation event")
    logger.info("-" * 80)
    event_handler.post_periodic_reevaluation(body, name)
    logger.info("Event posted")
    logger.info("-" * 80)

    try:
        logger.info("")
        logger.info("Recalculating schedule")
        logger.info("-" * 80)
        schedule_result = await scheduler_handler.calculate_schedule(
            priority, energy_consumption
        )

        if schedule_result:
            logger.info("Schedule recalculated")
            logger.info("-" * 80)

            logger.info("")
            logger.info("Updating status")
            logger.info("-" * 80)
            status_update = status_handler.build_status_from_schedule(schedule_result)
            status_handler.apply_status_patch(patch, status_update)
            logger.info("Status updated")
            logger.info("-" * 80)

            logger.info("")
            logger.info("=" * 80)
            logger.info(f"RE-EVALUATION COMPLETED: '{name}'")
            logger.info(f"   New Action: {schedule_result.decision.action.value}")
            logger.info("=" * 80)
            logger.info("")

            return {"re_evaluated": True, "action": schedule_result.decision.action.value}

    except Exception as e:
        logger.warning("")
        logger.warning("=" * 80)
        logger.warning(f"RE-EVALUATION ERROR: '{name}'")
        logger.warning(f"   Error: {e}")
        logger.warning("=" * 80)
        logger.warning("")

    return {"re_evaluated": False}
