"""
Cria um template no ambiente Prod de PRIO a partir de uma planilha Excel.

Uso:
    python criar_template_prio.py
"""
import sys
import tkinter as tk
from tkinter import filedialog

import pandas as pd

from Lighthouse.lighthouse import connect


ENVIRONMENT = "prod"
CLIENT_NAME = "prio"

TYPE_TO_SOURCE = {
    "manual text":          ("Manual", "String"),
    "manual string":        ("Manual", "String"),
    "manual float":         ("Manual", "Float"),
    "manual integer":       ("Manual", "Int"),
    "manual int":           ("Manual", "Int"),
    "manual boolean":       ("Manual", "Boolean"),
    "timeseries float":     ("TimeSeries", "Float"),
    "timeseries integer":   ("TimeSeries", "Int"),
    "timeseries int":       ("TimeSeries", "Int"),
    "timeseries text":      ("TimeSeries", "String"),
    "timeseries string":    ("TimeSeries", "String"),
    "timeseries_float":     ("TimeSeries", "Float"),
    "timeseries_integer":   ("TimeSeries", "Int"),
    "timeseries_text":      ("TimeSeries", "String"),
    "time series float":    ("TimeSeries", "Float"),
    "time series integer":  ("TimeSeries", "Int"),
    "time series text":     ("TimeSeries", "String"),
    "time series":          ("TimeSeries", "Float"),
    "relational text":      ("Relational", "String"),
    "relational_text":      ("Relational", "String"),
}

SOURCE_TO_TYPE = {
    ("Manual", "String"):    "Manual Text",
    ("Manual", "Float"):     "Manual Float",
    ("Manual", "Int"):       "Manual Integer",
    ("Manual", "Boolean"):   "Manual Boolean",
    ("TimeSeries", "Float"): "Time Series Float",
    ("TimeSeries", "Int"):   "Time Series Integer",
    ("TimeSeries", "String"): "Time Series Text",
    ("Relational", "String"): "Relational Text",
}


