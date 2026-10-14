#!/usr/bin/env bash
# Build both images in Azure and deploy everything; safe to re-run. GitHub Actions runs this on
# every merge to main, with settings from repository variables and secrets. From a laptop it is
# the manual fallback and reads .env and .env.azure (both written or used by `make setup-github`).
set -euo pipefail
cd "$(dirname "$0")/.."

RG="${MF_RESOURCE_GROUP:-monsieur-francais}"

if [ -z "${GITHUB_ACTIONS:-}" ]; then
  # Production runs main; deploying another branch from here would replace what main put there.
  branch=$(git rev-parse --abbrev-ref HEAD)
  if [ "$branch" != main ] && [ -z "${MF_DEPLOY_ANY_BRANCH:-}" ]; then
    echo "deploy: on $branch, not main. Set MF_DEPLOY_ANY_BRANCH=1 to deploy it anyway." >&2
    exit 1
  fi
  if [ ! -f .env ] || [ ! -f .env.azure ]; then
    echo "deploy: needs .env and .env.azure; run make setup-github first" >&2
    exit 1
  fi
  set -a
  # shellcheck disable=SC1091
  . ./.env
  # shellcheck disable=SC1091
  . ./.env.azure
  set +a
fi

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
echo "A first sign-in on a new database asks for the setup code (MF_PROD_SETUP_CODE in .env.azure)."
