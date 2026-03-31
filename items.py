"""
Código para fazer cadastro de items em um workspace específico
"""

import pandas as pd
import tqdm
import logging
from utils import traverse_attributes, fix_unit_of_measurement
from datetime import datetime
from data_processor import get_item_enrollment_data
from config import parse_args, get_lighthouse_client, setup_logging


def find_attribute_reference(attribute_name: str, attribute_dict: dict) -> str:
    key = attribute_name.strip().lower()
    if key in attribute_dict:
        return attribute_dict[key]
    else:
        return ''

def create_update_report(tracking_data: list, client_name, environment, ws_equipment_names: set = None, output_filename: str = None) -> None:
    """
    Create a comprehensive Excel report showing all attributes/subattributes
    with their update status and parent relationships.

    Args:
        tracking_data: List of dictionaries containing tracking information
        client_name: Name of the client
        environment: Environment name
        ws_equipment_names: Set of equipment names present in the workspace
        output_filename: Name of the output Excel file
    """
    if not output_filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"logs/update_report_{client_name}_{environment}_{timestamp}.xlsx"

    # Convert tracking data to DataFrame
    df = pd.DataFrame(tracking_data)

    # Add not_found_reason column for records not found in workspace
    if ws_equipment_names is not None:
        found_attributes = {
            (rec['equipment_name'], rec['attribute_name'])
            for rec in tracking_data
            if not rec['is_subattribute'] and rec['found_in_ws']
        }

        def get_not_found_reason(row):
            if row['found_in_ws']:
                return ''
            if row['equipment_name'] not in ws_equipment_names:
                return '[a] Equipamento ausente no workspace'
            if not row['is_subattribute']:
                return '[b] Atributo não encontrado no workspace'
            if (row['equipment_name'], row['attribute_name']) in found_attributes:
                return '[c] Subatributo não encontrado (atributo pai OK)'
            return '[d] Subatributo não encontrado (atributo pai também ausente)'

        df['not_found_reason'] = df.apply(get_not_found_reason, axis=1)

    # Sort by equipment, then by attributes, then by subattributes
    df = df.sort_values(['equipment_name', 'attribute_name', 'is_subattribute', 'subattribute_name'],
                       na_position='first')
    
    # Create summary statistics
    total_items = len(df)
    total_attributes = len(df[~df['is_subattribute']])
    total_subattributes = len(df[df['is_subattribute']])
    found_items = len(df[df['found_in_ws']])
    updated_items = len(df[df['was_updated']])
    skipped_empty_value = len(df[df['skipped_empty_value']])
    failed_updates = len(df[df['found_in_ws'] & ~df['was_updated'] & ~df['skipped_empty_value']])
    
    # Create summary sheet data
    summary_data = {
        'Metric': ['Total Items in Excel', 'Total Attributes', 'Total Subattributes', 
                  'Found in Workspace', 'Successfully Updated', 'Not Found', 'Found but Not Updated',
                  '    No value to update', '    Failed'],
        'Count': [total_items, total_attributes, total_subattributes, 
                 found_items, updated_items, total_items - found_items, found_items - updated_items,
                 skipped_empty_value, failed_updates],
        'Percentage': [100.0, 
                      (total_attributes / total_items * 100) if total_items > 0 else 0,
                      (total_subattributes / total_items * 100) if total_items > 0 else 0,
                      (found_items / total_items * 100) if total_items > 0 else 0,
                      (updated_items / total_items * 100) if total_items > 0 else 0,
                      ((total_items - found_items) / total_items * 100) if total_items > 0 else 0,
                      ((found_items - updated_items) / total_items * 100) if total_items > 0 else 0,
                      (skipped_empty_value / total_items * 100) if total_items > 0 else 0,
                      (failed_updates / total_items * 100) if total_items > 0 else 0]
    }
    summary_df = pd.DataFrame(summary_data)
    
    # Write to Excel with multiple sheets
    with pd.ExcelWriter(output_filename, engine='xlsxwriter') as writer:
        # Write summary sheet
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        # Write detailed data
        df.to_excel(writer, sheet_name='Detailed_Report', index=False)
        
        # Write filtered views
        not_found_df = df[~df['found_in_ws']]
        not_found_df.to_excel(writer, sheet_name='Not_Found_in_WS', index=False)
        
        found_not_updated_df = df[df['found_in_ws'] & ~df['was_updated']]
        found_not_updated_df.to_excel(writer, sheet_name='Found_Not_Updated', index=False)
        
        skipped_empty_df = df[df['skipped_empty_value']]
        skipped_empty_df.to_excel(writer, sheet_name='Skipped_Empty_Values', index=False)
        
        failed_updates_df = df[df['found_in_ws'] & ~df['was_updated'] & ~df['skipped_empty_value']]
        failed_updates_df.to_excel(writer, sheet_name='Failed_Updates', index=False)
        
        updated_df = df[df['was_updated']]
        updated_df.to_excel(writer, sheet_name='Successfully_Updated', index=False)
    
    logging.info(f"Update report saved to: {output_filename}")
    logging.info("Summary:")
    logging.info(f"  Total items in Excel: {total_items}")
    logging.info(f"  Attributes: {total_attributes}")
    logging.info(f"  Subattributes: {total_subattributes}")
    logging.info(f"  Found in workspace: {found_items} ({found_items/total_items*100:.1f}%)")
    logging.info(f"  Successfully updated: {updated_items} ({updated_items/total_items*100:.1f}%)")
    logging.info(f"  Not found: {total_items - found_items} ({(total_items-found_items)/total_items*100:.1f}%)")
    logging.info(f"  Found but not updated: {found_items - updated_items} ({(found_items-updated_items)/total_items*100:.1f}%)")
    logging.info(f"      No value to update: {skipped_empty_value} ({skipped_empty_value/total_items*100:.1f}%)")
    logging.info(f"      Failed: {failed_updates} ({failed_updates/total_items*100:.1f}%)")

