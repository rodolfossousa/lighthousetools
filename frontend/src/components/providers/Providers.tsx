"use client";
import { ReactNode, createContext, useContext, useState, useMemo, useEffect, useCallback } from "react";
import { ThemeProvider, CssBaseline } from "@mui/material";
import { buildTheme } from "@/theme/theme";
import { AuthProvider } from "@/lib/AuthContext";

type ThemeMode = "dark" | "light";

interface ThemeModeCtx {
  mode: ThemeMode;
  toggleMode: () => void;
}

const ThemeModeContext = createContext<ThemeModeCtx>({ mode: "dark", toggleMode: () => {} });

export function useThemeMode() {
  return useContext(ThemeModeContext);
}

export default function Providers({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<ThemeMode>("dark");

  useEffect(() => {
    const stored = localStorage.getItem("lh_theme_mode") as ThemeMode | null;
    if (stored === "light" || stored === "dark") setMode(stored);
  }, []);

  const toggleMode = useCallback(() => {
    setMode((prev) => {
      const next = prev === "dark" ? "light" : "dark";
      localStorage.setItem("lh_theme_mode", next);
      return next;
    });
  }, []);

  const theme = useMemo(() => buildTheme(mode), [mode]);

  return (
    <AuthProvider>
      <ThemeModeContext.Provider value={{ mode, toggleMode }}>
        <ThemeProvider theme={theme}>
          <CssBaseline />
          {children}
        </ThemeProvider>
      </ThemeModeContext.Provider>
    </AuthProvider>
  );
}
