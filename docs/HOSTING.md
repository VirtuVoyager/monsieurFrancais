# Hosting on Azure (single owner)

The app as it is today, hosted for one person (the owner) and used mostly from a phone. Multi-user
work, the tutor features and the examiner module come later ([DEPLOYMENT.md](DEPLOYMENT.md)).

## What runs where

| Piece | Azure resource | Size | Rough cost a month |
|---|---|---|---|
| Web (Next.js) | Container App, public HTTPS | 0.25 vCPU, 0.5 GiB, sleeps when unused | 0–2 USD (inside the monthly free grant) |
| API (FastAPI + background jobs) | Container App, internal only | 0.5 vCPU, 1 GiB, one replica, sleeps when unused | 0–3 USD |
| Database | PostgreSQL Flexible Server, Burstable B1ms, 32 GB, pgvector | 7-day point-in-time backups | ~16 USD; free for 12 months while the free-account offer lasts (portal → "Free services" lists it with hours left) |
| Media (audio, recordings, notes) | Storage account, Azure Files share mounted at `/app/media` | 20 GB quota, 7-day soft delete | < 0.50 USD |
| Images | Container Registry, Basic | | ~5 USD |
| Logs | Log Analytics, 30-day retention, 0.15 GB daily cap | | 0 (inside the 5 GB free allowance) |
| AI | Your existing Azure OpenAI and Speech resources | unchanged | capped in the app's Budget screen |

About **21 USD a month** for hosting, or about 5 USD while the database free tier lasts. These are
list prices from memory: check them in the Azure pricing calculator for your region.

Choices worth knowing:

- **Sleeping apps.** With `minReplicas` 0 both apps stop after a few idle minutes and cost nothing.
  The first visit after a pause takes 10–20 s while the API migrates, seeds and starts. Background
  jobs (retrying deferred grading, note audio, embeddings) run only while the API is awake, and
  catch up when it wakes. Setting the repository variable `MF_MIN_REPLICAS` to 1 keeps both warm for about 10 USD more.
- **Region.** `centralindia` by default, close to you; Azure OpenAI and Speech stay in `eastus`.
  Set `MF_LOCATION` before the first deploy to change it.
- **The API is not public.** Only the web app has an address; it proxies `/api` and
  `/media/catalog` to the API inside the Container Apps environment.
- **Database access.** Public endpoint limited to Azure services, with TLS and a generated
  password. A private network would cost more than everything else combined.
- **Custom domain.** Optional. Container Apps gives the default `*.azurecontainerapps.io` address
  free HTTPS, which is all the microphone needs. A domain of your own costs only its registration
  (about 10–15 USD a year) and Azure issues the certificate free (see below).
- **Feature flags.** Not yet. You are the owner (`users.role = owner`): every module is open and
  every feature is on. Who-gets-what arrives with invited users (DEPLOYMENT.md § 2), where the
  per-user budget caps already block spending by anyone with a cap of 0.

## How code reaches production

`main` is production. Work lands on `virtuvoyager_dev`, then a PR from `virtuvoyager_dev` to
`main`. When it merges and CI passes on `main`, the **Deploy** workflow runs `infra/deploy.sh`:
it creates or updates every Azure resource from `infra/main.bicep`, builds both images in Azure
and rolls them out (migrations run when the new API starts). **Actions → Deploy → Run workflow**
redeploys by hand, and the `production` environment in the repo settings can require your
approval before each deploy.

GitHub signs in to Azure with OpenID Connect, so no Azure password is stored anywhere. Your
Azure OpenAI and Speech keys and the generated database password, session key and setup code are
encrypted secrets of the `production` environment; the endpoint, region and resource group are
plain repository variables.

## One-time setup (laptop)

GitHub cannot grant itself access to your Azure subscription, so this is done once by you, signed
in as the subscription owner, from the repo root with `.env` holding your Azure OpenAI and Speech
settings:

1. Install the tools, sign in and register the Azure services:

   ```bash
   brew install azure-cli gh libpq && brew link --force libpq   # libpq gives pg_dump/pg_restore
   az login && az account set --subscription "<your subscription>"
   gh auth login
   for ns in Microsoft.App Microsoft.OperationalInsights Microsoft.DBforPostgreSQL \
             Microsoft.ContainerRegistry Microsoft.Storage Microsoft.ManagedIdentity; do
     az provider register --namespace $ns
   done
   ```

2. Connect GitHub to Azure. `MF_BUDGET_EMAIL` adds a monthly budget alert on the resource group
   (30 USD by default):

   ```bash
   MF_BUDGET_EMAIL=you@example.com make setup-github
   ```

   It creates the `monsieur-francais` resource group, generates the production secrets (also kept
   in the gitignored `.env.azure`; never commit it), creates an app registration that only this
   repo's `production` environment can sign in as, with rights on that resource group only, and
   stores the variables and secrets in GitHub.

3. Merge `virtuvoyager_dev` into `main`. The first Deploy run takes about 15 minutes and prints the
   address in the run summary.

4. Copy your data, so the hosted app has your progress, notes, glossaries and generated audio
   (run `make audio` first so every clip goes along):

   ```bash
   make deploy-data
   ```

   It opens the database to your current IP for the copy only, replaces the hosted database with
   your local one, uploads `media/` and restarts the API.

5. Open the address on your phone, sign in with your usual passphrase, then **Share → Add to Home
   Screen** (Safari) or **Install app** (Chrome) for a full-screen app.

   If you skip step 4, the hosted database starts empty: the first sign-in asks for a new
   passphrase and the setup code (`MF_PROD_SETUP_CODE` in `.env.azure`), so nobody else who finds
   the address can claim the account.

## Updating

Merge to `main`; that is all, including changes under `infra/`. After changing a key in `.env`,
re-run `make setup-github` (it updates the GitHub secrets) and then the Deploy workflow.
`make deploy` runs the same deployment from a laptop as a fallback; it refuses to run from a
branch other than `main` (`MF_DEPLOY_ANY_BRANCH=1` overrides).

Content pipeline jobs run against the hosted database and media from inside the API container:

```bash
az containerapp exec -g monsieur-francais -n mf-api --command "python -m app.jobs.generate_audio"
az containerapp exec -g monsieur-francais -n mf-api --command "python -m app.jobs.build_glossaries"
```

## Custom domain (optional)

Buy a domain anywhere, then:

```bash
az containerapp hostname add -g monsieur-francais -n mf-web --hostname french.example.com
# Add the CNAME (to the app's default address) and the TXT asuid record the command prints, then:
az containerapp hostname bind -g monsieur-francais -n mf-web --hostname french.example.com \
  --environment mf-env --validation-method CNAME
```

## When something is wrong

```bash
az containerapp logs show -g monsieur-francais -n mf-api --follow     # API, jobs, migrations
az containerapp logs show -g monsieur-francais -n mf-web --follow
az containerapp revision list -g monsieur-francais -n mf-api -o table
```

- **Restore the database:** Portal → the PostgreSQL server → Backup and restore (any point in the
  last 7 days, into a new server).
- **Restore a deleted file share:** Portal → storage account → File shares → Show deleted.
- **Tear everything down:** `az group delete -n monsieur-francais`. Your local copy is untouched.
