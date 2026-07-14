'use client';

/**
 * AutoWebAgent - Auth Context
 * =============================
 * React context for authentication state management.
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { api, ApiError } from './api';

interface User {
  id: string;
  email: string;
  username: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
  is_verified: boolean;
  active_sessions: number;
  total_tasks_executed: number;
  has_deepseek_key: boolean;
  has_anticaptcha_key: boolean;
  has_proxy_credentials: boolean;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

interface RegisterData {
  email: string;
  username: string;
  password: string;
  full_name?: string;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const isAuthenticated = !!user;

  // Load user on mount
  useEffect(() => {
    const stored = localStorage.getItem('user');
    if (stored) {
      try {
        setUser(JSON.parse(stored));
      } catch {}
    }

    // Verify token is still valid
    const accessToken = localStorage.getItem('access_token');
    if (accessToken) {
      api.get<User>('/auth/me')
        .then((userData) => {
          setUser(userData);
          localStorage.setItem('user', JSON.stringify(userData));
        })
        .catch(() => {
          api.clearTokens();
          setUser(null);
        })
        .finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const tokens = await api.post<{
      access_token: string;
      refresh_token: string;
    }>('/auth/login', { email, password });

    api.setTokens(tokens.access_token, tokens.refresh_token);

    const userData = await api.get<User>('/auth/me');
    setUser(userData);
    localStorage.setItem('user', JSON.stringify(userData));
  }, []);

  const register = useCallback(async (data: RegisterData) => {
    await api.post('/auth/register', data);
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.post('/auth/logout');
    } catch {}
    api.clearTokens();
    setUser(null);
  }, []);

  const refreshUser = useCallback(async () => {
    try {
      const userData = await api.get<User>('/auth/me');
      setUser(userData);
      localStorage.setItem('user', JSON.stringify(userData));
    } catch {}
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, isLoading, isAuthenticated, login, register, logout, refreshUser }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
