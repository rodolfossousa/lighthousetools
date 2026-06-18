"use client";
import { useState } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Alert,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  LinearProgress,
} from "@mui/material";
import { Add as AddIcon, Delete as DeleteIcon } from "@mui/icons-material";
import AppLayout from "@/components/layout/AppLayout";
import { api } from "@/lib/api";

interface AttributeRow {
  name: string;
  type: string;
  unit: string;
  decimal_places: number;
  default_value: string;
  description: string;
}

const ATTR_TYPES = [
  "Manual Text",
  "Manual Float",
  "Manual Integer",
  "Manual Boolean",
  "TimeSeries Float",
  "TimeSeries Integer",
  "TimeSeries Text",
];

export default function TemplatesPage() {
  const [tab, setTab] = useState(0);

  return (
    <AppLayout>
      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 3 }}>
        <Tab label="Criar Template" />
        <Tab label="Copiar Template" />
      </Tabs>

      {tab === 0 && <CreateTemplateSection />}
      {tab === 1 && <CopyTemplateSection />}
    </AppLayout>
  );
}

function CreateTemplateSection() {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [attributes, setAttributes] = useState<AttributeRow[]>([
    { name: "", type: "Manual Text", unit: "", decimal_places: 2, default_value: "", description: "" },
  ]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState("");

  const env = typeof window !== "undefined" ? localStorage.getItem("lh_environment") || "" : "";
  const client = typeof window !== "undefined" ? localStorage.getItem("lh_client_name") || "" : "";

  const addRow = () => {
    setAttributes([...attributes, { name: "", type: "Manual Text", unit: "", decimal_places: 2, default_value: "", description: "" }]);
  };

  const removeRow = (idx: number) => {
    setAttributes(attributes.filter((_, i) => i !== idx));
  };

  const updateRow = (idx: number, field: keyof AttributeRow, value: string | number) => {
    const updated = [...attributes];
    (updated[idx] as any)[field] = value;
    setAttributes(updated);
  };

  const handleCreate = async () => {
    setLoading(true);
    setResult(null);
    setError("");
    try {
      const apiAttrs = attributes
        .filter((a) => a.name)
        .map((a) => ({
          name: a.name,
          description: a.description,
          type: a.type,
          unit_of_measurement: a.unit,
          decimal_places: a.decimal_places,
          default_value: a.default_value || null,
        }));
      await api.post("/templates", {
        name,
        description,
        attributes: apiAttrs,
        environment: env,
        client_name: client,
      });
      setResult(`Template '${name}' criado com sucesso.`);
      setName("");
      setDescription("");
      setAttributes([{ name: "", type: "Manual Text", unit: "", decimal_places: 2, default_value: "", description: "" }]);
    } catch (e: any) {
      setError(e.message);
    }
    setLoading(false);
  };

  return (
    <Box>
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 2 }}>Informações do Template</Typography>
          <Box sx={{ display: "flex", gap: 2, mb: 2 }}>
            <TextField
              size="small"
              label="Nome do template"
              value={name}
              onChange={(e) => setName(e.target.value)}
              sx={{ flex: 1 }}
            />
            <TextField
              size="small"
              label="Descrição"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              sx={{ flex: 1 }}
            />
          </Box>
        </CardContent>
      </Card>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
            <Typography variant="h6">Atributos ({attributes.length})</Typography>
            <Button size="small" startIcon={<AddIcon />} onClick={addRow}>
              Adicionar
            </Button>
          </Box>
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Nome</TableCell>
                  <TableCell>Tipo</TableCell>
                  <TableCell>Unidade</TableCell>
                  <TableCell>Decimais</TableCell>
                  <TableCell>Valor padrão</TableCell>
                  <TableCell>Descrição</TableCell>
                  <TableCell width={50}></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {attributes.map((attr, idx) => (
                  <TableRow key={idx}>
                    <TableCell>
                      <TextField
                        size="small"
                        variant="standard"
                        value={attr.name}
                        onChange={(e) => updateRow(idx, "name", e.target.value)}
                        placeholder="Nome do atributo"
                      />
                    </TableCell>
                    <TableCell>
                      <FormControl size="small" variant="standard" sx={{ minWidth: 130 }}>
                        <Select value={attr.type} onChange={(e) => updateRow(idx, "type", e.target.value)}>
                          {ATTR_TYPES.map((t) => (
                            <MenuItem key={t} value={t}>{t}</MenuItem>
                          ))}
                        </Select>
                      </FormControl>
                    </TableCell>
                    <TableCell>
                      <TextField
                        size="small"
                        variant="standard"
                        value={attr.unit}
                        onChange={(e) => updateRow(idx, "unit", e.target.value)}
                        sx={{ width: 80 }}
                      />
                    </TableCell>
                    <TableCell>
                      <TextField
                        size="small"
                        variant="standard"
                        type="number"
                        value={attr.decimal_places}
                        onChange={(e) => updateRow(idx, "decimal_places", Number(e.target.value))}
                        sx={{ width: 60 }}
                      />
                    </TableCell>
                    <TableCell>
                      <TextField
                        size="small"
                        variant="standard"
                        value={attr.default_value}
                        onChange={(e) => updateRow(idx, "default_value", e.target.value)}
                        sx={{ width: 100 }}
                      />
                    </TableCell>
                    <TableCell>
                      <TextField
                        size="small"
                        variant="standard"
                        value={attr.description}
                        onChange={(e) => updateRow(idx, "description", e.target.value)}
                      />
                    </TableCell>
                    <TableCell>
                      <IconButton size="small" onClick={() => removeRow(idx)}>
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      <Button variant="contained" onClick={handleCreate} disabled={loading || !name}>
        {loading ? "Criando..." : "Criar Template"}
      </Button>
      {loading && <LinearProgress sx={{ mt: 1 }} />}
      {result && <Alert severity="success" sx={{ mt: 2 }}>{result}</Alert>}
      {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
    </Box>
  );
}

function CopyTemplateSection() {
  const [templateId, setTemplateId] = useState("");
  const [sourceTemplates, setSourceTemplates] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState("");

  const env = typeof window !== "undefined" ? localStorage.getItem("lh_environment") || "" : "";
  const client = typeof window !== "undefined" ? localStorage.getItem("lh_client_name") || "" : "";

  const loadTemplates = async () => {
    try {
      const data = await api.get<Record<string, string>>(`/sync/templates/list?environment=${env}&client_name=${client}`);
      setSourceTemplates(data);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleCopy = async () => {
    setLoading(true);
    setResult(null);
    setError("");
    try {
      const res = await api.post<{ message: string }>("/templates/copy", {
        template_id: templateId,
        source_environment: env,
        source_client: client,
        target_environment: env,
        target_client: client,
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
        <Typography variant="h6" sx={{ mb: 2 }}>Copiar Template entre ambientes</Typography>

        <Button variant="outlined" onClick={loadTemplates} sx={{ mb: 2 }}>
          Carregar templates do ambiente atual
        </Button>

        {Object.keys(sourceTemplates).length > 0 && (
          <Box sx={{ mb: 2 }}>
            <FormControl fullWidth size="small" sx={{ mb: 2 }}>
              <InputLabel>Template de origem</InputLabel>
              <Select value={templateId} label="Template de origem" onChange={(e) => setTemplateId(e.target.value)}>
                {Object.entries(sourceTemplates)
                  .sort(([, a], [, b]) => a.localeCompare(b))
                  .map(([id, name]) => (
                    <MenuItem key={id} value={id}>{name}</MenuItem>
                  ))}
              </Select>
            </FormControl>
            <Button variant="contained" onClick={handleCopy} disabled={!templateId || loading}>
              {loading ? "Copiando..." : "Copiar Template"}
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
