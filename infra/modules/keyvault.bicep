param appName string
param location string

@secure()
param openAiApiKey string = ''

var kvName = '${appName}-kv-${take(uniqueString(resourceGroup().id), 6)}'

resource vault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: kvName
  location: location
  properties: {
    sku: { family: 'A', name: 'standard' }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
  }
}

resource openAiSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!empty(openAiApiKey)) {
  parent: vault
  name: 'openai-api-key'
  properties: { value: openAiApiKey }
}

output vaultUri string = vault.properties.vaultUri
output vaultName string = vault.name
