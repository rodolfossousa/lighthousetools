"""
Script de verificação de cadastro de templates.

Compara o que está cadastrado no Lighthouse (API) com o que está descrito
nos dicionários de dados. Gera um relatório Excel com todas as divergências.

Verificações realizadas:
  - Template ausente na API
  - Atributo ausente na API
  - Subatributo ausente na API
  - Categorias divergentes (atributo ou subatributo)
  - Unidade de medida divergente (atributo ou subatributo)

Uso:
    python verify_enrollment.py <client_name> [environment]
    python verify_enrollment.py petroreconcavo prod
"""

import logging
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from data_processor import get_template_enrollment_data
from config import parse_args, setup_logging
from utils import fix_unit_of_measurement
from Lighthouse.lighthouse import connect


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def normalize_categories(raw) -> frozenset:
    """
    Normaliza categorias para um frozenset de strings para comparação uniforme.
    Aceita string CSV ("Cat1, Cat2") ou lista de dicts [{"name": "Cat1"}].
    """
    if isinstance(raw, str):
        return frozenset(
            c.replace(";", "").strip()
            for c in raw.split(",")
            if c.replace(";", "").strip()
        )
    if isinstance(raw, list):
        result = set()
        for item in raw:
            if isinstance(item, dict):
                name = item.get("name", "").strip()
            else:
                name = str(item).strip()
            if name:
                result.add(name)
        return frozenset(result)
    return frozenset()


def norm_unit(u) -> str:
    return fix_unit_of_measurement(str(u or "").strip())


def make_issue(template, level, attribute, subattribute, issue_type, expected, found):
    return {
        "template": template,
        "level": level,
        "attribute": attribute,
        "subattribute": subattribute,
        "issue_type": issue_type,
        "expected": str(expected),
        "found": str(found),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Busca de dados da API
# ──────────────────────────────────────────────────────────────────────────────

def fetch_template_api_data(ws, template_id, template_name, dict_subattrs):
    """
    Busca todos os atributos do template e, em paralelo, os subatributos dos
    atributos que possuem subatributos no dicionário de dados.

    Retorna um dict:
        {
          "attr_name_lower": {
              "attr":     <dict da API>,
              "subattrs": { "subattr_name_lower": <dict da API> }
          },
          ...
        }
    ou None em caso de falha.
    """
    response = ws.get_template_attributes(template_id)
    if not response or "attributes" not in response:
        logging.warning(f"Template '{template_name}': falha ao buscar atributos da API")
        return None

    api_attrs = response["attributes"]

    # Apenas busca subatributos dos pais que realmente têm subatributos no dicionário
    parents_with_subattrs = {
        row["attribute_name"].strip().lower()
        for _, row in dict_subattrs.iterrows()
    }

    attr_map = {
        attr["name"].strip().lower(): {"attr": attr, "subattrs": {}}
        for attr in api_attrs
    }

    def fetch_subattrs(attr):
        resp = ws.get_template_attribute_subattributes(attr["id"])
        subattrs = resp.get("attributes", []) if resp else []
        return attr["name"].strip().lower(), {
            s["name"].strip().lower(): s for s in subattrs
        }

    attrs_to_fetch = [
        attr for attr in api_attrs
        if attr["name"].strip().lower() in parents_with_subattrs
    ]

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(fetch_subattrs, attr) for attr in attrs_to_fetch]
        for future in as_completed(futures):
            parent_key, subattr_map = future.result()
            if parent_key in attr_map:
                attr_map[parent_key]["subattrs"] = subattr_map

    return attr_map


# ──────────────────────────────────────────────────────────────────────────────
# Comparações
# ──────────────────────────────────────────────────────────────────────────────

def compare_attribute(template_name, attr_name, dict_row, api_attr):
    issues = []

    # Categorias
    dict_cats = normalize_categories(dict_row.get("categories"))
    api_cats  = normalize_categories(api_attr.get("categories", []))
    if dict_cats != api_cats:
        issues.append(make_issue(
            template_name, "attribute", attr_name, "",
            "wrong_categories",
            ", ".join(sorted(dict_cats)),
            ", ".join(sorted(api_cats)),
        ))

    # Unidade de medida
    exp_unit = norm_unit(dict_row.get("unit_of_measurement", ""))
    got_unit = norm_unit(api_attr.get("unit_of_measurement", ""))
    if exp_unit != got_unit:
        issues.append(make_issue(
            template_name, "attribute", attr_name, "",
            "wrong_unit", exp_unit, got_unit,
        ))

    return issues


