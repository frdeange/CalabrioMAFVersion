export interface User {
  id: string;
  name: string;
  email: string;
  roles: string[];
}

export interface TokenState {
  accessToken: string;
  expiresOn: Date;
  scopes: string[];
}