def main(client_name, environment):
    setup_logging("items")
    logging.info(f"Buscando e processando dados para o cliente: {client_name}...")
    try:
        excel_templates, attributes, subattributes = get_item_enrollment_data(client_name)
    except ValueError as e:
        logging.error(e, exc_info=True)
        return



    # Initialize tracking data
    tracking_data = []
    
    # Initialize tracking data with all items from Excel (attributes and subattributes)
    logging.info("Initializing tracking data from Excel file...")
    
    # Add all attributes to tracking
    for _, row in attributes.iterrows():
        tracking_data.append({
            'equipment_name': row['asset_name'],
            'template_name': row['template_name'],
            'attribute_name': row['attribute_name'],
            'subattribute_name': None,
            'parent_attribute_name': None,
            'value_in_excel': row['value'],
            'is_subattribute': False,
            'found_in_ws': False,
            'was_updated': False,
            'skipped_empty_value': False,
            'update_error': None,
            'item_id': None,
            'attribute_id': None,
            'subattribute_id': None
        })
    
    # Add all subattributes to tracking
    for _, row in subattributes.iterrows():
        tracking_data.append({
            'equipment_name': row['asset_name'],
            'template_name': row['template_name'],
            'attribute_name': row['attribute_name'],
            'subattribute_name': row['subattribute_name'],
            'parent_attribute_name': row['attribute_name'],
            'value_in_excel': row['value'],
            'is_subattribute': True,
            'found_in_ws': False,
            'was_updated': False,
            'skipped_empty_value': False,
            'update_error': None,
            'item_id': None,
            'attribute_id': None,
            'subattribute_id': None
        })
    
    logging.info(f"Initialized tracking for {len(tracking_data)} items ({len(attributes)} attributes, {len(subattributes)} subattributes)")

    ws = get_lighthouse_client(client_name, environment)
    
    enrolled_items = ws.get_items()

    # get unique equipment names in excel_templates
    equipment_names = excel_templates['asset_name'].unique()
    
    # remove from enrolled_items any item that is not in equipment_names
    enrolled_items = {item_id: item_name for item_id, item_name in enrolled_items.items() if item_name in equipment_names}

    equipment_names_not_in_ws = set(equipment_names) - set(enrolled_items.values())
    if equipment_names_not_in_ws:
        logging.warning(f">>>>> {len(equipment_names_not_in_ws)} equipamento(s) da planilha não encontrados no workspace:")
        for name in sorted(equipment_names_not_in_ws):
            logging.warning(f"  Equipamento ausente no workspace: {name}")

    attributes_to_update = []
    subattributes_to_update = []
    total_updated_attributes = 0
    total_updated_subattributes = 0

    for item_id in enrolled_items:
        item_name = enrolled_items[item_id]

        item_attributes = ws.get_item_attributes(item_id)
        item_attributes = item_attributes.get('attributes', [])

        if not item_attributes:
            expected_count = sum(1 for r in tracking_data if r['equipment_name'] == item_name)
            logging.warning(
                f">>>>> {item_name}: encontrado no workspace mas sem atributos cadastrados "
                f"({expected_count} atributo(s)/subatributo(s) da planilha não poderão ser atualizados)"
            )
            continue
        
        for attribute in tqdm.tqdm(item_attributes, desc=f"Attributes ({item_name})"):

            # Use traverse_attributes to get all attributes and sub-attributes
            all_attributes = traverse_attributes(attribute)


            # Para cada atributo/subatributo, veja se ele está na planilha e atualize o valor
            for attr_record in all_attributes:

                equipment_name = item_name
                attribute_name = attr_record['attribute_name']
                attribute_id = attr_record['attribute_id']
                # attribute_type = attr_record['attribute_type']

                subattribute_name = attr_record.get('subattribute_name')
                # Verifica se é realmente um subatributo (não é NaN e não é vazio)
                is_subattribute = (subattribute_name is not None and 
                                not pd.isna(subattribute_name) and 
                                subattribute_name != '')
                
                is_manual_attribute = True if attr_record.get('attribute_data_source', False) == "Manual" else False
                
                if is_subattribute:
                    subattribute_id = attr_record.get('subattribute_id', False)
                
                # Find the corresponding tracking record
                tracking_record = None
                for track_rec in tracking_data:
                    if (track_rec['equipment_name'] == equipment_name and
                        track_rec['attribute_name'] == attribute_name and
                        track_rec['is_subattribute'] == is_subattribute):

                        if is_subattribute:
                            if track_rec['subattribute_name'] == subattribute_name:
                                tracking_record = track_rec
                                break
                        else:
                            if track_rec['subattribute_name'] is None:
                                tracking_record = track_rec
                                break
                
                # Update tracking record with workspace data
                if tracking_record:
                    tracking_record['found_in_ws'] = True
                    tracking_record['item_id'] = item_id
                    tracking_record['attribute_id'] = attribute_id
                    if is_subattribute:
                        tracking_record['subattribute_id'] = subattribute_id
                

                # Se for subatributo, procura na tabela de subatributos
                if is_subattribute:
                    row = subattributes[
                        (subattributes['asset_name'] == equipment_name) & 
                        (subattributes['attribute_name'] == attribute_name) & 
                        (subattributes['subattribute_name'] == subattribute_name)
                    ]
                # Se for atributo, procura na tabela de atributos
                else:
                    row = attributes[
                        (attributes['asset_name'] == equipment_name) & 
                        (attributes['attribute_name'] == attribute_name)
                    ]
                # Se não encontrar atributo ou subatributo na planilha, pular
                if row.size == 0:
                    continue
                
                # Fetch unit of measurement and decimal places
                unit_of_measurement = fix_unit_of_measurement(row.iloc[0].get('unit_of_measurement', ''))
                decimal_places = str(row.iloc[0].get('decimal_places', ''))

                # If attribute is manual or subattribute, prepare for manual update
                if is_subattribute or is_manual_attribute:
                    value = row.iloc[0]['value']
                    # V1 format stores all top-level attribute content in 'reference';
                    # fall back to it when value is empty and this is a manual (non-subattribute) attribute
                    if not is_subattribute and (value is None or pd.isna(value)):
                        value = row.iloc[0].get('reference')
                    manual_value = None if value is None or pd.isna(value) else str(value)

                    if manual_value is None and tracking_record:
                        tracking_record['skipped_empty_value'] = True

                    subattributes_to_update.append({
                        'id': subattribute_id if is_subattribute else attribute_id,
                        'value': manual_value
                    })

                # Se for atributo time series
                elif not is_subattribute and not is_manual_attribute:
                    reference = row.iloc[0]['reference']
                    attributes_to_update.append({
                        'id': attribute_id,
                        'unit_of_measurement': unit_of_measurement,
                        'engineering_unit': unit_of_measurement,
                        'reference': reference,
                        'decimal_places': decimal_places
                    })
                

        # After processing all attributes of the item, update them in batch
        if attributes_to_update:
            try:
                ws.update_attribute_batch(item_id, attributes_to_update)
                logging.info(f">>>>> Atualizado {item_name} - {len(attributes_to_update)} atributos ")
                
                # Mark as updated in tracking data
                for attr_update in attributes_to_update:
                    for track_rec in tracking_data:
                        if (track_rec['attribute_id'] == attr_update['id'] and 
                            not track_rec['is_subattribute']):
                            track_rec['was_updated'] = True
                            break
                
                total_updated_attributes += len(attributes_to_update)
            except Exception as e:
                logging.error(f"Erro ao atualizar atributos de {item_name}: {e}", exc_info=True)
                # Mark errors in tracking data
                for attr_update in attributes_to_update:
                    for track_rec in tracking_data:
                        if (track_rec['attribute_id'] == attr_update['id'] and 
                            not track_rec['is_subattribute']):
                            track_rec['update_error'] = str(e)
                            break
            finally:
                attributes_to_update = []  # Clear the list after updating
                
        if subattributes_to_update:
            try:
                result = ws.update_manual_attributes(item_id, subattributes_to_update)
                if result.status_code not in  [200, 201, 202]:
                    raise Exception(f"Failed to update subattributes: {result.text}")
                logging.info(f">>>>> Atualizado {item_name} - {len(subattributes_to_update)} subatributos/atributos manuais ")
                
                # Mark as updated in tracking data
                for subattr_update in subattributes_to_update:
                    for track_rec in tracking_data:
                        if (track_rec['subattribute_id'] == subattr_update['id'] and 
                            track_rec['is_subattribute']):
                            track_rec['was_updated'] = True
                            break
                
                total_updated_subattributes += len(subattributes_to_update)
            except Exception as e:
                logging.error(f">>>>> Erro ao atualizar subatributos de {item_name}: {str(e)}", exc_info=True)
                # Mark errors in tracking data
                for subattr_update in subattributes_to_update:
                    for track_rec in tracking_data:
                        if (track_rec['subattribute_id'] == subattr_update['id'] and 
                            track_rec['is_subattribute']):
                            track_rec['update_error'] = str(e)
                            break
            finally:
                subattributes_to_update = []  # Clear the list after updating

    # Surface attributes/subattributes that never matched anything in the workspace
    not_found_records = [rec for rec in tracking_data if not rec['found_in_ws']]
    if not_found_records:
        ws_equipment_names = set(enrolled_items.values())
        found_attributes = {
            (rec['equipment_name'], rec['attribute_name'])
            for rec in tracking_data
            if not rec['is_subattribute'] and rec['found_in_ws']
        }

        equip_not_in_ws = [r for r in not_found_records if r['equipment_name'] not in ws_equipment_names]
        equip_in_ws = [r for r in not_found_records if r['equipment_name'] in ws_equipment_names]

        attrs_not_found = [r for r in equip_in_ws if not r['is_subattribute']]

        subattrs_not_found = [r for r in equip_in_ws if r['is_subattribute']]
        subattrs_parent_found = [r for r in subattrs_not_found if (r['equipment_name'], r['attribute_name']) in found_attributes]
        subattrs_parent_not_found = [r for r in subattrs_not_found if (r['equipment_name'], r['attribute_name']) not in found_attributes]

        logging.warning(f">>>>> {len(not_found_records)} item(ns) não encontrado(s) no workspace:")

        if equip_not_in_ws:
            logging.warning(f"  [a] Equipamento ausente no workspace ({len(equip_not_in_ws)} registro(s)):")
            for rec in equip_not_in_ws:
                suffix = f" > Subatributo: {rec['subattribute_name']}" if rec['is_subattribute'] else ""
                logging.warning(f"    {rec['equipment_name']} | Atributo: {rec['attribute_name']}{suffix}")

        if attrs_not_found:
            logging.warning(f"  [b] Atributo não encontrado no workspace ({len(attrs_not_found)} registro(s)):")
            for rec in attrs_not_found:
                logging.warning(f"    {rec['equipment_name']} | Atributo: {rec['attribute_name']}")

        if subattrs_parent_found:
            logging.warning(f"  [c] Subatributo não encontrado (atributo pai OK) ({len(subattrs_parent_found)} registro(s)):")
            for rec in subattrs_parent_found:
                logging.warning(f"    {rec['equipment_name']} | Atributo: {rec['attribute_name']} | Subatributo: {rec['subattribute_name']}")

        if subattrs_parent_not_found:
            logging.warning(f"  [d] Subatributo não encontrado (atributo pai também ausente) ({len(subattrs_parent_not_found)} registro(s)):")
            for rec in subattrs_parent_not_found:
                logging.warning(f"    {rec['equipment_name']} | Atributo: {rec['attribute_name']} | Subatributo: {rec['subattribute_name']}")
    else:
        logging.info("Todos os atributos e subatributos foram encontrados no workspace.")

    logging.info(f"Total de atributos atualizados: {total_updated_attributes}")
    logging.info(f"Total de subatributos atualizados: {total_updated_subattributes}")
    
    # Generate comprehensive update report
    create_update_report(tracking_data, client_name, environment, ws_equipment_names=set(enrolled_items.values()))

if __name__ == "__main__":
    args = parse_args()
    main(args.client, args.environment)

