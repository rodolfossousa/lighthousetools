export interface User {
  id: number;
  username: string;
  name: string;
  is_admin: boolean;
}

export interface Environment {
  environment: string;
  client_name: string;
}

export interface Vessel {
  name: string;
}

export interface ItemNode {
  id: string;
  name: string;
  template_name: string;
  parent_id: string | null;
  has_children: boolean;
  depth: number;
}

export interface ItemAttribute {
  id_attribute: string;
  name_attribute: string;
  value: string;
  specification: string;
  reference: string;
  category: string;
  unit_of_measurement: string;
  decimal_places: string;
  description: string;
}

export interface SubAttribute {
  id_attribute: string;
  name_attribute: string;
  value: string;
  specification: string;
  parent_attribute_id: string;
  category: string;
  parent_name: string;
  parent_reference: string;
  unit_of_measurement: string;
  decimal_places: string;
  description: string;
}

export interface Generator {
  vessel: string;
  id: string;
  name: string;
  id_attribute: string;
  name_attribute: string;
  value: string;
  specification: string;
}

export interface SyncHistoryEntry {
  sync_type: string;
  environment: string;
  client: string;
  vessel: string | null;
  last_updated: string;
}

export interface DDProject {
  id: string;
  name: string;
  client: string;
  environment: string;
  status: string;
  ws_parent_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface DDItem {
  id: string;
  project_id: string;
  name: string;
  template_id: string | null;
  template_name: string | null;
  parent_item_id: string | null;
  ws_item_id: string | null;
  sort_order: number;
  created_at: string;
}

export interface DDAttribute {
  id: number;
  item_id: string;
  template_attribute_id: string | null;
  name: string;
  data_source: string;
  data_type: string;
  reference: string;
  value: string;
  unit_of_measurement: string;
  decimal_places: number;
  categories: string;
  parent_attribute_id: number | null;
  sort_order: number;
  parent_name?: string;
}

export interface TemplateEntry {
  template_id: string;
  template_name: string;
}

export interface TemplateAttribute {
  id: string;
  name: string;
  description: string;
  data_source: string;
  data_type: string;
  unit_of_measurement: string;
  default_value: string;
  categories: string;
  parent_id: string;
}
