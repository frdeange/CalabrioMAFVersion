import { InteractionType, PublicClientApplication } from '@azure/msal-browser';
import {
  MSAL_GUARD_CONFIG,
  MSAL_INSTANCE,
  MSAL_INTERCEPTOR_CONFIG,
  MsalGuardConfiguration,
  MsalInterceptorConfiguration
} from '@azure/msal-angular';
import { Provider } from '@angular/core';
import { environment } from '../../../environments/environment';

const resourceBase = environment.apimUrl || environment.apiUrl;
const msalAuthConfig = {
  clientId: environment.msalConfig.clientId || '9dfbf018-d41b-4579-8b6c-e58d1a9a52be',
  authority: environment.msalConfig.authority || 'https://login.microsoftonline.com/common',
  redirectUri: environment.msalConfig.redirectUri || 'http://localhost:4200',
  scopes: environment.msalConfig.scopes?.length
    ? environment.msalConfig.scopes
    : ['api://9dfbf018-d41b-4579-8b6c-e58d1a9a52be/access_as_user']
};

const protectedResourceMap = new Map<string, string[]>();
protectedResourceMap.set(`${resourceBase}/*`, msalAuthConfig.scopes);

export const msalInstance = new PublicClientApplication({
  auth: {
    clientId: msalAuthConfig.clientId,
    authority: msalAuthConfig.authority,
    redirectUri: msalAuthConfig.redirectUri
  },
  cache: {
    cacheLocation: 'localStorage',
    storeAuthStateInCookie: false
  }
});

export const msalGuardConfig: MsalGuardConfiguration = {
  interactionType: InteractionType.Redirect,
  authRequest: {
    scopes: msalAuthConfig.scopes
  }
};

export const msalInterceptorConfig: MsalInterceptorConfiguration = {
  interactionType: InteractionType.Redirect,
  protectedResourceMap
};

export const msalProviders: Provider[] = [
  { provide: MSAL_INSTANCE, useValue: msalInstance },
  { provide: MSAL_GUARD_CONFIG, useValue: msalGuardConfig },
  { provide: MSAL_INTERCEPTOR_CONFIG, useValue: msalInterceptorConfig }
];
