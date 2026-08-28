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
from typing import Any, Dict, Optional

import kopf
from kubernetes import config

from app.config import (
    API_GROUP,
    API_VERSION,
    PLURAL,
    get_energy_api_url,
    get_reevaluation_interval,
)
from app.handlers import (
    ValidationError,
    get_event_handler,
    get_status_handler,
    get_validation_handler,
)
from app.index import get_profile_index
from app.services import SimpleSchedulerService
from app.services.energy_api_client import EnergyAPIClient

# Get configuration from environment
REEVALUATION_INTERVAL_SECONDS = get_reevaluation_interval()
ENERGY_API_URL = get_energy_api_url()

logger = logging.getLogger(__name__)

# Handler instances - initialized at module load time
validation_handler = get_validation_handler()
status_handler = get_status_handler()
event_handler = get_event_handler()
profile_index = get_profile_index()

# Initialize Energy API Client and Scheduler Service
energy_api_client = EnergyAPIClient(api_url=ENERGY_API_URL) if ENERGY_API_URL else None
scheduler_service: SimpleSchedulerService = SimpleSchedulerService(energy_api_client=energy_api_client)


def _apply_demand_report_result(patch: kopf.Patch, resolved_watts: Optional[float]) -> None:
    """Record the outcome of a report_demand() call on the patch.

    measuredWatts is informational only (see its docstring in
    app/crd/models.py) - merged into the existing energyMetrics dict rather
    than replacing it, since apply_status_patch() already populated
    requiredWatts/sufficient/etc. there earlier in the same reconcile.
    """
    patch.status["demandReported"] = resolved_watts is not None
    patch.status["energyMetrics"] = {
        **(patch.status.get("energyMetrics") or {}),
        "measuredWatts": resolved_watts,
    }


