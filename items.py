"""
Código para fazer cadastro de items em um workspace específico
"""

import pandas as pd
from lighthouse import Lighthouse, clients
import sys
import json
import tqdm
import numpy as np
from utils import traverse_attributes
from datetime import datetime
from templates import fix_unit_of_measurement 
from dictionaries import DICTIONARIES
from data_processor import get_item_enrollment_data

if len(sys.argv) < 1:
    print("Uso: python -m enroll_templates.templates <CLIENT_NAME> [ENVIRONMENT]")
    sys.exit(1)

CLIENT_NAME = sys.argv[1] if len(sys.argv) > 1 else ""
ENVIRONMENT = sys.argv[2] if len(sys.argv) > 2 else "dev"


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def find_attribute_reference(attribute_name: str, attribute_dict: dict) -> str:
    key = attribute_name.strip().lower()
    if key in attribute_dict:
        return attribute_dict[key]
    else:
        return ''

def create_update_report(tracking_data: list, output_filename: str = None) -> None:
    """
    Create a comprehensive Excel report showing all attributes/subattributes
    with their update status and parent relationships.
    
    Args:
        tracking_data: List of dictionaries containing tracking information
        output_filename: Name of the output Excel file
    """
    if not output_filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"logs/update_report_{CLIENT_NAME}_{ENVIRONMENT}_{timestamp}.xlsx"
    
    # Convert tracking data to DataFrame
    df = pd.DataFrame(tracking_data)
    
    # Sort by equipment, then by attributes, then by subattributes
    df = df.sort_values(['equipment_name', 'attribute_name', 'is_subattribute', 'subattribute_name'], 
                       na_position='first')
    
    # Create summary statistics
    total_items = len(df)
    total_attributes = len(df[df['is_subattribute'] == False])
    total_subattributes = len(df[df['is_subattribute'] == True])
    found_items = len(df[df['found_in_ws'] == True])
    updated_items = len(df[df['was_updated'] == True])
    skipped_empty_value = len(df[df['skipped_empty_value'] == True])
    failed_updates = len(df[(df['found_in_ws'] == True) & (df['was_updated'] == False) & (df['skipped_empty_value'] == False)])
    
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
        not_found_df = df[df['found_in_ws'] == False]
        not_found_df.to_excel(writer, sheet_name='Not_Found_in_WS', index=False)
        
        found_not_updated_df = df[(df['found_in_ws'] == True) & (df['was_updated'] == False)]
        found_not_updated_df.to_excel(writer, sheet_name='Found_Not_Updated', index=False)
        
        skipped_empty_df = df[df['skipped_empty_value'] == True]
        skipped_empty_df.to_excel(writer, sheet_name='Skipped_Empty_Values', index=False)
        
        failed_updates_df = df[(df['found_in_ws'] == True) & (df['was_updated'] == False) & (df['skipped_empty_value'] == False)]
        failed_updates_df.to_excel(writer, sheet_name='Failed_Updates', index=False)
        
        updated_df = df[df['was_updated'] == True]
        updated_df.to_excel(writer, sheet_name='Successfully_Updated', index=False)
    
    print(f"{bcolors.HEADER}Update report saved to: {output_filename}{bcolors.ENDC}")
    print(f"{bcolors.OKGREEN}Summary:{bcolors.ENDC}")
    print(f"  Total items in Excel: {total_items}")
    print(f"  Attributes: {total_attributes}")
    print(f"  Subattributes: {total_subattributes}")
    print(f"  Found in workspace: {found_items} ({found_items/total_items*100:.1f}%)")
    print(f"  Successfully updated: {updated_items} ({updated_items/total_items*100:.1f}%)")
    print(f"  Not found: {total_items - found_items} ({(total_items-found_items)/total_items*100:.1f}%)")
    print(f"  Found but not updated: {found_items - updated_items} ({(found_items-updated_items)/total_items*100:.1f}%)")
    print(f"      No value to update: {skipped_empty_value} ({skipped_empty_value/total_items*100:.1f}%)")
    print(f"      Failed: {failed_updates} ({failed_updates/total_items*100:.1f}%)")

