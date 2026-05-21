import { Injectable } from '@angular/core';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class ApiService {
  public readonly baseUrl: string;
  public readonly chatUrl: string;

  constructor() {
    const base = environment.apimUrl || environment.apiUrl;
    this.baseUrl = base;
    this.chatUrl = `${base}/chat`;
  }
}
