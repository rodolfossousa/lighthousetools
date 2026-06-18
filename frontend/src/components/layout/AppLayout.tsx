"use client";
import { ReactNode, useEffect, useState, useCallback } from "react";
import { useRouter, usePathname } from "next/navigation";
import { Box, Toolbar } from "@mui/material";
import Sidebar, { DRAWER_WIDTH, DRAWER_COLLAPSED } from "./Sidebar";
import TopBar from "./TopBar";
import { useAuth } from "@/lib/AuthContext";

const PAGE_TITLES: Record<string, string> = {
  "/": "Início",
  "/dictionary": "Dicionário de Dados",
  "/templates": "Cadastro de Templates",
  "/explorer": "Explorador",
  "/library": "Biblioteca de Templates",
  "/models": "Modelos",
  "/sync": "Sincronização",
  "/settings": "Configurações",
};

export default function AppLayout({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  const [environment, setEnvironment] = useState<string | null>(null);
  const [clientName, setClientName] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("lh_sidebar_collapsed");
    if (stored === "true") setCollapsed(true);
  }, []);

  const toggleSidebar = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem("lh_sidebar_collapsed", String(next));
      return next;
    });
  }, []);

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [loading, user, router]);

  useEffect(() => {
    setEnvironment(localStorage.getItem("lh_environment"));
    setClientName(localStorage.getItem("lh_client_name"));
  }, [pathname]);

  if (loading || !user) return null;

  const title = PAGE_TITLES[pathname] || "Lighthouse Tools";
  const drawerWidth = collapsed ? DRAWER_COLLAPSED : DRAWER_WIDTH;

  return (
    <Box sx={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar
        userName={user.name}
        environment={environment}
        clientName={clientName}
        isAdmin={user.is_admin}
        collapsed={collapsed}
        onToggle={toggleSidebar}
      />
      <TopBar title={title} drawerWidth={drawerWidth} />
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: `calc(100% - ${drawerWidth}px)`,
          bgcolor: "background.default",
          minHeight: "100vh",
          transition: "width 0.2s ease",
        }}
      >
        <Toolbar />
        {children}
      </Box>
    </Box>
  );
}
