"""
EnergyAwareOrchestration Kubernetes Operator

This operator watches EnergyAwareOrchestration custom resources and:
1. Calculates execution schedules based on priority and energy availability
2. Updates CR status with scheduling decisions
3. Posts Kubernetes events for observability

Scheduling Logic:
- Critical: Deploy immediately (24/7 operation)
- NonCritical: If energy insufficient, delay by 6 hours
- Optional: Find best slot in next 24 hours based on energy availability
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import kopf
from kubernetes import config

from app.servicesv2.eao_scheduler_service import EAOSchedulerService, ScheduleResult

API_GROUP = "eas.hiro.io"
API_VERSION = "v1"
PLURAL = "energyawareorchestrations"

logger = logging.getLogger(__name__)


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


async def _calculate_schedule_async(
    priority: str,
    energy_consumption: int,
) -> Optional[ScheduleResult]:
    """
    Calculate schedule using the scheduler service.
    
    Note: This function is async and should be called from Kopf's async handlers.
    Since Kopf manages its own event loop, we don't create database sessions here
    to avoid event loop conflicts. The scheduler will work without energy data.
    
    Args:
        priority: Workload priority (Critical, NonCritical, Optional)
        energy_consumption: Required energy in Watts
        
    Returns:
        ScheduleResult or None if scheduling failed
    """
    try:
        # Use scheduler without database to avoid event loop conflicts
        # The scheduling logic still works based on priority
        scheduler = EAOSchedulerService()
        result = await scheduler.calculate_schedule(
            priority=priority,
            required_energy_watts=float(energy_consumption),
        )
        return result
            
    except Exception as e:
        logger.error(f"Error calculating schedule: {e}")
        return None


def _extract_spec_field(spec: Dict[str, Any], field: str, default: Any = None) -> Any:
    """Extract a field from spec with a default value."""
    if spec is None:
        return default
    return spec.get(field, default)


def _build_status_patch(schedule_result: ScheduleResult) -> Dict[str, Any]:
    """
    Build a status patch from the schedule result.
    
    Args:
        schedule_result: Result from the scheduler
        
    Returns:
        Dictionary to patch into CR status
    """
    return schedule_result.to_dict()


@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **_: Any) -> None:
    """
    Global operator configuration hook.
    """
    _load_kube_config()

    # Tune Kopf settings for production use.
    settings.posting.level = logging.INFO
    settings.posting.enabled = True
    settings.persistence.progress_storage = kopf.AnnotationsProgressStorage(
        prefix="eas.hiro.io"
    )
    
    logger.info("EAO Operator configured with energy-aware scheduling")


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

    # Extract spec fields
    energy_consumption = int(_extract_spec_field(spec, "energyConsumption", 0))
    forecast_window_days = int(_extract_spec_field(spec, "forecastWindowDays", 7))
    priority = _extract_spec_field(spec, "priority", "NonCritical")
    application_ref = _extract_spec_field(spec, "applicationRef", {})

    # Extract application details
    app_name = application_ref.get("name")
    app_namespace = application_ref.get("namespace", namespace)

    # Validate required fields
    if not app_name:
        kopf.event(
            body,
            type="Warning",
            reason="ValidationFailed",
            message="applicationRef.name is required"
        )
        patch.status["phase"] = "Failed"
        patch.status["decision"] = {
            "action": "Waiting",
            "reason": "Validation failed: applicationRef.name is required"
        }
        patch.status["lastUpdated"] = datetime.now(timezone.utc).isoformat()
        raise kopf.PermanentError("applicationRef.name is required")

    logger.info(f"Processing: priority={priority}, energy={energy_consumption}W, app={app_name}")

    # Post event: Processing started
    try:
        kopf.event(
            body,
            type="Normal",
            reason="Scheduling",
            message=f"Calculating schedule for '{name}' (Priority: {priority}, Energy: {energy_consumption}W)"
        )
    except Exception as e:
        logger.warning(f"Failed to post scheduling event: {e}")

    # Calculate schedule using async scheduler (Kopf handles the event loop)
    try:
        schedule_result = await _calculate_schedule_async(priority, energy_consumption)
        
        if schedule_result:
            # Build status patch
            status_update = _build_status_patch(schedule_result)
            
            # Apply to patch
            for key, value in status_update.items():
                patch.status[key] = value
            
            # Log decision
            decision = schedule_result.decision
            logger.info(f"Schedule decision for '{name}': {decision.action.value} - {decision.reason}")
            
            if decision.scheduled_slot:
                slot = decision.scheduled_slot
                logger.info(f"  Scheduled slot: {slot.slot_number} ({slot.start_time} - {slot.end_time})")
                if slot.available_energy_watts is not None:
                    logger.info(f"  Available energy: {slot.available_energy_watts}W")
            
            # Post event: Schedule calculated
            try:
                kopf.event(
                    body,
                    type="Normal",
                    reason="Scheduled",
                    message=f"{decision.action.value}: {decision.reason}"
                )
            except Exception as e:
                logger.warning(f"Failed to post scheduled event: {e}")
            
            return {"scheduled": True, "action": decision.action.value}
        else:
            # Scheduling failed
            patch.status["phase"] = "Failed"
            patch.status["decision"] = {
                "action": "Waiting",
                "reason": "Failed to calculate schedule"
            }
            patch.status["lastUpdated"] = datetime.now(timezone.utc).isoformat()
            
            kopf.event(
                body,
                type="Warning",
                reason="SchedulingFailed",
                message="Failed to calculate execution schedule"
            )
            
            return {"scheduled": False, "error": "Scheduling failed"}
            
    except Exception as e:
        logger.error(f"Error during scheduling for '{name}': {e}")
        
        patch.status["phase"] = "Failed"
        patch.status["decision"] = {
            "action": "Waiting",
            "reason": f"Scheduling error: {str(e)}"
        }
        patch.status["lastUpdated"] = datetime.now(timezone.utc).isoformat()
        
        kopf.event(
            body,
            type="Warning",
            reason="Error",
            message=f"Scheduling error: {str(e)}"
        )
        
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
    try:
        kopf.event(
            body,
            type="Normal",
            reason="Deleting",
            message=f"EnergyAwareOrchestration '{name}' is being deleted"
        )
    except Exception as e:
        logger.warning(f"Failed to post delete event: {e}")
    
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
    
    # Trigger reconciliation
    energy_consumption = int(_extract_spec_field(spec, "energyConsumption", 0))
    priority = _extract_spec_field(spec, "priority", "NonCritical")
    
    try:
        schedule_result = await _calculate_schedule_async(priority, energy_consumption)
        
        if schedule_result:
            status_update = _build_status_patch(schedule_result)
            for key, value in status_update.items():
                patch.status[key] = value
            
            logger.info(f"Re-evaluated '{name}': {schedule_result.decision.action.value}")
            
            return {"re_evaluated": True, "action": schedule_result.decision.action.value}
        
    except Exception as e:
        logger.warning(f"Error during periodic re-evaluation for '{name}': {e}")
    
    return {"re_evaluated": False}