def compare_subattribute(template_name, attr_name, subattr_name, dict_row, api_subattr):
    issues = []

    # Categorias — templates.py sempre adiciona 'Limits' automaticamente,
    # então o esperado é o dicionário + 'Limits'.
    dict_cats = normalize_categories(dict_row.get("categories"))
    expected_cats = dict_cats | frozenset(["Limits"])
    api_cats = normalize_categories(api_subattr.get("categories", []))
    if expected_cats != api_cats:
        issues.append(make_issue(
            template_name, "subattribute", attr_name, subattr_name,
            "wrong_categories",
            ", ".join(sorted(expected_cats)),
            ", ".join(sorted(api_cats)),
        ))

    # Unidade de medida
    exp_unit = norm_unit(dict_row.get("unit_of_measurement", ""))
    got_unit = norm_unit(api_subattr.get("unit_of_measurement", ""))
    if exp_unit != got_unit:
        issues.append(make_issue(
            template_name, "subattribute", attr_name, subattr_name,
            "wrong_unit", exp_unit, got_unit,
        ))

    return issues


# ──────────────────────────────────────────────────────────────────────────────
# Verificação por template
# ──────────────────────────────────────────────────────────────────────────────

def verify_template(ws, template_id, template_name, template_dict):
    """
    Verifica atributos e subatributos de um único template.
    Retorna lista de dicts de divergências.
    """
    issues = []

    dict_attrs    = template_dict[template_dict["attribute_level"] == "attribute"]
    dict_subattrs = template_dict[template_dict["attribute_level"] == "subattribute"]

    api_map = fetch_template_api_data(ws, template_id, template_name, dict_subattrs)
    if api_map is None:
        return [make_issue(template_name, "template", "", "", "api_error", "", "Falha ao buscar atributos")]

    # ── Atributos ──────────────────────────────────────────────────────────────
    for _, row in dict_attrs.iterrows():
        attr_name = row["attribute_name"].strip()
        key = attr_name.lower()

        if key not in api_map:
            issues.append(make_issue(
                template_name, "attribute", attr_name, "",
                "missing_in_api", attr_name, "",
            ))
            continue

        issues.extend(compare_attribute(template_name, attr_name, row, api_map[key]["attr"]))

    # ── Subatributos ───────────────────────────────────────────────────────────
    for _, row in dict_subattrs.iterrows():
        attr_name    = row["attribute_name"].strip()
        subattr_name = row["subattribute_name"].strip()
        parent_key   = attr_name.lower()
        child_key    = subattr_name.lower()

        if parent_key not in api_map:
            # Pai ausente — já foi registrado acima ou é atributo padrão
            continue

        subattrs = api_map[parent_key]["subattrs"]
        if child_key not in subattrs:
            issues.append(make_issue(
                template_name, "subattribute", attr_name, subattr_name,
                "missing_in_api", subattr_name, "",
            ))
            continue

        issues.extend(compare_subattribute(
            template_name, attr_name, subattr_name, row, subattrs[child_key]
        ))

    return issues


# ──────────────────────────────────────────────────────────────────────────────
# Geração do relatório
# ──────────────────────────────────────────────────────────────────────────────

ISSUE_TYPE_PT = {
    "missing_in_api":   "Ausente na API (não cadastrado)",
    "wrong_categories": "Categorias divergentes",
    "wrong_unit":       "Unidade de medida divergente",
    "api_error":        "Erro de API",
}


