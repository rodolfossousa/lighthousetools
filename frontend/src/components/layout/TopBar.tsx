"use client";
import { AppBar, Toolbar, Typography, Button, Box } from "@mui/material";
import { Logout as LogoutIcon } from "@mui/icons-material";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/AuthContext";

interface TopBarProps {
  title: string;
  drawerWidth: number;
}

export default function TopBar({ title, drawerWidth }: TopBarProps) {
  const { logout } = useAuth();
  const router = useRouter();

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  return (
    <AppBar
      position="fixed"
      elevation={0}
      sx={{
        width: `calc(100% - ${drawerWidth}px)`,
        ml: `${drawerWidth}px`,
        bgcolor: "background.default",
        borderBottom: "1px solid",
        borderColor: "divider",
        transition: "width 0.2s ease, margin-left 0.2s ease",
      }}
    >
      <Toolbar>
        <Typography variant="h6" sx={{ flexGrow: 1, color: "text.primary" }}>
          {title}
        </Typography>
        <Button
          color="inherit"
          startIcon={<LogoutIcon />}
          onClick={handleLogout}
          sx={{ color: "text.secondary" }}
        >
          Sair
        </Button>
      </Toolbar>
    </AppBar>
  );
}
