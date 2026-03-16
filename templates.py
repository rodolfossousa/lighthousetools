"""
Código para fazer cadastro de templates em um workspace específico
"""

import pandas as pd
import json
import tqdm
import numpy as np
import logging
from datetime import datetime
from dictionaries import DICTIONARIES
from data_processor import get_template_enrollment_data
from config import parse_args, get_lighthouse_client, setup_logging


def find_template_id_by_name(enrolled_templates, template_name):
    """
    Encontra ID do template pelo nome.
    enrolled_templates é uma lista de dicionários no formato:
    {"id": "nome do template"}
    """
    for template in enrolled_templates:
        if enrolled_templates[template] == template_name:
            return template
    return None

def find_category_id_by_name(categories, category_name):
    """
    Encontra ID da categoria pelo nome
    """
    for category in categories:
        if category["name"] == category_name:
            return category["id"]
    return None

def find_attribute_id_by_name(template_attributes, search_name):
    for attribute in template_attributes:
        if attribute['name'] == search_name:
            return attribute['id']
    
    return None
    
def get_default_attributes_and_subattributes():
    with open("default_attributes.json", "r", encoding='utf8') as f:
        all_default_attributes = json.load(f)

        # Cria uma cópia para manipular e manter apenas atributos sem subatributos
        default_attributes = all_default_attributes.copy()
        default_subattributes = all_default_attributes.copy()

        for attr in all_default_attributes:
            # Se parent_id não for "", remove o atributo da lista pois irá em outra lista
            if "parent_id" in attr and attr["parent_id"]:
                default_attributes.remove(attr)
            else:
                # Se parent_id for "", remove o atributo da lista de subatributos
                default_subattributes.remove(attr)

    return default_attributes, default_subattributes

def check_default_attributes(template_attributes, default_attributes):
    
    # se não houver atributos no template, retorna todos os atributos padrão
    # print(template_attributes)
    # if len(template_attributes) == 0:
    #     return default_attributes
    
    current_attributes = [attribute['name'] for attribute in template_attributes]
    not_found = []

    for searched_attribute in default_attributes:
        if not searched_attribute["name"] in current_attributes:
            not_found.append(searched_attribute)

    return not_found

def check_default_subattributes_for_template(ws, template_attributes, default_subattributes):
    """
    para cada atributo, verificar se os subatributos estão corretos
    """

    # agrupar subatributos por atributo para facilitar a consulta
    needed_subattributes = {}

    for default_subattribute in default_subattributes:
        parent_attribute_name = default_subattribute['parent_id']
        if parent_attribute_name in needed_subattributes:
            needed_subattributes[parent_attribute_name].append(default_subattribute)
        else:
            needed_subattributes[parent_attribute_name] = [default_subattribute]

    for template_attribute in template_attributes:
        # Encontrar lista de subatributos necessários para o atributo
        parent_attribute_name = template_attribute['name']

        # pula caso não seja um dos atributos padrão
        if not parent_attribute_name in needed_subattributes:
            continue

        # caso seja um atributo necessário, verificar se possui todos os subatributos
        # se não possuir, manter na lista de necessários
        current_subattributes = ws.get_template_attribute_subattributes(template_attribute['id'])['attributes']
        # logging.debug(f"Subatributos de {template_attribute['name']}: {len(current_subattributes)}")
        existent_subattributes_names_list = [attr['name'] for attr in current_subattributes]

        for default_subattribute in needed_subattributes[parent_attribute_name]:
            if default_subattribute['name'] in existent_subattributes_names_list:
                needed_subattributes[parent_attribute_name] = [
                    sub for sub in needed_subattributes[parent_attribute_name]
                    if sub['name'] != default_subattribute['name']
                ]

                if len(needed_subattributes[parent_attribute_name]) == 0:
                    del needed_subattributes[parent_attribute_name]

    return needed_subattributes

def fix_categories_uuid(attribute, categories, ws = None):
    categories_list = attribute['categories']
    categories_id_list = []
    for category_name in categories_list:
        # remove ";" from the category name and strip it
        if not category_name or not isinstance(category_name, str):
            category_name = ""
        category_name = category_name.replace(";", "").strip()
        category_id = find_category_id_by_name(categories, category_name)

        if not category_id:
            logging.warning(f"Category '{category_name}' not found")
            if not ws:
                raise NameError(f"Category '{category_name}' not found and ws is None, cannot create category")
            else:
                ws.post_category({'name': category_name, 'group_id': find_attributes_group_id(ws)})
                categories = ws.get_categories()
                category_id = find_category_id_by_name(categories, category_name)
                logging.info(f"cadastrada {category_name} com id: {category_id}")
        categories_id_list.append(category_id)

    attribute['categories'] = categories_id_list
    return attribute