def generate_report(all_issues, client_name, environment):
    timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"logs/verify_enrollment_{client_name}_{environment}_{timestamp}.xlsx"

    if not all_issues:
        logging.info("Nenhuma divergência encontrada. O cadastro está de acordo com o dicionário de dados.")
        detail_df = pd.DataFrame(columns=[
            "template", "level", "attribute", "subattribute",
            "issue_type", "issue_type_pt", "expected", "found",
        ])
        summary_df = pd.DataFrame(columns=["issue_type", "issue_type_pt", "count"])
    else:
        detail_df = pd.DataFrame(all_issues)
        detail_df["issue_type_pt"] = detail_df["issue_type"].map(ISSUE_TYPE_PT).fillna(detail_df["issue_type"])
        detail_df = detail_df.sort_values(["template", "level", "attribute", "subattribute"])

        summary_df = (
            detail_df.groupby(["issue_type", "issue_type_pt"])
            .size()
            .reset_index(name="count")
            .sort_values("count", ascending=False)
        )

    with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
        workbook = writer.book

        # ── Aba Resumo ──────────────────────────────────────────────────────
        summary_df.to_excel(writer, sheet_name="Resumo", index=False)
        ws_summary = writer.sheets["Resumo"]
        ws_summary.set_column("A:A", 28)
        ws_summary.set_column("B:B", 38)
        ws_summary.set_column("C:C", 10)

        # ── Aba Divergências ────────────────────────────────────────────────
        detail_df.to_excel(writer, sheet_name="Divergências", index=False)
        ws_detail = writer.sheets["Divergências"]
        ws_detail.set_column("A:A", 40)  # template
        ws_detail.set_column("B:B", 14)  # level
        ws_detail.set_column("C:C", 55)  # attribute
        ws_detail.set_column("D:D", 40)  # subattribute
        ws_detail.set_column("E:E", 22)  # issue_type
        ws_detail.set_column("F:F", 38)  # issue_type_pt
        ws_detail.set_column("G:G", 55)  # expected
        ws_detail.set_column("H:H", 55)  # found

        # Colorir linhas por tipo de issue
        red_fmt    = workbook.add_format({"bg_color": "#FFB3B3"})
        orange_fmt = workbook.add_format({"bg_color": "#FFD9A0"})
        yellow_fmt = workbook.add_format({"bg_color": "#FFFAAA"})

        if not detail_df.empty:
            for row_idx, row in enumerate(detail_df.itertuples(), start=1):
                fmt = None
                if row.issue_type == "missing_in_api":
                    fmt = red_fmt
                elif row.issue_type == "wrong_categories":
                    fmt = orange_fmt
                elif row.issue_type == "wrong_unit":
                    fmt = yellow_fmt
                if fmt:
                    ws_detail.set_row(row_idx, None, fmt)

    logging.info(f"Relatório salvo em: {output_path}")
    return output_path


# ──────────────────────────────────────────────────────────────────────────────
# Pipeline principal
# ──────────────────────────────────────────────────────────────────────────────

def pipeline(client_name, environment):
    ws = connect(client_name, environment, False)

    logging.info(f"Carregando dicionário de dados para '{client_name}'...")
    try:
        dict_df = get_template_enrollment_data(client_name)
    except ValueError as e:
        logging.error(e)
        return

    enrolled_templates  = ws.get_templates()          # {id: name}
    template_name_to_id = {name: tid for tid, name in enrolled_templates.items()}

    unique_templates = dict_df["template_name"].unique()
    logging.info(f"Templates no dicionário de dados: {len(unique_templates)}")
    logging.info(f"Templates cadastrados na API:     {len(enrolled_templates)}")

    all_issues = []
    for template_name in tqdm(unique_templates, desc="Verificando templates"):
        if template_name not in template_name_to_id:
            logging.warning(f"Template '{template_name}' não encontrado na API")
            all_issues.append(make_issue(
                template_name, "template", "", "",
                "missing_in_api", template_name, "",
            ))
            continue

        template_id   = template_name_to_id[template_name]
        template_dict = dict_df[dict_df["template_name"] == template_name]
        template_issues = verify_template(ws, template_id, template_name, template_dict)
        all_issues.extend(template_issues)

        n = len(template_issues)
        if n:
            logging.info(f"  {template_name}: {n} divergência(s)")
        else:
            logging.info(f"  {template_name}: OK")

    total = len(all_issues)
    if total:
        logging.warning(f"\nTotal de divergências encontradas: {total}")
    else:
        logging.info("\nNenhuma divergência encontrada.")

    generate_report(all_issues, client_name, environment)


if __name__ == "__main__":
    setup_logging("verify_enrollment")
    args = parse_args()
    pipeline(args.client, args.environment)
