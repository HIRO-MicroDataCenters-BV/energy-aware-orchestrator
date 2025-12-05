"""
CRD Builder for EnergyAwareOrchestration.

This module generates the CRD YAML for the EnergyAwareOrchestration custom resource
using Pydantic models converted to JSON Schema.

Usage:
    # As module (from project root)
    python -m app.crd.builder

    # Direct execution (from app/crd directory)
    python builder.py

    # Via shell script (from project root)
    ./scripts/generate-crd.sh
"""
import os
import sys
from pathlib import Path

import yaml
from pydantic import BaseModel

# Handle both direct execution and module import
try:
    from .energy_aware_orchestration_model import EnergyAwareOrchestrationSpec, EnergyAwareOrchestrationStatus
except ImportError:
    from energy_aware_orchestration_model import EnergyAwareOrchestrationSpec, EnergyAwareOrchestrationStatus


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


def get_project_root() -> Path:
    """Find the project root directory (contains pyproject.toml or charts/)."""
    current = Path(__file__).resolve().parent
    for _ in range(10):  # Max 10 levels up
        if (current / "pyproject.toml").exists() or (current / "charts").exists():
            return current
        current = current.parent
    # Fallback: assume we're in app/crd/
    return Path(__file__).resolve().parent.parent.parent


def generate_crd_yaml(include_helm_annotations: bool = False) -> str:
    """
    Generate CRD YAML content.
    
    Args:
        include_helm_annotations: If True, adds Helm hook annotations for upgrade support
    """
    crd = build_crd()
    
    if include_helm_annotations:
        # Add Helm hook annotations for CRD lifecycle management
        crd["metadata"]["annotations"] = {
            "helm.sh/hook": "pre-install,pre-upgrade",
            "helm.sh/hook-weight": "-5",
            "helm.sh/hook-delete-policy": "before-hook-creation",
        }
    
    return yaml.dump(crd, default_flow_style=False, sort_keys=False)


def main():
    """Generate CRD YAML and write to all required locations."""
    project_root = get_project_root()
    script_dir = Path(__file__).resolve().parent
    
    # Output locations
    outputs = {
        "local": script_dir / "energy-aware-orchestration-crd.yaml",
        "helm_crds": project_root / "charts" / "crds" / "energy-aware-orchestration-crd.yaml",
    }
    
    # Generate CRD YAML
    crd_yaml = generate_crd_yaml(include_helm_annotations=False)
    
    # Add header comment
    header = """# AUTO-GENERATED FILE - DO NOT EDIT MANUALLY
# Generated by: python -m app.crd.builder
# Source: app/crd/energy_aware_orchestration_model.py
#
# To regenerate, run: ./scripts/generate-crd.sh
#
# Deployment:
#   - Fresh install: Helm auto-installs from charts/crds/
#   - Upgrades: Run ./scripts/deploy-crd.sh or kubectl apply -f this file
---
"""
    
    print("Generating EnergyAwareOrchestration CRD...")
    print()
    
    # Write to local directory
    outputs["local"].write_text(header + crd_yaml)
    print(f"Written: {outputs['local']}")
    
    # Create charts/crds/ directory if needed and write
    outputs["helm_crds"].parent.mkdir(parents=True, exist_ok=True)
    outputs["helm_crds"].write_text(header + crd_yaml)
    print(f"Written: {outputs['helm_crds']}")
    
    print()
    print("CRD generation complete!")
    print()
    print("Deployment:")
    print("  • Fresh install: helm install ... (CRD auto-installed from charts/crds/)")
    print("  • CRD update:    kubectl apply -f charts/crds/energy-aware-orchestration-crd.yaml")
    print("  • Full deploy:   ./scripts/deploy-all.sh")


if __name__ == "__main__":
    main()
