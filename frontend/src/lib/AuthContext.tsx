"use client";
import { createContext, useContext, useEffect, useState, ReactNode, useCallback } from "react";
import type { User } from "@/types";

interface AuthState {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<string | null>;
  logout: () => void;
}

const AuthContext = createContext<AuthState>({
  user: null,
  token: null,
  loading: true,
  login: async () => "Not initialized",
  logout: () => {},
});

const API_URL = "http://localhost:8001/api";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem("token");
    if (!stored) {
      setLoading(false);
      return;
    }
    fetch(`${API_URL}/auth/me`, {
      headers: { Authorization: `Bearer ${stored}` },
    })
      .then((res) => {
        if (!res.ok) throw new Error();
        return res.json();
      })
      .then((data) => {
        setUser(data);
        setToken(stored);
      })
      .catch(() => {
        localStorage.removeItem("token");
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (username: string, password: string): Promise<string | null> => {
    try {
      const res = await fetch(`${API_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      if (!res.ok) return "Utilizador ou senha incorretos.";
      const data = await res.json();
      localStorage.setItem("token", data.access_token);
      setToken(data.access_token);
      setUser(data.user);
      return null;
    } catch {
      return "Erro ao conectar com o servidor.";
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("token");
    localStorage.removeItem("lh_environment");
    localStorage.removeItem("lh_client_name");
    setUser(null);
    setToken(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
