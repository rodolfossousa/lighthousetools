"use client";
import { useState, useEffect, useCallback } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Chip,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableRow,
  IconButton,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Tabs,
  Tab,
  LinearProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Tooltip,
} from "@mui/material";
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Save as SaveIcon,
  Cancel as CancelIcon,
  FolderOpen,
  ExpandMore as ExpandMoreIcon,
  Settings as GearIcon,
  AccountTree as TreeIcon,
  DriveFileRenameOutline as RenameIcon,
  CloudUpload as CloudUploadIcon,
} from "@mui/icons-material";
import { SimpleTreeView, TreeItem } from "@mui/x-tree-view";
import AppLayout from "@/components/layout/AppLayout";
import { api } from "@/lib/api";
import type { DDProject, DDItem, DDAttribute, TemplateEntry } from "@/types";

const STATUS_COLORS: Record<string, "warning" | "success" | "error"> = {
  Rascunho: "warning",
  Cadastrado: "success",
  Cancelado: "error",
};

const COLORS = {
  root: "#66BB6A",
  branch: "#42A5F5",
  leaf: "#FFA726",
};

function getItemDepth(item: DDItem, items: DDItem[]): number {
  let depth = 0;
  let current = item;
  while (current.parent_item_id) {
    depth++;
    const parent = items.find((i) => i.id === current.parent_item_id);
    if (!parent) break;
    current = parent;
  }
  return depth;
}

function getItemColor(item: DDItem, items: DDItem[]) {
  const depth = getItemDepth(item, items);
  if (depth === 0) return COLORS.root;
  const hasChildren = items.some((i) => i.parent_item_id === item.id);
  if (hasChildren) return COLORS.branch;
  return COLORS.leaf;
}

function getItemIcon(item: DDItem, items: DDItem[]) {
  const color = getItemColor(item, items);
  const depth = getItemDepth(item, items);
  if (depth === 0) return <FolderOpen sx={{ fontSize: 14, color }} />;
  const hasChildren = items.some((i) => i.parent_item_id === item.id);
  if (hasChildren) return <TreeIcon sx={{ fontSize: 14, color }} />;
  return <GearIcon sx={{ fontSize: 14, color }} />;
}

