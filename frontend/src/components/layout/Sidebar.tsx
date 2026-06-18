"use client";
import { usePathname, useRouter } from "next/navigation";
import {
  Drawer,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Box,
  Typography,
  Divider,
  Avatar,
  Chip,
  IconButton,
  Tooltip,
} from "@mui/material";
import {
  Home as HomeIcon,
  MenuBook as DictionaryIcon,
  NoteAdd as TemplatesIcon,
  AccountTree as ExplorerIcon,
  LibraryBooks as LibraryIcon,
  Hub as ModelsIcon,
  Sync as SyncIcon,
  Settings as SettingsIcon,
  ChevronLeft as CollapseIcon,
  Menu as ExpandIcon,
  DarkMode as DarkModeIcon,
  LightMode as LightModeIcon,
} from "@mui/icons-material";
import { useThemeMode } from "@/components/providers/Providers";
import LighthouseLogo, { ShapeDigitalBadge } from "@/components/LighthouseLogo";

const DRAWER_WIDTH = 260;
const DRAWER_COLLAPSED = 64;

interface SidebarProps {
  userName: string;
  environment: string | null;
  clientName: string | null;
  isAdmin: boolean;
  collapsed: boolean;
  onToggle: () => void;
}

const NAV_ITEMS = [
  { label: "Início", path: "/", icon: <HomeIcon /> },
  { label: "Dicionário de Dados", path: "/dictionary", icon: <DictionaryIcon /> },
  { label: "Cadastro de Templates", path: "/templates", icon: <TemplatesIcon /> },
  { label: "Explorador", path: "/explorer", icon: <ExplorerIcon /> },
  { label: "Biblioteca de Templates", path: "/library", icon: <LibraryIcon /> },
  { label: "Modelos", path: "/models", icon: <ModelsIcon /> },
  { label: "Sincronização", path: "/sync", icon: <SyncIcon /> },
];

export default function Sidebar({ userName, environment, clientName, isAdmin, collapsed, onToggle }: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { mode, toggleMode } = useThemeMode();

  const width = collapsed ? DRAWER_COLLAPSED : DRAWER_WIDTH;

  return (
    <Drawer
      variant="permanent"
      sx={{
        width,
        flexShrink: 0,
        "& .MuiDrawer-paper": {
          width,
          boxSizing: "border-box",
          bgcolor: "background.paper",
          transition: "width 0.2s ease",
          overflowX: "hidden",
        },
      }}
    >
      {/* Logo + collapse */}
      <Box sx={{
        p: collapsed ? 1 : 2, display: "flex", alignItems: "center",
        justifyContent: collapsed ? "center" : "space-between", minHeight: 64,
      }}>
        <LighthouseLogo size="small" collapsed={collapsed} />
        {!collapsed && (
          <Tooltip title="Encolher menu" placement="right">
            <IconButton size="small" onClick={onToggle}>
              <CollapseIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        )}
        {collapsed && (
          <Tooltip title="Expandir menu" placement="right">
            <IconButton size="small" onClick={onToggle} sx={{ position: "absolute", right: 4, top: 20 }}>
              <ExpandIcon sx={{ fontSize: 16 }} />
            </IconButton>
          </Tooltip>
        )}
      </Box>

      {/* User info */}
      {!collapsed && (
        <Box sx={{ px: 2, pb: 1.5 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Avatar sx={{ bgcolor: "primary.main", width: 28, height: 28, fontSize: 12 }}>
              {userName.charAt(0).toUpperCase()}
            </Avatar>
            <Box sx={{ minWidth: 0 }}>
              <Typography variant="body2" noWrap sx={{ fontSize: 12, fontWeight: 500 }}>{userName}</Typography>
              {environment && (
                <Chip label={`${environment} / ${clientName}`} size="small"
                  sx={{ height: 18, fontSize: 10, mt: 0.2 }} />
              )}
            </Box>
          </Box>
        </Box>
      )}

      <Divider />

      {/* Navigation */}
      <List sx={{ px: collapsed ? 0.5 : 1, pt: 1 }}>
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.path || (item.path !== "/" && pathname.startsWith(item.path));
          return (
            <Tooltip key={item.path} title={collapsed ? item.label : ""} placement="right">
              <ListItemButton
                selected={active}
                onClick={() => router.push(item.path)}
                sx={{
                  borderRadius: 2,
                  mb: 0.3,
                  justifyContent: collapsed ? "center" : "flex-start",
                  px: collapsed ? 1 : 2,
                  "&.Mui-selected": {
                    bgcolor: "rgba(92,157,255,0.12)",
                    "&:hover": { bgcolor: "rgba(92,157,255,0.18)" },
                  },
                }}
              >
                <ListItemIcon sx={{
                  minWidth: collapsed ? 0 : 36,
                  color: active ? "primary.main" : "text.secondary",
                  justifyContent: "center",
                }}>
                  {item.icon}
                </ListItemIcon>
                {!collapsed && (
                  <ListItemText primary={item.label}
                    primaryTypographyProps={{ fontSize: 14, fontWeight: active ? 600 : 400 }} />
                )}
              </ListItemButton>
            </Tooltip>
          );
        })}
      </List>

      <Box sx={{ flexGrow: 1 }} />

      <Divider />

      {/* Bottom actions */}
      <List sx={{ px: collapsed ? 0.5 : 1, pb: 0.5 }}>
        <Tooltip title={collapsed ? (mode === "dark" ? "Modo claro" : "Modo escuro") : ""} placement="right">
          <ListItemButton onClick={toggleMode}
            sx={{ borderRadius: 2, mb: 0.3, justifyContent: collapsed ? "center" : "flex-start", px: collapsed ? 1 : 2 }}>
            <ListItemIcon sx={{ minWidth: collapsed ? 0 : 36, justifyContent: "center" }}>
              {mode === "dark" ? <LightModeIcon /> : <DarkModeIcon />}
            </ListItemIcon>
            {!collapsed && (
              <ListItemText primary={mode === "dark" ? "Modo Claro" : "Modo Escuro"}
                primaryTypographyProps={{ fontSize: 14 }} />
            )}
          </ListItemButton>
        </Tooltip>

        <Tooltip title={collapsed ? (isAdmin ? "Configurações" : "Ambiente") : ""} placement="right">
          <ListItemButton
            selected={pathname === "/settings"}
            onClick={() => router.push("/settings")}
            sx={{ borderRadius: 2, justifyContent: collapsed ? "center" : "flex-start", px: collapsed ? 1 : 2 }}
          >
            <ListItemIcon sx={{ minWidth: collapsed ? 0 : 36, justifyContent: "center" }}>
              <SettingsIcon />
            </ListItemIcon>
            {!collapsed && (
              <ListItemText primary={isAdmin ? "Configurações" : "Ambiente"}
                primaryTypographyProps={{ fontSize: 14 }} />
            )}
          </ListItemButton>
        </Tooltip>
      </List>

      {/* Shape Digital badge */}
      {!collapsed && (
        <Box sx={{ px: 2, pb: 1.5, pt: 0.5 }}>
          <ShapeDigitalBadge />
        </Box>
      )}
    </Drawer>
  );
}

export { DRAWER_WIDTH, DRAWER_COLLAPSED };
