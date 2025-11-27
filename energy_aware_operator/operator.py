import datetime as dt
import logging
from typing import Any, Dict, List

import kopf
from kubernetes import client, config


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
        prefix="eas.hiro.io/progress"
    )


def _generate_schedule(
    energy_consumption: int,
    forecast_window_days: int,
) -> Dict[str, Any]:
    """
    Naive placeholder implementation that generates a simple execution schedule.

    In a real implementation this would call an external forecaster or cost API.
    """
    today = dt.date.today()
    now = dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc)

    schedule: List[Dict[str, Any]] = []

    for offset in range(forecast_window_days):
        day = today + dt.timedelta(days=offset)
        # Example heuristic: full-day window with a fixed "cost" derived from energy consumption.
        base_cost = round(energy_consumption / 100.0, 2)

        schedule.append(
            {
                "date": day.isoformat(),
                "times": [
                    {
                        "start": "00:00:00",
                        "stop": "24:00:00",
                        "cost": base_cost,
                    }
                ],
            }
        )

    return {
        "updated": now.isoformat(),
        "schedule": schedule,
    }


def _extract_spec_field(spec: Dict[str, Any], field: str, default: Any = None) -> Any:
    if spec is None:
        return default
    return spec.get(field, default)


@kopf.on.create(API_GROUP, API_VERSION, PLURAL)
@kopf.on.update(API_GROUP, API_VERSION, PLURAL)
@kopf.on.resume(API_GROUP, API_VERSION, PLURAL)
def reconciling_handler(
    spec: Dict[str, Any],
    status: Dict[str, Any],
    name: str,
    namespace: str,
    logger: kopf.Logger,
    **_: Any,
) -> Dict[str, Any]:
    """
    Main reconciliation handler for EnergyAwareOrchestration resources.

    - Reads desired state from `.spec`.
    - Computes / refreshes `.status.executionSchedule`.
    """
    energy_consumption = int(_extract_spec_field(spec, "energyConsumption", 0))
    forecast_window_days = int(_extract_spec_field(spec, "forecastWindowDays", 7))

    priority = _extract_spec_field(spec, "priority", "NonCritical")
    application_ref = _extract_spec_field(spec, "applicationRef", {})

    logger.info(
        "Reconciling EnergyAwareOrchestration",
        name=name,
        namespace=namespace,
        priority=priority,
        application_ref=application_ref,
    )

    execution_schedule = _generate_schedule(
        energy_consumption=energy_consumption,
        forecast_window_days=forecast_window_days,
    )

    new_status: Dict[str, Any] = dict(status or {})
    new_status["executionSchedule"] = execution_schedule

    return new_status


@kopf.on.delete(API_GROUP, API_VERSION, PLURAL)
def deletion_handler(
    name: str,
    namespace: str,
    logger: kopf.Logger,
    **_: Any,
) -> None:
    """
    Cleanup hook for CR deletion.

    Currently this only logs, but this is the right place to clean up any
    external resources (jobs, database records, etc.).
    """
    logger.info(
        "EnergyAwareOrchestration deleted. Cleaning up external resources.",
        name=name,
        namespace=namespace,
    )



