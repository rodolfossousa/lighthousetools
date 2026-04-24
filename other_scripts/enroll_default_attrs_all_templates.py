"""
Verifica todos os templates do workspace e cadastra os atributos/subatributos
padrão (default_attributes.json) que estiverem ausentes.

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
from templates import (
    enroll_default_attributes,
    enroll_default_subattributes,
    evaluate_api_response,
)

CLIENT      = "jirau"
ENVIRONMENT = "prod"  # altere para "dev" se necessário

ws = connect(CLIENT, ENVIRONMENT, False)
print(f"Conectado: {CLIENT} / {ENVIRONMENT}")


# %% BLOCO 2 — Buscar todos os templates e categorias do workspace

all_templates = ws.get_templates()  # {template_id: template_name}
categories    = ws.get_categories()

print(f"Templates encontrados: {len(all_templates)}")
for tid, name in sorted(all_templates.items(), key=lambda x: x[1]):
    print(f"  {name}")


# %% BLOCO 3 — Verificar e cadastrar atributos/subatributos padrão em cada template

results = []

for template_id, template_name in tqdm(all_templates.items(), desc="Processando templates"):
    enroll_default_attributes(ws, template_id, categories, template_name)
    enroll_default_subattributes(ws, template_id, categories, template_name)

print("Concluído.")


# %% BLOCO 4 — Verificação pós-cadastro: conferir se ainda falta algo

from templates import (
    get_default_attributes_and_subattributes,
    check_default_attributes,
    check_default_subattributes_for_template,
)

default_attrs, default_subattrs = get_default_attributes_and_subattributes()
issues = []

for template_id, template_name in tqdm(all_templates.items(), desc="Verificando"):
    template_attrs = ws.get_template_attributes(template_id)["attributes"]

    missing_attrs = check_default_attributes(template_attrs, default_attrs)
    for a in missing_attrs:
        issues.append({"template": template_name, "level": "attribute", "name": a["name"]})

    missing_subs = check_default_subattributes_for_template(ws, template_attrs, default_subattrs)
    for parent_name, subs in missing_subs.items():
        for s in subs:
            issues.append({"template": template_name, "level": "subattribute", "name": f"{parent_name} | {s['name']}"})

if issues:
    issues_df = pd.DataFrame(issues)
    print(f"\n{len(issues)} item(ns) ainda ausente(s) após o cadastro:")
    print(issues_df.to_string(index=False))
else:
    print("\nTodos os atributos padrão estão cadastrados em todos os templates.")


# %% BLOCO 5 — Salvar relatório

LOGS_DIR = os.path.join(_PROJECT_ROOT, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)
timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
output_path = os.path.join(LOGS_DIR, f"default_attrs_audit_{CLIENT}_{ENVIRONMENT}_{timestamp}.xlsx")

issues_df = pd.DataFrame(issues) if issues else pd.DataFrame(columns=["template", "level", "name"])
issues_df.to_excel(output_path, index=False)
print(f"Relatório salvo em: {output_path}")
