import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api, getToken, setToken } from "./api.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function boot() {
      if (!getToken()) {
        setLoading(false);
        return;
      }
      try {
        const data = await api("/api/auth/me");
        setUser(data.user);
      } catch {
        setToken(null);
        setUser(null);
      } finally {
        setLoading(false);
      }
    }
    boot();
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
      async login(email, password) {
        const data = await api("/api/auth/login", {
          method: "POST",
          body: JSON.stringify({ email, password }),
        });
        setToken(data.access_token);
        setUser(data.user);
        return data.user;
      },
      logout() {
        if (getToken()) {
          api("/api/auth/logout", { method: "POST" }).catch(() => {});
        }
        setToken(null);
        setUser(null);
      },
      refreshUser(next) {
        setUser(next);
      },
    }),
    [user, loading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
