import { Injectable, signal } from '@angular/core';
import {
  CognitoUser,
  CognitoUserPool,
  AuthenticationDetails,
  CognitoUserSession,
} from 'amazon-cognito-identity-js';
import { environment } from '../../../environments/environment';

export interface AuthUser {
  email: string;
  groups: string[];
  idToken: string;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly pool = new CognitoUserPool({
    UserPoolId: environment.cognito.userPoolId,
    ClientId: environment.cognito.userPoolClientId,
  });

  readonly currentUser = signal<AuthUser | null>(null);

  constructor() {
    this.restoreSession();
  }

  private restoreSession(): void {
    const cognitoUser = this.pool.getCurrentUser();
    if (!cognitoUser) return;

    cognitoUser.getSession((err: Error | null, session: CognitoUserSession | null) => {
      if (err || !session) return;
      this.currentUser.set(this.toAuthUser(session));
    });
  }

  login(email: string, password: string): Promise<AuthUser> {
    const authDetails = new AuthenticationDetails({ Username: email, Password: password });
    const cognitoUser = new CognitoUser({ Username: email, Pool: this.pool });

    return new Promise((resolve, reject) => {
      cognitoUser.authenticateUser(authDetails, {
        onSuccess: (session) => {
          const user = this.toAuthUser(session);
          this.currentUser.set(user);
          resolve(user);
        },
        onFailure: (err) => reject(err),
      });
    });
  }

  logout(): void {
    this.pool.getCurrentUser()?.signOut();
    this.currentUser.set(null);
  }

  getIdToken(): string | null {
    return this.currentUser()?.idToken ?? null;
  }

  isAdmin(): boolean {
    return this.currentUser()?.groups.includes('admin') ?? false;
  }

  private toAuthUser(session: CognitoUserSession): AuthUser {
    const idToken = session.getIdToken();
    const payload = idToken.decodePayload() as Record<string, unknown>;
    const groupsRaw = payload['cognito:groups'];
    const groups = Array.isArray(groupsRaw) ? (groupsRaw as string[]) : [];

    return {
      email: (payload['email'] as string) ?? '',
      groups,
      idToken: idToken.getJwtToken(),
    };
  }
}
