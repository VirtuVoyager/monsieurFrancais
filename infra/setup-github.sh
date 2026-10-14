#!/usr/bin/env bash
# One-off: let GitHub Actions deploy main to Azure on every merge. Run from a laptop signed in to
# Azure (`az login`, as the subscription owner) and GitHub (`gh auth login`), with .env in place.
#
# - Creates the resource group and generates the production secrets (kept in .env.azure too).
# - Creates an app registration that GitHub signs in as via OpenID Connect: no Azure password
#   is stored anywhere, and only this repo's "production" environment can use it.
# - Stores the settings as repository variables and the keys as encrypted environment secrets.
set -euo pipefail
cd "$(dirname "$0")/.."

RG="${MF_RESOURCE_GROUP:-monsieur-francais}"
LOCATION="${MF_LOCATION:-centralindia}"
REPO="${MF_GITHUB_REPO:-$(git remote get-url origin | sed -E 's#(git@github.com:|https://github.com/)##; s#\.git$##')}"
NAME="monsieur-francais-deploy"

for tool in az gh openssl; do
  command -v "$tool" >/dev/null || { echo "setup: $tool is not installed" >&2; exit 1; }
done
[ -f .env ] || { echo "setup: .env with the Azure OpenAI and Speech settings is missing" >&2; exit 1; }
set -a
# shellcheck disable=SC1091
. ./.env
set +a

# Generated once. Losing .env.azure is harmless: the values also live in GitHub and Azure, and
# the database password can be reset in the portal.
if [ ! -f .env.azure ]; then
  umask 077
  {
    echo "MF_PG_PASSWORD=$(openssl rand -hex 24)"
    echo "MF_PROD_SECRET_KEY=$(openssl rand -hex 32)"
    echo "MF_PROD_SETUP_CODE=$(openssl rand -hex 4)"
  } > .env.azure
fi
set -a
# shellcheck disable=SC1091
. ./.env.azure
set +a

subscription=$(az account show --query id -o tsv)
tenant=$(az account show --query tenantId -o tsv)
scope=$(az group create --name "$RG" --location "$LOCATION" --query id -o tsv)

client=$(az ad app list --display-name "$NAME" --query "[0].appId" -o tsv)
if [ -z "$client" ]; then
  client=$(az ad app create --display-name "$NAME" --query appId -o tsv)
  az ad sp create --id "$client" --output none
fi
# GitHub's token names the repo either by name or, for newer repositories, by name and numeric
# IDs (repo:Owner@123/repo@456:...). Trust both; each only matches this repo's environment.
ids=$(gh api "repos/$REPO" --jq '"\(.owner.login)@\(.owner.id)/\(.name)@\(.id)"')
existing=$(az ad app federated-credential list --id "$client" --query "[].name" -o tsv)
trust() {
  grep -qx "$1" <<<"$existing" && return
  az ad app federated-credential create --id "$client" --parameters "{
    \"name\": \"$1\",
    \"issuer\": \"https://token.actions.githubusercontent.com\",
    \"subject\": \"repo:$2:environment:production\",
    \"audiences\": [\"api://AzureADTokenExchange\"]
  }" --output none
}
trust production "$REPO"
trust production-ids "$ids"

# On this resource group only: Contributor to create and update everything, plus role assignment
# rights because the template lets the apps pull images from the registry.
for role in Contributor "Role Based Access Control Administrator"; do
  az role assignment create --assignee "$client" --role "$role" --scope "$scope" --output none
done

gh api --method PUT "repos/$REPO/environments/production" --silent
# Optional settings are only stored when .env has them; the template has defaults.
variable() { [ -z "$2" ] || gh variable set "$1" --repo "$REPO" --body "$2"; }
variable AZURE_CLIENT_ID "$client"
variable AZURE_TENANT_ID "$tenant"
variable AZURE_SUBSCRIPTION_ID "$subscription"
variable AZURE_RESOURCE_GROUP "$RG"
variable MF_AZURE_OPENAI_ENDPOINT "$MF_AZURE_OPENAI_ENDPOINT"
variable MF_AZURE_SPEECH_REGION "$MF_AZURE_SPEECH_REGION"
variable MF_BUDGET_EMAIL "${MF_BUDGET_EMAIL:-}"
variable MF_AZURE_OPENAI_TEXT_DEPLOYMENT "${MF_AZURE_OPENAI_TEXT_DEPLOYMENT:-}"
variable MF_AZURE_OPENAI_EMBEDDING_DEPLOYMENT "${MF_AZURE_OPENAI_EMBEDDING_DEPLOYMENT:-}"
variable MF_AZURE_OPENAI_REALTIME_DEPLOYMENT "${MF_AZURE_OPENAI_REALTIME_DEPLOYMENT:-}"

# Read from stdin so no key appears in a command line or the terminal.
secret() { printf '%s' "$2" | gh secret set "$1" --repo "$REPO" --env production; }
secret MF_AZURE_OPENAI_API_KEY "$MF_AZURE_OPENAI_API_KEY"
secret MF_AZURE_SPEECH_KEY "$MF_AZURE_SPEECH_KEY"
secret MF_PG_PASSWORD "$MF_PG_PASSWORD"
secret MF_PROD_SECRET_KEY "$MF_PROD_SECRET_KEY"
secret MF_PROD_SETUP_CODE "$MF_PROD_SETUP_CODE"

echo "Done: $REPO deploys to resource group $RG whenever CI passes on main."
echo "Re-run this after changing a key in .env, then re-run the Deploy workflow."
