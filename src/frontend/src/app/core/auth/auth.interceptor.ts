import { HttpEvent, HttpHandlerFn, HttpInterceptorFn, HttpRequest } from '@angular/common/http';
import { inject } from '@angular/core';
import { MsalInterceptor } from '@azure/msal-angular';
import { Observable } from 'rxjs';

export const authInterceptor: HttpInterceptorFn = (
  req: HttpRequest<unknown>,
  next: HttpHandlerFn
): Observable<HttpEvent<unknown>> => inject(MsalInterceptor).intercept(req, {
  handle: (request: HttpRequest<unknown>) => next(request)
});
