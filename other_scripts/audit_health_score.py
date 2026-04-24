"""
Auditoria e correção dos atributos de Health Score no workspace.

Verifica:
  - Itens folha (último nível) devem ter Health Score Method = "Complex Average"
  - Itens não-folha (pais) devem ter Health Score Method = "Weighted Average"
  - Todos os itens devem ter todos os atributos/subatributos de HS definidos em default_attributes.json

Correções:
  - Atualiza o valor de Health Score Method nos itens incorretos
  - Cadastra atributos de HS ausentes no template do ativo afetado

Executar bloco a bloco em um ambiente com suporte a #%% (VS Code, Jupyter, Spyder).
"""

# %% BLOCO 1 — Imports e conexão ao workspace
import json
import os
import sys
import pandas as pd
from tqdm import tqdm
from datetime import datetime

# Garante que a raiz do projeto está no path para importar templates.py e default_attributes.json
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from lighthouse import connect
from templates import (
    evaluate_api_response,
    fix_categories_uuid,
)

DEFAULT_ATTRS_PATH = os.path.join(_PROJECT_ROOT, "default_attributes.json")
LOGS_DIR = os.path.join(_PROJECT_ROOT, "logs")

CLIENT = "jirau"
ENVIRONMENT = "prod"  # altere para "dev" se necessário

ws = connect(CLIENT, ENVIRONMENT, False)
print(f"Conectado: {CLIENT} / {ENVIRONMENT}")


# %% BLOCO 2 — Carregar definições de Health Score de default_attributes.json

with open(DEFAULT_ATTRS_PATH, "r", encoding="utf-8") as f:
    all_defaults = json.load(f)

# Atributos HS: aqueles que têm "Health Score" nas categorias
hs_all = [a for a in all_defaults if "Health Score" in a.get("categories", [])]
hs_root = [a for a in hs_all if "parent_id" not in a]
hs_subs = [a for a in hs_all if "parent_id" in a]

hs_root_names = {a["name"] for a in hs_root}
hs_sub_names  = {a["name"] for a in hs_subs}
hs_all_names  = hs_root_names | hs_sub_names

print("Atributos raiz de HS:", sorted(hs_root_names))
print("Sub-atributos de HS:", sorted(hs_sub_names))


# %% BLOCO 3 — Buscar todos os itens e construir hierarquia (folha vs não-folha)
# ws.get_items() devolve {item_id: item_name}.
# ws.get_item(item_id) devolve os detalhes completos, incluindo:
#   - has_children: bool  → false = folha, true = tem filhos
#   - template.id         → template_id do item (usado no bloco 7)

all_items = ws.get_items()  # {item_id: item_name}
print(f"Total de itens: {len(all_items)}")

item_detail_cache = {}

for item_id in tqdm(all_items, desc="Buscando detalhes dos itens"):
    try:
        item_detail_cache[item_id] = ws.get_item(item_id)
    except Exception as e:
        print(f"  AVISO: falha ao buscar item {all_items[item_id]} ({item_id}): {e}")

leaf_ids     = {iid for iid, d in item_detail_cache.items() if not d.get("has_children", False)}
non_leaf_ids = {iid for iid, d in item_detail_cache.items() if d.get("has_children", False)}

print(f"Itens folha (último nível): {len(leaf_ids)}")
print(f"Itens não-folha (pais):     {len(non_leaf_ids)}")


# %% BLOCO 4 — Buscar atributos de Health Score de cada item

records = []

for item_id, item_name in tqdm(all_items.items(), desc="Lendo atributos HS"):
    is_leaf = item_id in leaf_ids
    expected_method = "Complex Average" if is_leaf else "Weighted Average"

    resp = ws.get_item_attributes(item_id)
    item_attrs = resp.get("attributes", []) if resp else []

    found_hs = {}       # name -> attribute dict
    hs_method_attr = None

    for attr in item_attrs:
        name = attr.get("name", "")

        if name in hs_root_names:
            found_hs[name] = attr
            if name == "Health Score Method":
                hs_method_attr = attr

        # Sub-atributos de HS ficam aninhados em "Health Score"
        if name == "Health Score":
            for sub in attr.get("sub_attributes", []):
                sub_name = sub.get("name", "")
                if sub_name in hs_sub_names:
                    found_hs[sub_name] = sub

    actual_method = hs_method_attr.get("value") if hs_method_attr else None
    method_ok = (actual_method == expected_method) if hs_method_attr else False

    records.append({
        "item_id":            item_id,
        "item_name":          item_name,
        "is_leaf":            is_leaf,
        "expected_hs_method": expected_method,
        "actual_hs_method":   actual_method,
        "hs_method_attr_id":  hs_method_attr.get("id") if hs_method_attr else None,
        "hs_method_ok":       method_ok,
        "hs_method_missing":  hs_method_attr is None,
        "hs_attrs_found":     sorted(found_hs.keys()),
        "hs_attrs_missing":   sorted(hs_all_names - found_hs.keys()),
    })

