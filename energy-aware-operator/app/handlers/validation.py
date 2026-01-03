"""
Validation handler for EnergyAwareOrchestration operator.

This module provides validation logic for custom resource specifications.
"""

import logging
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Exception raised when CR validation fails."""

    def __init__(self, message: str, field: Optional[str] = None):
        """
        Initialize validation error.

        Args:
            message: Error message
            field: Field that failed validation
        """
        self.message = message
        self.field = field
        super().__init__(message)


class ValidationHandler:
    """
    Handler for validating EnergyAwareOrchestration custom resources.

    This handler extracts and validates spec fields, ensuring all required
    fields are present and have valid values.
    """

    @staticmethod
    def extract_spec_field(
        spec: Dict[str, Any],
        field: str,
        default: Any = None
    ) -> Any:
        """
        Extract a field from spec with a default value.

        Args:
            spec: The CR spec dictionary
            field: Field name to extract
            default: Default value if field is missing

        Returns:
            Field value or default
        """
        if spec is None:
            return default
        return spec.get(field, default)

    def validate_and_extract_spec(
        self,
        spec: Dict[str, Any],
        namespace: str
    ) -> Dict[str, Any]:
        """
        Validate and extract all required fields from the spec.

        Args:
            spec: The CR spec dictionary
            namespace: The namespace of the CR

        Returns:
            Dictionary with extracted and validated fields:
            {
                "energy_consumption": int,
                "forecast_window_days": int,
                "priority": str,
                "app_name": str,
                "app_namespace": str,
            }

        Raises:
            ValidationError: If validation fails
        """
        # Extract spec fields
        energy_consumption = int(
            self.extract_spec_field(spec, "energyConsumption", 0)
        )
        forecast_window_days = int(
            self.extract_spec_field(spec, "forecastWindowDays", 7)
        )
        priority = self.extract_spec_field(spec, "priority", "Preferred")
        application_ref = self.extract_spec_field(spec, "applicationRef", {})

        # Extract application details
        app_name = application_ref.get("name")
        app_namespace = application_ref.get("namespace", namespace)

        # Validate required fields
        if not app_name:
            raise ValidationError(
                "applicationRef.name is required",
                field="applicationRef.name"
            )

        # Validate energy consumption is positive
        if energy_consumption < 0:
            raise ValidationError(
                f"energyConsumption must be non-negative, got {energy_consumption}",
                field="energyConsumption"
            )

        # Validate priority is valid
        valid_priorities = ["Critical", "Preferred", "Optional"]
        if priority not in valid_priorities:
            logger.warning(
                f"Invalid priority '{priority}', defaulting to 'Preferred'. "
                f"Valid values: {valid_priorities}"
            )
            priority = "Preferred"

        # Validate forecast window
        if forecast_window_days < 1 or forecast_window_days > 30:
            logger.warning(
                f"forecastWindowDays {forecast_window_days} out of range (1-30), "
                f"using default 7"
            )
            forecast_window_days = 7

        logger.info(
            f"Validated spec: priority={priority}, energy={energy_consumption}W, "
            f"app={app_name}, namespace={app_namespace}"
        )

        return {
            "energy_consumption": energy_consumption,
            "forecast_window_days": forecast_window_days,
            "priority": priority,
            "app_name": app_name,
            "app_namespace": app_namespace,
        }

    def validate_spec_quick(
        self,
        spec: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Quick validation check without extraction.

        Args:
            spec: The CR spec dictionary

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            application_ref = self.extract_spec_field(spec, "applicationRef", {})
            app_name = application_ref.get("name")

            if not app_name:
                return False, "applicationRef.name is required"

            return True, None

        except Exception as e:
            return False, str(e)


# Singleton instance
_validation_handler: Optional[ValidationHandler] = None


def get_validation_handler() -> ValidationHandler:
    """
    Get the global validation handler instance.

    Returns:
        ValidationHandler singleton instance
    """
    global _validation_handler
    if _validation_handler is None:
        _validation_handler = ValidationHandler()
    return _validation_handler
