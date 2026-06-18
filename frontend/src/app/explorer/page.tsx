"use client";
import { useState, useEffect, useCallback } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Alert,
  TextField,
  Button,
  IconButton,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Tabs,
  Tab,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tooltip,
  LinearProgress,
  Checkbox,
} from "@mui/material";
import {
  ExpandMore as ExpandMoreIcon,
  Edit as EditIcon,
  Save as SaveIcon,
  Cancel as CancelIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
  DriveFileRenameOutline as RenameIcon,
  FolderOpen,
  Settings as GearIcon,
  AccountTree as TreeIcon,
} from "@mui/icons-material";
import { SimpleTreeView, TreeItem } from "@mui/x-tree-view";
import AppLayout from "@/components/layout/AppLayout";
import { api } from "@/lib/api";
import type { ItemNode, ItemAttribute, SubAttribute } from "@/types";

const COLORS = {
  system: "#66BB6A",
  subsystem: "#42A5F5",
  equipment: "#FFA726",
};

function getItemColor(node: ItemNode) {
  if (node.is_leaf) return COLORS.equipment;
  if (node.parent_id) return COLORS.subsystem;
  return COLORS.system;
}

function getItemIcon(node: ItemNode) {
  if (node.is_leaf) return <GearIcon sx={{ fontSize: 14, color: COLORS.equipment }} />;
  if (node.parent_id) return <TreeIcon sx={{ fontSize: 14, color: COLORS.subsystem }} />;
  return <FolderOpen sx={{ fontSize: 14, color: COLORS.system }} />;
}

