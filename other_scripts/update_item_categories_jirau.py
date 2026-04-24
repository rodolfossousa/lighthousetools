"""
Atualiza as categorias dos itens da Jirau com base no template:
  - Template "Motoventilador"  → adiciona categoria "Motoventiladores"
  - Template "Gerador"         → adiciona categoria "Unidades Geradoras"

A categoria é adicionada às existentes — categorias já presentes não são removidas.
Executar bloco a bloco em um ambiente com suporte a #%% (VS Code, Jupyter, Spyder).
"""

# %% BLOCO 1 — Imports e conexão ao workspace
import os
import sys
import pandas as pd
from tqdm import tqdm
from datetime import datetime

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from lighthouse import connect
from templates import find_category_id_by_name, find_attributes_group_id

CLIENT      = "jirau"
ENVIRONMENT = "prod"  # altere para "dev" se necessário

ws = connect(CLIENT, ENVIRONMENT, False)
print(f"Conectado: {CLIENT} / {ENVIRONMENT}")


# %% BLOCO 2 — Definir mapeamento template → categoria e garantir que as categorias existem

TEMPLATE_CATEGORY_MAP = {
    "Motoventilador": "Motoventiladores",
    "Gerador":        "Unidades Geradoras",
}

# Encontra ou cria cada categoria necessária, retornando {category_name: category_id}
category_ids = {}

for category_name in TEMPLATE_CATEGORY_MAP.values():
    cat_id = find_category_id_by_name(ws, category_name)
    if not cat_id:
        print(f"Categoria '{category_name}' não encontrada — criando...")
        ws.post_category({"name": category_name, "group_id": find_attributes_group_id(ws)})
        cat_id = find_category_id_by_name(ws, category_name)
    category_ids[category_name] = cat_id
    print(f"  '{category_name}': {cat_id}")


# %% BLOCO 3 — Buscar itens filtrados por template

items_by_template = {}

for template_name in TEMPLATE_CATEGORY_MAP:
    items = ws.get_template_items(template_name=template_name)  # {item_id: item_name}
    items_by_template[template_name] = items
    print(f"Template '{template_name}': {len(items)} item(ns)")


# %% BLOCO 4 — Atualizar categorias de cada item

results = []

for template_name, items in items_by_template.items():
    target_category_name = TEMPLATE_CATEGORY_MAP[template_name]
    target_category_id   = category_ids[target_category_name]

    for item_id, item_name in tqdm(items.items(), desc=f"Atualizando '{template_name}'"):
        # Verifica se o item já tem a categoria para evitar chamada desnecessária
        existing = ws.get_item_categories(item_id) or {}
        already_has = any(c.get("id") == target_category_id for c in existing.get("categories", []))

        if already_has:
            results.append({
                "item_name": item_name,
                "template":  template_name,
                "category":  target_category_name,
                "status":    "skipped",
                "detail":    "already_has_category",
            })
            continue

        try:
            # POST adiciona sem remover categorias existentes
            resp    = ws.add_item_categories(item_id, [target_category_id])
            success = resp.status_code in [200, 201, 202, 204]
            results.append({
                "item_name": item_name,
                "template":  template_name,
                "category":  target_category_name,
                "status":    "updated" if success else "failed",
                "detail":    "ok" if success else resp.text,
            })
        except Exception as e:
            results.append({
                "item_name": item_name,
                "template":  template_name,
                "category":  target_category_name,
                "status":    "failed",
                "detail":    str(e),
            })

df = pd.DataFrame(results)
print(df["status"].value_counts().to_string())


# %% BLOCO 5 — Salvar relatório

LOGS_DIR = os.path.join(_PROJECT_ROOT, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)
timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
output_path = os.path.join(LOGS_DIR, f"update_item_categories_{CLIENT}_{ENVIRONMENT}_{timestamp}.xlsx")

df.to_excel(output_path, index=False)
print(f"Relatório salvo em: {output_path}")