def fix_unit_of_measurement(unit_of_measurement:str):
    """
    Normaliza a unidade de medida para o formato correto.
    Exemplo:
        kpa, kPa, KPa -> kPa
        KPag, kPag -> kPag
        °C, ºC -> °C
        Pa, pa -> Pa
        °F, DEG F -> °F
        G, g -> g
        rpm, Rpm -> rpm
    """
    if not isinstance(unit_of_measurement, str):
        return unit_of_measurement

    if unit_of_measurement.strip() == '':
        return ''

    unit = unit_of_measurement.strip().lower()

    # normalize whitespace and lowercase (unit already lowercased above)
    unit_norm = " ".join(unit.split())

    # flattened, case-insensitive mapping (all keys stored in lowercase)
    mapping = {
        'pa': 'Pa',
        'kpa': 'kPa',
        'kpag': 'kPag',

        '°c': '°C',
        'ºc': '°C',
        'oc': '°C',
        'deg c': '°C',
        'degc': '°C',

        '°f': '°F',
        'ºf': '°F',
        'of': '°F',

        'deg f': '°F',
        'degf': '°F',

        'g': 'g',

        'rpm': 'rpm',

        "psig": "psig",
        "psid": "psid",

        "ips": "IPS",
    }

    # return the canonical unit if found (case-insensitive), else original trimmed string
    return mapping.get(unit_norm, unit_of_measurement.strip())


def find_attributes_group_id(ws) -> str:
    groups = ws.get_groups()

    # encontra id do grupo de atributos:
    for group in groups:
        if group['name'] == "Attribute Categories":
            return group['id']

    # se não encontrou, cadastra
    response = ws.post_group({'name': 'Attribute Categories'})
    if response.get('status_code', '422') == '422':
        raise ValueError(
            'Erro ao cadastrar grupo de atributos "Attribute Categories"')

    return response

def is_number(val):
    try:
        float(str(val).replace(',', '.'))
        return True
    except (ValueError, TypeError):
        return False

def enroll_default_attributes(ws, template_id, categories, template_name):
    template_attributes = ws.get_template_attributes(template_id)['attributes']
    default_attributes, _ = get_default_attributes_and_subattributes()
    attributes_not_found = check_default_attributes(template_attributes, default_attributes)
    if len(attributes_not_found):
        logging.info(f"Atributos padrão não encontrados para o template {template_name}, cadastrando {len(attributes_not_found)}")
        for attribute_not_found in attributes_not_found:
            # attribute_not_found['name'] = attribute_not_found['name'].title()
            logging.info(f"\tCadastrando atributo {attribute_not_found['name']}")
            attribute_not_found = fix_categories_uuid(attribute_not_found, categories, ws)
            response = ws.post_template_attribute(template_id, attribute_not_found)

def enroll_default_subattributes(ws, template_id, categories, template_name):
    template_attributes = ws.get_template_attributes(template_id)['attributes']
    _, default_subattributes = get_default_attributes_and_subattributes()
    subattributes_not_found = check_default_subattributes_for_template(ws, template_attributes, default_subattributes)
    total_not_found = sum([len(subattributes_not_found[attribute]) for attribute in subattributes_not_found])
    if total_not_found:
        logging.info(f"Subatributos padrão não encontrados para o template {template_name}: {total_not_found}")
    for attribute_name in subattributes_not_found:
        attribute_id = find_attribute_id_by_name(template_attributes, attribute_name)
        if not attribute_id:
            logging.warning(f'Atributo {attribute_name} não encontrado no template')
            continue
        for subattribute in subattributes_not_found[attribute_name]:
            subattribute['parent_id'] = attribute_id
            subattribute = fix_categories_uuid(subattribute, categories, ws)
            logging.info(f"\tCadastrando subatributo {attribute_name} | {subattribute['name']}")
            ws.post_template_attribute(template_id, subattribute)

