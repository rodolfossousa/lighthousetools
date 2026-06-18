"use client";
import { useState, useEffect, useCallback } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  Alert,
  Chip,
  LinearProgress,
} from "@mui/material";
import { DataGrid, GridColDef, GridRowSelectionModel } from "@mui/x-data-grid";
import AppLayout from "@/components/layout/AppLayout";
import { api } from "@/lib/api";
import type { Generator } from "@/types";

export default function ModelsPage() {
  const [vessels, setVessels] = useState<string[]>([]);
  const [vesselFilter, setVesselFilter] = useState("");
  const [search, setSearch] = useState("");
  const [generators, setGenerators] = useState<Generator[]>([]);
  const [selection, setSelection] = useState<GridRowSelectionModel>([]);
  const [newStatus, setNewStatus] = useState("OFFLINE");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ success: number; error: number; errors: string[] } | null>(null);

  useEffect(() => {
    api.get<string[]>("/explorer/vessels").then(setVessels).catch(() => {});
  }, []);

  const fetchGenerators = useCallback(async () => {
    const params = new URLSearchParams();
    if (vesselFilter) params.set("vessel", vesselFilter);
    if (search) params.set("search", search);
    const data = await api.get<Generator[]>(`/models?${params}`);
    setGenerators(data);
  }, [vesselFilter, search]);

  useEffect(() => {
    fetchGenerators();
  }, [fetchGenerators]);

  const handleExecute = async () => {
    const env = localStorage.getItem("lh_environment") || "";
    const client = localStorage.getItem("lh_client_name") || "";
    const ids = selection.map((idx) => generators[idx as number]?.id_attribute).filter(Boolean) as string[];
    if (!ids.length) return;
    setLoading(true);
    setResult(null);
    try {
      const res = await api.post<{ success: number; error: number; errors: string[] }>("/models/status", {
        generator_ids: ids,
        status: newStatus,
        environment: env,
        client_name: client,
      });
      setResult(res);
    } catch (e: any) {
      setResult({ success: 0, error: 1, errors: [e.message] });
    }
    setLoading(false);
  };

  const columns: GridColDef[] = [
    { field: "vessel", headerName: "Vessel", flex: 1 },
    { field: "name", headerName: "Equipamento", flex: 1.5 },
    { field: "value", headerName: "Modelo", flex: 1.5 },
    { field: "specification", headerName: "Tipo", flex: 1 },
    { field: "id_attribute", headerName: "Generator ID", flex: 1.5 },
  ];

  const rows = generators.map((g, i) => ({ ...g, id: i, item_id: g.id }));

  return (
    <AppLayout>
      <Box sx={{ display: "flex", gap: 2, mb: 3 }}>
        <FormControl sx={{ minWidth: 180 }} size="small">
          <InputLabel>Vessel</InputLabel>
          <Select value={vesselFilter} label="Vessel" onChange={(e) => setVesselFilter(e.target.value)}>
            <MenuItem value="">Todos</MenuItem>
            {vessels.map((v) => (
              <MenuItem key={v} value={v}>{v}</MenuItem>
            ))}
          </Select>
        </FormControl>
        <TextField
          size="small"
          label="Buscar"
          placeholder="equipamento ou modelo..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          sx={{ minWidth: 280 }}
        />
        <Chip label={`${generators.length} modelos`} variant="outlined" sx={{ alignSelf: "center" }} />
      </Box>

      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 0, "&:last-child": { pb: 0 } }}>
          <DataGrid
            rows={rows}
            columns={columns}
            checkboxSelection
            onRowSelectionModelChange={setSelection}
            rowSelectionModel={selection}
            autoHeight
            pageSizeOptions={[25, 50, 100]}
            initialState={{ pagination: { paginationModel: { pageSize: 25 } } }}
            sx={{ border: "none" }}
            disableRowSelectionOnClick
          />
        </CardContent>
      </Card>

      {selection.length > 0 && (
        <Card>
          <CardContent sx={{ display: "flex", alignItems: "center", gap: 2 }}>
            <Typography variant="body2">
              <strong>{selection.length}</strong> modelo(s) selecionado(s)
            </Typography>
            <FormControl size="small" sx={{ minWidth: 140 }}>
              <InputLabel>Novo status</InputLabel>
              <Select value={newStatus} label="Novo status" onChange={(e) => setNewStatus(e.target.value)}>
                <MenuItem value="OFFLINE">OFFLINE</MenuItem>
                <MenuItem value="ONLINE">ONLINE</MenuItem>
              </Select>
            </FormControl>
            <Button variant="contained" onClick={handleExecute} disabled={loading}>
              Executar
            </Button>
          </CardContent>
          {loading && <LinearProgress />}
        </Card>
      )}

      {result && (
        <Box sx={{ mt: 2 }}>
          {result.success > 0 && (
            <Alert severity="success" sx={{ mb: 1 }}>
              {result.success} modelo(s) alterado(s) para <strong>{newStatus}</strong>.
            </Alert>
          )}
          {result.error > 0 && (
            <Alert severity="error">
              {result.error} modelo(s) falharam.
              {result.errors.map((err, i) => (
                <Typography key={i} variant="caption" display="block">{err}</Typography>
              ))}
            </Alert>
          )}
        </Box>
      )}
    </AppLayout>
  );
}
