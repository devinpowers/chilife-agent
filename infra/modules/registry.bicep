param appName string
param location string

// uniqueString makes the name globally unique per resource group
var registryName = '${appName}${take(uniqueString(resourceGroup().id), 8)}'

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: registryName
  location: location
  sku: { name: 'Basic' }
  properties: {
    adminUserEnabled: true   // needed to push from local docker CLI on first deploy
  }
}

output loginServer string = registry.properties.loginServer
output registryName string = registry.name
