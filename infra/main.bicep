param appName string = 'chilife'
param location string = resourceGroup().location
param containerImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

@secure()
param openAiApiKey string = ''

module registry 'modules/registry.bicep' = {
  name: 'registry'
  params: { appName: appName, location: location }
}

module keyvault 'modules/keyvault.bicep' = {
  name: 'keyvault'
  params: { appName: appName, location: location, openAiApiKey: openAiApiKey }
}

module storage 'modules/storage.bicep' = {
  name: 'storage'
  params: { appName: appName, location: location }
}

module containerApp 'modules/container-apps.bicep' = {
  name: 'containerApp'
  params: {
    appName: appName
    location: location
    containerImage: containerImage
    registryLoginServer: registry.outputs.loginServer
    storageAccountName: storage.outputs.storageAccountName
    storageAccountKey: storage.outputs.storageAccountKey   // @secure() in module
    fileShareName: storage.outputs.fileShareName
    openAiApiKey: openAiApiKey
  }
}

output appUrl string = containerApp.outputs.appUrl
output registryLoginServer string = registry.outputs.loginServer
output registryName string = registry.outputs.registryName
output containerAppName string = containerApp.outputs.containerAppName
