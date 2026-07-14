/**
 * AutoWebAgent - API Client
 * ==========================
 * Centralized HTTP client for all backend API calls.
 * Handles JWT tokens, refresh flow, and error handling.
 */

// Always use relative URL — Next.js rewrites handle proxy to backend
const API_BASE = '/api/v1';

type RequestOptions = Omit<RequestInit, 'body'> & {
  body?: BodyInit | null;
};

class ApiClient {
  private accessToken: string | null = null;
  private refreshToken: string | null = null;
  private refreshPromise: Promise<void> | null = null;

  constructor() {
    // Restore tokens from localStorage
    if (typeof window !== 'undefined') {
      this.accessToken = localStorage.getItem('access_token');
      this.refreshToken = localStorage.getItem('refresh_token');
    }
  }

  setTokens(access: string, refresh: string) {
    this.accessToken = access;
    this.refreshToken = refresh;
    if (typeof window !== 'undefined') {
      localStorage.setItem('access_token', access);
      localStorage.setItem('refresh_token', refresh);
    }
  }

  clearTokens() {
    this.accessToken = null;
    this.refreshToken = null;
    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');
    }
  }

  private async refreshAccessToken(): Promise<void> {
    if (!this.refreshToken) throw new Error('No refresh token');

    // Deduplicate concurrent refresh calls
    if (this.refreshPromise) return this.refreshPromise;

    this.refreshPromise = (async () => {
      try {
        const res = await fetch(`${API_BASE}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: this.refreshToken }),
        });

        if (!res.ok) throw new Error('Token refresh failed');

        const data = await res.json();
        this.setTokens(data.access_token, data.refresh_token);
      } finally {
        this.refreshPromise = null;
      }
    })();

    return this.refreshPromise;
  }

  async request<T = unknown>(
    endpoint: string,
    options: RequestOptions = {}
  ): Promise<T> {
    // Ensure trailing slash before query params to avoid Next.js 308 redirects
    let url = `${API_BASE}${endpoint}`;
    if (!url.includes('?')) {
      if (!url.endsWith('/')) url += '/';
    } else {
      const [path, query] = url.split('?', 2);
      url = (path.endsWith('/') ? path : path + '/') + '?' + query;
    }
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    if (this.accessToken) {
      headers['Authorization'] = `Bearer ${this.accessToken}`;
    }

    const fetchOptions: RequestInit = {
      ...options,
      headers,
    };

    if (options.body !== undefined && options.body !== null) {
      fetchOptions.body = JSON.stringify(options.body);
    }

    let res = await fetch(url, fetchOptions);

    // Auto-refresh on 401
    if (res.status === 401 && this.refreshToken) {
      try {
        await this.refreshAccessToken();
        headers['Authorization'] = `Bearer ${this.accessToken}`;
        res = await fetch(url, { ...fetchOptions, headers });
      } catch {
        this.clearTokens();
        window.location.href = '/auth/login';
        throw new Error('Session expired');
      }
    }

    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: 'Request failed' }));
      let message = 'Request failed';
      if (error.detail) {
        if (Array.isArray(error.detail)) {
          message = error.detail.map((err: any) => err.msg || JSON.stringify(err)).join(', ');
        } else if (typeof error.detail === 'string') {
          message = error.detail;
        } else if (typeof error.detail === 'object') {
          message = error.detail.message || JSON.stringify(error.detail);
        }
      }
      throw new ApiError(message, res.status);
    }

    return res.json();
  }

  // ── Convenience Methods ───────────────────────────────

  get<T = unknown>(endpoint: string) {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  post<T = unknown>(endpoint: string, body?: object) {
    return this.request<T>(endpoint, { method: 'POST', body: body as any });
  }

  put<T = unknown>(endpoint: string, body?: object) {
    return this.request<T>(endpoint, { method: 'PUT', body: body as any });
  }

  delete<T = unknown>(endpoint: string) {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
    this.name = 'ApiError';
  }
}

export const api = new ApiClient();
