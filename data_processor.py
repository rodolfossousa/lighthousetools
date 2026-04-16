import pandas as pd
import numpy as np
import logging
from dictionaries import DICTIONARIES
from utils import fix_unit_of_measurement

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

def clean_and_standardize_data(df):
    """
    Applies global cleaning and standardization rules to the raw DataFrame,
    normalizing both V1 and V2 data dictionaries into a single internal schema.
    """
    # Replace en dashes with hyphens
    df = df.replace('–', '-', regex=True)

    # Trim strings and remove double spaces
    df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
    df = df.map(lambda x: " ".join(str(x).strip().split()) if isinstance(x, str) else x)

    # Detect Schema Version
    is_v2 = 'asset_name' in df.columns and 'template' in df.columns
    
    if is_v2:
        # V2 Mapping
        df = df.rename(columns={
            'template': 'template_name',
            'type': 'data_type'
        })
        
        # Ensure required columns exist for V2
        required_cols_v2 = ['parent_asset_name', 'subattribute_name', 'reference', 'value', 'unit_of_measurement', 'decimal_places', 'categories']
        for col in required_cols_v2:
            if col not in df.columns:
                df[col] = None
                
        # Fill subattribute empty strings if None
        df['subattribute_name'] = df['subattribute_name'].fillna('')
        
        # Calculate attribute level based on subattribute_name
        df['attribute_level'] = df['subattribute_name'].apply(
            lambda x: 'subattribute' if str(x).strip() != '' else 'attribute'
        )
        
    else:
        # V1 Mapping
        df = df.rename(columns={
            'Template': 'template_name',
            'Equipamento': 'asset_name',
            'Categories': 'categories'
        })
        
        df['parent_asset_name'] = None
        
        # Split parent and subattribute names explicitly
        df['subattribute_name'] = df['attribute_name'].apply(
            lambda x: str(x).split('|')[1].strip() if isinstance(x, str) and '|' in x else ''
        )
        df['attribute_name'] = df['attribute_name'].apply(
            lambda x: str(x).split('|')[0].strip() if isinstance(x, str) and '|' in x else (str(x).strip() if x is not None else None)
        )
        
        # Identify attribute level
        df['attribute_level'] = df['subattribute_name'].apply(
            lambda x: 'subattribute' if str(x).strip() != '' else 'attribute'
        )

        # In V1, 'Value' column holds 'reference' for attributes and 'value' for subattributes
        if 'Value' not in df.columns:
            df['Value'] = None
            
        df['reference'] = df.apply(lambda row: row['Value'] if row['attribute_level'] == 'attribute' else None, axis=1)
        df['value'] = df.apply(lambda row: row['Value'] if row['attribute_level'] == 'subattribute' else None, axis=1)
        
        # Infer data_type for V1
        df['data_type'] = df['attribute_level'].apply(
            lambda x: 'Time Series Float' if x == 'attribute' else 'Manual Float'
        )

        # Ensure required cols for V1 mapping
        for col in ['unit_of_measurement', 'decimal_places']:
            if col not in df.columns:
                df[col] = None

    # Handle NaNs and defaults for specific columns
    df['unit_of_measurement'] = df['unit_of_measurement'].fillna('')
    df['unit_of_measurement'] = df['unit_of_measurement'].apply(fix_unit_of_measurement)
    
    df['decimal_places'] = df['decimal_places'].fillna(2)
    df = df.replace({np.nan: None})

    # Ensure internal schema is consistent
    final_cols = ['template_name', 'asset_name', 'parent_asset_name', 'attribute_name', 'subattribute_name', 'attribute_level', 'reference', 'value', 'unit_of_measurement', 'decimal_places', 'categories', 'data_type']
    
    # Drop any extra columns not in the final schema to keep it clean
    for col in df.columns:
        if col not in final_cols and col not in ['__source_spreadsheet', '__source_sheet']:
            df = df.drop(columns=[col])

    return df

