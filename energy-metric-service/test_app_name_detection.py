#!/usr/bin/env python3
"""
Script to test app-name label detection logic and show how pods are identified.
This helps understand the priority order for app identification.
"""

def detect_app_from_labels(labels):
    """
    Detect app name and type from pod labels (same logic as API).
    
    Priority order:
    1. app.kubernetes.io/name (standard Kubernetes label)
    2. app (common standard label)
    3. app-name (custom label for energy-metric-service)
    """
    # Check for standard Kubernetes labels (preferred)
    if 'app.kubernetes.io/name' in labels:
        return {
            'app_name': labels['app.kubernetes.io/name'],
            'app_type': 'standard',
            'label_source': 'app.kubernetes.io/name',
            'app_name_label': labels.get('app-name')  # Captured separately
        }
    
    # Check for common 'app' label (also considered standard)
    if 'app' in labels:
        return {
            'app_name': labels['app'],
            'app_type': 'standard',
            'label_source': 'app',
            'app_name_label': labels.get('app-name')  # Captured separately
        }
    
    # Check for custom 'app-name' label (energy-metric-service custom)
    if 'app-name' in labels:
        return {
            'app_name': labels['app-name'],
            'app_type': 'custom',
            'label_source': 'app-name',
            'app_name_label': labels.get('app-name')  # Same value
        }
    
    # No recognizable app label found
    return None


# Test scenarios
test_cases = [
    {
        "name": "Standard K8s app with app-name label",
        "labels": {
            "app.kubernetes.io/name": "nginx",
            "app.kubernetes.io/version": "1.21.0",
            "app-name": "K8s"
        }
    },
    {
        "name": "Standard K8s app with 'app' label and app-name",
        "labels": {
            "app": "postgres",
            "app-name": "K8s"
        }
    },
    {
        "name": "Custom app (only app-name)",
        "labels": {
            "app-name": "K8s",
            "workload-type": "Optional"
        }
    },
    {
        "name": "Standard K8s app (no app-name)",
        "labels": {
            "app.kubernetes.io/name": "redis",
            "app.kubernetes.io/version": "7.0"
        }
    },
    {
        "name": "All three labels present",
        "labels": {
            "app.kubernetes.io/name": "my-service",
            "app": "my-app",
            "app-name": "K8s"
        }
    }
]

print("=" * 80)
print("APP NAME DETECTION TEST")
print("=" * 80)

for i, test in enumerate(test_cases, 1):
    print(f"\n{i}. {test['name']}")
    print("-" * 80)
    print("Labels:")
    for key, value in test['labels'].items():
        print(f"  {key}: {value}")
    
    result = detect_app_from_labels(test['labels'])
    
    if result:
        print("\nDetection Result:")
        print(f"  app_name: {result['app_name']}")
        print(f"  app_type: {result['app_type']}")
        print(f"  label_source: {result['label_source']}")
        print(f"  app_name_label: {result['app_name_label']}")
    else:
        print("\nDetection Result: No app labels found")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("""
Current Priority Order:
1. app.kubernetes.io/name → standard (highest priority)
2. app → standard
3. app-name → custom (lowest priority)

Key Point:
- If a pod has BOTH 'app.kubernetes.io/name: nginx' AND 'app-name: K8s'
  - app_name will be "nginx" (from app.kubernetes.io/name)
  - app_type will be "standard"
  - app_name_label will be "K8s" (captured separately for filtering)

To group all pods with 'app-name: K8s', use:
  filter by app_name_label == "K8s" (regardless of app_type)
""")

