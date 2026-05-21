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

const protectedResourceMap = new Map<string, string[]>();
protectedResourceMap.set(`${resourceBase}/*`, environment.msalConfig.scopes);

export const msalInstance = new PublicClientApplication({
  auth: {
    clientId: environment.msalConfig.clientId,
    authority: environment.msalConfig.authority,
    redirectUri: environment.msalConfig.redirectUri
  },
  cache: {
    cacheLocation: 'localStorage',
    storeAuthStateInCookie: false
  }
});

export const msalGuardConfig: MsalGuardConfiguration = {
  interactionType: InteractionType.Redirect,
  authRequest: {
    scopes: environment.msalConfig.scopes
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
