export const environment = {
  production: true,
  apiUrl: 'https://calabriomafpoc-apim.azure-api.net/supervisor-assist',
  apimUrl: 'https://calabriomafpoc-apim.azure-api.net/supervisor-assist',
  msalConfig: {
    clientId: '9dfbf018-d41b-4579-8b6c-e58d1a9a52be',
    authority: 'https://login.microsoftonline.com/common',
    redirectUri: 'http://localhost:8080',
    scopes: ['api://9dfbf018-d41b-4579-8b6c-e58d1a9a52be/access_as_user']
  }
};