df = pd.DataFrame(records)
print("\nResumo geral:")
print(df.groupby(["is_leaf", "hs_method_ok", "hs_method_missing"]).size().to_string())


# %% BLOCO 5 — Análise: itens com problemas

wrong_method   = df[~df["hs_method_ok"] & ~df["hs_method_missing"]].copy()
missing_method = df[df["hs_method_missing"]].copy()
missing_attrs  = df[df["hs_attrs_missing"].apply(len) > 0].copy()

print(f"Itens com Health Score Method INCORRETO: {len(wrong_method)}")
print(f"Itens SEM o atributo Health Score Method: {len(missing_method)}")
print(f"Itens com atributos de HS ausentes:       {len(missing_attrs)}")

if not wrong_method.empty:
    print("\n--- Health Score Method incorreto ---")
    for _, row in wrong_method.iterrows():
        print(f"  {row['item_name']:50s}  folha={row['is_leaf']}  "
              f"atual='{row['actual_hs_method']}'  esperado='{row['expected_hs_method']}'")

if not missing_method.empty:
    print("\n--- Health Score Method ausente ---")
    for _, row in missing_method.iterrows():
        print(f"  {row['item_name']:50s}  folha={row['is_leaf']}")


# %% BLOCO 6 — Corrigir Health Score Method nos itens com valor errado

fix_results = []

for _, row in tqdm(wrong_method.iterrows(), total=len(wrong_method), desc="Corrigindo HS Method"):
    item_id     = row["item_id"]
    attr_id     = row["hs_method_attr_id"]
    new_value   = row["expected_hs_method"]

    try:
        result  = ws.update_manual_attributes(item_id, [{"id": attr_id, "value": new_value}])
        success = result.status_code in [200, 201, 202]
        fix_results.append({
            "item_name": row["item_name"],
            "is_leaf":   row["is_leaf"],
            "old_value": row["actual_hs_method"],
            "new_value": new_value,
            "success":   success,
            "detail":    "ok" if success else result.text,
        })
    except Exception as e:
        fix_results.append({
            "item_name": row["item_name"],
            "is_leaf":   row["is_leaf"],
            "old_value": row["actual_hs_method"],
            "new_value": new_value,
            "success":   False,
            "detail":    str(e),
        })

fix_df = pd.DataFrame(fix_results) if fix_results else pd.DataFrame()
if not fix_df.empty:
    print(fix_df["success"].value_counts().to_string())
else:
    print("Nenhuma correção necessária.")


# %% BLOCO 7 — Identificar templates com atributos de HS ausentes

all_templates    = ws.get_templates()  # {template_id: template_name}

# Agrupa atributos ausentes por template_id para não cadastrar repetidamente
templates_to_fix = {}  # {template_id: set(missing_attr_names)}

for _, row in missing_attrs.iterrows():
    item_id = row["item_id"]
    detail  = item_detail_cache.get(item_id) or ws.get_item(item_id)
    template_id = detail.get("template", {}).get("id") if detail else None

    if not template_id:
        print(f"AVISO: template_id não encontrado para '{row['item_name']}'")
        continue

    if template_id not in templates_to_fix:
        templates_to_fix[template_id] = set()
    templates_to_fix[template_id].update(row["hs_attrs_missing"])

print(f"Templates que precisam de atributos de HS: {len(templates_to_fix)}")
for tid, missing in sorted(templates_to_fix.items(), key=lambda x: all_templates.get(x[0], x[0])):
    print(f"  {all_templates.get(tid, tid)}: {sorted(missing)}")


# %% BLOCO 8 — Cadastrar atributos de HS ausentes nos templates afetados

hs_default_by_name = {a["name"]: a for a in hs_all}
enroll_results = []

