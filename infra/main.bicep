// Monsieur Français on Azure, sized for one learner and cheap to leave running.
// Deployed by infra/deploy.sh; see docs/DEPLOYMENT.md for the runbook and costs.

@description('Region for everything here. Azure OpenAI and Speech stay where they already are.')
param location string = resourceGroup().location

@description('Short prefix for resource names.')
param prefix string = 'mf'

@description('false on the very first run, before any image exists in the registry.')
param deployApps bool = true

param apiImage string = ''
param webImage string = ''

@description('0 lets both apps sleep when unused (free, with a cold start of a few seconds); 1 keeps them warm for roughly 10 USD a month more.')
@minValue(0)
@maxValue(1)
param minReplicas int = 0

@secure()
param postgresPassword string
@secure()
param secretKey string
@secure()
param setupCode string

param azureOpenAiEndpoint string
@secure()
param azureOpenAiKey string
param azureOpenAiTextDeployment string = 'gpt-5.4-mini'
param azureOpenAiEmbeddingDeployment string = 'text-embedding-3-small'
param azureOpenAiRealtimeDeployment string = 'gpt-realtime-2.1-mini'
@secure()
param azureSpeechKey string
param azureSpeechRegion string

param timezone string = 'Asia/Kolkata'

@description('Monthly budget for this resource group in USD; AI spend is capped inside the app.')
param budgetUsd int = 30
@description('Where Azure sends budget alerts. Empty skips the budget.')
param budgetEmail string = ''
param budgetStart string = utcNow('yyyy-MM-01')

var suffix = uniqueString(resourceGroup().id)
var apiName = '${prefix}-api'

resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${prefix}-logs'
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
    // Far below the 5 GB monthly free allowance; a runaway log loop cannot cost money.
    workspaceCapping: { dailyQuotaGb: json('0.15') }
  }
}

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: '${prefix}${suffix}'
  location: location
  sku: { name: 'Basic' }
  properties: { adminUserEnabled: false }
}

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${prefix}-apps'
  location: location
}

var acrPull = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '7f951dda-4ed3-4680-a7ca-43fe172d538d'
)

resource pull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, identity.id, acrPull)
  scope: registry
  properties: {
    roleDefinitionId: acrPull
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: '${prefix}media${suffix}'
  location: location
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
  }
}

resource files 'Microsoft.Storage/storageAccounts/fileServices@2023-05-01' = {
  parent: storage
  name: 'default'
  properties: {
    // Deleted recordings or clips can be restored for a week.
    shareDeleteRetentionPolicy: { enabled: true, days: 7 }
  }
}

// Mounted at /app/media: catalogue audio, speaking recordings, uploaded notes.
resource mediaShare 'Microsoft.Storage/storageAccounts/fileServices/shares@2023-05-01' = {
  parent: files
  name: 'media'
  properties: { shareQuota: 20, accessTier: 'TransactionOptimized' }
}

resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: '${prefix}-db-${suffix}'
  location: location
  sku: { name: 'Standard_B1ms', tier: 'Burstable' }
  properties: {
    version: '16'
    administratorLogin: 'mfadmin'
    administratorLoginPassword: postgresPassword
    storage: { storageSizeGB: 32, autoGrow: 'Disabled' }
    backup: { backupRetentionDays: 7, geoRedundantBackup: 'Disabled' }
    highAvailability: { mode: 'Disabled' }
    network: { publicNetworkAccess: 'Enabled' }
  }
}

// The knowledge base needs these; Azure only allows extensions listed here.
resource extensions 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2024-08-01' = {
  parent: postgres
  name: 'azure.extensions'
  properties: { value: 'VECTOR,UNACCENT,PG_TRGM', source: 'user-override' }
}

resource database 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2024-08-01' = {
  parent: postgres
  name: 'mf'
  dependsOn: [extensions]
}

// 0.0.0.0 means "Azure services"; a private network would cost more than everything else
// here combined. The password and TLS protect the connection.
resource azureAccess 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2024-08-01' = {
  parent: postgres
  name: 'azure-services'
  properties: { startIpAddress: '0.0.0.0', endIpAddress: '0.0.0.0' }
}

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${prefix}-env'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logs.properties.customerId
        sharedKey: logs.listKeys().primarySharedKey
      }
    }
  }
}

resource environmentMedia 'Microsoft.App/managedEnvironments/storages@2024-03-01' = {
  parent: environment
  name: 'media'
  properties: {
    azureFile: {
      accountName: storage.name
      accountKey: storage.listKeys().keys[0].value
      shareName: mediaShare.name
      accessMode: 'ReadWrite'
    }
  }
}

var databaseUrl = 'postgresql+psycopg://mfadmin:${postgresPassword}@${postgres.properties.fullyQualifiedDomainName}:5432/mf?sslmode=require'
var providers = ['GRADER', 'NOTES', 'GLOSSARY', 'EMBEDDING', 'SPEECH', 'REALTIME']