export default function ExplorerPage() {
  const [vessels, setVessels] = useState<string[]>([]);
  const [selectedVessel, setSelectedVessel] = useState("");
  const [items, setItems] = useState<ItemNode[]>([]);
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);
  const [attributes, setAttributes] = useState<ItemAttribute[]>([]);
  const [subattributes, setSubattributes] = useState<SubAttribute[]>([]);
  const [generators, setGenerators] = useState<any[]>([]);
  const [tab, setTab] = useState(0);
  const [saveResult, setSaveResult] = useState<{ type: "success" | "error"; msg: string } | null>(null);

  // Edit dialog state
  const [editAttr, setEditAttr] = useState<(ItemAttribute | SubAttribute) | null>(null);
  const [editType, setEditType] = useState<"attribute" | "subattribute">("attribute");
  const [editFields, setEditFields] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.get<string[]>("/explorer/vessels").then(setVessels).catch(() => {});
  }, []);

  useEffect(() => {
    if (selectedVessel) {
      api.get<ItemNode[]>(`/explorer/items/${encodeURIComponent(selectedVessel)}`).then(setItems).catch(() => {});
    }
  }, [selectedVessel]);

  const handleSelectItem = useCallback(async (itemId: string) => {
    setSelectedItemId(itemId);
    setSaveResult(null);
    try {
      const [attrs, subs, gens] = await Promise.all([
        api.get<ItemAttribute[]>(`/explorer/items/${itemId}/attributes`),
        api.get<SubAttribute[]>(`/explorer/items/${itemId}/subattributes`),
        api.get<any[]>(`/explorer/items/${itemId}/generators`),
      ]);
      setAttributes(attrs);
      setSubattributes(subs);
      setGenerators(gens);
    } catch {
      setAttributes([]);
      setSubattributes([]);
      setGenerators([]);
    }
  }, []);

  const openEditDialog = (attr: ItemAttribute | SubAttribute, type: "attribute" | "subattribute") => {
    setEditAttr(attr);
    setEditType(type);
    setEditFields({
      value: attr.value || "",
      reference: ("reference" in attr ? attr.reference : "") || "",
      unit_of_measurement: attr.unit_of_measurement || "",
      decimal_places: attr.decimal_places || "",
      description: attr.description || "",
    });
  };

  const handleSaveAttribute = async () => {
    if (!editAttr || !selectedItemId) return;
    setSaving(true);
    setSaveResult(null);
    const env = localStorage.getItem("lh_environment") || "";
    const client = localStorage.getItem("lh_client_name") || "";
    const qs = `environment=${encodeURIComponent(env)}&client_name=${encodeURIComponent(client)}`;
    try {
      await api.patch(`/explorer/items/${selectedItemId}/attribute-full?${qs}`, {
        attribute_id: editAttr.id_attribute,
        attr_type: editType,
        value: editFields.value || null,
        reference: editFields.reference || null,
        unit_of_measurement: editFields.unit_of_measurement || null,
        decimal_places: editFields.decimal_places || null,
        description: editFields.description || null,
      });
      setSaveResult({ type: "success", msg: "Atributo atualizado." });
      setEditAttr(null);
      handleSelectItem(selectedItemId);
    } catch (e: any) {
      setSaveResult({ type: "error", msg: e.message });
    } finally {
      setSaving(false);
    }
  };

  // Tree
  const rootItems = items.filter((i) => !i.parent_id);
  const getChildren = (parentId: string) => items.filter((i) => i.parent_id === parentId);

  const renderTree = (node: ItemNode) => (
    <TreeItem
      key={node.id}
      itemId={node.id}
      label={
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, py: 0.2 }}>
          {getItemIcon(node)}
          <Typography variant="body2" sx={{ fontSize: 12, color: getItemColor(node), fontWeight: node.id === selectedItemId ? 700 : 400 }}>
            {node.name}
          </Typography>
        </Box>
      }
      onClick={() => handleSelectItem(node.id)}
    >
      {getChildren(node.id).map(renderTree)}
    </TreeItem>
  );

  const selectedItem = items.find((i) => i.id === selectedItemId);

  // Group by category
  const subsByParent: Record<string, SubAttribute[]> = {};
  for (const s of subattributes) {
    (subsByParent[s.parent_attribute_id] ??= []).push(s);
  }
  const byCategory: Record<string, ItemAttribute[]> = {};
  for (const a of attributes) {
    (byCategory[a.category || "Sem Categoria"] ??= []).push(a);
  }

  return (
    <AppLayout>
      <Box sx={{ display: "flex", gap: 2, height: "calc(100vh - 130px)" }}>
        {/* Árvore */}
        <Card sx={{ width: 320, flexShrink: 0, overflow: "auto" }}>
          <CardContent sx={{ p: 1.5 }}>
            <FormControl size="small" fullWidth sx={{ mb: 1.5 }}>
              <InputLabel>Vessel</InputLabel>
              <Select value={selectedVessel} label="Vessel" onChange={(e) => setSelectedVessel(e.target.value)}>
                {vessels.map((v) => (<MenuItem key={v} value={v}>{v}</MenuItem>))}
              </Select>
            </FormControl>
            <Box sx={{ display: "flex", gap: 1, mb: 1, flexWrap: "wrap" }}>
              <Chip icon={<FolderOpen sx={{ fontSize: 12 }} />} label="Sistema" size="small"
                sx={{ bgcolor: `${COLORS.system}22`, color: COLORS.system, height: 20, fontSize: 10 }} />
              <Chip icon={<TreeIcon sx={{ fontSize: 12 }} />} label="Subsistema" size="small"
                sx={{ bgcolor: `${COLORS.subsystem}22`, color: COLORS.subsystem, height: 20, fontSize: 10 }} />
              <Chip icon={<GearIcon sx={{ fontSize: 12 }} />} label="Equipamento" size="small"
                sx={{ bgcolor: `${COLORS.equipment}22`, color: COLORS.equipment, height: 20, fontSize: 10 }} />
            </Box>
            {rootItems.length > 0 ? (
              <SimpleTreeView>{rootItems.map(renderTree)}</SimpleTreeView>
            ) : (
              <Typography variant="body2" color="text.secondary" sx={{ mt: 2, textAlign: "center" }}>
                {selectedVessel ? "Nenhum item encontrado." : "Seleciona um vessel."}
              </Typography>
            )}
          </CardContent>
        </Card>

        {/* Detalhe */}
        <Box sx={{ flex: 1, overflow: "auto" }}>
          {selectedItem ? (
            <>
              <Box sx={{ mb: 2 }}>
                <Typography variant="h6">{selectedItem.name}</Typography>
                <Typography variant="body2" color="text.secondary">
                  Template: {selectedItem.template_name || "—"} · ID: {selectedItem.id.substring(0, 12)}...
                </Typography>
              </Box>

              {saveResult && (
                <Alert severity={saveResult.type} sx={{ mb: 2 }} onClose={() => setSaveResult(null)}>
                  {saveResult.msg}
                </Alert>
              )}

              <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
                <Tab label={`Atributos (${attributes.length})`} />
                <Tab label={`Modelos (${generators.length})`} />
                <Tab label="Ações" />
              </Tabs>

              {/* TAB: Atributos */}
              {tab === 0 && (
                <Box>
                  <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: "block" }}>
                    Clica no ícone de edição para alterar um atributo.
                  </Typography>

                  {Object.entries(byCategory).sort(([a], [b]) => a.localeCompare(b)).map(([cat, attrs]) => {
                    const nSubs = attrs.reduce((sum, a) => sum + (subsByParent[a.id_attribute]?.length || 0), 0);
                    return (
                      <Accordion key={cat} disableGutters sx={{ mb: 0.5, "&:before": { display: "none" } }}>
                        <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ minHeight: 40 }}>
                          <Box sx={{ display: "flex", alignItems: "center", gap: 1, width: "100%" }}>
                            <Typography variant="subtitle2" sx={{ color: "primary.main" }}>{cat}</Typography>
                            <Chip label={`${attrs.length} attr`} size="small" sx={{ height: 18, fontSize: 10 }} />
                            {nSubs > 0 && (
                              <Chip label={`${nSubs} limiares`} size="small" color="warning" sx={{ height: 18, fontSize: 10 }} />
                            )}
                          </Box>
                        </AccordionSummary>
                        <AccordionDetails sx={{ p: 0 }}>
                          {attrs.map((attr) => {
                            const subs = subsByParent[attr.id_attribute] || [];
                            const isTS = attr.specification?.includes("TimeSeries") || attr.specification?.includes("Time");
                            return (
                              <Accordion key={attr.id_attribute} disableGutters elevation={0}
                                sx={{ ml: 2, "&:before": { display: "none" }, bgcolor: "transparent" }}>
                                <AccordionSummary
                                  expandIcon={subs.length > 0 ? <ExpandMoreIcon sx={{ fontSize: 16 }} /> : <Box sx={{ width: 16 }} />}
                                  sx={{ minHeight: 36, px: 1 }}
                                >
                                  <Box sx={{ display: "flex", alignItems: "center", gap: 1, width: "100%", overflow: "hidden" }}>
                                    <Tooltip title="Editar atributo">
                                      <Box component="span" onClick={(e) => { e.stopPropagation(); openEditDialog(attr, "attribute"); }}
                                        sx={{ display: "inline-flex", cursor: "pointer", p: 0.3, borderRadius: 1, "&:hover": { bgcolor: "action.hover" } }}>
                                        <EditIcon sx={{ fontSize: 14 }} />
                                      </Box>
                                    </Tooltip>
                                    <Typography variant="body2" sx={{ fontWeight: 500, minWidth: 160, fontSize: 13 }}>
                                      {attr.name_attribute}
                                    </Typography>
                                    <Box sx={{ flex: 1, display: "flex", gap: 1, alignItems: "center", overflow: "hidden" }}>
                                      {isTS && attr.reference ? (
                                        <Chip label={attr.reference} size="small" variant="outlined" color="info"
                                          sx={{ height: 20, fontSize: 11 }} />
                                      ) : attr.value ? (
                                        <Typography variant="body2" sx={{ fontSize: 12 }}>{attr.value}</Typography>
                                      ) : (
                                        <Typography variant="body2" sx={{ fontSize: 12, color: "text.disabled" }}>—</Typography>
                                      )}
                                      {attr.unit_of_measurement && (
                                        <Chip label={attr.unit_of_measurement} size="small" variant="outlined"
                                          sx={{ height: 18, fontSize: 9 }} />
                                      )}
                                    </Box>
                                    <Chip label={attr.specification} size="small" sx={{ height: 18, fontSize: 10, flexShrink: 0 }} />
                                    {subs.length > 0 && (
                                      <Chip label={`${subs.length}`} size="small" color="warning"
                                        sx={{ height: 16, fontSize: 9, minWidth: 20, flexShrink: 0 }} />
                                    )}
                                  </Box>
                                </AccordionSummary>
                                {subs.length > 0 && (
                                  <AccordionDetails sx={{ py: 0, pl: 3, pr: 1 }}>
                                    <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: "block" }}>
                                      Limiares
                                    </Typography>
                                    <TableContainer>
                                      <Table size="small">
                                        <TableBody>
                                          {subs.map((sub) => (
                                            <TableRow key={sub.id_attribute} sx={{ "&:last-child td": { borderBottom: 0 } }}>
                                              <TableCell sx={{ fontSize: 12, py: 0.5, pl: 0, width: 24 }}>
                                                <Tooltip title="Editar limiar">
                                                  <IconButton size="small"
                                                    onClick={() => openEditDialog(sub, "subattribute")}
                                                    sx={{ p: 0.3 }}>
                                                    <EditIcon sx={{ fontSize: 12 }} />
                                                  </IconButton>
                                                </Tooltip>
                                              </TableCell>
                                              <TableCell sx={{ fontSize: 12, py: 0.5, width: "35%" }}>
                                                ↳ {sub.name_attribute}
                                              </TableCell>
                                              <TableCell sx={{ fontSize: 12, py: 0.5 }}>
                                                {sub.value || "—"}
                                              </TableCell>
                                              <TableCell sx={{ fontSize: 10, py: 0.5, color: "text.secondary", width: 80 }}>
                                                {sub.specification}
                                              </TableCell>
                                            </TableRow>
                                          ))}
                                        </TableBody>
                                      </Table>
                                    </TableContainer>
                                  </AccordionDetails>
                                )}
                              </Accordion>
                            );
                          })}
                        </AccordionDetails>
                      </Accordion>
                    );
                  })}
                </Box>
              )}

              {/* TAB: Modelos */}
              {tab === 1 && (
                <ModelsTab
                  generators={generators}
                  onStatusChanged={() => handleSelectItem(selectedItemId!)}
                />
              )}

              {/* TAB: Ações */}
              {tab === 2 && (
                <ActionsTab
                  itemId={selectedItemId!}
                  itemName={selectedItem.name}
                  vessel={selectedVessel}
                  onRefresh={() => {
                    api.get<ItemNode[]>(`/explorer/items/${encodeURIComponent(selectedVessel)}`).then(setItems).catch(() => {});
                    handleSelectItem(selectedItemId!);
                  }}
                />
              )}
            </>
          ) : (
            <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%" }}>
              <Typography color="text.secondary">Seleciona um item na árvore para ver detalhes.</Typography>
            </Box>
          )}
        </Box>
      </Box>

      {/* ============ Dialog: Editar Atributo ============ */}
      <Dialog open={!!editAttr} onClose={() => setEditAttr(null)} maxWidth="sm" fullWidth>
        <DialogTitle>Editar Atributo</DialogTitle>
        <DialogContent>
          {editAttr && (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
              {saving && <LinearProgress />}

              {/* Read-only info */}
              <TextField size="small" label="Item" value={selectedItemId || ""} slotProps={{ input: { readOnly: true } }}
                sx={{ "& .MuiInputBase-input": { color: "text.secondary" } }} />
              <TextField size="small" label="Atributo" value={editAttr.name_attribute} slotProps={{ input: { readOnly: true } }}
                sx={{ "& .MuiInputBase-input": { color: "text.secondary" } }} />
              <TextField size="small" label="Tipo" value={editAttr.specification || ""} slotProps={{ input: { readOnly: true } }}
                sx={{ "& .MuiInputBase-input": { color: "text.secondary" } }} />

              {/* Editable fields */}
              <TextField size="small" label="Descrição"
                value={editFields.description || ""}
                onChange={(e) => setEditFields((f) => ({ ...f, description: e.target.value }))}
              />
              <TextField size="small" label="Referência (Sensor / Tag)"
                value={editFields.reference || ""}
                onChange={(e) => setEditFields((f) => ({ ...f, reference: e.target.value }))}
              />
              <TextField size="small" label="Valor"
                value={editFields.value || ""}
                onChange={(e) => setEditFields((f) => ({ ...f, value: e.target.value }))}
              />
              <TextField size="small" label="Unidade de Medida"
                value={editFields.unit_of_measurement || ""}
                onChange={(e) => setEditFields((f) => ({ ...f, unit_of_measurement: e.target.value }))}
              />
              <TextField size="small" label="Casas Decimais" type="number"
                value={editFields.decimal_places || ""}
                onChange={(e) => setEditFields((f) => ({ ...f, decimal_places: e.target.value }))}
              />
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditAttr(null)} disabled={saving}>Cancelar</Button>
          <Button variant="contained" onClick={handleSaveAttribute} disabled={saving} startIcon={<SaveIcon />}>
            Guardar
          </Button>
        </DialogActions>
      </Dialog>
    </AppLayout>
  );
}