def enroll_attributes(ws, template_id, categories, excel_templates, template_name):
    attributes_to_enroll = excel_templates[excel_templates['type'] == 'attribute']
    attributes_to_enroll = attributes_to_enroll[attributes_to_enroll['attribute_name'].notnull()]  # Drop lines where attribute_name is NaN
    attributes_to_enroll = attributes_to_enroll[attributes_to_enroll['Template'] == template_name]
    attributes_to_enroll = attributes_to_enroll[[ 'Template', 'attribute_name', 'Categories', 'decimal_places', 'unit_of_measurement']]
    attributes_to_enroll['attribute_name'] = attributes_to_enroll['attribute_name'].apply(lambda x: x.strip())
    attributes_to_enroll = attributes_to_enroll.rename(columns={
        'attribute_name': 'name',
        'Categories': 'categories',
        'decimal_places': 'decimal_places',
        'unit_of_measurement': 'unit_of_measurement',
        'Template': 'template'
    })
    attributes_to_enroll = attributes_to_enroll.drop_duplicates()
    template_attributes = ws.get_template_attributes(template_id)['attributes']
    current_attributes = [attribute['name'].strip().lower() for attribute in template_attributes]
    status = {'enrolled': 0, 'skipped': 0, 'failed': 0}
    attributes_status = {}
    for _, row in tqdm.tqdm(attributes_to_enroll.iterrows(), total=attributes_to_enroll.shape[0], desc=f"Cadastrando atributos de {template_name}"):
        attribute = row.to_dict()
        if attribute['name'].strip().lower() in current_attributes:
            attribute['status'] = 'skipped'
            attributes_status[attribute['name']] = attribute
            status['skipped'] += 1
            continue
        data = {
            'name': attribute['name'].strip(),
            'description': '',
            'categories': [attribute['categories']],
            'type': 'Time Series Float',
            'decimal_places': str(int(attribute['decimal_places'])),
            'unit_of_measurement': fix_unit_of_measurement(attribute['unit_of_measurement'])
        }
        data = fix_categories_uuid(data, categories, ws)
        
        response = ws.post_template_attribute(template_id, data)

        current_attributes.append(data['name'].lower()) # garante que não será adicionado novamente caso tenha linha duplicada
        
        if not response:
            attribute['status'] = 'failed'
            status['failed'] += 1
        else:
            attribute['status'] = 'enrolled'
            status['enrolled'] += 1
        attributes_status[attribute['name']] = attribute
    logging.info(f"Template {template_name}: {status['enrolled']} cadastrados, {status['skipped']} já existiam, {status['failed']} falharam")
    log_file = f"logs/{template_name}_attributes_log.txt"
    with open(log_file, "w", encoding="utf-8") as f:
        for attr_name, attr in attributes_status.items():
            f.write(f"{attr_name}: {attr['status']}\n")
    logging.debug(f"Log saved to {log_file}")
    return status

