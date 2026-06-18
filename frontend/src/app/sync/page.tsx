"use client";
import { useState, useEffect } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Alert,
  LinearProgress,
  Tabs,
  Tab,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from "@mui/material";
import { DataGrid, GridColDef } from "@mui/x-data-grid";
import AppLayout from "@/components/layout/AppLayout";
import { api } from "@/lib/api";
import type { SyncHistoryEntry } from "@/types";

export default function SyncPage() {
  const [tab, setTab] = useState(0);
  const [history, setHistory] = useState<SyncHistoryEntry[]>([]);

  useEffect(() => {
    api.get<SyncHistoryEntry[]>("/sync/history").then(setHistory).catch(() => {});
  }, []);

  const historyColumns: GridColDef[] = [
    { field: "tipo", headerName: "Tipo", flex: 1 },
    { field: "environment", headerName: "Ambiente", flex: 0.8 },
    { field: "client", headerName: "Cliente", flex: 0.8 },
    { field: "vessel", headerName: "Vessel", flex: 1 },
    { field: "last_updated", headerName: "Última atualização", flex: 1.2 },
  ];

  const historyRows = history.map((h, i) => ({
    id: i,
    tipo: h.sync_type === "items" ? "Items / Generators" : "Templates",
    environment: h.environment.toUpperCase(),
    client: h.client.toUpperCase(),
    vessel: h.vessel || "—",
    last_updated: h.last_updated,
  }));

  return (
    <AppLayout>
      {/* Histórico */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 2 }}>Status das sincronizações</Typography>
          {history.length === 0 ? (
            <Alert severity="info">Nenhuma sincronização realizada ainda.</Alert>
          ) : (
            <DataGrid
              rows={historyRows}
              columns={historyColumns}
              autoHeight
              pageSizeOptions={[10]}
              initialState={{ pagination: { paginationModel: { pageSize: 10 } } }}
              sx={{ border: "none" }}
              disableRowSelectionOnClick
            />
          )}
        </CardContent>
      </Card>

      {/* Tabs */}
      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 3 }}>
        <Tab label="Items / Atributos / Generators" />
        <Tab label="Template Attributes" />
      </Tabs>

      {tab === 0 && <SyncItemsSection />}
      {tab === 1 && <SyncTemplatesSection />}
    </AppLayout>
  );
}

