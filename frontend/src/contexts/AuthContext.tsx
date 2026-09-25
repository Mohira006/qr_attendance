import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import i18n from "@/i18n/config";
import { authApi } from "@/services/authApi";
import { tokenStorage } from "@/services/tokenStorage";
import type { UserResponse } from "@/types/models";

interface AuthContextValue {
  user: UserResponse | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function bootstrap() {
      if (!tokenStorage.getAccessToken()) {
        setIsLoading(false);
        return;
      }
      try {
        const me = await authApi.me();
        if (!cancelled) {
          setUser(me);
          void i18n.changeLanguage(me.preferred_language);
        }
      } catch {
        tokenStorage.clear();
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  async function login(email: string, password: string) {
    const response = await authApi.login(email, password);
    tokenStorage.setTokens(response.access_token, response.refresh_token);
    setUser(response.user);
    // The account's saved preference wins over whatever was guessed/selected
    // pre-login, so language follows the person across devices and browsers.
    void i18n.changeLanguage(response.user.preferred_language);
  }

  async function logout() {
    try {
      await authApi.logout(tokenStorage.getRefreshToken());
    } catch {
      // Best-effort: still clear local state even if the server call fails
      // (e.g. the network just dropped).
    }
    tokenStorage.clear();
    setUser(null);
  }

  return <AuthContext.Provider value={{ user, isLoading, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