def enroll_subattributes(ws, template_id, categories, excel_templates, template_name):
    template_attributes = ws.get_template_attributes(template_id)['attributes']
    subattributes_to_enroll = excel_templates[excel_templates['type'] == 'subattribute']
    # check if there is any subattribute to enroll for the template
    if subattributes_to_enroll[subattributes_to_enroll['Template'] == template_name].shape[0] == 0:
        logging.info(f"Nenhum subatributo para cadastrar no template {template_name}")
        return None
    subattributes_to_enroll = subattributes_to_enroll[subattributes_to_enroll['Template'] == template_name]
    subattributes_to_enroll = subattributes_to_enroll[['Template', 'attribute_name', 'Categories', 'decimal_places', 'unit_of_measurement', 'Value']]
    subattributes_to_enroll = subattributes_to_enroll.drop_duplicates()
    subattributes_to_enroll = subattributes_to_enroll.rename(columns={
        'attribute_name': 'name',
        'Categories': 'categories',
        'decimal_places': 'decimal_places',
        'unit_of_measurement': 'unit_of_measurement',
        'Template': 'template',
        'Value': 'value'
    })
    subattributes_to_enroll['type'] = 'Manual Float'
    subattributes_to_enroll[['parent_name', 'name']] = subattributes_to_enroll['name'].str.split('|', n=1, expand=True)
    subattributes_to_enroll['parent_name'] = subattributes_to_enroll['parent_name'].str.strip()
    subattributes_to_enroll['name'] = subattributes_to_enroll['name'].str.strip()
    subattributes_to_enroll['parent_id'] = subattributes_to_enroll['parent_name'].apply(
        lambda parent_name: find_attribute_id_by_name(template_attributes, parent_name)
    )
    subattributes_to_enroll['value'] = subattributes_to_enroll['value'].apply(
        lambda v: v if is_number(v) else ''
    )
    logging.info(f"Total de subatributos a cadastrar para o template {template_name}: {subattributes_to_enroll.shape[0]}")
    logging.info("Criando lista de subatributos. Isso pode demorar")
    template_attributes_subattribute_dict = {}
    for template_attribute in tqdm.tqdm(template_attributes, desc="Mapping subattributes"):
        subattributes_dict = ws.get_template_attribute_subattributes(template_attribute['id'])['attributes']
        template_attributes_subattribute_dict[template_attribute['name']] = [attr['name'] for attr in subattributes_dict]
    
    status = {'enrolled': 0, 'skipped': 0, 'failed': 0, 'parent_not_found': 0}
    subattributes_status = {}
    for _, row in tqdm.tqdm(subattributes_to_enroll.iterrows(), total=subattributes_to_enroll.shape[0], desc=f"Cadastrando subatributos de {template_name}"):
        subattribute = row.to_dict()
        template_attribute_name = subattribute['parent_name']
        try:
            if subattribute['name'] in template_attributes_subattribute_dict[template_attribute_name]:
                status['skipped'] += 1
                subattribute['status'] = 'skipped'
                subattributes_status[subattribute['name']] = subattribute
                continue
        except:
            status['parent_not_found'] += 1
            subattribute['status'] = 'parent_not_found'
            subattributes_status[subattribute['name']] = subattribute
            continue
        data = {
            'name': subattribute['name'].strip(),
            'description': '',
            'categories': ['Limits'], # Força categoria Limits em todos os subatributos
            'type': subattribute['type'],
            'decimal_places': subattribute['decimal_places'],
            'unit_of_measurement': fix_unit_of_measurement(subattribute['unit_of_measurement']),
            'default_value': None,
            'parent_id': subattribute['parent_id']
        }
        data = fix_categories_uuid(data, categories, ws)
        # answer = input(f"Cadastrar subatributo {data['parent_id']} | {data['name']} ? Dados: {data}. Pressione Enter para continuar...")
        # if answer.lower() == 'n':
        #     print("Pulando...")
        #     continue
        response = ws.post_template_attribute(template_id, data)
        if not response:
            subattribute['status'] = 'failed'
            status['failed'] += 1
        else:
            subattribute['status'] = 'enrolled'
            status['enrolled'] += 1
        subattributes_status[f"{subattribute['parent_name']} | {subattribute['name']}"] = subattribute
    logging.info(
        f"Template {template_name} subattributes: {status['enrolled']} cadastrados, {status['skipped']} pulados, {status['failed']} falharam, {status['parent_not_found']} órfãos")
    log_file = f"logs/{template_name}_subattributes_log.txt"
    with open(log_file, "w", encoding="utf-8") as f:
        for attr_name, attr in subattributes_status.items():
            f.write(f"{attr_name}: {attr['status']}\n")
    logging.debug(f"Log saved to {log_file}")
    return status

def fix_attribute_with_limits(client_name, environment):
    ws = get_lighthouse_client(client_name, environment)
    
    def has_matched_attribute(attributes, compared_attribute):
        count = 0
        for attribute in attributes:
            if attribute['name'] == compared_attribute['name']:
                count += 1
        
        if count == 2:
            return True
        return False

    
    templates = ws.get_templates()
    for template in templates:
        template_attributes = ws.get_template_attributes(template)['attributes']
        for attribute in template_attributes:
            # print(attribute)
            if "Limits" in [x['name'] for x in attribute['categories']]:
                logging.info(f"Template {templates[template]} atributo {attribute['name']}")
                if has_matched_attribute(template_attributes, attribute):
                    ws.delete_template_attribute(attribute['id'])


