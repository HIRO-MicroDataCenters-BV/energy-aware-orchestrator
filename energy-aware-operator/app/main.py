"""
Main entry point for the Energy-Aware Kubernetes Operator.

This module provides the main entry point for running the operator,
either as a standalone script or through the installed console script.
"""

import logging
import sys

import kopf

from app.config import configure_logging
from app import operator as operator_module

logger = logging.getLogger(__name__)


def main() -> None:
    """
    Main entry point for the operator.
    
    This function:
    1. Configures logging
    2. Starts the Kopf operator
    3. Handles shutdown gracefully
    """
    # Configure logging first
    configure_logging()
    
    logger.info("=" * 80)
    logger.info("Energy-Aware Kubernetes Operator Starting")
    logger.info("=" * 80)
    
    try:
        # Run the operator
        # Kopf will automatically discover handlers in the operator module
        kopf.run(
            [operator_module],
            standalone=True,
            liveness_endpoint="http://0.0.0.0:8080/healthz",
        )
    except KeyboardInterrupt:
        logger.info("Operator interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Operator failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

