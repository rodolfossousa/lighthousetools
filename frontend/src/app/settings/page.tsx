"use client";
import { useState, useEffect } from "react";
import { useAuth } from "@/lib/AuthContext";
import {
  Box,
  Card,
  CardContent,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  Alert,
  Chip,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Checkbox,
  FormControlLabel,
  Divider,
} from "@mui/material";
import { Delete as DeleteIcon, Add as AddIcon } from "@mui/icons-material";
import AppLayout from "@/components/layout/AppLayout";
import { api } from "@/lib/api";
import type { User } from "@/types";

export default function SettingsPage() {
  const { user } = useAuth();
  const isAdmin = user?.is_admin;

  return (
    <AppLayout>
      <Box sx={{ maxWidth: 800, mx: "auto" }}>
        <EnvironmentSection />
        {isAdmin && (
          <>
            <Divider sx={{ my: 4 }} />
            <UsersSection />
          </>
        )}
      </Box>
    </AppLayout>
  );
}

function EnvironmentSection() {
  const [environments, setEnvironments] = useState<Record<string, string[]>>({});
  const [selectedEnv, setSelectedEnv] = useState("");
  const [selectedClient, setSelectedClient] = useState("");
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const stored = localStorage.getItem("lh_environment") || "";
    const storedClient = localStorage.getItem("lh_client_name") || "";
    setSelectedEnv(stored);
    setSelectedClient(storedClient);
    if (stored && storedClient) setConnected(true);
    api.get<Record<string, string[]>>("/environments").then(setEnvironments).catch(() => {});
  }, []);

  const handleConnect = async () => {
    setError("");
    try {
      await api.post("/environments/connect", { environment: selectedEnv, client_name: selectedClient });
      localStorage.setItem("lh_environment", selectedEnv);
      localStorage.setItem("lh_client_name", selectedClient);
      setConnected(true);
    } catch (e: any) {
      setError(e.message);
    }
  };

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2, display: "flex", alignItems: "center", gap: 1 }}>
          Ambiente
          {connected && <Chip label="Conectado" color="success" size="small" />}
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
              onChange={(e) => { setSelectedClient(e.target.value); setConnected(false); }}
              disabled={!selectedEnv}
            >
              {(environments[selectedEnv] || []).map((c) => (
                <MenuItem key={c} value={c}>{c}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <Button variant="contained" onClick={handleConnect} disabled={!selectedEnv || !selectedClient}>
            {connected ? "Reconectar" : "Conectar"}
          </Button>
        </Box>
      </CardContent>
    </Card>
  );
}

function UsersSection() {
  const [users, setUsers] = useState<User[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newUsername, setNewUsername] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newIsAdmin, setNewIsAdmin] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState("");

  const fetchUsers = async () => {
    try {
      const data = await api.get<User[]>("/users");
      setUsers(data);
    } catch { /* ignorar se não for admin */ }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const createUser = async () => {
    setError("");
    try {
      await api.post("/users", { name: newName, username: newUsername, password: newPassword, is_admin: newIsAdmin });
      setShowCreate(false);
      setNewName("");
      setNewUsername("");
      setNewPassword("");
      setNewIsAdmin(false);
      setResult("Utilizador criado.");
      fetchUsers();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const deleteUser = async (userId: number) => {
    try {
      await api.delete(`/users/${userId}`);
      fetchUsers();
    } catch (e: any) {
      setError(e.message);
    }
  };

  return (
    <>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
        <Typography variant="h6">Gestão de Utilizadores</Typography>
        <Button startIcon={<AddIcon />} onClick={() => setShowCreate(true)}>
          Novo utilizador
        </Button>
      </Box>

      {result && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setResult(null)}>{result}</Alert>}
      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>{error}</Alert>}

      <Card>
        <CardContent sx={{ p: 0, "&:last-child": { pb: 0 } }}>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Nome</TableCell>
                  <TableCell>Username</TableCell>
                  <TableCell>Admin</TableCell>
                  <TableCell width={60}></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {users.map((u) => (
                  <TableRow key={u.id}>
                    <TableCell>{u.name}</TableCell>
                    <TableCell>{u.username}</TableCell>
                    <TableCell>
                      {u.is_admin ? <Chip label="Sim" size="small" color="primary" /> : "Não"}
                    </TableCell>
                    <TableCell>
                      {u.username !== "admin" && (
                        <IconButton size="small" color="error" onClick={() => deleteUser(u.id)}>
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      <Dialog open={showCreate} onClose={() => setShowCreate(false)}>
        <DialogTitle>Novo Utilizador</DialogTitle>
        <DialogContent>
          <TextField fullWidth label="Nome completo" value={newName} onChange={(e) => setNewName(e.target.value)} sx={{ mt: 1, mb: 2 }} />
          <TextField fullWidth label="Username" value={newUsername} onChange={(e) => setNewUsername(e.target.value)} sx={{ mb: 2 }} />
          <TextField fullWidth label="Senha" type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} sx={{ mb: 2 }} />
          <FormControlLabel
            control={<Checkbox checked={newIsAdmin} onChange={(e) => setNewIsAdmin(e.target.checked)} />}
            label="Administrador"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowCreate(false)}>Cancelar</Button>
          <Button variant="contained" onClick={createUser} disabled={!newName || !newUsername || !newPassword}>
            Criar
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
