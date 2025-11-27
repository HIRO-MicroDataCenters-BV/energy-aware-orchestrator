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
        prefix="eas.hiro.io"
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


def _create_deployment(name: str, namespace: str, image: str, logger: kopf.Logger) -> None:
    """
    Create a simple Deployment for the given EnergyAwareOrchestration resource.
    """
    apps_v1 = client.AppsV1Api()

    # Define the deployment
    deployment = client.V1Deployment(
        metadata=client.V1ObjectMeta(
            name=f"app-{name}",
            namespace=namespace,
            labels={
                "app": name,
                "managed-by": "energy-aware-orchestrator",
                "eao-name": name
            }
        ),
        spec=client.V1DeploymentSpec(
            replicas=1,
            selector=client.V1LabelSelector(
                match_labels={
                    "app": name,
                    "eao-name": name
                }
            ),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(
                    labels={
                        "app": name,
                        "eao-name": name
                    }
                ),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name="app",
                            image=image,
                            ports=[client.V1ContainerPort(container_port=80)]
                        )
                    ]
                )
            )
        )
    )

    deployment_name = f"app-{name}"

    try:
        # Check if deployment already exists
        try:
            apps_v1.read_namespaced_deployment(name=deployment_name, namespace=namespace)
            logger.info(f"Deployment {deployment_name} already exists in namespace {namespace}")
        except client.exceptions.ApiException as e:
            if e.status == 404:
                # Deployment doesn't exist, create it
                apps_v1.create_namespaced_deployment(namespace=namespace, body=deployment)
                logger.info(f"Successfully created Deployment {deployment_name} with image {image} in namespace {namespace}")
            else:
                raise
    except Exception as e:
        logger.error(f"Failed to create Deployment: {e}")
        raise


@kopf.on.create(API_GROUP, API_VERSION, PLURAL)
def create_fn(spec: Dict[str, Any], status: Dict[str, Any], name: str, namespace: str, logger: kopf.Logger,
              **_: Any, ) -> None:
    """
    Main reconciliation handler for EnergyAwareOrchestration resources.

    - Reads desired state from `.spec`.
    - Logs the execution schedule from `.status.executionSchedule`.
    - Creates a simple nginx Deployment.
    """
    logger.info(f"CREATE handler triggered for {name} in namespace {namespace}")

    energy_consumption = int(_extract_spec_field(spec, "energyConsumption", 0))
    forecast_window_days = int(_extract_spec_field(spec, "forecastWindowDays", 7))
    priority = _extract_spec_field(spec, "priority", "NonCritical")
    application_ref = _extract_spec_field(spec, "applicationRef", {})

    # Extract application details from applicationRef
    app_name = application_ref.get("name")
    app_image = application_ref.get("image")
    app_namespace = application_ref.get("namespace", namespace)

    # Validate required fields
    if not app_name:
        raise ValueError("applicationRef.name is required")
    if not app_image:
        raise ValueError("applicationRef.image is required")

    logger.info(f"Spec values - energyConsumption: {energy_consumption}, forecastWindowDays: {forecast_window_days}, priority: {priority}")
    logger.info(f"Application - name: {app_name}, image: {app_image}, namespace: {app_namespace}")

    # Get execution schedule from status
    execution_schedule = status.get("executionSchedule", {}) if status else {}

    if execution_schedule:
        logger.info(f"Execution Schedule:")
        logger.info(f"  Updated: {execution_schedule.get('updated', 'N/A')}")
        schedule_list = execution_schedule.get("schedule", [])
        logger.info(f"  Number of days scheduled: {len(schedule_list)}")
        for day_schedule in schedule_list:
            date = day_schedule.get("date", "N/A")
            times = day_schedule.get("times", [])
            logger.info(f"  Date: {date}, Time slots: {len(times)}")
            for time_slot in times:
                start = time_slot.get("start", "N/A")
                stop = time_slot.get("stop", "N/A")
                cost = time_slot.get("cost", "N/A")
                logger.info(f"    {start} - {stop}, cost: {cost}")
    else:
        logger.info("No execution schedule found in status")

    # Create Deployment
    logger.info(f"Creating Deployment for {app_name} with image {app_image} in namespace {app_namespace}")
    _create_deployment(app_name, app_namespace, app_image, logger)

    logger.info(f"Finished processing {name}")


@kopf.on.delete(API_GROUP, API_VERSION, PLURAL)
def deletion_handler(
        name: str,
        namespace: str,
        logger: kopf.Logger,
        **_: Any,
) -> None:
    """
    Cleanup hook for CR deletion.

    Deletes the nginx Deployment created by this operator.
    """
    logger.info(f"EnergyAwareOrchestration {name} deleted from namespace {namespace}. Cleaning up external resources.")

    # Delete the Deployment
    apps_v1 = client.AppsV1Api()
    deployment_name = f"app-{name}"

    try:
        apps_v1.delete_namespaced_deployment(
            name=deployment_name,
            namespace=namespace,
            body=client.V1DeleteOptions()
        )
        logger.info(f"Successfully deleted Deployment {deployment_name} from namespace {namespace}")
    except client.exceptions.ApiException as e:
        if e.status == 404:
            logger.info(f"Deployment {deployment_name} not found, nothing to clean up")
        else:
            logger.error(f"Failed to delete Deployment {deployment_name}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error while deleting Deployment: {e}")
