
#!/bin/bash

# Check if API key argument is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <OPENAI_API_KEY>"
    echo "Example: $0 sk-your-openai-api-key-here"
    exit 1
fi

OPENAI_API_KEY=$1

# Azure Login
az login

# Login to Azure Container Registry
az acr login --name nenosys

# Build Docker image for amd64 architecture (Azure Container Instances compatibility)
docker build --platform linux/amd64 -t logbotai .

# Tag the image for Azure Container Registry
docker tag logbotai nenosys.azurecr.io/logbotai:latest

# Push the image to Azure Container Registry
docker push nenosys.azurecr.io/logbotai:latest

# Delete existing container instance (if exists)
az container delete --resource-group neno-ai-sweden-central --name logbotai --yes

# Get registry password for authentication
REGISTRY_PASSWORD=$(az acr credential show --name nenosys --query "passwords[0].value" --output tsv)

# Create new container instance with the updated image
az container create \
  --resource-group neno-ai-sweden-central \
  --name logbotai \
  --image nenosys.azurecr.io/logbotai:latest \
  --ports 8000 \
  --ip-address Public \
  --cpu 2 \
  --memory 4 \
  --registry-login-server nenosys.azurecr.io \
  --registry-username nenosys \
  --os-type Linux \
  --registry-password $REGISTRY_PASSWORD \
  --environment-variables PYTHONUNBUFFERED=1 \
  --secure-environment-variables OPENAI_API_KEY=$OPENAI_API_KEY

# Show container details (optional)
az container show --resource-group neno-ai-sweden-central --name logbotai --query "{FQDN:ipAddress.fqdn,ProvisioningState:provisioningState}" --out table