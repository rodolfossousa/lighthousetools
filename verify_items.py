"""
Script de verificação de cadastro de equipamentos (items).

Compara o que está cadastrado nos equipamentos do workspace com o que está
descrito nos dicionários de dados. Gera um relatório Excel com divergências.

Verificações realizadas:
  - Equipamento ausente no workspace
  - Atributo ausente no item do workspace
  - Subatributo ausente no item do workspace
  - Referência (tag) divergente para atributos time series
  - Valor divergente para atributos/subatributos manuais

Uso:
    python verify_items.py <client_name> [environment]
    python verify_items.py petroreconcavo prod
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from data_processor import get_item_enrollment_data
from config import parse_args, setup_logging
from utils import traverse_attributes
from Lighthouse.lighthouse import connect


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def normalize_value(v):
    """
    Normaliza um valor para comparação uniforme.
    Retorna None para valores vazios/ausentes.
    Valores numéricos são normalizados (ex: "1.0" == "1").
    """
    if v is None:
        return None
    if isinstance(v, float) and np.isnan(v):
        return None
    s = str(v).strip()
    if s == '' or s.lower() in ('nan', 'none', 'null'):
        return None
    try:
        f = float(s.replace(',', '.'))
        if f == int(f):
            return str(int(f))
        return str(round(f, 10))  # evita floating point noise
    except (ValueError, OverflowError):
        return s


def make_issue(equipment, template, level, attribute, subattribute, issue_type, expected, found):
    return {
        'equipment': equipment,
        'template': template,
        'level': level,
        'attribute': attribute,
        'subattribute': subattribute,
        'issue_type': issue_type,
        'expected': str(expected) if expected is not None else '',
        'found': str(found) if found is not None else '',
    }


# ──────────────────────────────────────────────────────────────────────────────
# Busca e indexação de dados da API por equipamento
# ──────────────────────────────────────────────────────────────────────────────

def build_api_attr_map(item_attributes):
    """
    A partir da lista de atributos de um item (retorno de ws.get_item_attributes),
    constrói um dict indexado para lookup eficiente:

        {
          "attr_name_lower": {
              "data_source": "Manual" | "Timeseries",
              "reference":   str | None,
              "value":       str | None,
              "subattrs": {
                  "subattr_name_lower": {
                      "data_source": str,
                      "value":       str | None,
                  }
              }
          }
        }
    """
    api_map = {}
    for attribute in item_attributes:
        records = traverse_attributes(attribute)
        for rec in records:
            attr_key = str(rec['attribute_name']).strip().lower()
            if not rec['is_subattribute']:
                if attr_key not in api_map:
                    api_map[attr_key] = {
                        'data_source': rec.get('attribute_data_source'),
                        'reference':   rec.get('attribute_reference'),
                        'value':       rec.get('attribute_value'),
                        'subattrs':    {},
                    }
            else:
                sub_key = str(rec['subattribute_name']).strip().lower()
                if attr_key not in api_map:
                    api_map[attr_key] = {
                        'data_source': None, 'reference': None, 'value': None, 'subattrs': {}
                    }
                api_map[attr_key]['subattrs'][sub_key] = {
                    'data_source': rec.get('subattribute_data_source'),
                    'value':       rec.get('subattribute_value'),
                }
    return api_map


# ──────────────────────────────────────────────────────────────────────────────
# Verificação por equipamento
# ──────────────────────────────────────────────────────────────────────────────

def verify_item(ws, item_id, item_name, template_name, dict_attrs, dict_subattrs):
    """
    Verifica atributos e subatributos de um equipamento específico.
    Retorna lista de dicts com divergências.
    """
    issues = []

    item_attributes_resp = ws.get_item_attributes(item_id)
    item_attributes = item_attributes_resp.get('attributes', []) if item_attributes_resp else []

    if not item_attributes:
        issues.append(make_issue(
            item_name, template_name, 'item', '', '',
            'no_attributes_in_api', item_name, 'Sem atributos cadastrados no workspace',
        ))
        return issues

    api_map = build_api_attr_map(item_attributes)

    # ── Atributos ──────────────────────────────────────────────────────────────
    for _, row in dict_attrs.iterrows():
        attr_name = str(row['attribute_name']).strip()
        attr_key  = attr_name.lower()

        if attr_key not in api_map:
            issues.append(make_issue(
                item_name, template_name, 'attribute', attr_name, '',
                'missing_in_api', attr_name, '',
            ))
            continue

        api_attr = api_map[attr_key]
        is_manual = (api_attr['data_source'] == 'Manual')

        if is_manual:
            # Valor manual: coluna 'value', com fallback para 'reference' (V1)
            dict_val = normalize_value(row.get('value'))
            if dict_val is None:
                dict_val = normalize_value(row.get('reference'))
            api_val = normalize_value(api_attr['value'])

            if dict_val is not None and dict_val != api_val:
                issues.append(make_issue(
                    item_name, template_name, 'attribute', attr_name, '',
                    'wrong_value', dict_val, api_val,
                ))
        else:
            # Atributo time series: compara referência (tag)
            dict_ref = normalize_value(row.get('reference'))
            api_ref  = normalize_value(api_attr['reference'])

            if dict_ref is not None and dict_ref != api_ref:
                issues.append(make_issue(
                    item_name, template_name, 'attribute', attr_name, '',
                    'wrong_reference', dict_ref, api_ref,
                ))

    # ── Subatributos ───────────────────────────────────────────────────────────
    for _, row in dict_subattrs.iterrows():
        attr_name    = str(row['attribute_name']).strip()
        subattr_name = str(row['subattribute_name']).strip()
        attr_key     = attr_name.lower()
        sub_key      = subattr_name.lower()

        if attr_key not in api_map:
            # Pai ausente — já foi reportado acima
            continue

        subattrs = api_map[attr_key]['subattrs']
        if sub_key not in subattrs:
            issues.append(make_issue(
                item_name, template_name, 'subattribute', attr_name, subattr_name,
                'missing_in_api', subattr_name, '',
            ))
            continue

        api_sub   = subattrs[sub_key]
        dict_val  = normalize_value(row.get('value'))
        api_val   = normalize_value(api_sub['value'])

        if dict_val is not None and dict_val != api_val:
            issues.append(make_issue(
                item_name, template_name, 'subattribute', attr_name, subattr_name,
                'wrong_value', dict_val, api_val,
            ))

    return issues


# ──────────────────────────────────────────────────────────────────────────────
# Geração do relatório
# ──────────────────────────────────────────────────────────────────────────────

ISSUE_TYPE_PT = {
    'equipment_not_in_api': 'Equipamento ausente no workspace',
    'no_attributes_in_api': 'Equipamento sem atributos cadastrados',
    'missing_in_api':       'Ausente no workspace (não cadastrado)',
    'wrong_reference':      'Referência (tag) divergente',
    'wrong_value':          'Valor divergente',
}


def generate_report(all_issues, client_name, environment):
    timestamp   = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = f'logs/verify_items_{client_name}_{environment}_{timestamp}.xlsx'

    if not all_issues:
        logging.info('Nenhuma divergência encontrada nos equipamentos.')
        detail_df  = pd.DataFrame(columns=[
            'equipment', 'template', 'level', 'attribute', 'subattribute',
            'issue_type', 'issue_type_pt', 'expected', 'found',
        ])
        summary_df = pd.DataFrame(columns=['issue_type', 'issue_type_pt', 'count'])
    else:
        detail_df = pd.DataFrame(all_issues)
        detail_df['issue_type_pt'] = detail_df['issue_type'].map(ISSUE_TYPE_PT).fillna(detail_df['issue_type'])
        detail_df = detail_df.sort_values(['equipment', 'attribute', 'subattribute'])

        summary_df = (
            detail_df.groupby(['issue_type', 'issue_type_pt'])
            .size()
            .reset_index(name='count')
            .sort_values('count', ascending=False)
        )

    with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
        workbook = writer.book

        # ── Aba Resumo ──────────────────────────────────────────────────────
        summary_df.to_excel(writer, sheet_name='Resumo', index=False)
        ws_summary = writer.sheets['Resumo']
        ws_summary.set_column('A:A', 28)
        ws_summary.set_column('B:B', 40)
        ws_summary.set_column('C:C', 10)

        # ── Aba Divergências ────────────────────────────────────────────────
        detail_df.to_excel(writer, sheet_name='Divergências', index=False)
        ws_detail = writer.sheets['Divergências']
        ws_detail.set_column('A:A', 45)  # equipment
        ws_detail.set_column('B:B', 38)  # template
        ws_detail.set_column('C:C', 14)  # level
        ws_detail.set_column('D:D', 55)  # attribute
        ws_detail.set_column('E:E', 40)  # subattribute
        ws_detail.set_column('F:F', 22)  # issue_type
        ws_detail.set_column('G:G', 40)  # issue_type_pt
        ws_detail.set_column('H:H', 45)  # expected
        ws_detail.set_column('I:I', 45)  # found

        red_fmt    = workbook.add_format({'bg_color': '#FFB3B3'})
        orange_fmt = workbook.add_format({'bg_color': '#FFD9A0'})
        yellow_fmt = workbook.add_format({'bg_color': '#FFFAAA'})

        if not detail_df.empty:
            for row_idx, row in enumerate(detail_df.itertuples(), start=1):
                if row.issue_type in ('missing_in_api', 'equipment_not_in_api', 'no_attributes_in_api'):
                    fmt = red_fmt
                elif row.issue_type in ('wrong_reference', 'wrong_value'):
                    fmt = orange_fmt
                else:
                    fmt = yellow_fmt
                ws_detail.set_row(row_idx, None, fmt)

    logging.info(f'Relatório salvo em: {output_path}')
    return output_path


# ──────────────────────────────────────────────────────────────────────────────
# Pipeline principal
# ──────────────────────────────────────────────────────────────────────────────

def pipeline(client_name, environment):
    ws = connect(client_name, environment, False)

    logging.info(f"Carregando dicionário de dados para '{client_name}'...")
    try:
        excel_df, attributes_df, subattributes_df = get_item_enrollment_data(client_name)
    except ValueError as e:
        logging.error(e)
        return

    # Identifica todos os equipamentos únicos no dicionário de dados
    equipment_names_in_dict = set(excel_df['asset_name'].dropna().unique())
    logging.info(f'Equipamentos no dicionário de dados: {len(equipment_names_in_dict)}')

    # Busca todos os items do workspace e filtra pelos que estão no dicionário
    logging.info('Buscando equipamentos no workspace...')
    all_items = ws.get_items()  # {id: name}
    relevant_items = {
        item_id: item_name
        for item_id, item_name in all_items.items()
        if item_name in equipment_names_in_dict
    }
    found_names    = set(relevant_items.values())
    missing_names  = equipment_names_in_dict - found_names

    logging.info(f'Equipamentos encontrados no workspace: {len(relevant_items)}')
    if missing_names:
        logging.warning(f'Equipamentos ausentes no workspace: {len(missing_names)}')

    all_issues = []

    # Registra equipamentos ausentes
    for eq_name in sorted(missing_names):
        template_name = excel_df[excel_df['asset_name'] == eq_name]['template_name'].iloc[0] \
            if not excel_df[excel_df['asset_name'] == eq_name].empty else ''
        all_issues.append(make_issue(
            eq_name, template_name, 'equipment', '', '',
            'equipment_not_in_api', eq_name, '',
        ))

    # Verifica cada equipamento encontrado
    def process_item(item_id, item_name):
        template_name = ''
        item_rows = excel_df[excel_df['asset_name'] == item_name]
        if not item_rows.empty:
            template_name = item_rows['template_name'].iloc[0]

        item_attrs    = attributes_df[attributes_df['asset_name'] == item_name]
        item_subattrs = subattributes_df[subattributes_df['asset_name'] == item_name]

        return verify_item(ws, item_id, item_name, template_name, item_attrs, item_subattrs)

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(process_item, item_id, item_name): item_name
            for item_id, item_name in relevant_items.items()
        }
        for future in tqdm(as_completed(futures), total=len(futures), desc='Verificando equipamentos'):
            item_name = futures[future]
            try:
                item_issues = future.result()
                all_issues.extend(item_issues)
                n = len(item_issues)
                if n:
                    logging.info(f'  {item_name}: {n} divergência(s)')
                else:
                    logging.info(f'  {item_name}: OK')
            except Exception as e:
                logging.error(f'  Erro ao verificar {item_name}: {e}', exc_info=True)

    total = len(all_issues)
    if total:
        logging.warning(f'\nTotal de divergências encontradas: {total}')
    else:
        logging.info('\nNenhuma divergência encontrada.')

    generate_report(all_issues, client_name, environment)


if __name__ == '__main__':
    setup_logging('verify_items')
    args = parse_args()
    pipeline(args.client, args.environment)
