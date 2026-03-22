import numpy as np

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


def traverse_attributes(attribute, parent_attribute_id=None, parent_attribute_name=None):
    """
    Traverse the attribute tree recursively and return a list of all attributes and sub-attributes
    
    Expected format:
    {'id': 'eadb3442-2a5d-4a7c-899a-634c4a9e9f5b', 'name': 'Health Score Method', 'categories': [], 
     'template_attribute_id': 'de8a4544-7cae-4d85-acf2-292dea539b07', 'data_source': 'Manual', 
     'data_type': 'Text', 'sub_attributes': [], 'histoseries': False, 
     'created_at': '2025-01-07T21:31:25.878030Z', 'updated_at': None, 'value': 'Average'}
    
    For root attributes: creates one line with attribute data
    For sub-attributes: creates one line with parent attribute data + sub-attribute data in subattribute_ columns
    """
    attributes_list = []
    
    if not isinstance(attribute, dict):
        return attributes_list
    
    
    if parent_attribute_id is None:
        # This is a root attribute - create a line for the attribute itself
        attribute_record = {
            'item_id': np.nan,  # Will be filled later
            'item_name': np.nan,  # Will be filled later
            'attribute_id': attribute.get('id', np.nan),
            'attribute_name': attribute.get('name', np.nan),
            'attribute_template_attribute_id': attribute.get('template_attribute_id', np.nan),
            'attribute_data_source': attribute.get('data_source', np.nan),
            'attribute_data_type': attribute.get('data_type', np.nan),
            'attribute_histoseries': attribute.get('histoseries', np.nan),
            'attribute_created_at': attribute.get('created_at', np.nan),
            'attribute_updated_at': attribute.get('updated_at', np.nan),
            'attribute_reference': attribute.get('reference', np.nan),
            'attribute_value': attribute.get('value', np.nan),
            'subattribute_id': np.nan,
            'subattribute_name': np.nan,
            'subattribute_template_attribute_id': np.nan,
            'subattribute_data_source': np.nan,
            'subattribute_data_type': np.nan,
            'subattribute_histoseries': np.nan,
            'subattribute_created_at': np.nan,
            'subattribute_updated_at': np.nan,
            'subattribute_value': np.nan,
            'is_subattribute': False
        }
        attributes_list.append(attribute_record)
        
        # Store current attribute info for children
        current_attribute_id = attribute.get('id')
        current_attribute_name = attribute.get('name')
    else:
        # This is a sub-attribute - create a line with parent info + sub-attribute info
        subattribute_record = {
            'item_id': np.nan,  # Will be filled later
            'item_name': np.nan,  # Will be filled later
            'attribute_id': parent_attribute_id,
            'attribute_name': parent_attribute_name,
            'attribute_template_attribute_id': np.nan,  # Parent data not passed down
            'attribute_data_source': np.nan,
            'attribute_data_type': np.nan,
            'attribute_histoseries': np.nan,
            'attribute_created_at': np.nan,
            'attribute_updated_at': np.nan,
            'attribute_reference': np.nan,
            'attribute_value': np.nan,
            'subattribute_id': attribute.get('id', np.nan),
            'subattribute_name': attribute.get('name', np.nan),
            'subattribute_template_attribute_id': attribute.get('template_attribute_id', np.nan),
            'subattribute_data_source': attribute.get('data_source', np.nan),
            'subattribute_data_type': attribute.get('data_type', np.nan),
            'subattribute_histoseries': attribute.get('histoseries', np.nan),
            'subattribute_created_at': attribute.get('created_at', np.nan),
            'subattribute_updated_at': attribute.get('updated_at', np.nan),
            'subattribute_value': attribute.get('value', np.nan),
            'is_subattribute': True
        }
        attributes_list.append(subattribute_record)
        
        # For sub-attributes, use the parent info for further nesting
        current_attribute_id = parent_attribute_id
        current_attribute_name = parent_attribute_name
    
    # Recursively process sub-attributes
    sub_attributes = attribute.get('sub_attributes', [])
    if sub_attributes and isinstance(sub_attributes, list):
        for sub_attribute in sub_attributes:
            attributes_list.extend(traverse_attributes(sub_attribute, current_attribute_id, current_attribute_name))
    
    return attributes_list