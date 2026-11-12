import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { apiClient } from "@/controllers/apiClient";
import type { UserProfile } from "@/models/types";

interface AuthContextValue {
  user: UserProfile | null;
  isAuthLoading: boolean;
  loginWithEmail: (email: string, password: string) => Promise<void>;
  registerWithEmail: (name: string, email: string, password: string) => Promise<void>;
  completeOAuthCallback: (token: string, defaultApiKey?: string | null) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isAuthLoading, setIsAuthLoading] = useState<boolean>(true);

  const loadSessionUser = useCallback(async () => {
    const token = apiClient.getAuthToken();
    if (!token) {
      setUser(null);
      setIsAuthLoading(false);
      return;
    }

    try {
      const profile = await apiClient.getCurrentUser();
      setUser(profile);
    } catch {
      apiClient.setAuthToken(null);
      setUser(null);
    } finally {
      setIsAuthLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSessionUser();
    const handleUnauthorized = () => {
      setUser(null);
    };
    window.addEventListener("vocara:unauthorized", handleUnauthorized);
    return () => window.removeEventListener("vocara:unauthorized", handleUnauthorized);
  }, [loadSessionUser]);

  const applySessionCredentials = (token: string, defaultApiKey?: string | null) => {
    apiClient.setAuthToken(token);
    if (defaultApiKey) {
      apiClient.setApiKey(defaultApiKey);
    }
  };

  const loginWithEmail = async (email: string, password: string) => {
    const session = await apiClient.loginUser(email, password);
    applySessionCredentials(session.access_token, session.default_api_key);
    setUser(session.user);
  };

  const registerWithEmail = async (name: string, email: string, password: string) => {
    const session = await apiClient.registerUser(name, email, password);
    applySessionCredentials(session.access_token, session.default_api_key);
    setUser(session.user);
  };

  const completeOAuthCallback = async (token: string, defaultApiKey?: string | null) => {
    applySessionCredentials(token, defaultApiKey);
    const profile = await apiClient.getCurrentUser();
    setUser(profile);
  };

  const logout = () => {
    apiClient.setAuthToken(null);
    apiClient.setApiKey(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthLoading,
        loginWithEmail,
        registerWithEmail,
        completeOAuthCallback,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}

