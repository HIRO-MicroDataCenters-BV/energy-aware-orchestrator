#!/bin/bash
set -e

echo "🔨 Generating EnergyAwareOrchestration CRD..."
python3 -m app.crd.builder
echo "✅ CRD generation complete!"
