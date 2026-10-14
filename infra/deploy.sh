#!/usr/bin/env bash
# Build both images in Azure and deploy everything. Safe to re-run: the first run creates the
# resources, later runs ship new images. Needs the Azure CLI (`az login`) and the repo's .env.
set -euo pipefail
cd "$(dirname "$0")/.."

RG="${MF_RESOURCE_GROUP:-monsieur-francais}"

# Production runs main (GitHub Actions ships it after CI); deploying another branch from here
# would replace what main put there.
branch=$(git rev-parse --abbrev-ref HEAD)
if [ "$branch" != main ] && [ -z "${MF_DEPLOY_ANY_BRANCH:-}" ]; then
  echo "deploy: on $branch, not main. Set MF_DEPLOY_ANY_BRANCH=1 to deploy it anyway." >&2
  exit 1
fi
LOCATION="${MF_LOCATION:-centralindia}"
SECRETS=.env.azure

if [ ! -f .env ]; then
  echo "deploy: .env with the Azure OpenAI and Speech keys is missing" >&2
  exit 1
fi
set -a
# shellcheck disable=SC1091
. ./.env
set +a

# Generated once and kept locally (gitignored); losing them only means signing in again
# (secret key) or resetting the database password in the portal.
if [ ! -f "$SECRETS" ]; then
  umask 077
  {
    echo "MF_PG_PASSWORD=$(openssl rand -hex 24)"
    echo "MF_PROD_SECRET_KEY=$(openssl rand -hex 32)"
    echo "MF_PROD_SETUP_CODE=$(openssl rand -hex 4)"
  } > "$SECRETS"
fi
set -a
# shellcheck disable=SC1090
. "./$SECRETS"
set +a

deploy() {
  az deployment group create --resource-group "$RG" --name monsieur \
    --template-file infra/main.bicep \
    --parameters \
      deployApps="$1" apiImage="${2:-}" webImage="${3:-}" \
      minReplicas="${MF_MIN_REPLICAS:-0}" \
      budgetEmail="${MF_BUDGET_EMAIL:-}" \
      postgresPassword="$MF_PG_PASSWORD" \
      secretKey="$MF_PROD_SECRET_KEY" \
      setupCode="$MF_PROD_SETUP_CODE" \
      azureOpenAiEndpoint="$MF_AZURE_OPENAI_ENDPOINT" \
      azureOpenAiKey="$MF_AZURE_OPENAI_API_KEY" \
      azureOpenAiTextDeployment="${MF_AZURE_OPENAI_TEXT_DEPLOYMENT:-gpt-5.4-mini}" \
      azureOpenAiEmbeddingDeployment="${MF_AZURE_OPENAI_EMBEDDING_DEPLOYMENT:-text-embedding-3-small}" \
      azureOpenAiRealtimeDeployment="${MF_AZURE_OPENAI_REALTIME_DEPLOYMENT:-gpt-realtime-2.1-mini}" \
      azureSpeechKey="$MF_AZURE_SPEECH_KEY" \
      azureSpeechRegion="$MF_AZURE_SPEECH_REGION" \
    --query properties.outputs --output json
}

output() { python3 -c "import json,sys; print(json.load(sys.stdin)['$1']['value'])"; }

az group create --name "$RG" --location "$LOCATION" --output none
echo "Creating or updating the shared resources (the first run takes about 10 minutes)…"
outputs=$(deploy false)
registry=$(echo "$outputs" | output registryName)

tag=$(git rev-parse --short HEAD)
echo "Building images $tag in Azure…"
az acr build --registry "$registry" --image "mf-api:$tag" --file api/Dockerfile . --output none
az acr build --registry "$registry" --image "mf-web:$tag" \
  --build-arg API_URL="http://$(echo "$outputs" | output apiName)" --file web/Dockerfile web --output none

echo "Deploying the apps…"
server=$(echo "$outputs" | output registryServer)
outputs=$(deploy true "$server/mf-api:$tag" "$server/mf-web:$tag")
echo
echo "Live at $(echo "$outputs" | output webUrl)"
echo "First sign-in on a new database asks for the setup code: MF_PROD_SETUP_CODE in $SECRETS."
