param appName string
param location string
param containerImage string
param registryLoginServer string
param storageAccountName string
param fileShareName string

@secure()
param storageAccountKey string

@secure()
param openAiApiKey string = ''

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: '${appName}-logs'
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${appName}-insights'
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

resource environment 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: '${appName}-env'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

// Azure Files storage mounted into the environment — persists SQLite file
resource envStorage 'Microsoft.App/managedEnvironments/storages@2023-05-01' = {
  parent: environment
  name: 'chilife-sqlite'
  properties: {
    azureFile: {
      accountName: storageAccountName
      accountKey: storageAccountKey
      shareName: fileShareName
      accessMode: 'ReadWrite'
    }
  }
}

resource containerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: '${appName}-app'
  location: location
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8501
        transport: 'http'
      }
      registries: [
        {
          server: registryLoginServer
          username: 'placeholder'
          passwordSecretRef: 'registry-password'
        }
      ]
      secrets: [
        { name: 'registry-password',  value: 'placeholder' }
        { name: 'openai-api-key',     value: empty(openAiApiKey) ? 'not-set' : openAiApiKey }
        { name: 'storage-key',        value: storageAccountKey }
      ]
    }
    template: {
      volumes: [
        {
          name: 'sqlite-data'
          storageName: envStorage.name
          storageType: 'AzureFile'
        }
      ]
      containers: [
        {
          name: appName
          image: containerImage
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          volumeMounts: [
            { volumeName: 'sqlite-data', mountPath: '/data' }
          ]
          env: [
            { name: 'APP_ENV',    value: 'production' }
            { name: 'SQLITE_DIR', value: '/data' }
            { name: 'OPENAI_API_KEY', secretRef: 'openai-api-key' }
            { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
              value: appInsights.properties.ConnectionString }
          ]
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 1
      }
    }
  }
}

output appUrl string = 'https://${containerApp.properties.configuration.ingress.fqdn}'
output containerAppName string = containerApp.name