def _clean(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    s = str(val).strip()
    return "" if s.lower() == "nan" else s


def main():
    template_name = input("Nome do template: ").strip()
    if not template_name:
        print("Nome não pode ser vazio.")
        return
    description = input("Descrição (Enter para vazio): ").strip()

    root = tk.Tk()
    root.withdraw()
    filepath = filedialog.askopenfilename(
        title="Selecione a planilha de atributos",
        filetypes=[("Excel", "*.xlsx *.xls")],
    )
    root.destroy()

    if not filepath:
        print("Nenhum ficheiro selecionado.")
        return

    print(f"\nLendo planilha: {filepath}")
    df = pd.read_excel(filepath, engine="openpyxl")
    df.columns = df.columns.str.strip().str.lower()

    if "name" not in df.columns:
        print("ERRO: Coluna 'name' não encontrada na planilha.")
        return

    df = df.replace({pd.NA: None, float("nan"): None})
    df = df.map(lambda x: x.strip() if isinstance(x, str) else x)

    print(f"Conectando ao Lighthouse ({ENVIRONMENT}/{CLIENT_NAME})...")
    ws = connect(client_name=CLIENT_NAME, environment=ENVIRONMENT, debug=False)

    cat_name_to_id = {}
    try:
        cats_raw = ws.get_categories()
        if isinstance(cats_raw, list):
            for cat in cats_raw:
                if isinstance(cat, dict):
                    cat_name_to_id[cat["name"].strip().lower()] = cat["id"]
    except Exception:
        pass

    has_parent_col = "parent" in df.columns
    root_attrs = []
    sub_attrs = []

    for _, row in df.iterrows():
        attr_name = row.get("name")
        if not attr_name or not isinstance(attr_name, str):
            continue

        raw_type = _clean(row.get("type")) or "Manual Text"
        source_pair = TYPE_TO_SOURCE.get(raw_type.lower().replace("_", " "), ("Manual", "String"))
        data_source, data_type = source_pair

        entry = {
            "name": attr_name,
            "description": _clean(row.get("description")),
            "data_source": data_source,
            "attribute_data_source": data_source,
            "value_type": data_type,
            "attribute_value_type": data_type,
            "unit_of_measurement": _clean(row.get("unit_of_measurement")) or _clean(row.get("unit")),
            "decimal_places": 0,
            "default_value": "",
        }

        dp = row.get("decimal_places")
        if dp is not None:
            try:
                entry["decimal_places"] = int(float(dp))
            except (ValueError, TypeError):
                pass

        dv = row.get("default_value")
        dv_clean = _clean(dv)
        if dv_clean:
            entry["default_value"] = dv_clean

        cat_val = row.get("category")
        if cat_val and isinstance(cat_val, str):
            cat_id = cat_name_to_id.get(cat_val.strip().lower())
            if cat_id:
                entry["categories"] = [cat_id]

        entry["_type_str"] = SOURCE_TO_TYPE.get((data_source, data_type), "Manual Text")

        parent_val = _clean(row.get("parent")) if has_parent_col else ""
        if parent_val:
            entry["_parent_name"] = parent_val
            sub_attrs.append(entry)
        else:
            root_attrs.append(entry)

    if not root_attrs and not sub_attrs:
        print("Nenhum atributo válido encontrado na planilha.")
        return

    print(f"\nAtributos raiz: {len(root_attrs)}")
    print(f"Subatributos:   {len(sub_attrs)}")
    print(f"Categorias carregadas do workspace: {len(cat_name_to_id)}")

    payload = {
        "name": template_name,
        "description": description,
        "attributes": [],
    }

    print(f"\nCriando template '{template_name}'...")
    response = ws.post_template(payload)

    if not (hasattr(response, "status_code") and response.status_code in (200, 201)):
        status = getattr(response, "status_code", "?")
        text = getattr(response, "text", str(response))
        print(f"ERRO ao criar template: HTTP {status} — {text}")
        return

    new_template = response.json()
    new_template_id = new_template.get("id", "")
    print(f"Template criado! ID: {new_template_id}")

    created = 0
    attr_errors = []
    name_to_id = {}

    def _create_attr(attr, parent_id=None):
        type_str = attr.get("_type_str", "Manual Text")
        raw_default = attr.get("default_value", "")
        if not raw_default and ("Float" in type_str or "Integer" in type_str):
            clean_default = None
        else:
            clean_default = raw_default if raw_default else None

        attr_payload = {
            "name": attr["name"],
            "description": attr.get("description", ""),
            "type": type_str,
            "unit_of_measurement": attr.get("unit_of_measurement", ""),
            "decimal_places": attr.get("decimal_places", 0),
            "default_value": clean_default,
            "categories": attr.get("categories", []),
        }
        if parent_id:
            attr_payload["parent_id"] = parent_id

        resp = ws.post_template_attribute(new_template_id, attr_payload)
        if hasattr(resp, "status_code") and resp.status_code not in (200, 201):
            return None, f"HTTP {resp.status_code} — {getattr(resp, 'text', '')}"
        return resp, None

    print(f"\nCriando {len(root_attrs)} atributo(s) raiz...")
    for attr in root_attrs:
        try:
            resp, err = _create_attr(attr)
            if err:
                attr_errors.append(f"{attr['name']}: {err}")
            else:
                created += 1
                print(f"  + {attr['name']}")
        except Exception as e:
            attr_errors.append(f"{attr['name']}: {e}")

    if sub_attrs:
        new_attrs_resp = ws.get_template_attributes(new_template_id)
        if isinstance(new_attrs_resp, list):
            new_attrs = new_attrs_resp
        elif isinstance(new_attrs_resp, dict):
            new_attrs = new_attrs_resp.get("attributes", [])
        else:
            new_attrs = []
        name_to_id = {a["name"].strip().lower(): a["id"] for a in new_attrs}

        print(f"\nCriando {len(sub_attrs)} subatributo(s)...")
        for sub in sub_attrs:
            parent_name = sub.pop("_parent_name", "")
            parent_id = name_to_id.get(parent_name.lower())
            if not parent_id:
                attr_errors.append(f"Pai '{parent_name}' não encontrado para '{sub['name']}'")
                continue
            try:
                resp, err = _create_attr(sub, parent_id=parent_id)
                if err:
                    attr_errors.append(f"{sub['name']}: {err}")
                else:
                    created += 1
                    print(f"  + {sub['name']} (sub de '{parent_name}')")
            except Exception as e:
                attr_errors.append(f"{sub['name']}: {e}")

    print(f"\n{'='*50}")
    print(f"Template '{template_name}' criado com {created} atributo(s).")
    print(f"  Atributos raiz: {len(root_attrs)}")
    print(f"  Subatributos:   {created - len(root_attrs) if created > len(root_attrs) else 0}")
    if attr_errors:
        print(f"\nErros:")
        for err in attr_errors:
            print(f"  - {err}")


if __name__ == "__main__":
    main()