def pipeline(client_name, environment):
    ws = get_lighthouse_client(client_name, environment)

    logging.info(f"Buscando e processando dados para o cliente: {client_name}...")
    try:
        excel_templates = get_template_enrollment_data(client_name)
    except ValueError as e:
        logging.error(e)
        return

    unique_templates = excel_templates["Template"].unique()

    # 3. Cadastrar todas as categorias que não existem
    categories = ws.get_categories()
    all_categories = excel_templates['Categories'].dropna().unique()
    attributes_goup_id = find_attributes_group_id(ws)
    for category in all_categories:
        category = category.replace(";", "").strip()
        # get or create category
        category_id = find_category_id_by_name(categories, category)
        if not category_id:
            logging.info(f"Categoria {category} não encontrada. Cadastrando...")
            response = ws.post_category({'name': category, 'group_id': attributes_goup_id})
            if hasattr(response, 'status_code') and response.status_code == 201:
                logging.info(f"Categoria {category} cadastrada com sucesso")
                categories = ws.get_categories()  # atualiza lista de categorias
            else:
                logging.error(f"Erro ao cadastrar categoria {category}: {getattr(response, 'text', response)}")

    # 4. Processar cadastro de templates, atributos e subatributos
    enrolled_templates = ws.get_templates()
    summary_tracking = []
    for template_name in unique_templates:
        logging.info(f"Verificando template {template_name}")
        template_id = find_template_id_by_name(enrolled_templates, template_name)
        if not template_id:
            logging.info(f"Verificando template {template_name}. NÃO ENCONTRADO. Cadastrando...")
            response = ws.post_template({"name": template_name, "description": "", "categories": []})
            template_id = response.json()['id']
            logging.info(f"Template {template_name} cadastrado com sucesso")
        else:
            logging.info(f"Verificando template {template_name}. OK")

        # Remove linhas em que template + atributo + subatributo estejam duplicados
        # excel_templates = excel_templates.drop_duplicates(subset=['Template', 'attribute_name'])

        # enroll_default_attributes(ws, template_id, categories, template_name)
        enroll_default_subattributes(ws, template_id, categories, template_name)
        attr_status = enroll_attributes(ws, template_id, categories, excel_templates, template_name)
        subattr_status = enroll_subattributes(ws, template_id, categories, excel_templates, template_name)
        summary_tracking.append({
            'template_name': template_name,
            'attributes_enrolled': attr_status['enrolled'] if attr_status else 0,
            'attributes_skipped': attr_status['skipped'] if attr_status else 0,
            'attributes_failed': attr_status['failed'] if attr_status else 0,
            'subattributes_enrolled': subattr_status['enrolled'] if subattr_status else 0,
            'subattributes_skipped': subattr_status['skipped'] if subattr_status else 0,
            'subattributes_failed': subattr_status['failed'] if subattr_status else 0,
            'subattributes_parent_not_found': subattr_status['parent_not_found'] if subattr_status else 0
        })
        
    generate_templates_summary_report(summary_tracking, client_name, environment)

def generate_templates_summary_report(summary_tracking, client_name, environment):

    total_templates = len(summary_tracking)
    total_attr_enrolled = sum(t['attributes_enrolled'] for t in summary_tracking)
    total_attr_skipped = sum(t['attributes_skipped'] for t in summary_tracking)
    total_attr_failed = sum(t['attributes_failed'] for t in summary_tracking)
    total_subattr_enrolled = sum(t['subattributes_enrolled'] for t in summary_tracking)
    total_subattr_skipped = sum(t['subattributes_skipped'] for t in summary_tracking)
    total_subattr_failed = sum(t['subattributes_failed'] for t in summary_tracking)
    total_subattr_parent_not_found = sum(t['subattributes_parent_not_found'] for t in summary_tracking)

    logging.info("\n===== GLOBAL SUMMARY REPORT =====")
    logging.info(f"Templates processed: {total_templates}")
    logging.info(f"Attributes: {total_attr_enrolled} enrolled, {total_attr_skipped} skipped, {total_attr_failed} failed")
    logging.info(f"Subattributes: {total_subattr_enrolled} enrolled, {total_subattr_skipped} skipped, {total_subattr_failed} failed, {total_subattr_parent_not_found} parent not found")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"logs/templates_global_report_{client_name}_{environment}_{timestamp}.xlsx"
    df = pd.DataFrame(summary_tracking)
    summary_data = {
        'Metric': [
            'Templates processed',
            'Attributes enrolled', 'Attributes skipped', 'Attributes failed',
            'Subattributes enrolled', 'Subattributes skipped', 'Subattributes failed', 'Subattributes parent not found'
        ],
        'Count': [
            total_templates,
            total_attr_enrolled, total_attr_skipped, total_attr_failed,
            total_subattr_enrolled, total_subattr_skipped, total_subattr_failed, total_subattr_parent_not_found
        ]
    }
    summary_df = pd.DataFrame(summary_data)
    with pd.ExcelWriter(output_filename, engine='xlsxwriter') as writer:
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        df.to_excel(writer, sheet_name='Detailed_Report', index=False)
    logging.info(f"Global summary report saved to: {output_filename}")


if __name__ == "__main__":
    setup_logging("templates")
    args = parse_args()
    pipeline(args.client, args.environment)