resource api 'Microsoft.App/containerApps@2024-03-01' = if (deployApps) {
  name: apiName
  location: location
  identity: { type: 'UserAssigned', userAssignedIdentities: { '${identity.id}': {} } }
  dependsOn: [pull, database, azureAccess]
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      activeRevisionsMode: 'Single'
      // Internal only: the web app proxies /api and /media, so the API has no public address.
      ingress: { external: false, targetPort: 8000, transport: 'http' }
      registries: [{ server: registry.properties.loginServer, identity: identity.id }]
      secrets: [
        { name: 'database-url', value: databaseUrl }
        { name: 'secret-key', value: secretKey }
        { name: 'setup-code', value: setupCode }
        { name: 'openai-key', value: azureOpenAiKey }
        { name: 'speech-key', value: azureSpeechKey }
      ]
    }
    template: {
      containers: [
        {
          name: 'api'
          image: apiImage
          resources: { cpu: json('0.5'), memory: '1Gi' }
          env: concat(
            [
              { name: 'MF_DATABASE_URL', secretRef: 'database-url' }
              { name: 'MF_SECRET_KEY', secretRef: 'secret-key' }
              { name: 'MF_SETUP_CODE', secretRef: 'setup-code' }
              { name: 'MF_COOKIE_SECURE', value: 'true' }
              { name: 'MF_TIMEZONE', value: timezone }
              { name: 'MF_AZURE_OPENAI_ENDPOINT', value: azureOpenAiEndpoint }
              { name: 'MF_AZURE_OPENAI_API_KEY', secretRef: 'openai-key' }
              { name: 'MF_AZURE_OPENAI_TEXT_DEPLOYMENT', value: azureOpenAiTextDeployment }
              { name: 'MF_AZURE_OPENAI_EMBEDDING_DEPLOYMENT', value: azureOpenAiEmbeddingDeployment }
              { name: 'MF_AZURE_OPENAI_REALTIME_DEPLOYMENT', value: azureOpenAiRealtimeDeployment }
              { name: 'MF_AZURE_SPEECH_KEY', secretRef: 'speech-key' }
              { name: 'MF_AZURE_SPEECH_REGION', value: azureSpeechRegion }
            ],
            map(providers, p => { name: 'MF_${p}_PROVIDER', value: 'azure' })
          )
          volumeMounts: [{ volumeName: 'media', mountPath: '/app/media' }]
          probes: [
            // Migrations and the idempotent seed run before the server starts listening.
            {
              type: 'Startup'
              httpGet: { path: '/health', port: 8000 }
              periodSeconds: 5
              failureThreshold: 36
            }
            { type: 'Liveness', httpGet: { path: '/health', port: 8000 }, periodSeconds: 30 }
          ]
        }
      ]
      // One replica: the background jobs run inside the API process and must not run twice.
      scale: { minReplicas: minReplicas, maxReplicas: 1 }
      volumes: [{ name: 'media', storageType: 'AzureFile', storageName: environmentMedia.name }]
    }
  }
}

resource web 'Microsoft.App/containerApps@2024-03-01' = if (deployApps) {
  name: '${prefix}-web'
  location: location
  identity: { type: 'UserAssigned', userAssignedIdentities: { '${identity.id}': {} } }
  dependsOn: [pull, api]
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: { external: true, targetPort: 3000, transport: 'auto', allowInsecure: false }
      registries: [{ server: registry.properties.loginServer, identity: identity.id }]
    }
    template: {
      containers: [
        {
          name: 'web'
          image: webImage
          resources: { cpu: json('0.25'), memory: '0.5Gi' }
        }
      ]
      scale: { minReplicas: minReplicas, maxReplicas: 2 }
    }
  }
}

resource budget 'Microsoft.Consumption/budgets@2023-11-01' = if (!empty(budgetEmail)) {
  name: '${prefix}-monthly'
  properties: {
    category: 'Cost'
    amount: budgetUsd
    timeGrain: 'Monthly'
    timePeriod: { startDate: budgetStart }
    notifications: {
      actual80: {
        enabled: true
        operator: 'GreaterThanOrEqualTo'
        threshold: 80
        contactEmails: [budgetEmail]
      }
      forecast100: {
        enabled: true
        operator: 'GreaterThanOrEqualTo'
        threshold: 100
        thresholdType: 'Forecasted'
        contactEmails: [budgetEmail]
      }
    }
  }
}

output registryName string = registry.name
output registryServer string = registry.properties.loginServer
output apiName string = apiName
output postgresServer string = postgres.name
output postgresHost string = postgres.properties.fullyQualifiedDomainName
output storageAccount string = storage.name
output webUrl string = deployApps ? 'https://${web!.properties.configuration.ingress.fqdn}' : ''