def validate_data(df):
    """
    Validates data and logs critical issues.
    """
    # Check for missing templates
    missing_templates = df['template_name'].isnull()
    if missing_templates.any():
        num_missing = missing_templates.sum()
        logging.warning(f"Foram encontradas {num_missing} linhas sem nome de 'template'. Estas linhas serão ignoradas.")
    
    # Return valid subset
    return df[df['template_name'].notnull()].copy()

def ingest_pipeline(client_name=None):
    """
    Main ingestion pipeline: Extract, Transform, Validate.
    Returns a clean, validated DataFrame ready for operations.
    """
    logging.info(f"Iniciando pipeline de ingestão para o cliente: {client_name or 'Todos'}")
    raw_df = extract_raw_data(client_name)
    clean_df = clean_and_standardize_data(raw_df)
    valid_df = validate_data(clean_df)
    logging.info("Pipeline de ingestão concluído com sucesso.")
    return valid_df

def get_template_enrollment_data(client_name=None):
    """
    Returns a cleaned DataFrame formatted specifically for template enrollment.
    """
    df = ingest_pipeline(client_name)

    # Remove logical duplicates within the same template.
    # NOTE: subattribute_name_norm must be included because clean_and_standardize_data
    # splits "Parent | Child" into separate columns before this point, so attribute_name
    # only contains the parent name for subattributes — without subattribute_name_norm
    # all subattributes of the same parent would be treated as duplicates.
    df['Template_norm'] = df['template_name'].apply(
        lambda x: " ".join(x.strip().split()).lower() if isinstance(x, str) else x
    )
    df['attribute_name_norm'] = df['attribute_name'].apply(normalize_attribute_key)
    df['subattribute_name_norm'] = df['subattribute_name'].apply(
        lambda x: " ".join(x.strip().split()).lower() if isinstance(x, str) else ''
    )

    before_dedup = len(df)
    df = df.drop_duplicates(subset=['Template_norm', 'attribute_level', 'attribute_name_norm', 'subattribute_name_norm'])
    removed_duplicates = before_dedup - len(df)

    if removed_duplicates > 0:
        logging.info(f"Removidas {removed_duplicates} linhas duplicadas de templates (Template + attribute_level + attribute_name + subattribute_name)")

    df = df.drop(columns=['Template_norm', 'attribute_name_norm', 'subattribute_name_norm'])
    
    return df

def get_item_enrollment_data(client_name=None):
    """
    Returns separate DataFrames for items/attributes and subattributes, 
    cleaned and formatted for the items.py workflow.
    """
    df = ingest_pipeline(client_name)

    # Drop rows missing critical linkage for items
    df = df.dropna(subset=['asset_name'])

    # Normalize values for references and values
    def normalize_val(x):
        if x is None or pd.isna(x):
            return None
        if isinstance(x, str):
            cleaned = x.split(',')[0].strip() if ',' in x else x.strip()
            return cleaned if cleaned != '' else None
        return x

    df['reference'] = df['reference'].apply(normalize_val)
    df['value'] = df['value'].apply(normalize_val)

    # Ensure required columns are present in the final output
    required_cols = ['template_name', 'asset_name', 'attribute_name', 'subattribute_name', 'reference', 'value', 'unit_of_measurement', 'decimal_places', 'data_type']
    df = df[required_cols]

    # Split into attributes and subattributes
    attributes_df = df[df['subattribute_name'] == '']
    subattributes_df = df[df['subattribute_name'] != ''].copy() # Explicit copy to avoid SettingWithCopyWarning

    # Convert subattribute values to numeric where possible, keeping NaNs for invalid ones
    subattributes_df['value'] = pd.to_numeric(subattributes_df['value'], errors='coerce')
    subattributes_df['value'] = subattributes_df['value'].apply(lambda x: None if pd.isna(x) else x)

    return df, attributes_df, subattributes_df
