#!/usr/bin/env zsh

set -e

VERSION=$(git rev-parse --short HEAD)
echo "Deploying version $VERSION"

# 1. Build the Docker Image
echo "Building Docker image..."
docker build -t policywonkcontainers.azurecr.io/policyacquisition:$VERSION .

# 2. Login to Azure Container Registry
echo "Logging into Azure Container Registry..."
az acr login --name PolicyWonkContainers

# 3. Push the Docker Image
echo "Pushing Docker image..."
docker push policywonkcontainers.azurecr.io/policyacquisition:$VERSION

# 4. Update the Azure Container Instance
echo "Updating Azure Container Instance..."
az container create \
  --resource-group policy \
  --name policyacquisition \
  --image policywonkcontainers.azurecr.io/policyacquisition:$VERSION

echo "Deployment of version $VERSION completed."