#!/usr/bin/env bash
# One-off: copy your local database and media (progress, notes, generated audio, recordings)
# into Azure, replacing what is there. Needs pg_dump/pg_restore 16+ and the Azure CLI.
set -euo pipefail
cd "$(dirname "$0")/.."

RG="${MF_RESOURCE_GROUP:-monsieur-francais}"
LOCAL_DB="${MF_LOCAL_DB:-postgresql://mf:mf@localhost:5432/mf}"
set -a
# shellcheck disable=SC1091
. ./.env.azure
set +a

out() {
  az deployment group show --resource-group "$RG" --name monsieur \
    --query "properties.outputs.$1.value" --output tsv
}
server=$(out postgresServer)
host=$(out postgresHost)
account=$(out storageAccount)
api=$(out apiName)

# Open the database to this machine only for the copy.
ip=$(curl -s https://api.ipify.org)
az postgres flexible-server firewall-rule create --resource-group "$RG" --server-name "$server" \
  --name copy-data --start-ip-address "$ip" --end-ip-address "$ip" --output none
trap 'az postgres flexible-server firewall-rule delete --resource-group "$RG" --server-name "$server" --name copy-data --yes --output none' EXIT

echo "Copying the database…"
if ! pg_dump --format=custom --no-owner --no-acl "$LOCAL_DB" \
  | PGPASSWORD="$MF_PG_PASSWORD" pg_restore --clean --if-exists --no-owner --no-acl \
      --dbname "host=$host port=5432 dbname=mf user=mfadmin sslmode=require"; then
  echo "pg_restore reported errors above. Ownership notices are harmless; anything else is not." >&2
fi

echo "Copying media…"
key=$(az storage account keys list --resource-group "$RG" --account-name "$account" \
  --query "[0].value" --output tsv)
az storage file upload-batch --account-name "$account" --account-key "$key" \
  --destination media --source media --output none

# A fresh start re-runs migrations and the seed against the copied data.
revision=$(az containerapp revision list --resource-group "$RG" --name "$api" \
  --query "[?properties.active].name | [0]" --output tsv)
az containerapp revision restart --resource-group "$RG" --name "$api" --revision "$revision" \
  --output none
echo "Done. Sign in with the same passphrase you use locally."
