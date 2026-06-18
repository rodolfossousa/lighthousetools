"use client";
import { useState, useEffect } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Alert,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from "@mui/material";
import { SimpleTreeView, TreeItem } from "@mui/x-tree-view";
import AppLayout from "@/components/layout/AppLayout";
import { api } from "@/lib/api";
import type { TemplateEntry, TemplateAttribute } from "@/types";

export default function LibraryPage() {
  const [templates, setTemplates] = useState<TemplateEntry[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateEntry | null>(null);
  const [attrs, setAttrs] = useState<TemplateAttribute[]>([]);

  const env = typeof window !== "undefined" ? localStorage.getItem("lh_environment") || "" : "";
  const client = typeof window !== "undefined" ? localStorage.getItem("lh_client_name") || "" : "";

  useEffect(() => {
    if (env && client) {
      api
        .get<TemplateEntry[]>(`/library/templates?environment=${env}&client_name=${client}`)
        .then(setTemplates)
        .catch(() => {});
    }
  }, [env, client]);

  const handleSelectTemplate = async (tpl: TemplateEntry) => {
    setSelectedTemplate(tpl);
    const data = await api.get<TemplateAttribute[]>(
      `/library/templates/${tpl.template_id}/tree?environment=${env}&client_name=${client}`
    );
    setAttrs(data);
  };

  const rootAttrs = attrs.filter((a) => !a.parent_id);
  const getChildren = (parentId: string) => attrs.filter((a) => a.parent_id === parentId);

  return (
    <AppLayout>
      <Box sx={{ display: "flex", gap: 3, height: "calc(100vh - 130px)" }}>
        {/* Lista de templates */}
        <Card sx={{ width: 300, flexShrink: 0, overflow: "auto" }}>
          <CardContent>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              Templates ({templates.length})
            </Typography>
            {templates.length === 0 ? (
              <Alert severity="info" variant="outlined">
                Nenhum template sincronizado.
              </Alert>
            ) : (
              <SimpleTreeView>
                {templates.map((tpl) => (
                  <TreeItem
                    key={tpl.template_id}
                    itemId={tpl.template_id}
                    label={tpl.template_name}
                    onClick={() => handleSelectTemplate(tpl)}
                  />
                ))}
              </SimpleTreeView>
            )}
          </CardContent>
        </Card>

        {/* Detalhes */}
        <Box sx={{ flex: 1, overflow: "auto" }}>
          {selectedTemplate ? (
            <>
              <Typography variant="h6" sx={{ mb: 0.5 }}>{selectedTemplate.template_name}</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                {rootAttrs.length} atributos · {attrs.length - rootAttrs.length} subatributos
              </Typography>

              <Card>
                <CardContent>
                  <SimpleTreeView>
                    {rootAttrs.map((attr) => (
                      <TreeItem
                        key={attr.id}
                        itemId={attr.id}
                        label={
                          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                            <Typography variant="body2">{attr.name}</Typography>
                            <Chip
                              label={`${attr.data_source} ${attr.data_type}`}
                              size="small"
                              sx={{ height: 18, fontSize: 10 }}
                            />
                            {attr.unit_of_measurement && (
                              <Chip
                                label={attr.unit_of_measurement}
                                size="small"
                                variant="outlined"
                                sx={{ height: 18, fontSize: 10 }}
                              />
                            )}
                          </Box>
                        }
                      >
                        {getChildren(attr.id).map((sub) => (
                          <TreeItem
                            key={sub.id}
                            itemId={sub.id}
                            label={
                              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                                <Typography variant="body2">{sub.name}</Typography>
                                <Chip
                                  label={`${sub.data_source} ${sub.data_type}`}
                                  size="small"
                                  sx={{ height: 18, fontSize: 10 }}
                                />
                              </Box>
                            }
                          />
                        ))}
                      </TreeItem>
                    ))}
                  </SimpleTreeView>
                </CardContent>
              </Card>
            </>
          ) : (
            <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%" }}>
              <Typography color="text.secondary">Seleciona um template para ver os atributos.</Typography>
            </Box>
          )}
        </Box>
      </Box>
    </AppLayout>
  );
}