def main():
    print(f"Buscando e processando dados para o cliente: {CLIENT_NAME}...")
    try:
        excel_templates, attributes, subattributes = get_item_enrollment_data(CLIENT_NAME)
    except ValueError as e:
        print(e)
        return



        # Initialize tracking data
        tracking_data = []
        
        # Initialize tracking data with all items from Excel (attributes and subattributes)
        print(f"{bcolors.HEADER}Initializing tracking data from Excel file...{bcolors.ENDC}")
        
        # Add all attributes to tracking
        for _, row in attributes.iterrows():
            tracking_data.append({
                'equipment_name': row['Equipamento'],
                'template_name': row['Template'],
                'attribute_name': row['attribute_name'],
                'subattribute_name': None,
                'parent_attribute_name': None,
                'value_in_excel': row['Value'],
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
                'equipment_name': row['Equipamento'],
                'template_name': row['Template'],
                'attribute_name': row['attribute_name'],
                'subattribute_name': row['subattribute_name'],
                'parent_attribute_name': row['attribute_name'],
                'value_in_excel': row['Value'],
                'is_subattribute': True,
                'found_in_ws': False,
                'was_updated': False,
                'skipped_empty_value': False,
                'update_error': None,
                'item_id': None,
                'attribute_id': None,
                'subattribute_id': None
            })
        
        print(f"{bcolors.OKBLUE}Initialized tracking for {len(tracking_data)} items ({len(attributes)} attributes, {len(subattributes)} subattributes){bcolors.ENDC}")

        ws = Lighthouse(api_key=clients[ENVIRONMENT][CLIENT_NAME]["api_key"],
                        env=ENVIRONMENT,
                        workspace_id=clients[ENVIRONMENT][CLIENT_NAME]["workspace_id"],
                        url=clients[ENVIRONMENT][CLIENT_NAME]["url"])
        
        enrolled_items = ws.get_items()

        # get unique equipment names in excel_templates
        equipment_names = excel_templates['Equipamento'].unique()
        
        # remove from enrolled_items any item that is not in equipment_names
        enrolled_items = {item_id: item_name for item_id, item_name in enrolled_items.items() if item_name in equipment_names}

        attributes_to_update = []
        subattributes_to_update = []
        total_updated_attributes = 0
        total_updated_subattributes = 0

        for item_id in enrolled_items:
            item_name = enrolled_items[item_id]

            item_attributes = ws.get_item_attributes(item_id)
            item_attributes = item_attributes.get('attributes', [])

            if not item_attributes:
                print(f"{bcolors.WARNING}>>>>> Nenhum atributo encontrado para o item {item_name} (ID: {item_id}){bcolors.ENDC}")
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
                            (subattributes['Equipamento'] == equipment_name) & 
                            (subattributes['attribute_name'] == attribute_name) & 
                            (subattributes['subattribute_name'] == subattribute_name)
                        ]
                    # Se for atributo, procura na tabela de atributos
                    else:
                        row = attributes[
                            (attributes['Equipamento'] == equipment_name) & 
                            (attributes['attribute_name'] == attribute_name)
                        ]
                    # Se não encontrar atributo ou subatributo na planilha, pular
                    if row.size == 0:
                        continue
                    
                    value = row.iloc[0]['Value']
                    unit_of_measurement = fix_unit_of_measurement(row.iloc[0].get('unit_of_measurement', ''))
                    decimal_places = str(row.iloc[0].get('decimal_places', ''))


                    # If attribute is manual or subattribute, prepare for manual update
                    if is_subattribute or is_manual_attribute:
                        manual_value = None if value is None or pd.isna(value) else str(value)

                        # print("\n>", subattribute_id if is_subattribute else attribute_id, value)
                        subattributes_to_update.append({
                            'id': subattribute_id if is_subattribute else attribute_id,
                            'value': manual_value
                        })

                    # Se for atributo
                    elif not is_subattribute and not is_manual_attribute:
                        attributes_to_update.append({
                            'id': attribute_id,
                            'unit_of_measurement': unit_of_measurement,
                            'engineering_unit': unit_of_measurement,
                            'reference': value,
                            'decimal_places': decimal_places
                        })
                    

            # After processing all attributes of the item, update them in batch
            if attributes_to_update:
                try:
                    ws.update_attribute_batch(item_id, attributes_to_update)
                    tqdm.tqdm.write(f"{bcolors.OKGREEN}>>>>> Atualizado {item_name} - {len(attributes_to_update)} atributos {bcolors.ENDC}")
                    
                    # Mark as updated in tracking data
                    for attr_update in attributes_to_update:
                        for track_rec in tracking_data:
                            if (track_rec['attribute_id'] == attr_update['id'] and 
                                not track_rec['is_subattribute']):
                                track_rec['was_updated'] = True
                                break
                    
                    total_updated_attributes += len(attributes_to_update)
                except Exception as e:
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
                    tqdm.tqdm.write(f"{bcolors.OKBLUE}>>>>> Atualizado {item_name} - {len(subattributes_to_update)} subatributos/atributos manuais {bcolors.ENDC}")
                    
                    # Mark as updated in tracking data
                    for subattr_update in subattributes_to_update:
                        for track_rec in tracking_data:
                            if (track_rec['subattribute_id'] == subattr_update['id'] and 
                                track_rec['is_subattribute']):
                                track_rec['was_updated'] = True
                                break
                    
                    total_updated_subattributes += len(subattributes_to_update)
                except Exception as e:
                    tqdm.tqdm.write(f"{bcolors.FAIL}>>>>> Erro ao atualizar subatributos de {item_name}: {str(e)}{bcolors.ENDC}")
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
            tqdm.tqdm.write(f"{bcolors.WARNING}>>>>> Atributos/Subatributos não encontrados no workspace:{bcolors.ENDC}")
            for rec in not_found_records:
                subattr_suffix = f" | Subatributo: {rec['subattribute_name']}" if rec['is_subattribute'] else ""
                tqdm.tqdm.write(
                    f"  Equipamento: {rec['equipment_name']} | Template: {rec['template_name']} | "
                    f"Atributo: {rec['attribute_name']}{subattr_suffix}"
                )
        else:
            tqdm.tqdm.write(f"{bcolors.OKGREEN}Todos os atributos e subatributos foram encontrados no workspace.{bcolors.ENDC}")

        tqdm.tqdm.write(f"{bcolors.HEADER}Total de atributos atualizados: {total_updated_attributes}{bcolors.ENDC}")
        tqdm.tqdm.write(f"{bcolors.HEADER}Total de subatributos atualizados: {total_updated_subattributes}{bcolors.ENDC}")
        
        # Generate comprehensive update report
        create_update_report(tracking_data)

if __name__ == "__main__":
    main()

