import pandas as pd
import numpy as np
import logging
from dictionaries import DICTIONARIES

def extract_raw_data(client_name=None):
    """
    Reads data from all spreadsheets defined in dictionaries.py.
    If client_name is provided, it only loads data for that specific client.
    Returns a single concatenated Pandas DataFrame.
    """
    all_dfs = []
    
    # If client_name is specified and exists, only process that one. Otherwise, process all.
    sources = {client_name: DICTIONARIES[client_name]} if client_name and client_name in DICTIONARIES else DICTIONARIES
    
    for source_name, entries in sources.items():
        for entry in entries:
            spreadsheet = entry.get("spreadsheet")
            tabs = entry.get("tabs", [])
            for sheet_name in tabs:
                logging.info(f"Lendo: source={source_name} spreadsheet={spreadsheet} sheet={sheet_name}")
                try:
                    df = pd.read_excel(spreadsheet, sheet_name=sheet_name, engine="openpyxl")
                    df['__source_spreadsheet'] = spreadsheet
                    df['__source_sheet'] = sheet_name
                    all_dfs.append(df)
                except Exception as e:
                    logging.error(f"Erro ao ler a aba '{sheet_name}' da planilha '{spreadsheet}': {e}")

    if not all_dfs:
        raise ValueError("Nenhuma planilha encontrada para processar. Verifique o dictionaries.py e o nome do cliente.")

    return pd.concat(all_dfs, ignore_index=True)


def normalize_attribute_key(attribute_name):
    """
    Normalizes attribute names for deduplication purposes.
    """
    if not isinstance(attribute_name, str):
        return attribute_name

    attribute_name = " ".join(attribute_name.strip().split())
    if '|' in attribute_name:
        parent_name, subattribute_name = attribute_name.split('|', 1)
        parent_name = " ".join(parent_name.strip().split())
        subattribute_name = " ".join(subattribute_name.strip().split())
        return f"{parent_name} | {subattribute_name}".lower()

    return attribute_name.lower()


def get_template_enrollment_data(client_name=None):
    """
    Returns a cleaned DataFrame formatted specifically for template, attribute, and subattribute enrollment.
    """
    df = extract_raw_data(client_name)

    # Replace all en dashes with hyphens
    df = df.replace('–', '-', regex=True)

    df = df.applymap(lambda x: " ".join(str(x).strip().split()) if isinstance(x, str) else x)

    # Fill NaNs where necessary before drop
    df['unit_of_measurement'] = df['unit_of_measurement'].fillna('')
    df['decimal_places'] = df['decimal_places'].fillna(2)
    df = df.replace({np.nan: None})

    # Drop lines where Template is not filled
    df = df[df['Template'].notnull()]
    
    # Identify type based on whether attribute_name contains a pipe
    df['type'] = df['attribute_name'].apply(
        lambda x: 'subattribute' if isinstance(x, str) and '|' in x else 'attribute'
    )

    # Remove logical duplicates within the same template
    df['Template_norm'] = df['Template'].apply(
        lambda x: " ".join(x.strip().split()).lower() if isinstance(x, str) else x
    )
    df['attribute_name_norm'] = df['attribute_name'].apply(normalize_attribute_key)
    
    before_dedup = len(df)
    df = df.drop_duplicates(subset=['Template_norm', 'type', 'attribute_name_norm'])
    removed_duplicates = before_dedup - len(df)
    
    if removed_duplicates > 0:
        logging.info(f"Removidas {removed_duplicates} linhas duplicadas de templates (Template + type + attribute_name)")
        
    df = df.drop(columns=['Template_norm', 'attribute_name_norm'])
    
    # Ensure Categories column exists
    if 'Categories' not in df.columns:
        df['Categories'] = None

    return df


def get_item_enrollment_data(client_name=None):
    """
    Returns separate DataFrames for items/attributes and subattributes, 
    cleaned and formatted for the items.py workflow.
    """
    df = extract_raw_data(client_name)

    # Replace en dashes with hyphens and trim strings
    df = df.replace('–', '-', regex=True)
    df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
    df = df.applymap(lambda x: " ".join(str(x).strip().split()) if isinstance(x, str) else x)

    # Drop rows missing critical linkage
    df = df.dropna(subset=['Template', 'Equipamento'])
    
    df['type'] = df['attribute_name'].apply(
        lambda x: 'subattribute' if isinstance(x, str) and '|' in x else 'attribute'
    )
    
    df['unit_of_measurement'] = df['unit_of_measurement'].fillna('')
    df['decimal_places'] = df['decimal_places'].fillna('2')
    df = df.replace({np.nan: None})

    # Split subattribute from attribute name
    df['subattribute_name'] = df['attribute_name'].apply(
        lambda x: x.split('|')[1].strip() if '|' in str(x) else ''
    )
    df['attribute_name'] = df['attribute_name'].apply(
        lambda x: x.split('|')[0].strip() if '|' in str(x) else str(x).strip()
    )

    # Normalize values (e.g. for Oil Analysis with multiple tags, taking the first)
    def normalize_value(x):
        if x is None or pd.isna(x):
            return None
        if isinstance(x, str):
            cleaned = x.split(',')[0].strip() if ',' in x else x.strip()
            return cleaned if cleaned != '' else None
        return x

    # Ensure Value column exists
    if 'Value' not in df.columns:
        df['Value'] = None

    df['Value'] = df['Value'].apply(normalize_value)
    
    # Ensure required columns are present
    required_cols = ['Template', 'Equipamento', 'attribute_name', 'subattribute_name', 'Value', 'unit_of_measurement', 'decimal_places']
    for col in required_cols:
        if col not in df.columns:
            df[col] = None
            
    df = df[required_cols]

    # Split into attributes and subattributes
    attributes_df = df[df['subattribute_name'] == '']
    subattributes_df = df[df['subattribute_name'] != ''].copy() # Explicit copy to avoid SettingWithCopyWarning

    # Convert subattribute values to numeric where possible, keeping NaNs for invalid ones
    subattributes_df['Value'] = pd.to_numeric(subattributes_df['Value'], errors='coerce')
    subattributes_df['Value'] = subattributes_df['Value'].apply(lambda x: None if pd.isna(x) else x)

    return df, attributes_df, subattributes_df
