export const environment = {
  production: false,
  apiUrl: 'http://localhost:8000',
  apimUrl: '', // local dev: direct to backend; prod uses APIM
  msalConfig: {
    clientId: '00000000-0000-0000-0000-000000000000',
    authority: 'https://login.microsoftonline.com/common',
    redirectUri: 'http://localhost:4200',
    scopes: ['api://supervisor-assist/.default']
  }
};
