"""
CRD Builder for EnergyAwareOrchestration

This script generates the CRD YAML for the EnergyAwareOrchestration custom resource
using Pydantic models converted to JSON Schema.
"""
import yaml
from typing import Optional
from enum import Enum
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


def pydantic_to_openapi_schema(model: type[BaseModel]) -> dict:
    """
    Convert Pydantic model to OpenAPI 3.0 schema (compatible with Kubernetes CRD).
    """
    schema = model.model_json_schema()

    # Convert JSON Schema to OpenAPI v3 schema
    def convert_schema(s: dict) -> dict:
        result = {}

        if "type" in s:
            result["type"] = s["type"]

        if "description" in s:
            result["description"] = s["description"]

        if "properties" in s:
            result["properties"] = {
                k: convert_schema(v) for k, v in s["properties"].items()
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

        # Handle $ref for nested models
        if "$ref" in s and "#/$defs/" in s["$ref"]:
            ref_name = s["$ref"].split("/")[-1]
            if "$defs" in schema and ref_name in schema["$defs"]:
                return convert_schema(schema["$defs"][ref_name])

        return result

    return convert_schema(schema)


def build_crd() -> dict:
    """Build the EnergyAwareOrchestration CRD."""
    spec_schema = pydantic_to_openapi_schema(EnergyAwareOrchestrationSpec)

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
                                "status": {"type": "object", "x-kubernetes-preserve-unknown-fields": True}
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
