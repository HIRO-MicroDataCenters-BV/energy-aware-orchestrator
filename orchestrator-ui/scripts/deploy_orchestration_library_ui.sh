#!/bin/bash

CLUSTER_NAME=${1:-sample}

ORCHRESTRATION_LIBRARY_UI_CHART_PATH="./charts/orchestrator-library-ui"
ORCHRESTRATION_LIBRARY_UI_NAMESPACE="aces-orchestrator-library-ui"
ORCHRESTRATION_LIBRARY_UI_RELEASE_NAME="aces-orchestrator-library-ui"
ORCHRESTRATION_LIBRARY_UI_APP_NAME="aces-orchestrator-library-ui"
ORCHRESTRATION_LIBRARY_UI_IMAGE_NAME="orchestrator-library-ui"
ORCHRESTRATION_LIBRARY_UI_IMAGE_TAG="alpha1"

if [ -z "$CLUSTER_NAME" ]; then
  echo "Usage: $0 <cluster-name> <docker-user> <docker-password>"
  exit 1
fi

echo "Build Docker image"
docker build -t $ORCHRESTRATION_LIBRARY_UI_IMAGE_NAME:$ORCHRESTRATION_LIBRARY_UI_IMAGE_TAG -f Dockerfile .

echo "Set the kubectl context to $CLUSTER_NAME cluster"
kubectl cluster-info --context kind-$CLUSTER_NAME
kubectl config use-context kind-$CLUSTER_NAME

echo "Load Image to Kind cluster named '$CLUSTER_NAME'"
kind load docker-image --name $CLUSTER_NAME $ORCHRESTRATION_LIBRARY_UI_IMAGE_NAME:$ORCHRESTRATION_LIBRARY_UI_IMAGE_TAG

echo "Deploy the $ORCHRESTRATION_LIBRARY_UI_RELEASE_NAME to the Kind cluster"
helm upgrade --install $ORCHRESTRATION_LIBRARY_UI_RELEASE_NAME $ORCHRESTRATION_LIBRARY_UI_CHART_PATH \
  --namespace $ORCHRESTRATION_LIBRARY_UI_NAMESPACE \
  --create-namespace \
  --set app.name=$ORCHRESTRATION_LIBRARY_UI_APP_NAME \
  --set app.image.repository=$ORCHRESTRATION_LIBRARY_UI_IMAGE_NAME \
  --set app.image.tag=$ORCHRESTRATION_LIBRARY_UI_IMAGE_TAG \
  --set namespace=$ORCHRESTRATION_LIBRARY_UI_NAMESPACE \
  --set app.image.pullPolicy=IfNotPresent \
  --set app.service.type=NodePort \
  --set app.service.port=4000 \
  --set app.service.nodePort=30010 \
  --set dummyRedeployTimestamp=$(date +%s)
  # set to pullPolicy=IfNotPresent to avoid pulling the image from the registry only for kind cluster
  # set dummyRedeployTimestamp to force redeploy

echo "Wait for the $ORCHRESTRATION_LIBRARY_UI_APP_NAME to be ready"
kubectl wait --for=condition=available --timeout=60s deployment/$ORCHRESTRATION_LIBRARY_UI_APP_NAME -n $ORCHRESTRATION_LIBRARY_UI_NAMESPACE --context kind-$CLUSTER_NAME

echo "Get the $ORCHRESTRATION_LIBRARY_UI_APP_NAME service"
kubectl get service -n $ORCHRESTRATION_LIBRARY_UI_APP_NAME --context kind-$CLUSTER_NAME

