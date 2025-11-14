#!/bin/bash

# Build script for workload-type-1 Docker image
#
# Environment variables:
#   DOCKER_REGISTRY - Registry to push image to (optional)
#   BUILD_PLATFORM  - Target platform for multi-arch builds (optional)
#                    Use "linux/amd64" for remote clusters from ARM64 dev machines
#
# Examples:
#   ./build.sh                                           # Native build
#   BUILD_PLATFORM=linux/amd64 ./build.sh              # AMD64 build for remote clusters  
#   DOCKER_REGISTRY=hiroregistry/shift2dc ./build.sh   # Build and push to registry
#   BUILD_PLATFORM=linux/amd64 DOCKER_REGISTRY=hiroregistry/shift2dc ./build.sh # Multi-arch + push

set -e

IMAGE_NAME="workload-type-1"
IMAGE_TAG="v1"
DOCKER_REGISTRY=${DOCKER_REGISTRY:-""}
BUILD_PLATFORM=${BUILD_PLATFORM:-""}
FULL_IMAGE_NAME="${IMAGE_NAME}:${IMAGE_TAG}"

echo "Building Docker image: ${FULL_IMAGE_NAME}"

# Build the Docker image with platform support
if [ -n "$BUILD_PLATFORM" ]; then
    echo "Building for platform: ${BUILD_PLATFORM}"
    docker buildx build --platform "${BUILD_PLATFORM}" -t "${FULL_IMAGE_NAME}" .
else
    echo "Building for native platform"
    docker build -t "${FULL_IMAGE_NAME}" .
fi

echo "Docker image built successfully: ${FULL_IMAGE_NAME}"

# Tag for registry if specified
if [ ! -z "$DOCKER_REGISTRY" ]; then
    docker tag "${FULL_IMAGE_NAME}" "${DOCKER_REGISTRY}:${IMAGE_NAME}-${IMAGE_TAG}"
    echo "Tagged image as ${DOCKER_REGISTRY}:${IMAGE_NAME}-${IMAGE_TAG}"
    
    echo "Pushing to registry..."
    docker push "${DOCKER_REGISTRY}:${IMAGE_NAME}-${IMAGE_TAG}"
    echo "Image pushed to registry successfully!"
fi

# Check if running on minikube
if command -v minikube &> /dev/null && minikube status &> /dev/null; then
    echo "Minikube detected. Loading image into minikube..."
    minikube image load "${FULL_IMAGE_NAME}"
    echo "Image loaded into minikube successfully"
else
    echo "Minikube not detected or not running. Image built locally."
fi

echo "Build completed successfully!"
echo "Image: ${FULL_IMAGE_NAME}"
echo ""
echo "To deploy to Kubernetes, run:"
echo "  ./deploy.sh"