// ===================== Modelos =====================

function ModelsTab({ generators, onStatusChanged }: {
  generators: any[]; onStatusChanged: () => void;
}) {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [newStatus, setNewStatus] = useState("OFFLINE");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ type: "success" | "error" | "warning"; msg: string } | null>(null);

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    if (selected.size === generators.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(generators.map((g) => g.id_attribute)));
    }
  };

  const handleChangeStatus = async () => {
    const ids = Array.from(selected);
    if (!ids.length) return;
    setLoading(true);
    setResult(null);
    const env = localStorage.getItem("lh_environment") || "";
    const client = localStorage.getItem("lh_client_name") || "";
    try {
      const res = await api.post<{ success: number; error: number; errors: string[] }>("/models/status", {
        generator_ids: ids,
        status: newStatus,
        environment: env,
        client_name: client,
      });
      if (res.error > 0) {
        setResult({ type: "warning", msg: `${res.success} alterado(s), ${res.error} falharam.` });
      } else {
        setResult({ type: "success", msg: `${res.success} modelo(s) alterado(s) para ${newStatus}.` });
      }
      setSelected(new Set());
      onStatusChanged();
    } catch (e: any) {
      setResult({ type: "error", msg: e.message });
    } finally {
      setLoading(false);
    }
  };

  if (generators.length === 0) {
    return (
      <Card><CardContent><Alert severity="info">Nenhum modelo associado.</Alert></CardContent></Card>
    );
  }

  return (
    <Box>
      {result && (
        <Alert severity={result.type === "warning" ? "warning" : result.type} sx={{ mb: 2 }} onClose={() => setResult(null)}>
          {result.msg}
        </Alert>
      )}

      {selected.size > 0 && (
        <Card sx={{ mb: 2 }}>
          <CardContent sx={{ display: "flex", alignItems: "center", gap: 2, py: 1.5, "&:last-child": { pb: 1.5 } }}>
            <Typography variant="body2"><strong>{selected.size}</strong> selecionado(s)</Typography>
            <FormControl size="small" sx={{ minWidth: 130 }}>
              <InputLabel>Status</InputLabel>
              <Select value={newStatus} label="Status" onChange={(e) => setNewStatus(e.target.value)}>
                <MenuItem value="OFFLINE">OFFLINE</MenuItem>
                <MenuItem value="ONLINE">ONLINE</MenuItem>
              </Select>
            </FormControl>
            <Button variant="contained" size="small" onClick={handleChangeStatus} disabled={loading}>
              Aplicar
            </Button>
            {loading && <LinearProgress sx={{ flex: 1 }} />}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent sx={{ p: 0, "&:last-child": { pb: 0 } }}>
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell padding="checkbox" sx={{ width: 40 }}>
                    <Checkbox size="small" checked={selected.size === generators.length && generators.length > 0}
                      indeterminate={selected.size > 0 && selected.size < generators.length}
                      onChange={toggleAll} />
                  </TableCell>
                  <TableCell>Modelo</TableCell>
                  <TableCell>Tipo</TableCell>
                  <TableCell>Generator ID</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {generators.map((g, i) => (
                  <TableRow key={i} hover selected={selected.has(g.id_attribute)}
                    onClick={() => toggleSelect(g.id_attribute)} sx={{ cursor: "pointer" }}>
                    <TableCell padding="checkbox">
                      <Checkbox size="small" checked={selected.has(g.id_attribute)} />
                    </TableCell>
                    <TableCell sx={{ fontSize: 13 }}>{g.value || g.name_attribute}</TableCell>
                    <TableCell>
                      <Chip label={g.specification} size="small" sx={{ height: 20, fontSize: 10 }} />
                    </TableCell>
                    <TableCell sx={{ fontSize: 11, color: "text.secondary" }}>
                      {g.id_attribute?.substring(0, 12)}...
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>
    </Box>
  );
}

// ===================== Ações =====================

function ActionsTab({ itemId, itemName, vessel, onRefresh }: {
  itemId: string; itemName: string; vessel: string; onRefresh: () => void;
}) {
  const [result, setResult] = useState<{ type: "success" | "error"; msg: string } | null>(null);

  const [newName, setNewName] = useState(itemName);
  const [renaming, setRenaming] = useState(false);

  const handleRename = async () => {
    if (!newName || newName === itemName) return;
    setRenaming(true);
    setResult(null);
    const qs = `environment=${encodeURIComponent(localStorage.getItem("lh_environment") || "")}&client_name=${encodeURIComponent(localStorage.getItem("lh_client_name") || "")}`;
    try {
      await api.patch(`/explorer/items/${itemId}/rename?${qs}`, { name: newName });
      setResult({ type: "success", msg: `Renomeado para "${newName}".` });
      onRefresh();
    } catch (e: any) {
      setResult({ type: "error", msg: e.message });
    } finally {
      setRenaming(false);
    }
  };

  const [templates, setTemplates] = useState<Record<string, string>>({});
  const [childName, setChildName] = useState("");
  const [childTemplate, setChildTemplate] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    const env = localStorage.getItem("lh_environment") || "";
    const client = localStorage.getItem("lh_client_name") || "";
    if (env && client) {
      api.get<Record<string, string>>(`/sync/templates/list?environment=${encodeURIComponent(env)}&client_name=${encodeURIComponent(client)}`)
        .then(setTemplates).catch(() => {});
    }
  }, []);

  const handleCreate = async () => {
    if (!childName || !childTemplate) return;
    setCreating(true);
    setResult(null);
    const env = localStorage.getItem("lh_environment") || "";
    const client = localStorage.getItem("lh_client_name") || "";
    try {
      await api.post("/explorer/items", {
        vessel, name: childName, template_id: childTemplate,
        parent_id: itemId, environment: env, client_name: client,
      });
      setResult({ type: "success", msg: `Item "${childName}" criado.` });
      setChildName("");
      setChildTemplate("");
      onRefresh();
    } catch (e: any) {
      setResult({ type: "error", msg: e.message });
    } finally {
      setCreating(false);
    }
  };

  const [confirmDelete, setConfirmDelete] = useState(false);
  const handleDelete = async () => {
    setConfirmDelete(false);
    setResult(null);
    const qs = `environment=${encodeURIComponent(localStorage.getItem("lh_environment") || "")}&client_name=${encodeURIComponent(localStorage.getItem("lh_client_name") || "")}`;
    try {
      await api.delete(`/explorer/items/${itemId}?${qs}`);
      setResult({ type: "success", msg: "Item removido." });
      onRefresh();
    } catch (e: any) {
      setResult({ type: "error", msg: e.message });
    }
  };

  const templateOptions = Object.entries(templates).map(([id, name]) => ({ id, name }));

  return (
    <Box sx={{ maxWidth: 600 }}>
      {result && (
        <Alert severity={result.type} sx={{ mb: 2 }} onClose={() => setResult(null)}>{result.msg}</Alert>
      )}
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="subtitle2" sx={{ mb: 1, display: "flex", alignItems: "center", gap: 1 }}>
            <RenameIcon fontSize="small" /> Renomear item
          </Typography>
          <Box sx={{ display: "flex", gap: 1 }}>
            <TextField size="small" fullWidth value={newName} onChange={(e) => setNewName(e.target.value)} />
            <Button variant="contained" size="small" onClick={handleRename}
              disabled={renaming || !newName || newName === itemName}>Renomear</Button>
          </Box>
        </CardContent>
      </Card>
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="subtitle2" sx={{ mb: 1, display: "flex", alignItems: "center", gap: 1 }}>
            <AddIcon fontSize="small" /> Criar equipamento filho
          </Typography>
          <TextField size="small" fullWidth label="Nome" value={childName}
            onChange={(e) => setChildName(e.target.value)} sx={{ mb: 1.5 }} />
          <FormControl size="small" fullWidth sx={{ mb: 1.5 }}>
            <InputLabel>Template</InputLabel>
            <Select value={childTemplate} label="Template" onChange={(e) => setChildTemplate(e.target.value)}>
              {templateOptions.sort((a, b) => a.name.localeCompare(b.name)).map((t) => (
                <MenuItem key={t.id} value={t.id}>{t.name}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <Button variant="contained" size="small" onClick={handleCreate}
            disabled={creating || !childName || !childTemplate} startIcon={<AddIcon />}>Criar</Button>
        </CardContent>
      </Card>
      <Card sx={{ borderColor: "error.main" }}>
        <CardContent>
          <Typography variant="subtitle2" sx={{ mb: 1, display: "flex", alignItems: "center", gap: 1, color: "error.main" }}>
            <DeleteIcon fontSize="small" /> Remover item
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            Remove <strong>{itemName}</strong> permanentemente da API e do banco local.
          </Typography>
          <Button variant="outlined" color="error" size="small" onClick={() => setConfirmDelete(true)}
            startIcon={<DeleteIcon />}>Remover</Button>
        </CardContent>
      </Card>
      <Dialog open={confirmDelete} onClose={() => setConfirmDelete(false)}>
        <DialogTitle>Confirmar remoção</DialogTitle>
        <DialogContent>
          <Typography>Tem certeza que deseja remover <strong>{itemName}</strong>?</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmDelete(false)}>Cancelar</Button>
          <Button color="error" variant="contained" onClick={handleDelete}>Remover</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
