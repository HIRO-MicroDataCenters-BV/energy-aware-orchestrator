"""
Configuration for EnergyAwareOrchestration Operator.

This module handles operator configuration including:
- Environment variable parsing
- Default values
- Configuration validation
"""

import logging
import os

logger = logging.getLogger(__name__)

# API configuration
API_GROUP = "eas.hiro.io"
API_VERSION = "v1"
PLURAL = "energyawareorchestrations"

# Re-evaluation interval configuration
DEFAULT_RECONCILE_INTERVAL_SECONDS = 600.0  # 10 minutes
ENV_VAR_RECONCILE_INTERVAL = "KOPF_RECONCILE_INTERVAL_SECONDS"


def get_reevaluation_interval() -> float:
    """
    Get the re-evaluation interval from environment variable or use default.

    Environment Variable:
        EAO_RECONCILE_INTERVAL_SECONDS: How often to re-evaluate schedules (in seconds)

    Returns:
        Interval in seconds (default: 600.0 = 10 minutes)

    Validation:
        - Must be a positive number
        - Falls back to default if invalid or not set
        - Logs warnings for invalid values
    """
    env_value = os.getenv(ENV_VAR_RECONCILE_INTERVAL)

    if env_value is None:
        logger.debug(
            f"{ENV_VAR_RECONCILE_INTERVAL} not set, using default: "
            f"{DEFAULT_RECONCILE_INTERVAL_SECONDS} seconds"
        )
        return DEFAULT_RECONCILE_INTERVAL_SECONDS

    try:
        interval = float(env_value)

        if interval <= 0:
            logger.warning(
                f"Invalid {ENV_VAR_RECONCILE_INTERVAL}={env_value} (must be > 0). "
                f"Using default: {DEFAULT_RECONCILE_INTERVAL_SECONDS} seconds"
            )
            return DEFAULT_RECONCILE_INTERVAL_SECONDS

        logger.info(
            f"Using {ENV_VAR_RECONCILE_INTERVAL} from environment: "
            f"{interval} seconds ({interval / 60:.1f} minutes)"
        )
        return interval

    except ValueError:
        logger.warning(
            f"Invalid {ENV_VAR_RECONCILE_INTERVAL}={env_value} (not a number). "
            f"Using default: {DEFAULT_RECONCILE_INTERVAL_SECONDS} seconds"
        )
        return DEFAULT_RECONCILE_INTERVAL_SECONDS