export default function DictionaryPage() {
  const [projects, setProjects] = useState<DDProject[]>([]);
  const [selectedProject, setSelectedProject] = useState<DDProject | null>(null);
  const [items, setItems] = useState<DDItem[]>([]);
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);
  const [attributes, setAttributes] = useState<DDAttribute[]>([]);
  const [subattributes, setSubattributes] = useState<DDAttribute[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [showNewProject, setShowNewProject] = useState(false);
  const [showNewItem, setShowNewItem] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");
  const [newItemName, setNewItemName] = useState("");
  const [newItemTemplateId, setNewItemTemplateId] = useState("");
  const [newItemParentId, setNewItemParentId] = useState("");
  const [templates, setTemplates] = useState<TemplateEntry[]>([]);
  const [tab, setTab] = useState(0);
  const [editingAttrs, setEditingAttrs] = useState<Record<number, Partial<DDAttribute>>>({});
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveResult, setSaveResult] = useState<{ type: "success" | "error"; msg: string } | null>(null);

  const env = typeof window !== "undefined" ? localStorage.getItem("lh_environment") || "" : "";
  const client = typeof window !== "undefined" ? localStorage.getItem("lh_client_name") || "" : "";

  const fetchProjects = useCallback(async () => {
    const data = await api.get<DDProject[]>("/dictionary/projects");
    setProjects(data);
  }, []);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  useEffect(() => {
    if (env && client) {
      api.get<TemplateEntry[]>(`/templates?environment=${env}&client_name=${client}`).then(setTemplates).catch(() => {});
    }
  }, [env, client]);

  const selectProject = async (project: DDProject) => {
    setSelectedProject(project);
    setSelectedItemId(null);
    setTab(0);
    setSaveResult(null);
    const [itemsData, summaryData] = await Promise.all([
      api.get<DDItem[]>(`/dictionary/projects/${project.id}/items`),
      api.get<any>(`/dictionary/projects/${project.id}/summary`),
    ]);
    setItems(itemsData);
    setSummary(summaryData);
  };

  const selectItem = async (itemId: string) => {
    setSelectedItemId(itemId);
    setEditing(false);
    setEditingAttrs({});
    setSaveResult(null);
    setTab(0);
    const [attrs, subs] = await Promise.all([
      api.get<DDAttribute[]>(`/dictionary/items/${itemId}/attributes`),
      api.get<DDAttribute[]>(`/dictionary/items/${itemId}/subattributes`),
    ]);
    setAttributes(attrs);
    setSubattributes(subs);
  };

  const createProject = async () => {
    await api.post("/dictionary/projects", { name: newProjectName, client, environment: env });
    setShowNewProject(false);
    setNewProjectName("");
    fetchProjects();
  };

  const createItem = async () => {
    if (!selectedProject) return;
    const template = templates.find((t) => t.template_id === newItemTemplateId);
    const res = await api.post<{ id: string }>(`/dictionary/projects/${selectedProject.id}/items`, {
      name: newItemName,
      template_id: newItemTemplateId || null,
      template_name: template?.template_name || null,
      parent_item_id: newItemParentId || null,
    });
    if (newItemTemplateId) {
      await api.post(`/dictionary/items/${res.id}/populate`, {
        template_id: newItemTemplateId,
        environment: env,
        client,
      });
    }
    setShowNewItem(false);
    setNewItemName("");
    setNewItemTemplateId("");
    setNewItemParentId("");
    selectProject(selectedProject);
  };

  const deleteProject = async () => {
    if (!selectedProject) return;
    await api.delete(`/dictionary/projects/${selectedProject.id}`);
    setSelectedProject(null);
    fetchProjects();
  };

  const saveAttributes = async () => {
    setSaving(true);
    setSaveResult(null);
    try {
      const updates = Object.entries(editingAttrs).map(([id, fields]) => ({ id: Number(id), ...fields }));
      if (updates.length === 0) {
        setSaveResult({ type: "error", msg: "Nenhuma alteração detectada." });
        setSaving(false);
        return;
      }
      const result = await api.patch<{ message: string }>("/dictionary/attributes", updates);
      setSaveResult({ type: "success", msg: result.message });
      setEditing(false);
      setEditingAttrs({});
      if (selectedItemId) selectItem(selectedItemId);
    } catch (e: any) {
      setSaveResult({ type: "error", msg: e.message });
    } finally {
      setSaving(false);
    }
  };

  // --- Tree ---
  const rootItems = items.filter((i) => !i.parent_item_id);
  const getChildItems = (parentId: string) => items.filter((i) => i.parent_item_id === parentId);
  const selectedItem = items.find((i) => i.id === selectedItemId);

  const renderItemTree = (item: DDItem) => (
    <TreeItem
      key={item.id}
      itemId={item.id}
      label={
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, py: 0.2 }}>
          {getItemIcon(item, items)}
          <Typography
            variant="body2"
            sx={{
              fontSize: 12,
              color: getItemColor(item, items),
              fontWeight: item.id === selectedItemId ? 700 : 400,
            }}
          >
            {item.name}
          </Typography>
          {item.template_name && (
            <Chip label={item.template_name} size="small"
              sx={{ height: 16, fontSize: 9, ml: 0.5, opacity: 0.7 }} />
          )}
        </Box>
      }
      onClick={() => selectItem(item.id)}
    >
      {getChildItems(item.id).map(renderItemTree)}
    </TreeItem>
  );

  // --- Group attributes by category, attach subattributes ---
  const subsByParent: Record<number, DDAttribute[]> = {};
  for (const s of subattributes) {
    if (s.parent_attribute_id != null) {
      (subsByParent[s.parent_attribute_id] ??= []).push(s);
    }
  }

  const byCategory: Record<string, DDAttribute[]> = {};
  for (const a of attributes) {
    const cat = a.categories || "Sem Categoria";
    (byCategory[cat] ??= []).push(a);
  }

  return (
    <AppLayout>
      <Box sx={{ display: "flex", gap: 2, height: "calc(100vh - 130px)" }}>
        {/* === Sidebar === */}
        <Card sx={{ width: 320, flexShrink: 0, overflow: "auto" }}>
          <CardContent sx={{ p: 1.5 }}>
            {/* Projetos */}
            <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 1 }}>
              <Typography variant="subtitle2" sx={{ fontSize: 13 }}>Projetos</Typography>
              <IconButton size="small" onClick={() => setShowNewProject(true)}>
                <AddIcon sx={{ fontSize: 18 }} />
              </IconButton>
            </Box>

            {projects.map((p) => (
              <Card
                key={p.id}
                variant="outlined"
                sx={{
                  mb: 0.5,
                  cursor: "pointer",
                  borderColor: selectedProject?.id === p.id ? "primary.main" : "divider",
                  bgcolor: selectedProject?.id === p.id ? "rgba(92,157,255,0.06)" : "transparent",
                }}
                onClick={() => selectProject(p)}
              >
                <CardContent sx={{ p: 1, "&:last-child": { pb: 1 } }}>
                  <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <Typography variant="body2" sx={{ fontSize: 12, fontWeight: 500 }}>{p.name}</Typography>
                    <Chip label={p.status} size="small"
                      color={STATUS_COLORS[p.status] || "default"}
                      sx={{ height: 18, fontSize: 9 }} />
                  </Box>
                  <Typography variant="caption" color="text.secondary" sx={{ fontSize: 10 }}>
                    {p.environment} / {p.client}
                  </Typography>
                </CardContent>
              </Card>
            ))}

            {/* Itens do projeto */}
            {selectedProject && (
              <>
                <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mt: 2, mb: 1 }}>
                  <Typography variant="subtitle2" sx={{ fontSize: 13 }}>Itens</Typography>
                  <IconButton size="small" onClick={() => setShowNewItem(true)}>
                    <AddIcon sx={{ fontSize: 18 }} />
                  </IconButton>
                </Box>

                {/* Legenda */}
                <Box sx={{ display: "flex", gap: 0.5, mb: 1, flexWrap: "wrap" }}>
                  <Chip icon={<FolderOpen sx={{ fontSize: 11 }} />} label="Raiz" size="small"
                    sx={{ bgcolor: `${COLORS.root}22`, color: COLORS.root, height: 18, fontSize: 9 }} />
                  <Chip icon={<TreeIcon sx={{ fontSize: 11 }} />} label="Sub" size="small"
                    sx={{ bgcolor: `${COLORS.branch}22`, color: COLORS.branch, height: 18, fontSize: 9 }} />
                  <Chip icon={<GearIcon sx={{ fontSize: 11 }} />} label="Folha" size="small"
                    sx={{ bgcolor: `${COLORS.leaf}22`, color: COLORS.leaf, height: 18, fontSize: 9 }} />
                </Box>

                {rootItems.length > 0 ? (
                  <SimpleTreeView>
                    {rootItems.map(renderItemTree)}
                  </SimpleTreeView>
                ) : (
                  <Typography variant="body2" color="text.secondary" sx={{ fontSize: 12, textAlign: "center", mt: 1 }}>
                    Nenhum item ainda.
                  </Typography>
                )}
              </>
            )}
          </CardContent>
        </Card>

        {/* === Main === */}
        <Box sx={{ flex: 1, overflow: "auto" }}>
          {/* Resumo do projeto (quando nenhum item selecionado) */}
          {selectedProject && !selectedItemId && (
            <>
              <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
                <Box>
                  <Typography variant="h6">{selectedProject.name}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {selectedProject.environment} / {selectedProject.client} · {selectedProject.created_at}
                  </Typography>
                </Box>
                <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
                  <Chip label={selectedProject.status} color={STATUS_COLORS[selectedProject.status] || "default"} />
                  <Tooltip title="Remover projeto">
                    <IconButton color="error" size="small" onClick={deleteProject}>
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </Box>
              </Box>

              {summary && (
                <Box sx={{ display: "flex", gap: 1.5, mb: 3, flexWrap: "wrap" }}>
                  {[
                    { label: "Equipamentos", value: summary.items, color: "#66BB6A" },
                    { label: "Com template", value: summary.items_with_template, color: "#42A5F5" },
                    { label: "Atributos", value: summary.attributes, color: "#FFA726" },
                    { label: "Com referência", value: summary.attributes_with_reference, color: "#AB47BC" },
                    { label: "Subatributos", value: summary.subattributes, color: "#EF5350" },
                  ].map((s) => (
                    <Card key={s.label} sx={{ flex: 1, minWidth: 120 }}>
                      <CardContent sx={{ textAlign: "center", py: 1.5, "&:last-child": { pb: 1.5 } }}>
                        <Typography variant="h5" sx={{ color: s.color, fontWeight: 600 }}>{s.value}</Typography>
                        <Typography variant="caption" color="text.secondary" sx={{ fontSize: 10 }}>{s.label}</Typography>
                      </CardContent>
                    </Card>
                  ))}
                </Box>
              )}

              {/* Cadastrar no Workspace */}
              <EnrollSection
                project={selectedProject}
                summary={summary}
                onProjectUpdated={() => {
                  fetchProjects();
                  selectProject({ ...selectedProject });
                }}
              />

              <Typography variant="body2" color="text.secondary" sx={{ textAlign: "center", mt: 3 }}>
                Seleciona um item na árvore para ver os atributos.
              </Typography>
            </>
          )}

          {/* Detalhe do item */}
          {selectedItem && (
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
                <Tab label="Ações" />
              </Tabs>

              {/* === TAB: Atributos === */}
              {tab === 0 && (
                <Box>
                  {saving && <LinearProgress sx={{ mb: 1 }} />}

                  {/* Barra de edição */}
                  <Box sx={{ display: "flex", justifyContent: "flex-end", gap: 1, mb: 1 }}>
                    {!editing ? (
                      <Button size="small" startIcon={<EditIcon />} onClick={() => setEditing(true)}>
                        Editar
                      </Button>
                    ) : (
                      <>
                        <Button size="small" startIcon={<CancelIcon />} color="inherit"
                          onClick={() => { setEditing(false); setEditingAttrs({}); }}>
                          Cancelar
                        </Button>
                        <Button size="small" variant="contained" startIcon={<SaveIcon />}
                          onClick={saveAttributes} disabled={saving}>
                          Guardar ({Object.keys(editingAttrs).length})
                        </Button>
                      </>
                    )}
                  </Box>

                  {/* Categorias como Accordions */}
                  {Object.entries(byCategory).sort(([a], [b]) => a.localeCompare(b)).map(([cat, attrs]) => {
                    const nSubs = attrs.reduce((sum, a) => sum + (subsByParent[a.id]?.length || 0), 0);
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
                            const subs = subsByParent[attr.id] || [];
                            return (
                              <Accordion key={attr.id} disableGutters elevation={0}
                                sx={{ ml: 2, "&:before": { display: "none" }, bgcolor: "transparent" }}>
                                <AccordionSummary
                                  expandIcon={subs.length > 0 ? <ExpandMoreIcon sx={{ fontSize: 16 }} /> : <Box sx={{ width: 16 }} />}
                                  sx={{ minHeight: 36, px: 1 }}
                                >
                                  <Box sx={{ display: "flex", alignItems: "center", gap: 1, width: "100%", overflow: "hidden" }}>
                                    <Typography variant="body2" sx={{ fontWeight: 500, minWidth: 160, fontSize: 13 }}>
                                      {attr.name}
                                    </Typography>

                                    {/* Referência / Tag */}
                                    <Box sx={{ flex: 1 }}>
                                      {editing ? (
                                        <TextField
                                          size="small"
                                          variant="standard"
                                          placeholder="Referência"
                                          value={editingAttrs[attr.id]?.reference ?? attr.reference ?? ""}
                                          onChange={(e) => {
                                            e.stopPropagation();
                                            setEditingAttrs((prev) => ({
                                              ...prev,
                                              [attr.id]: { ...prev[attr.id], reference: e.target.value },
                                            }));
                                          }}
                                          onClick={(e) => e.stopPropagation()}
                                          sx={{ width: "100%", "& input": { fontSize: 12 } }}
                                        />
                                      ) : (
                                        <Typography variant="body2" sx={{ fontSize: 12, color: attr.reference ? "text.primary" : "text.disabled" }}>
                                          {attr.reference || "—"}
                                        </Typography>
                                      )}
                                    </Box>

                                    {/* Valor */}
                                    <Box sx={{ flex: 1 }}>
                                      {editing ? (
                                        <TextField
                                          size="small"
                                          variant="standard"
                                          placeholder="Valor"
                                          value={editingAttrs[attr.id]?.value ?? attr.value ?? ""}
                                          onChange={(e) => {
                                            e.stopPropagation();
                                            setEditingAttrs((prev) => ({
                                              ...prev,
                                              [attr.id]: { ...prev[attr.id], value: e.target.value },
                                            }));
                                          }}
                                          onClick={(e) => e.stopPropagation()}
                                          sx={{ width: "100%", "& input": { fontSize: 12 } }}
                                        />
                                      ) : (
                                        <Typography variant="body2" sx={{ fontSize: 12, color: attr.value ? "text.primary" : "text.disabled" }}>
                                          {attr.value || "—"}
                                        </Typography>
                                      )}
                                    </Box>

                                    <Chip label={`${attr.data_source} ${attr.data_type}`} size="small"
                                      sx={{ height: 18, fontSize: 9, flexShrink: 0 }} />
                                    {attr.unit_of_measurement && (
                                      <Tooltip title="Unidade">
                                        <Chip label={attr.unit_of_measurement} size="small" variant="outlined"
                                          sx={{ height: 18, fontSize: 9, flexShrink: 0 }} />
                                      </Tooltip>
                                    )}
                                    {subs.length > 0 && (
                                      <Chip label={`${subs.length}`} size="small" color="warning"
                                        sx={{ height: 16, fontSize: 9, minWidth: 20, flexShrink: 0 }} />
                                    )}
                                  </Box>
                                </AccordionSummary>
                                {subs.length > 0 && (
                                  <AccordionDetails sx={{ py: 0, pl: 3, pr: 1 }}>
                                    <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: "block" }}>
                                      Limiares / Subatributos
                                    </Typography>
                                    <TableContainer>
                                      <Table size="small">
                                        <TableBody>
                                          {subs.map((sub) => (
                                            <TableRow key={sub.id} sx={{ "&:last-child td": { borderBottom: 0 } }}>
                                              <TableCell sx={{ fontSize: 12, py: 0.5, pl: 0, width: "30%" }}>
                                                ↳ {sub.name}
                                              </TableCell>
                                              <TableCell sx={{ fontSize: 12, py: 0.5, width: "25%" }}>
                                                {editing ? (
                                                  <TextField
                                                    size="small"
                                                    variant="standard"
                                                    placeholder="Referência"
                                                    value={editingAttrs[sub.id]?.reference ?? sub.reference ?? ""}
                                                    onChange={(e) =>
                                                      setEditingAttrs((prev) => ({
                                                        ...prev,
                                                        [sub.id]: { ...prev[sub.id], reference: e.target.value },
                                                      }))
                                                    }
                                                    sx={{ width: "100%", "& input": { fontSize: 12 } }}
                                                  />
                                                ) : (
                                                  <span style={{ color: sub.reference ? undefined : "#666" }}>
                                                    {sub.reference || "—"}
                                                  </span>
                                                )}
                                              </TableCell>
                                              <TableCell sx={{ fontSize: 12, py: 0.5, width: "25%" }}>
                                                {editing ? (
                                                  <TextField
                                                    size="small"
                                                    variant="standard"
                                                    placeholder="Valor"
                                                    value={editingAttrs[sub.id]?.value ?? sub.value ?? ""}
                                                    onChange={(e) =>
                                                      setEditingAttrs((prev) => ({
                                                        ...prev,
                                                        [sub.id]: { ...prev[sub.id], value: e.target.value },
                                                      }))
                                                    }
                                                    sx={{ width: "100%", "& input": { fontSize: 12 } }}
                                                  />
                                                ) : (
                                                  <span style={{ color: sub.value ? undefined : "#666" }}>
                                                    {sub.value || "—"}
                                                  </span>
                                                )}
                                              </TableCell>
                                              <TableCell sx={{ fontSize: 9, py: 0.5, color: "text.secondary", width: "20%" }}>
                                                {sub.data_source} {sub.data_type}
                                                {sub.unit_of_measurement ? ` · ${sub.unit_of_measurement}` : ""}
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

                  {attributes.length === 0 && (
                    <Alert severity="info" sx={{ mt: 1 }}>Nenhum atributo para este item.</Alert>
                  )}
                </Box>
              )}

              {/* === TAB: Ações === */}
              {tab === 1 && (
                <DictionaryActionsTab
                  itemId={selectedItemId!}
                  itemName={selectedItem.name}
                  items={items}
                  templates={templates}
                  projectId={selectedProject!.id}
                  onRefresh={() => {
                    selectProject(selectedProject!);
                  }}
                />
              )}
            </>
          )}

          {!selectedProject && (
            <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%" }}>
              <Typography color="text.secondary">Seleciona ou cria um projeto para começar.</Typography>
            </Box>
          )}
        </Box>
      </Box>

      {/* Dialog: Novo projeto */}
      <Dialog open={showNewProject} onClose={() => setShowNewProject(false)}>
        <DialogTitle>Novo Projeto</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth label="Nome do projeto" value={newProjectName}
            onChange={(e) => setNewProjectName(e.target.value)}
            sx={{ mt: 1 }} autoFocus
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowNewProject(false)}>Cancelar</Button>
          <Button variant="contained" onClick={createProject} disabled={!newProjectName}>Criar</Button>
        </DialogActions>
      </Dialog>

      {/* Dialog: Novo item */}
      <Dialog open={showNewItem} onClose={() => setShowNewItem(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Novo Item</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth label="Nome" value={newItemName}
            onChange={(e) => setNewItemName(e.target.value)}
            sx={{ mt: 1, mb: 2 }} autoFocus
          />
          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel>Template (opcional)</InputLabel>
            <Select value={newItemTemplateId} label="Template (opcional)"
              onChange={(e) => setNewItemTemplateId(e.target.value)}>
              <MenuItem value="">Nenhum</MenuItem>
              {templates.sort((a, b) => a.template_name.localeCompare(b.template_name)).map((t) => (
                <MenuItem key={t.template_id} value={t.template_id}>{t.template_name}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl fullWidth>
            <InputLabel>Item pai (opcional)</InputLabel>
            <Select value={newItemParentId} label="Item pai (opcional)"
              onChange={(e) => setNewItemParentId(e.target.value)}>
              <MenuItem value="">Raiz</MenuItem>
              {items.map((i) => (
                <MenuItem key={i.id} value={i.id}>{i.name}</MenuItem>
              ))}
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowNewItem(false)}>Cancelar</Button>
          <Button variant="contained" onClick={createItem} disabled={!newItemName}>Criar</Button>
        </DialogActions>
      </Dialog>
    </AppLayout>
  );
}

// ===================== Ações =====================

function DictionaryActionsTab({ itemId, itemName, items, templates, projectId, onRefresh }: {
  itemId: string; itemName: string; items: DDItem[]; templates: TemplateEntry[];
  projectId: string; onRefresh: () => void;
}) {
  const [result, setResult] = useState<{ type: "success" | "error"; msg: string } | null>(null);

  // --- Renomear ---
  const [newName, setNewName] = useState(itemName);
  const [renaming, setRenaming] = useState(false);

  const handleRename = async () => {
    if (!newName || newName === itemName) return;
    setRenaming(true);
    setResult(null);
    try {
      await api.patch(`/dictionary/items/${itemId}/rename`, { name: newName });
      setResult({ type: "success", msg: `Renomeado para "${newName}".` });
      onRefresh();
    } catch (e: any) {
      setResult({ type: "error", msg: e.message });
    } finally {
      setRenaming(false);
    }
  };

  // --- Criar filho ---
  const [childName, setChildName] = useState("");
  const [childTemplate, setChildTemplate] = useState("");
  const [creating, setCreating] = useState(false);

  const env = typeof window !== "undefined" ? localStorage.getItem("lh_environment") || "" : "";
  const client = typeof window !== "undefined" ? localStorage.getItem("lh_client_name") || "" : "";

  const handleCreate = async () => {
    if (!childName) return;
    setCreating(true);
    setResult(null);
    try {
      const template = templates.find((t) => t.template_id === childTemplate);
      const res = await api.post<{ id: string }>(`/dictionary/projects/${projectId}/items`, {
        name: childName,
        template_id: childTemplate || null,
        template_name: template?.template_name || null,
        parent_item_id: itemId,
      });
      if (childTemplate) {
        await api.post(`/dictionary/items/${res.id}/populate`, {
          template_id: childTemplate,
          environment: env,
          client,
        });
      }
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

  // --- Apagar ---
  const [confirmDelete, setConfirmDelete] = useState(false);
  const handleDelete = async () => {
    setConfirmDelete(false);
    setResult(null);
    try {
      await api.delete(`/dictionary/items/${itemId}`);
      setResult({ type: "success", msg: "Item removido." });
      onRefresh();
    } catch (e: any) {
      setResult({ type: "error", msg: e.message });
    }
  };

  return (
    <Box sx={{ maxWidth: 600 }}>
      {result && (
        <Alert severity={result.type} sx={{ mb: 2 }} onClose={() => setResult(null)}>
          {result.msg}
        </Alert>
      )}

      {/* Renomear */}
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="subtitle2" sx={{ mb: 1, display: "flex", alignItems: "center", gap: 1 }}>
            <RenameIcon fontSize="small" /> Renomear item
          </Typography>
          <Box sx={{ display: "flex", gap: 1 }}>
            <TextField size="small" fullWidth value={newName} onChange={(e) => setNewName(e.target.value)} />
            <Button variant="contained" size="small" onClick={handleRename}
              disabled={renaming || !newName || newName === itemName}>
              Renomear
            </Button>
          </Box>
        </CardContent>
      </Card>

      {/* Criar filho */}
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="subtitle2" sx={{ mb: 1, display: "flex", alignItems: "center", gap: 1 }}>
            <AddIcon fontSize="small" /> Criar item filho
          </Typography>
          <TextField size="small" fullWidth label="Nome" value={childName}
            onChange={(e) => setChildName(e.target.value)} sx={{ mb: 1.5 }} />
          <FormControl size="small" fullWidth sx={{ mb: 1.5 }}>
            <InputLabel>Template (opcional)</InputLabel>
            <Select value={childTemplate} label="Template (opcional)"
              onChange={(e) => setChildTemplate(e.target.value)}>
              <MenuItem value="">Nenhum</MenuItem>
              {templates.sort((a, b) => a.template_name.localeCompare(b.template_name)).map((t) => (
                <MenuItem key={t.template_id} value={t.template_id}>{t.template_name}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <Button variant="contained" size="small" onClick={handleCreate}
            disabled={creating || !childName} startIcon={<AddIcon />}>
            Criar
          </Button>
        </CardContent>
      </Card>

      {/* Apagar */}
      <Card sx={{ borderColor: "error.main" }}>
        <CardContent>
          <Typography variant="subtitle2" sx={{ mb: 1, display: "flex", alignItems: "center", gap: 1, color: "error.main" }}>
            <DeleteIcon fontSize="small" /> Remover item
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            Remove <strong>{itemName}</strong> permanentemente do projeto.
          </Typography>
          <Button variant="outlined" color="error" size="small" onClick={() => setConfirmDelete(true)}
            startIcon={<DeleteIcon />}>
            Remover
          </Button>
        </CardContent>
      </Card>

      <Dialog open={confirmDelete} onClose={() => setConfirmDelete(false)}>
        <DialogTitle>Confirmar remoção</DialogTitle>
        <DialogContent>
          <Typography>Tem certeza que deseja remover <strong>{itemName}</strong>? Esta ação não pode ser desfeita.</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmDelete(false)}>Cancelar</Button>
          <Button color="error" variant="contained" onClick={handleDelete}>Remover</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

// ===================== Cadastrar no Workspace =====================

function EnrollSection({ project, summary, onProjectUpdated }: {
  project: DDProject; summary: any; onProjectUpdated: () => void;
}) {
  const [wsParentId, setWsParentId] = useState(project.ws_parent_id || "");
  const [savingParent, setSavingParent] = useState(false);
  const [enrolling, setEnrolling] = useState(false);
  const [progress, setProgress] = useState<string | null>(null);
  const [result, setResult] = useState<{ type: "success" | "error" | "warning"; msg: string } | null>(null);

  const env = typeof window !== "undefined" ? localStorage.getItem("lh_environment") || "" : "";
  const client = typeof window !== "undefined" ? localStorage.getItem("lh_client_name") || "" : "";

  const handleSaveParent = async () => {
    if (!wsParentId.trim()) return;
    setSavingParent(true);
    try {
      await api.patch(`/dictionary/projects/${project.id}/ws-parent`, { ws_parent_id: wsParentId.trim() });
      onProjectUpdated();
    } catch (e: any) {
      setResult({ type: "error", msg: e.message });
    } finally {
      setSavingParent(false);
    }
  };

  const handleEnroll = async () => {
    setEnrolling(true);
    setResult(null);
    setProgress("Cadastrando no Workspace...");
    try {
      const res = await api.post<{
        message: string; created: number; updated: number; errors: string[];
      }>(`/dictionary/projects/${project.id}/enroll`, { environment: env, client_name: client });

      if (res.errors && res.errors.length > 0) {
        setResult({
          type: "warning",
          msg: `${res.message}\n\nErros:\n${res.errors.map((e) => `• ${e}`).join("\n")}`,
        });
      } else {
        setResult({ type: "success", msg: res.message });
      }
      onProjectUpdated();
    } catch (e: any) {
      setResult({ type: "error", msg: e.message });
    } finally {
      setEnrolling(false);
      setProgress(null);
    }
  };

  const hasWsParent = !!project.ws_parent_id;
  const hasItemsWithTemplate = summary && summary.items_with_template > 0;
  const isAlreadyCadastrado = project.status === "Cadastrado";

  return (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        <Typography variant="subtitle2" sx={{ mb: 1.5, display: "flex", alignItems: "center", gap: 1 }}>
          <CloudUploadIcon fontSize="small" color="primary" />
          Cadastrar no Workspace
        </Typography>

        {/* Definir ws_parent_id */}
        {!hasWsParent && (
          <>
            <Alert severity="warning" sx={{ mb: 1.5, fontSize: 12 }}>
              ID do item pai no Workspace não definido. Informe o ID do item existente no Lighthouse onde os equipamentos serão cadastrados como filhos.
            </Alert>
            <Box sx={{ display: "flex", gap: 1 }}>
              <TextField
                size="small" fullWidth label="ID do item pai no Workspace"
                value={wsParentId} onChange={(e) => setWsParentId(e.target.value)}
              />
              <Button variant="contained" size="small" onClick={handleSaveParent}
                disabled={savingParent || !wsParentId.trim()}>
                Guardar
              </Button>
            </Box>
          </>
        )}

        {/* Pronto para cadastrar */}
        {hasWsParent && (
          <>
            <Box sx={{ display: "flex", gap: 1, alignItems: "center", mb: 1.5, flexWrap: "wrap" }}>
              <Chip label={`Parent: ${project.ws_parent_id?.substring(0, 12)}...`} size="small"
                sx={{ height: 22, fontSize: 10 }} />
              {isAlreadyCadastrado && (
                <Chip label="Já cadastrado" size="small" color="success" sx={{ height: 22, fontSize: 10 }} />
              )}
            </Box>

            {!hasItemsWithTemplate && (
              <Alert severity="warning" sx={{ fontSize: 12 }}>
                Nenhum item com template definido. Adiciona itens com template antes de cadastrar.
              </Alert>
            )}

            {hasItemsWithTemplate && summary && summary.attributes > 0 && summary.attributes_with_reference === 0 && (
              <Alert severity="info" sx={{ mb: 1.5, fontSize: 12 }}>
                Nenhum atributo TimeSeries possui tag preenchida. Os atributos podem ser atualizados depois.
              </Alert>
            )}

            {hasItemsWithTemplate && (
              <>
                {enrolling && <LinearProgress sx={{ mb: 1 }} />}
                {progress && (
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1, fontSize: 12 }}>
                    {progress}
                  </Typography>
                )}
                <Button
                  variant="contained" startIcon={<CloudUploadIcon />}
                  onClick={handleEnroll} disabled={enrolling}
                >
                  {isAlreadyCadastrado ? "Atualizar no Workspace" : "Cadastrar no Workspace"}
                </Button>
              </>
            )}
          </>
        )}

        {result && (
          <Alert severity={result.type === "warning" ? "warning" : result.type} sx={{ mt: 1.5, whiteSpace: "pre-line" }}
            onClose={() => setResult(null)}>
            {result.msg}
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}
