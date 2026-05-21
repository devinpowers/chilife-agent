param appName string
param location string

// Storage account names: 3-24 chars, lowercase alphanumeric only, globally unique
var storageName = '${appName}${take(uniqueString(resourceGroup().id), 8)}'

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageName
  location: location
  kind: 'StorageV2'
  sku: { name: 'Standard_LRS' }
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
  }
}

resource fileService 'Microsoft.Storage/storageAccounts/fileServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
}

resource fileShare 'Microsoft.Storage/storageAccounts/fileServices/shares@2023-01-01' = {
  parent: fileService
  name: 'chilife-data'
  properties: {
    shareQuota: 1
  }
}

output storageAccountName string = storageAccount.name
output storageAccountKey string = storageAccount.listKeys().keys[0].value
output fileShareName string = fileShare.name
