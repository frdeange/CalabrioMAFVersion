export const environment = {
  production: true,
  apiUrl: '__API_URL__',
  apimUrl: '__APIM_URL__',
  msalConfig: {
    clientId: '00000000-0000-0000-0000-000000000000',
    authority: 'https://login.microsoftonline.com/common',
    redirectUri: '__REDIRECT_URI__',
    scopes: ['api://supervisor-assist/.default']
  }
};
