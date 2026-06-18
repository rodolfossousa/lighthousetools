"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/AuthContext";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid2 as Grid,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Button,
  Alert,
  Chip,
} from "@mui/material";
import {
  Storage as StorageIcon,
  Sync as SyncIcon,
  MenuBook as DictIcon,
  NoteAdd as TemplateIcon,
} from "@mui/icons-material";
import AppLayout from "@/components/layout/AppLayout";
import { api } from "@/lib/api";

export default function HomePage() {
  const { user } = useAuth();
  const router = useRouter();

  const [environments, setEnvironments] = useState<Record<string, string[]>>({});
  const [selectedEnv, setSelectedEnv] = useState("");
  const [selectedClient, setSelectedClient] = useState("");
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const stored = localStorage.getItem("lh_environment");
    const storedClient = localStorage.getItem("lh_client_name");
    if (stored && storedClient) {
      setSelectedEnv(stored);
      setSelectedClient(storedClient);
      setConnected(true);
    }
    api.get<Record<string, string[]>>("/environments").then(setEnvironments).catch(() => {});
  }, []);

  const handleConnect = async () => {
    setError("");
    try {
      await api.post("/environments/connect", {
        environment: selectedEnv,
        client_name: selectedClient,
      });
      localStorage.setItem("lh_environment", selectedEnv);
      localStorage.setItem("lh_client_name", selectedClient);
      setConnected(true);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const quickLinks = [
    { label: "Dicionário de Dados", icon: <DictIcon />, path: "/dictionary", color: "#5C9DFF" },
    { label: "Templates", icon: <TemplateIcon />, path: "/templates", color: "#FF8A65" },
    { label: "Explorador", icon: <StorageIcon />, path: "/explorer", color: "#66BB6A" },
    { label: "Sincronização", icon: <SyncIcon />, path: "/sync", color: "#AB47BC" },
  ];

  return (
    <AppLayout>
      <Box sx={{ maxWidth: 900, mx: "auto" }}>
        <Typography variant="h4" sx={{ mb: 1 }}>
          Bem-vindo, {user?.name}!
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
          Lighthouse Tools — Gestão de ativos, templates e dicionário de dados.
        </Typography>

        {/* Seleção de ambiente */}
        <Card sx={{ mb: 4 }}>
          <CardContent sx={{ p: 3 }}>
            <Typography variant="h6" sx={{ mb: 2, display: "flex", alignItems: "center", gap: 1 }}>
              Ambiente
              {connected && (
                <Chip label="Conectado" color="success" size="small" />
              )}
            </Typography>

            {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

            <Box sx={{ display: "flex", gap: 2, alignItems: "flex-end" }}>
              <FormControl sx={{ minWidth: 200 }} size="small">
                <InputLabel>Ambiente</InputLabel>
                <Select
                  value={selectedEnv}
                  label="Ambiente"
                  onChange={(e) => {
                    setSelectedEnv(e.target.value);
                    setSelectedClient("");
                    setConnected(false);
                  }}
                >
                  {Object.keys(environments).map((env) => (
                    <MenuItem key={env} value={env}>{env}</MenuItem>
                  ))}
                </Select>
              </FormControl>

              <FormControl sx={{ minWidth: 200 }} size="small">
                <InputLabel>Cliente</InputLabel>
                <Select
                  value={selectedClient}
                  label="Cliente"
                  onChange={(e) => {
                    setSelectedClient(e.target.value);
                    setConnected(false);
                  }}
                  disabled={!selectedEnv}
                >
                  {(environments[selectedEnv] || []).map((c) => (
                    <MenuItem key={c} value={c}>{c}</MenuItem>
                  ))}
                </Select>
              </FormControl>

              <Button
                variant="contained"
                onClick={handleConnect}
                disabled={!selectedEnv || !selectedClient}
              >
                Conectar
              </Button>
            </Box>
          </CardContent>
        </Card>

        {/* Atalhos */}
        <Typography variant="h6" sx={{ mb: 2 }}>
          Acesso Rápido
        </Typography>
        <Grid container spacing={2}>
          {quickLinks.map((link) => (
            <Grid size={{ xs: 12, sm: 6, md: 3 }} key={link.path}>
              <Card
                sx={{
                  cursor: "pointer",
                  transition: "transform 0.15s, box-shadow 0.15s",
                  "&:hover": {
                    transform: "translateY(-2px)",
                    boxShadow: `0 4px 20px ${link.color}22`,
                    borderColor: link.color,
                  },
                }}
                onClick={() => router.push(link.path)}
              >
                <CardContent sx={{ textAlign: "center", py: 3 }}>
                  <Box sx={{ color: link.color, mb: 1 }}>{link.icon}</Box>
                  <Typography variant="subtitle2">{link.label}</Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Box>
    </AppLayout>
  );
}