function SyncItemsSection() {
  const [searchTerm, setSearchTerm] = useState("");
  const [candidates, setCandidates] = useState<{ id: string; name: string }[]>([]);
  const [selectedRoot, setSelectedRoot] = useState("");
  const [vesselName, setVesselName] = useState("");
  const [loading, setLoading] = useState(false);
  const [searching, setSearching] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState("");

  const env = typeof window !== "undefined" ? localStorage.getItem("lh_environment") || "" : "";
  const client = typeof window !== "undefined" ? localStorage.getItem("lh_client_name") || "" : "";

  const handleSearch = async () => {
    setSearching(true);
    setError("");
    setCandidates([]);
    try {
      const data = await api.post<{ id: string; name: string }[]>("/sync/search-root", {
        search_term: searchTerm,
        environment: env,
        client_name: client,
      });
      setCandidates(data);
      if (!data.length) setError(`Nenhum item encontrado com '${searchTerm}'.`);
    } catch (e: any) {
      setError(e.message);
    }
    setSearching(false);
  };

  const handleSync = async () => {
    setLoading(true);
    setResult(null);
    setError("");
    try {
      const res = await api.post<{ message: string }>("/sync/items", {
        root_id: selectedRoot,
        vessel_name: vesselName || searchTerm.toUpperCase(),
        environment: env,
        client_name: client,
      });
      setResult(res.message);
    } catch (e: any) {
      setError(e.message);
    }
    setLoading(false);
  };

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 1 }}>Sincronizar Items / Atributos / Generators</Typography>
        <Chip label={`${env} / ${client}`} size="small" sx={{ mb: 2 }} />

        <Box sx={{ display: "flex", gap: 2, mb: 2 }}>
          <TextField
            size="small"
            label="Nome do vessel"
            placeholder="MV32, BRAVO, PRIO..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            sx={{ flex: 1 }}
          />
          <Button variant="outlined" onClick={handleSearch} disabled={!searchTerm || searching}>
            {searching ? "Buscando..." : "Buscar"}
          </Button>
        </Box>

        {candidates.length > 0 && (
          <Box sx={{ mb: 2 }}>
            <FormControl size="small" fullWidth sx={{ mb: 2 }}>
              <InputLabel>Item raiz</InputLabel>
              <Select value={selectedRoot} label="Item raiz" onChange={(e) => setSelectedRoot(e.target.value)}>
                {candidates.map((c) => (
                  <MenuItem key={c.id} value={c.id}>{c.name} ({c.id.substring(0, 8)}...)</MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              size="small"
              fullWidth
              label="Nome do vessel para gravar"
              value={vesselName || searchTerm.toUpperCase()}
              onChange={(e) => setVesselName(e.target.value)}
              sx={{ mb: 2 }}
            />
            <Button variant="contained" onClick={handleSync} disabled={!selectedRoot || loading}>
              {loading ? "Sincronizando..." : "Sincronizar Items"}
            </Button>
          </Box>
        )}

        {loading && <LinearProgress sx={{ mt: 1 }} />}
        {result && <Alert severity="success" sx={{ mt: 2 }}>{result}</Alert>}
        {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
      </CardContent>
    </Card>
  );
}

function SyncTemplatesSection() {
  const [templates, setTemplates] = useState<Record<string, string>>({});
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingList, setLoadingList] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState("");

  const env = typeof window !== "undefined" ? localStorage.getItem("lh_environment") || "" : "";
  const client = typeof window !== "undefined" ? localStorage.getItem("lh_client_name") || "" : "";

  const loadTemplates = async () => {
    setLoadingList(true);
    try {
      const data = await api.get<Record<string, string>>(`/sync/templates/list?environment=${env}&client_name=${client}`);
      setTemplates(data);
    } catch (e: any) {
      setError(e.message);
    }
    setLoadingList(false);
  };

  const handleSync = async () => {
    setLoading(true);
    setResult(null);
    setError("");
    try {
      const res = await api.post<{ message: string }>("/sync/templates", {
        environment: env,
        client_name: client,
        template_ids: selectedIds.length ? selectedIds : null,
      });
      setResult(res.message);
    } catch (e: any) {
      setError(e.message);
    }
    setLoading(false);
  };

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 1 }}>Sincronizar Template Attributes</Typography>
        <Chip label={`${env} / ${client}`} size="small" sx={{ mb: 2 }} />

        <Button variant="outlined" onClick={loadTemplates} disabled={loadingList} sx={{ mb: 2 }}>
          {loadingList ? "Carregando..." : "Carregar templates"}
        </Button>

        {Object.keys(templates).length > 0 && (
          <Box sx={{ mb: 2 }}>
            <FormControl size="small" fullWidth sx={{ mb: 2 }}>
              <InputLabel>Templates (vazio = todos)</InputLabel>
              <Select
                multiple
                value={selectedIds}
                label="Templates (vazio = todos)"
                onChange={(e) => setSelectedIds(e.target.value as string[])}
                renderValue={(sel) => sel.map((id) => templates[id]).join(", ")}
              >
                {Object.entries(templates)
                  .sort(([, a], [, b]) => a.localeCompare(b))
                  .map(([id, name]) => (
                    <MenuItem key={id} value={id}>{name}</MenuItem>
                  ))}
              </Select>
            </FormControl>
            <Button variant="contained" onClick={handleSync} disabled={loading}>
              {loading ? "Sincronizando..." : selectedIds.length ? `Sincronizar ${selectedIds.length} template(s)` : "Sincronizar todos"}
            </Button>
          </Box>
        )}

        {loading && <LinearProgress sx={{ mt: 1 }} />}
        {result && <Alert severity="success" sx={{ mt: 2 }}>{result}</Alert>}
        {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
      </CardContent>
    </Card>
  );
}