for template_id, missing_names in tqdm(templates_to_fix.items(), desc="Cadastrando nos templates"):
    template_name = all_templates.get(template_id, template_id)

    template_attrs   = ws.get_template_attributes(template_id)["attributes"]
    existing_by_name = {a["name"].lower(): a["id"] for a in template_attrs}

    # Passo 1: atributos raiz ausentes
    for attr_name in sorted(missing_names):
        attr_def = hs_default_by_name.get(attr_name)
        if not attr_def or "parent_id" in attr_def:
            continue  # sub-atributo — tratado no passo 2
        if attr_name.lower() in existing_by_name:
            continue

        data = {
            "name":                attr_def["name"],
            "description":         attr_def.get("description", ""),
            "categories":          list(attr_def.get("categories", [])),
            "type":                attr_def["type"],
            "decimal_places":      str(int(attr_def.get("decimal_places", 1))),
            "unit_of_measurement": attr_def.get("unit_of_measurement", ""),
            "default_value":       attr_def.get("default_value"),
        }
        data = fix_categories_uuid(data, None, ws)
        resp = ws.post_template_attribute(template_id, data)
        ok, detail = evaluate_api_response(resp)

        enroll_results.append({
            "template": template_name,
            "level":    "attribute",
            "name":     attr_name,
            "success":  ok,
            "detail":   detail,
        })
        if ok:
            existing_by_name[attr_name.lower()] = None  # evita duplicata na mesma execução

    # Recarregar atributos do template para pegar IDs dos recém-criados
    template_attrs   = ws.get_template_attributes(template_id)["attributes"]
    attr_name_to_id  = {a["name"]: a["id"] for a in template_attrs}

    # Passo 2: sub-atributos ausentes
    for attr_name in sorted(missing_names):
        attr_def = hs_default_by_name.get(attr_name)
        if not attr_def or "parent_id" not in attr_def:
            continue  # atributo raiz — já tratado

        parent_name = attr_def["parent_id"]
        parent_id   = attr_name_to_id.get(parent_name)

        if not parent_id:
            enroll_results.append({
                "template": template_name,
                "level":    "subattribute",
                "name":     f"{parent_name} | {attr_name}",
                "success":  False,
                "detail":   f"atributo pai '{parent_name}' não encontrado no template",
            })
            continue

        existing_subs_resp = ws.get_template_attribute_subattributes(parent_id)
        existing_subs = {s["name"].lower() for s in existing_subs_resp.get("attributes", [])}
        if attr_name.lower() in existing_subs:
            continue

        cats = list(attr_def.get("categories", []))
        if "Limits" not in cats:
            cats.insert(0, "Limits")

        data = {
            "name":                attr_def["name"],
            "description":         attr_def.get("description", ""),
            "categories":          cats,
            "type":                attr_def["type"],
            "decimal_places":      str(int(attr_def.get("decimal_places", 1))),
            "unit_of_measurement": attr_def.get("unit_of_measurement", ""),
            "default_value":       attr_def.get("default_value"),
            "parent_id":           parent_id,
        }
        data = fix_categories_uuid(data, None, ws)
        resp = ws.post_template_attribute(template_id, data)
        ok, detail = evaluate_api_response(resp)

        enroll_results.append({
            "template": template_name,
            "level":    "subattribute",
            "name":     f"{parent_name} | {attr_name}",
            "success":  ok,
            "detail":   detail,
        })

enroll_df = pd.DataFrame(enroll_results) if enroll_results else pd.DataFrame()
if not enroll_df.empty:
    print(enroll_df.groupby(["level", "success"]).size().to_string())
else:
    print("Nenhum atributo para cadastrar nos templates.")


# %% BLOCO 9 — Salvar relatório final em Excel

os.makedirs(LOGS_DIR, exist_ok=True)
timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
output_path = os.path.join(LOGS_DIR, f"audit_health_score_{CLIENT}_{ENVIRONMENT}_{timestamp}.xlsx")

with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
    df.to_excel(writer, sheet_name="Todos_os_Itens", index=False)

    wrong_method.to_excel(writer, sheet_name="HS_Method_Incorreto", index=False)
    missing_method.to_excel(writer, sheet_name="HS_Method_Ausente", index=False)
    missing_attrs.to_excel(writer, sheet_name="Atributos_HS_Ausentes", index=False)

    if not fix_df.empty:
        fix_df.to_excel(writer, sheet_name="Correcoes_HS_Method", index=False)

    if not enroll_df.empty:
        enroll_df.to_excel(writer, sheet_name="Cadastros_Nos_Templates", index=False)

print(f"\nRelatório salvo em: {output_path}")
