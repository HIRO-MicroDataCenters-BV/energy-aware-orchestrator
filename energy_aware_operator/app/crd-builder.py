"""
CRD Builder for EnergyAwareOrchestration

This script generates the CRD YAML for the EnergyAwareOrchestration custom resource
using Pydantic models converted to JSON Schema.
"""
import yaml
from typing import Optional, List
from enum import Enum
from datetime import datetime, date
from pydantic import BaseModel, Field


class Priority(str, Enum):
    """Priority levels for workload scheduling."""
    CRITICAL = "Critical"
    NON_CRITICAL = "NonCritical"
    OPTIONAL = "Optional"


class ApplicationRef(BaseModel):
    """Reference to the application."""
    name: str = Field(..., description="Name of the application")
    namespace: Optional[str] = Field(None, description="Target namespace for the application")


class EnergyAwareOrchestrationSpec(BaseModel):
    """Spec for EnergyAwareOrchestration resource."""
    energyConsumption: int = Field(
        ...,
        ge=0,
        description="Estimated energy consumption (arbitrary units, e.g. kWh)"
    )
    forecastWindowDays: int = Field(
        ...,
        ge=1,
        le=30,
        description="Number of days to forecast the execution schedule for."
    )
    priority: Priority = Field(
        default=Priority.NON_CRITICAL,
        description="Business priority of the workload. Used for scheduling and cost/energy optimisation."
    )
    applicationRef: ApplicationRef = Field(
        ...,
        description="Reference to the application"
    )


class TimeSlot(BaseModel):
    """Time slot for execution."""
    start: str = Field(..., description="Start time in HH:MM:SS format")
    stop: str = Field(..., description="Stop time in HH:MM:SS format")
    cost: float = Field(..., description="Energy cost for this time slot")


class DailySchedule(BaseModel):
    """Daily schedule entry."""
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    times: List[TimeSlot] = Field(..., description="List of time slots for this date")


class ExecutionSchedule(BaseModel):
    """Execution schedule with timestamp."""
    updated: Optional[datetime] = Field(None, description="UTC timestamp of the last schedule computation")
    schedule: Optional[List[DailySchedule]] = Field(None, description="List of per-day schedules")


class EnergyAwareOrchestrationStatus(BaseModel):
    """Status for EnergyAwareOrchestration resource."""
    executionSchedule: Optional[ExecutionSchedule] = Field(
        None,
        description="Computed execution schedule and last update timestamp"
    )


def pydantic_to_openapi_schema(model: type[BaseModel], add_time_patterns: bool = False) -> dict:
    """
    Convert Pydantic model to OpenAPI 3.0 schema (compatible with Kubernetes CRD).
    
    Args:
        model: The Pydantic model to convert
        add_time_patterns: If True, adds regex patterns for time fields (start/stop)
    """
    schema = model.model_json_schema()

    # Convert JSON Schema to OpenAPI v3 schema
    def convert_schema(s: dict, field_name: str = "") -> dict:
        result = {}

        # Handle anyOf (used for Optional fields) - extract the non-null type
        if "anyOf" in s:
            # Find the non-null schema in anyOf
            non_null_schemas = [item for item in s["anyOf"] if item.get("type") != "null"]
            if non_null_schemas:
                # Use the first non-null schema and merge with current dict
                main_schema = non_null_schemas[0].copy()
                if "description" in s:
                    main_schema["description"] = s["description"]
                return convert_schema(main_schema, field_name)

        if "type" in s:
            result["type"] = s["type"]

        if "description" in s:
            result["description"] = s["description"]

        if "properties" in s:
            result["properties"] = {
                k: convert_schema(v, k) for k, v in s["properties"].items()
            }

        if "required" in s:
            result["required"] = s["required"]

        if "enum" in s:
            result["enum"] = s["enum"]

        if "minimum" in s:
            result["minimum"] = s["minimum"]

        if "maximum" in s:
            result["maximum"] = s["maximum"]

        if "items" in s:
            result["items"] = convert_schema(s["items"])

        if "format" in s:
            result["format"] = s["format"]

        if "pattern" in s:
            result["pattern"] = s["pattern"]

        # Add time pattern validation for start/stop fields
        if add_time_patterns and field_name in ["start", "stop"] and result.get("type") == "string":
            result["pattern"] = r"^([01]\d|2[0-3]):[0-5]\d:[0-5]\d$"

        # Handle $ref for nested models
        if "$ref" in s and "#/$defs/" in s["$ref"]:
            ref_name = s["$ref"].split("/")[-1]
            if "$defs" in schema and ref_name in schema["$defs"]:
                return convert_schema(schema["$defs"][ref_name], field_name)

        return result

    return convert_schema(schema)


def add_format_annotations(schema: dict, parent_key: str = "") -> dict:
    """
    Add Kubernetes-specific format annotations to schema fields.
    
    Args:
        schema: The schema dict to annotate
        parent_key: The parent field name for context
    """
    result = schema.copy()
    
    # Add format annotations based on field names and types
    if result.get("type") == "integer":
        if parent_key == "energyConsumption":
            result["format"] = "int64"
        elif parent_key == "forecastWindowDays":
            result["format"] = "int32"
    
    if result.get("type") == "number":
        if parent_key == "cost":
            result["format"] = "double"
    
    if result.get("type") == "string":
        if parent_key == "date" and "Date in YYYY-MM-DD format" in result.get("description", ""):
            result["format"] = "date"
    
    # Recursively process nested properties
    if "properties" in result:
        result["properties"] = {
            k: add_format_annotations(v, k) 
            for k, v in result["properties"].items()
        }
    
    if "items" in result:
        result["items"] = add_format_annotations(result["items"], parent_key)
    
    return result


def build_crd() -> dict:
    """Build the EnergyAwareOrchestration CRD."""
    spec_schema = pydantic_to_openapi_schema(EnergyAwareOrchestrationSpec)
    spec_schema = add_format_annotations(spec_schema)
    
    status_schema = pydantic_to_openapi_schema(EnergyAwareOrchestrationStatus, add_time_patterns=True)
    status_schema = add_format_annotations(status_schema)

    return {
        "apiVersion": "apiextensions.k8s.io/v1",
        "kind": "CustomResourceDefinition",
        "metadata": {
            "name": "energyawareorchestrations.eas.hiro.io"
        },
        "spec": {
            "group": "eas.hiro.io",
            "scope": "Namespaced",
            "names": {
                "kind": "EnergyAwareOrchestration",
                "plural": "energyawareorchestrations",
                "singular": "energyawareorchestration",
                "shortNames": ["eao"]
            },
            "versions": [
                {
                    "name": "v1",
                    "served": True,
                    "storage": True,
                    "schema": {
                        "openAPIV3Schema": {
                            "type": "object",
                            "description": "Energy-aware orchestration schedule application.",
                            "properties": {
                                "apiVersion": {"type": "string"},
                                "kind": {"type": "string"},
                                "metadata": {"type": "object"},
                                "spec": spec_schema,
                                "status": status_schema
                            }
                        }
                    }
                }
            ]
        }
    }


def main():
    """Generate and print the CRD YAML."""
    import os

    crd = build_crd()
    yaml_content = yaml.dump(crd, default_flow_style=False, sort_keys=False)

    # Print to stdout
    print(yaml_content)

    # Also write to file in the same directory as this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(script_dir, "energyawareorchestration-crd.yaml")

    with open(output_file, 'w') as f:
        f.write(yaml_content)

    print(f"\n# CRD written to: {output_file}", file=__import__('sys').stderr)


if __name__ == "__main__":
    main()