async def _report_demand_if_needed(
    name: str,
    namespace: str,
    spec: Dict[str, Any],
    old_status: Dict[str, Any],
    schedule_result: Dict[str, Any],
    patch: kopf.Patch,
) -> None:
    """
    Report the CR's demand forecast (current slot + next 1 day, in
    predefined 6-hour slots) to energy-metric-service, skipping the whole
    batch when nothing has changed since the last successfully reported
    forecast for a Scheduled decision (see the demandReported field's
    docstring in app/crd/models.py for why plain content comparison
    against `status` isn't enough on its own). DeployImmediately has no
    scheduledSlot to compare against, so it always re-reports - bounded,
    small cost per reconcile.

    Never raises - a problem here must not prevent the CR's own scheduling
    decision (already applied to `patch` by the caller) from being
    persisted.
    """
    if not energy_api_client:
        return

    try:
        decision = schedule_result.get("decision", {}) or {}
        action = decision.get("action")
        energy_metrics = schedule_result.get("energyMetrics", {}) or {}
        required_watts = energy_metrics.get("requiredWatts")
        identifier = f"{namespace}/{name}"
        application_name = (spec.get("applicationRef") or {}).get("name")

        if required_watts is None:
            return

        if action != "DeployImmediately":
            scheduled_slot = decision.get("scheduledSlot")
            if action != "Scheduled" or not scheduled_slot:
                # Delayed/Waiting/unknown - nothing concrete to report yet
                return

            old_decision = old_status.get("decision") or {}
            old_scheduled_slot = old_decision.get("scheduledSlot") or {}
            old_energy_metrics = old_status.get("energyMetrics") or {}

            unchanged = (
                old_decision.get("action") == action
                and old_scheduled_slot.get("slotStart") == scheduled_slot.get("slotStart")
                and old_scheduled_slot.get("slotEnd") == scheduled_slot.get("slotEnd")
                and old_energy_metrics.get("requiredWatts") == required_watts
                and old_status.get("demandReported") is True
            )
            if unchanged:
                logger.debug(f"Demand forecast unchanged for '{identifier}', skipping report")
                return

        forecast_slots = scheduler_service.forecast_demand_slots(
            required_energy_watts=float(required_watts),
            schedule_result=schedule_result,
        )
        if not forecast_slots:
            return

        resolved = await energy_api_client.report_demand_batch(
            identifier=identifier,
            slots=[
                {
                    "slot_start_time": slot["slot_start"].isoformat(),
                    "slot_end_time": slot["slot_end"].isoformat(),
                    "required_watts": slot["watts"],
                    "application_name": application_name if slot["running"] else None,
                }
                for slot in forecast_slots
            ],
        )
        _apply_demand_report_result(patch, resolved[0] if resolved else None)

    except Exception as e:
        logger.warning(f"Demand reporting skipped for '{namespace}/{name}' due to an error: {e}")


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
    """
    _load_kube_config()

    # Tune Kopf settings for production use
    settings.posting.enabled = True
    settings.persistence.progress_storage = kopf.AnnotationsProgressStorage(
        prefix="eas.hiro.io"
    )

    logger.info("=" * 80)
    logger.info("EAO Operator configured with energy-aware scheduling")
    logger.info(f"Handlers ready: {validation_handler.__class__.__name__}, "
                f"{status_handler.__class__.__name__}, "
                f"{event_handler.__class__.__name__}")
    logger.info(f"Re-evaluation interval: {REEVALUATION_INTERVAL_SECONDS} seconds "
                f"({REEVALUATION_INTERVAL_SECONDS / 60:.1f} minutes)")
    logger.info(f"Energy API URL: {ENERGY_API_URL}")
    logger.info("=" * 80)


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
            field=e.field or "unknown", message=e.message
        )
        status_handler.apply_status_patch(patch, failure_status)

        raise kopf.PermanentError(e.message)

    # Extract validated fields
    energy_consumption = validated_spec["energy_consumption"]
    priority = validated_spec["priority"]
    app_api_version = validated_spec["app_api_version"]
    app_kind = validated_spec["app_kind"]
    app_name = validated_spec["app_name"]
    app_namespace = validated_spec["app_namespace"]

    logger.info(f"   Priority: {priority}")
    logger.info(f"   Energy Required: {energy_consumption}W")
    logger.info(f"   Application: {app_api_version} {app_kind}/{app_name} (namespace: {app_namespace})")
    logger.info("-" * 80)

    # Register in profile index: "<app_namespace>/<app_name>" → this EAO CR
    profile_index.register(
        app_namespace=app_namespace,
        app_name=app_name,
        eao_name=name,
        eao_namespace=namespace,
        priority=priority,
        energy_consumption=energy_consumption,
        app_kind=app_kind,
        app_api_version=app_api_version,
    )
    logger.info(f"   Indexed: {app_namespace}/{app_name} → {namespace}/{name} ({len(profile_index)} total)")

    # Post event: Processing started
    logger.info("")
    logger.info("STEP 2: Posting Kubernetes Event")
    logger.info("-" * 80)
    event_handler.post_scheduling_started(body, name, priority, energy_consumption)
    logger.info("Event posted: Scheduling started")
    logger.info("-" * 80)

    # Calculate schedule using async scheduler
    logger.info("")
    logger.info("STEP 3: Calculating Schedule")
    logger.info("-" * 80)
    try:
        schedule_result = await scheduler_service.calculate_schedule(
            priority, float(energy_consumption)
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

            # Report demand to energy-metric-service (best-effort, skips
            # when unchanged - see _report_demand_if_needed)
            await _report_demand_if_needed(name, namespace, spec, status, schedule_result, patch)

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
            action = schedule_result.get("decision", {}).get("action", "Unknown")
            logger.info(f"   Action: {action}")
            logger.info("=" * 80)
            logger.info("")

            return {"scheduled": True, "action": action}
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
            reason=f"Scheduling error: {str(e)}", error=str(e)
        )
        status_handler.apply_status_patch(patch, failure_status)
        event_handler.post_error(body, str(e))

        logger.error("=" * 80, exc_info=True)
        logger.error("")
        raise kopf.TemporaryError(f"Scheduling failed: {e}", delay=60)


@kopf.on.delete(API_GROUP, API_VERSION, PLURAL, optional=True)
async def deletion_handler(
    name: str, namespace: str, body: Dict[str, Any], logger: kopf.Logger, **_: Any
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

    # Remove from profile index
    app_ref = (body.get("spec") or {}).get("applicationRef") or {}
    app_name = app_ref.get("name")
    app_namespace = app_ref.get("namespace") or namespace
    if app_name:
        profile_index.unregister(app_namespace, app_name)
        logger.info(f"   Deindexed: {app_namespace}/{app_name} ({len(profile_index)} remaining)")

    # Post Kubernetes event: Resource being deleted
    logger.info("")
    logger.info("Posting deletion event")
    logger.info("-" * 80)
    event_handler.post_deletion(body, name)
    logger.info("Event posted: Deleting")
    logger.info("-" * 80)

    # Deactivate this CR's demand record, if any
    logger.info("")
    logger.info("Performing cleanup")
    logger.info("-" * 80)
    if energy_api_client:
        identifier = f"{namespace}/{name}"
        try:
            await energy_api_client.delete_demand(identifier)
            logger.info(f"   Demand record cleared for '{identifier}'")
        except Exception as e:
            logger.warning(f"   Failed to clear demand record for '{identifier}': {e}")
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

    This runs at configured intervals to:
    - Re-calculate schedules based on updated energy availability
    - Update CR status if scheduling decision changes
    """
    # Get current phase
    current_phase = status.get("phase", "Pending")

    # Only re-evaluate if not already completed
    if current_phase in ["Completed"]:
        logger.debug(f"Skipping re-evaluation for '{name}': phase is {current_phase}")
        return {"skipped": True, "reason": f"Phase is {current_phase}"}

    logger.info("")
    logger.info("=" * 80)
    logger.info(f"PERIODIC RE-EVALUATION: '{name}' (namespace: {namespace})")
    logger.info(f"   Current Phase: {current_phase}")
    logger.info("=" * 80)

    # Extract spec fields
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
        schedule_result = await scheduler_service.calculate_schedule(
            priority, float(energy_consumption)
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

            # Report demand to energy-metric-service (best-effort, skips
            # when unchanged - see _report_demand_if_needed)
            await _report_demand_if_needed(name, namespace, spec, status, schedule_result, patch)

            logger.info("")
            logger.info("=" * 80)
            logger.info(f"RE-EVALUATION COMPLETED: '{name}'")
            action = schedule_result.get("decision", {}).get("action", "Unknown")
            logger.info(f"   New Action: {action}")
            logger.info("=" * 80)
            logger.info("")

            return {"re_evaluated": True, "action": action}

    except Exception as e:
        logger.warning("")
        logger.warning("=" * 80)
        logger.warning(f"RE-EVALUATION ERROR: '{name}'")
        logger.warning(f"   Error: {e}")
        logger.warning("=" * 80)
        logger.warning("")

    return {"re_evaluated": False}


@kopf.on.cleanup()
async def cleanup(**_: Any) -> None:
    """
    Cleanup handler - closes HTTP connections on operator shutdown.
    """
    if energy_api_client:
        await energy_api_client.close()
        logger.info("Energy API client connections closed")

