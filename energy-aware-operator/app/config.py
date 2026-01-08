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
CRD_NAME = f"{PLURAL}.{API_GROUP}"

# Re-evaluation interval configuration
DEFAULT_RECONCILE_INTERVAL_SECONDS = 600.0  # 10 minutes
ENV_VAR_RECONCILE_INTERVAL = "KOPF_RECONCILE_INTERVAL_SECONDS"

# Energy API configuration
ENV_VAR_ENERGY_API_URL = "ENERGY_API_URL"
DEFAULT_ENERGY_API_URL = "http://0.0.0.0:8086"

# Logging configuration
ENV_VAR_LOG_LEVEL = "LOG_LEVEL"
DEFAULT_LOG_LEVEL = "INFO"


def get_reevaluation_interval() -> float:
    """
    Get the re-evaluation interval from environment variable or use default.

    Environment Variable:
        KOPF_RECONCILE_INTERVAL_SECONDS: How often to re-evaluate schedules (in seconds)

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


def get_energy_api_url() -> str:
    """
    Get the Energy API URL from environment or use default.

    Returns:
        Energy API URL
    """
    url = os.getenv(ENV_VAR_ENERGY_API_URL, DEFAULT_ENERGY_API_URL)
    logger.info(f"Energy API URL: {url}")
    return url


def get_log_level() -> str:
    """
    Get the log level from environment or use default.

    Returns:
        Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    level = os.getenv(ENV_VAR_LOG_LEVEL, DEFAULT_LOG_LEVEL).upper()
    
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if level not in valid_levels:
        logger.warning(
            f"Invalid {ENV_VAR_LOG_LEVEL}={level}. "
            f"Using default: {DEFAULT_LOG_LEVEL}"
        )
        level = DEFAULT_LOG_LEVEL
    
    return level


def configure_logging() -> None:
    """
    Configure logging for the operator.
    
    Sets up logging format, level, and handlers.
    """
    log_level = get_log_level()
    
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    # Set Kopf logger to WARNING to reduce noise
    logging.getLogger("kopf").setLevel(logging.WARNING)
    logging.getLogger("kopf.objects").setLevel(logging.WARNING)
    logging.getLogger("kopf.reactor").setLevel(logging.WARNING)
    
    logger.info(f"Logging configured with level: {log_level}")

