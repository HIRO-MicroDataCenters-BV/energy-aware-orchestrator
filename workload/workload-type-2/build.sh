#!/bin/bash

# Build script for workload-type-2 application
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

APP_NAME="workload-type-2"
TAG="v1"
DOCKER_REGISTRY=${DOCKER_REGISTRY:-""}
BUILD_PLATFORM=${BUILD_PLATFORM:-""}

echo "Building $APP_NAME Docker image..."

# Build the Docker image with platform support
if [ -n "$BUILD_PLATFORM" ]; then
    echo "Building for platform: ${BUILD_PLATFORM}"
    docker buildx build --platform "${BUILD_PLATFORM}" -t $APP_NAME:$TAG .
else
    echo "Building for native platform"
    docker build -t $APP_NAME:$TAG .
fi

# Tag for registry if specified
if [ ! -z "$DOCKER_REGISTRY" ]; then
    docker tag $APP_NAME:$TAG $DOCKER_REGISTRY:$APP_NAME-$TAG
    echo "Tagged image as $DOCKER_REGISTRY:$APP_NAME-$TAG"
    
    echo "Pushing to registry..."
    docker push $DOCKER_REGISTRY:$APP_NAME-$TAG
    echo "Image pushed to registry successfully!"
fi

echo "Build completed successfully!"
echo "Image: $APP_NAME:$TAG"

# Show image size
docker images $APP_NAME:$TAG --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"