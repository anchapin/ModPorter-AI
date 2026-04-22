/**
 * Auth API client for portkit
 * Handles authentication including OAuth
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL
  ? import.meta.env.VITE_API_BASE_URL + '/api/v1'
  : import.meta.env.VITE_API_URL
    ? import.meta.env.VITE_API_URL.replace(/\/api\/v1$/, '') + '/api/v1'
    : '/api/v1';

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
}

export interface RegisterResponse {
  message: string;
  user_id: string;
}

export interface OAuthStatus {
  provider: string;
  enabled: boolean;
  connected: boolean;
  email?: string;
  username?: string;
}

class AuthClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      const errorData = await response
        .json()
        .catch(() => ({ detail: 'Request failed' }));
      throw new Error(errorData.detail || 'Request failed');
    }
    return response.json();
  }

  async login(request: LoginRequest): Promise<LoginResponse> {
    const response = await fetch(`${this.baseUrl}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    return this.handleResponse<LoginResponse>(response);
  }

  async register(request: RegisterRequest): Promise<RegisterResponse> {
    const response = await fetch(`${this.baseUrl}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    return this.handleResponse<RegisterResponse>(response);
  }

  async logout(): Promise<void> {
    const token = this.getStoredToken();
    if (!token) return;

    await fetch(`${this.baseUrl}/auth/logout`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    });
    this.clearTokens();
  }

  async refreshToken(refreshToken: string): Promise<{ access_token: string }> {
    const response = await fetch(`${this.baseUrl}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    return this.handleResponse<{ access_token: string }>(response);
  }

  async getCurrentUser(token: string) {
    const response = await fetch(`${this.baseUrl}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return this.handleResponse(response);
  }

  async getOAuthAuthorizationUrl(
    provider: 'discord' | 'github' | 'google'
  ): Promise<{ authorization_url: string }> {
    const response = await fetch(`${this.baseUrl}/auth/oauth/${provider}`, {
      method: 'GET',
    });
    return this.handleResponse<{ authorization_url: string }>(response);
  }

  async getOAuthStatus(
    provider: 'discord' | 'github' | 'google',
    token: string
  ): Promise<OAuthStatus> {
    const response = await fetch(
      `${this.baseUrl}/auth/oauth/${provider}/status`,
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    return this.handleResponse<OAuthStatus>(response);
  }

  async unlinkOAuth(
    provider: 'discord' | 'github' | 'google',
    token: string
  ): Promise<{ message: string }> {
    const response = await fetch(
      `${this.baseUrl}/auth/oauth/${provider}/unlink`,
      {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    return this.handleResponse<{ message: string }>(response);
  }

  storeToken(key: string, token: string): void {
    localStorage.setItem(key, token);
  }

  getStoredToken(key: string = 'access_token'): string | null {
    return localStorage.getItem(key);
  }

  clearTokens(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  }

  isAuthenticated(): boolean {
    return !!this.getStoredToken();
  }
}

export const authClient = new AuthClient();
export { AuthClient };
