#!/bin/bash

# Script to build and run the Angular SSR application in Docker

set -e

echo "Building Docker image..."
docker build -t orchestrator-ui:latest .

echo "\nDocker image built successfully!"

echo "\nStarting container..."
docker run -p 4000:4000 --name orchestrator-ui orchestrator-ui:latest

# The container will keep running in the foreground
# Press Ctrl+C to stop it