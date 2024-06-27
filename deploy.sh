#!/usr/bin/env zsh

set -e

VERSION=$(git rev-parse --short HEAD)
echo "Deploying version $VERSION"

# 1. Build the Docker Image
echo "Building Docker image..."
docker build -t policywonkcontainers.azurecr.io/policyacquisition:$VERSION .

# 2. Fetch registry credentials
echo "Fetching Azure Container Registry credentials..."
REGISTRY_NAME="policywonkcontainers"
ACR_CREDENTIALS=$(az acr credential show --name $REGISTRY_NAME --query "{username:username, password:passwords[0].value}" -o tsv)
ACR_USERNAME=$(echo $ACR_CREDENTIALS | cut -f1)
ACR_PASSWORD=$(echo $ACR_CREDENTIALS | cut -f2)

# 3. Login to Azure Container Registry using fetched credentials
echo "Logging into Azure Container Registry..."
echo $ACR_PASSWORD | docker login policywonkcontainers.azurecr.io -u $ACR_USERNAME --password-stdin

# 4. Push the Docker Image
echo "Pushing Docker image..."
docker push policywonkcontainers.azurecr.io/policyacquisition:$VERSION

# 5. Prepare environment variable arguments for `az container create`
ENV_VARS=""
while IFS= read -r line; do
  IFS='=' read -r key value <<< "$line"
  ENV_VARS+="'$key'='$value' "
done < .env.prod

# Remove trailing space
ENV_VARS=$(echo $ENV_VARS | sed 's/ *$//g')

# 5. Update the Azure Container Instance
echo "Updating Azure Container Instance..."
echo "az container create \
  --resource-group policy \
  --name policyacquisition \
  --cpu 1 \
  --memory 8 \
  --restart-policy OnFailure \
  --image policywonkcontainers.azurecr.io/policyacquisition:$VERSION \
  --registry-login-server policywonkcontainers.azurecr.io \
  --registry-username $ACR_USERNAME \
  --registry-password $ACR_PASSWORD \
  --environment-variables $ENV_VARS"

az container create \
  --resource-group policy \
  --name policyacquisition \
  --cpu 1 \
  --memory 8 \
  --restart-policy OnFailure \
  --image policywonkcontainers.azurecr.io/policyacquisition:$VERSION \
  --registry-login-server policywonkcontainers.azurecr.io \
  --registry-username $ACR_USERNAME \
  --registry-password $ACR_PASSWORD \
  --environment-variables $ENV_VARS

echo "Deployment of version $VERSION completed."