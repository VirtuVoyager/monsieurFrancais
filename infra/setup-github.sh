#!/usr/bin/env bash
# One-off, after the first `make deploy`: let GitHub Actions deploy main without storing any
# Azure secret. Creates an app registration that trusts this repo's "production" environment
# (OpenID Connect) and may only manage the app's resource group, then sets the repo variables.
set -euo pipefail
cd "$(dirname "$0")/.."

RG="${MF_RESOURCE_GROUP:-monsieur-francais}"
REPO="${MF_GITHUB_REPO:-$(git remote get-url origin | sed -E 's#(git@github.com:|https://github.com/)##; s#\.git$##')}"
NAME="monsieur-francais-deploy"

subscription=$(az account show --query id -o tsv)
tenant=$(az account show --query tenantId -o tsv)
scope=$(az group show -n "$RG" --query id -o tsv)

client=$(az ad app list --display-name "$NAME" --query "[0].appId" -o tsv)
if [ -z "$client" ]; then
  client=$(az ad app create --display-name "$NAME" --query appId -o tsv)
  az ad sp create --id "$client" --output none
fi

if ! az ad app federated-credential list --id "$client" --query "[].name" -o tsv | grep -qx production; then
  az ad app federated-credential create --id "$client" --parameters "{
    \"name\": \"production\",
    \"issuer\": \"https://token.actions.githubusercontent.com\",
    \"subject\": \"repo:$REPO:environment:production\",
    \"audiences\": [\"api://AzureADTokenExchange\"]
  }" --output none
fi

# Contributor on the resource group only: build images (ACR Tasks) and update the apps.
az role assignment create --assignee "$client" --role Contributor --scope "$scope" --output none

echo "Trusting GitHub repo $REPO, environment 'production'."
if command -v gh >/dev/null; then
  gh api --method PUT "repos/$REPO/environments/production" --silent
  gh variable set AZURE_CLIENT_ID --repo "$REPO" --body "$client"
  gh variable set AZURE_TENANT_ID --repo "$REPO" --body "$tenant"
  gh variable set AZURE_SUBSCRIPTION_ID --repo "$REPO" --body "$subscription"
  gh variable set AZURE_RESOURCE_GROUP --repo "$REPO" --body "$RG"
  echo "Repository variables set. Merges to main now deploy after CI passes."
else
  echo "Install the GitHub CLI (brew install gh) and re-run, or add these repository variables"
  echo "under Settings → Secrets and variables → Actions → Variables, and create an"
  echo "environment named 'production' under Settings → Environments:"
  echo "  AZURE_CLIENT_ID=$client"
  echo "  AZURE_TENANT_ID=$tenant"
  echo "  AZURE_SUBSCRIPTION_ID=$subscription"
  echo "  AZURE_RESOURCE_GROUP=$RG"
fi
