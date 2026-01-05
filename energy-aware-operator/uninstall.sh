#!/bin/bash
set -e

# Simple Uninstall Script
# Just run: ./uninstall.sh

echo "Uninstalling Energy-Aware Operator..."
echo ""

# Delete custom resources
echo "Deleting custom resources..."
kubectl delete eao --all --ignore-not-found=true > /dev/null 2>&1
echo "✓ Custom resources deleted"

# Uninstall Helm release
echo "Uninstalling operator..."
helm uninstall energy-operator --ignore-not-found > /dev/null 2>&1
echo "✓ Operator uninstalled"

echo ""
echo "✅ Uninstall complete!"
echo ""
echo "To remove CRD (optional):"
echo "  kubectl delete crd energyawareorchestrations.eas.hiro.io"
echo ""


