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
  Chip,
  Checkbox,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  FormControlLabel,
} from "@mui/material";
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Search as AnalyzeIcon,
  ContentCopy as CopyIcon,
  Warning as WarningIcon,
} from "@mui/icons-material";
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
        <Tab label="Copiar entre Ambientes" />
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

interface AnalysisResult {
  templates_to_copy: Array<{
    id: string;
    name: string;
    attrs: any[];
    root_count: number;
    sub_count: number;
  }>;
  duplicates: string[];
  missing_categories: string[];
}

function CopyTemplateSection() {
  const [environments, setEnvironments] = useState<Record<string, string[]>>({});
  const [srcEnv, setSrcEnv] = useState("");
  const [srcClient, setSrcClient] = useState("");
  const [sourceTemplates, setSourceTemplates] = useState<Record<string, string>>({});
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [proceedAnyway, setProceedAnyway] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadingTemplates, setLoadingTemplates] = useState(false);
  const [copying, setCopying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<string | null>(null);
  const [copyErrors, setCopyErrors] = useState<string[]>([]);
  const [error, setError] = useState("");

  const env = typeof window !== "undefined" ? localStorage.getItem("lh_environment") || "" : "";
  const client = typeof window !== "undefined" ? localStorage.getItem("lh_client_name") || "" : "";

  useEffect(() => {
    api.get<Record<string, string[]>>("/environments").then(setEnvironments).catch(() => {});
  }, []);

  const isSameEnv = srcEnv === env && srcClient === client;

  const loadSourceTemplates = async () => {
    setLoadingTemplates(true);
    setError("");
    setSourceTemplates({});
    setSelectedIds(new Set());
    setAnalysis(null);
    setResult(null);
    setCopyErrors([]);
    try {
      const data = await api.get<Record<string, string>>(
        `/templates/source-templates?environment=${srcEnv}&client_name=${srcClient}`
      );
      setSourceTemplates(data);
    } catch (e: any) {
      setError(e.message);
    }
    setLoadingTemplates(false);
  };

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
    setAnalysis(null);
    setResult(null);
  };

  const toggleAll = () => {
    if (selectedIds.size === Object.keys(sourceTemplates).length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(Object.keys(sourceTemplates)));
    }
    setAnalysis(null);
    setResult(null);
  };

  const handleAnalyze = async () => {
    setLoading(true);
    setError("");
    setAnalysis(null);
    setResult(null);
    setCopyErrors([]);
    setProceedAnyway(false);
    try {
      const data = await api.post<AnalysisResult>("/templates/copy/analyze", {
        template_ids: Array.from(selectedIds),
        source_environment: srcEnv,
        source_client: srcClient,
        target_environment: env,
        target_client: client,
      });
      setAnalysis(data);
    } catch (e: any) {
      setError(e.message);
    }
    setLoading(false);
  };

  const handleCopy = async () => {
    if (!analysis) return;
    setCopying(true);
    setResult(null);
    setCopyErrors([]);
    setError("");
    setProgress(0);
    try {
      const data = await api.post<{ message: string; created: number; errors: string[] }>("/templates/copy/execute", {
        templates: analysis.templates_to_copy,
        source_environment: srcEnv,
        source_client: srcClient,
        target_environment: env,
        target_client: client,
      });
      setResult(data.message);
      setCopyErrors(data.errors || []);
      setProgress(100);
    } catch (e: any) {
      setError(e.message);
    }
    setCopying(false);
  };

  const sortedTemplates = Object.entries(sourceTemplates).sort(([, a], [, b]) => a.localeCompare(b));

  return (
    <Box>
      {/* Destino */}
      <Card sx={{ mb: 2 }}>
        <CardContent sx={{ py: 2 }}>
          <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 0.5 }}>
            Ambiente de destino (atual)
          </Typography>
          <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
            <Chip label={env || "—"} color="primary" size="small" />
            <Chip label={client || "—"} variant="outlined" size="small" />
          </Box>
        </CardContent>
      </Card>

      {/* Origem */}
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 2 }}>Origem</Typography>
          <Box sx={{ display: "flex", gap: 2, mb: 2 }}>
            <FormControl size="small" sx={{ flex: 1 }}>
              <InputLabel>Ambiente de origem</InputLabel>
              <Select
                value={srcEnv}
                label="Ambiente de origem"
                onChange={(e) => {
                  setSrcEnv(e.target.value);
                  setSrcClient("");
                  setSourceTemplates({});
                  setSelectedIds(new Set());
                  setAnalysis(null);
                  setResult(null);
                }}
              >
                {Object.keys(environments).map((e) => (
                  <MenuItem key={e} value={e}>{e}</MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl size="small" sx={{ flex: 1 }}>
              <InputLabel>Cliente de origem</InputLabel>
              <Select
                value={srcClient}
                label="Cliente de origem"
                onChange={(e) => {
                  setSrcClient(e.target.value);
                  setSourceTemplates({});
                  setSelectedIds(new Set());
                  setAnalysis(null);
                  setResult(null);
                }}
                disabled={!srcEnv}
              >
                {(environments[srcEnv] || []).map((c) => (
                  <MenuItem key={c} value={c}>{c}</MenuItem>
                ))}
              </Select>
            </FormControl>
            <Button
              variant="outlined"
              onClick={loadSourceTemplates}
              disabled={!srcEnv || !srcClient || isSameEnv || loadingTemplates}
              sx={{ whiteSpace: "nowrap" }}
            >
              {loadingTemplates ? "Carregando..." : "Carregar Templates"}
            </Button>
          </Box>
          {isSameEnv && srcEnv && (
            <Alert severity="info" sx={{ mt: 1 }}>Origem e destino são o mesmo ambiente.</Alert>
          )}
        </CardContent>
      </Card>

      {/* Lista de templates da origem */}
      {sortedTemplates.length > 0 && (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 1 }}>
              <Typography variant="h6">
                Templates da origem ({sortedTemplates.length})
              </Typography>
              <Button size="small" onClick={toggleAll}>
                {selectedIds.size === sortedTemplates.length ? "Desmarcar todos" : "Selecionar todos"}
              </Button>
            </Box>
            <List dense sx={{ maxHeight: 300, overflow: "auto", border: 1, borderColor: "divider", borderRadius: 1 }}>
              {sortedTemplates.map(([id, name]) => (
                <ListItem key={id} disablePadding>
                  <ListItemButton onClick={() => toggleSelect(id)} dense>
                    <ListItemIcon sx={{ minWidth: 36 }}>
                      <Checkbox
                        edge="start"
                        checked={selectedIds.has(id)}
                        disableRipple
                        size="small"
                      />
                    </ListItemIcon>
                    <ListItemText primary={name} primaryTypographyProps={{ fontSize: 14 }} />
                  </ListItemButton>
                </ListItem>
              ))}
            </List>

            {selectedIds.size > 0 && (
              <Box sx={{ mt: 2 }}>
                <Button
                  variant="contained"
                  startIcon={<AnalyzeIcon />}
                  onClick={handleAnalyze}
                  disabled={loading}
                >
                  {loading ? "Analisando..." : `Analisar ${selectedIds.size} template(s)`}
                </Button>
              </Box>
            )}
            {loading && <LinearProgress sx={{ mt: 1 }} />}
          </CardContent>
        </Card>
      )}

      {/* Resultado da análise */}
      {analysis && (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2 }}>Resultado da Análise</Typography>

            {analysis.duplicates.length > 0 && (
              <Alert severity="warning" sx={{ mb: 2 }}>
                <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
                  Templates já existem no destino (serão ignorados):
                </Typography>
                {analysis.duplicates.map((d) => (
                  <Typography key={d} variant="body2">• {d}</Typography>
                ))}
              </Alert>
            )}

            {analysis.missing_categories.length > 0 && (
              <Alert severity="error" icon={<WarningIcon />} sx={{ mb: 2 }}>
                <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
                  Categorias não encontradas no destino:
                </Typography>
                {analysis.missing_categories.map((c) => (
                  <Typography key={c} variant="body2">• {c}</Typography>
                ))}
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                  Crie estas categorias no destino, ou os atributos serão copiados sem categoria.
                </Typography>
              </Alert>
            )}

            {analysis.templates_to_copy.length === 0 ? (
              <Alert severity="info">Nenhum template novo para copiar.</Alert>
            ) : (
              <>
                <Typography variant="subtitle2" sx={{ mb: 1 }}>
                  Templates a copiar ({analysis.templates_to_copy.length}):
                </Typography>
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Template</TableCell>
                        <TableCell align="center">Atributos</TableCell>
                        <TableCell align="center">Subatributos</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {analysis.templates_to_copy.map((t) => (
                        <TableRow key={t.id}>
                          <TableCell>{t.name}</TableCell>
                          <TableCell align="center">{t.root_count}</TableCell>
                          <TableCell align="center">{t.sub_count}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>

                {analysis.missing_categories.length > 0 && (
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={proceedAnyway}
                        onChange={(e) => setProceedAnyway(e.target.checked)}
                        size="small"
                      />
                    }
                    label="Continuar mesmo assim (atributos com categorias em falta serão copiados sem categoria)"
                    sx={{ mt: 2 }}
                  />
                )}

                <Box sx={{ mt: 2 }}>
                  <Button
                    variant="contained"
                    color="success"
                    startIcon={<CopyIcon />}
                    onClick={handleCopy}
                    disabled={
                      copying ||
                      analysis.templates_to_copy.length === 0 ||
                      (analysis.missing_categories.length > 0 && !proceedAnyway)
                    }
                  >
                    {copying ? "Copiando..." : `Copiar ${analysis.templates_to_copy.length} template(s)`}
                  </Button>
                </Box>
                {copying && <LinearProgress sx={{ mt: 1 }} />}
              </>
            )}
          </CardContent>
        </Card>
      )}

      {/* Resultado final */}
      {result && <Alert severity="success" sx={{ mt: 2 }}>{result}</Alert>}
      {copyErrors.length > 0 && (
        <Alert severity="error" sx={{ mt: 2 }}>
          <Typography variant="body2" sx={{ fontWeight: 600 }}>Erros:</Typography>
          {copyErrors.map((e, i) => (
            <Typography key={i} variant="body2">• {e}</Typography>
          ))}
        </Alert>
      )}
      {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
    </Box>
  );
}
