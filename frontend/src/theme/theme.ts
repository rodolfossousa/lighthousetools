"use client";
import { createTheme, Theme } from "@mui/material/styles";

const shared = {
  typography: {
    fontFamily: "'Inter', 'Roboto', 'Helvetica', sans-serif",
    h4: { fontWeight: 700 },
    h5: { fontWeight: 600 },
    h6: { fontWeight: 600 },
  },
  shape: { borderRadius: 12 },
  components: {
    MuiPaper: {
      styleOverrides: { root: { backgroundImage: "none" } },
    },
    MuiButton: {
      styleOverrides: { root: { textTransform: "none" as const, fontWeight: 600 } },
    },
  },
};

export function buildTheme(mode: "dark" | "light"): Theme {
  const isDark = mode === "dark";
  return createTheme({
    ...shared,
    palette: {
      mode,
      primary: { main: "#5C9DFF", light: "#8BBBFF", dark: "#3A7AE0" },
      secondary: { main: "#FF8A65" },
      background: {
        default: isDark ? "#0F1117" : "#F5F6FA",
        paper: isDark ? "#1A1D27" : "#FFFFFF",
      },
      divider: isDark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.08)",
    },
    components: {
      ...shared.components,
      MuiCard: {
        styleOverrides: {
          root: {
            backgroundImage: "none",
            border: isDark ? "1px solid rgba(255,255,255,0.06)" : "1px solid rgba(0,0,0,0.08)",
          },
        },
      },
      MuiDrawer: {
        styleOverrides: {
          paper: {
            borderRight: isDark ? "1px solid rgba(255,255,255,0.06)" : "1px solid rgba(0,0,0,0.08)",
          },
        },
      },
    },
  });
}

const theme = buildTheme("dark");
export default theme;
