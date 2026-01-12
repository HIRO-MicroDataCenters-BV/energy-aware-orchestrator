#!/usr/bin/env python3
"""
Diagnostic script to check why CR app_name_label is null.
"""

import json

# Your API response
response = {
  "status": "success",
  "apps": [
    {
      "app_name": "critical-api-service",
      "app_type": "custom-resource",
      "app_name_label": None,
      "target_app_name": "api-gateway",
      "target_app_kind": "Deployment",
      "target_app_namespace": "production",
      "pods": [],
      "pod_count": 0,
      "namespaces": ["default"]
    },
    {
      "app_name": "nginx",
      "app_type": "standard",
      "app_name_label": "K8s",
      "pods": [
        {
          "name": "nginx-deployment-5dbcdf8c6f-g7zfz",
          "namespace": "default",
          "labels": {
            "app": "nginx",
            "app-name": "K8s",
          }
        },
        {
          "name": "nginx-deployment-5dbcdf8c6f-khrdn",
          "namespace": "default",
          "labels": {
            "app": "nginx",
            "app-name": "K8s",
          }
        }
      ],
      "pod_count": 2,
      "namespaces": ["default"]
    }
  ]
}

print("=" * 80)
print("CUSTOM RESOURCE TARGET DIAGNOSIS")
print("=" * 80)

cr = response["apps"][0]
nginx_app = response["apps"][1]

print(f"\n🔍 Custom Resource: {cr['app_name']}")
print(f"   Target: {cr['target_app_kind']}/{cr['target_app_name']}")
print(f"   Target Namespace: {cr['target_app_namespace']}")
print(f"   app_name_label: {cr['app_name_label']}")

print(f"\n📦 Available Apps:")
for app in response["apps"]:
    if app["app_type"] != "custom-resource":
        print(f"   - {app['app_name']} in {app['namespaces']} (pods: {app['pod_count']})")

print(f"\n❌ PROBLEM DETECTED:")
print(f"   CR is looking for '{cr['target_app_name']}' in '{cr['target_app_namespace']}' namespace")
print(f"   But nginx deployment is in 'default' namespace")

print(f"\n✅ SOLUTION 1: Update CR to target nginx in default")
print(f"""
kubectl apply -f - <<EOF
apiVersion: eas.hiro.io/v1
kind: EnergyAwareOrchestration
metadata:
  name: critical-api-service
  namespace: default
spec:
  priority: Critical
  energyConsumption: 100
  forecastWindowDays: 14
  applicationRef:
    apiVersion: apps/v1
    kind: Deployment
    name: nginx           # ← Changed from api-gateway
    namespace: default    # ← Changed from production
EOF
""")

print(f"\n✅ SOLUTION 2: Create api-gateway in production with app-name label")
print(f"""
kubectl create namespace production
kubectl create deployment api-gateway --image=nginx:latest -n production
kubectl patch deployment api-gateway -n production -p '
{{
  "spec": {{
    "template": {{
      "metadata": {{
        "labels": {{
          "app-name": "K8s"
        }}
      }}
    }}
  }}
}}'
""")

print(f"\n💡 TIP: To check what's in your cluster:")
print(f"   kubectl get deployment -A")
print(f"   kubectl get deployment nginx -n default -o yaml")
print(f"   kubectl get energyawareorchestration critical-api-service -n default -o yaml")

print("\n" + "=" * 80)

