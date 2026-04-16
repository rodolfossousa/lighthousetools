from lighthouse import connect
import pandas as pd

client_name = "prio"
environment = "prod"
ws = connect(client_name, environment, debug=False)


# read template attributes from csv
template_attributes = pd.read_csv('template_attributes.csv', sep=';')

template_attribute_ids = template_attributes['id'].tolist()


for template_attribute_id in template_attribute_ids:
    print(f"Deleting template attribute with id: {template_attribute_id}")
    response = ws.delete_template_attribute(template_attribute_id)
    if response.status_code in [204, 200]:
        print(f"Successfully deleted template attribute with id: {template_attribute_id}")
    else:
        print(f"Failed to delete template attribute with id: {template_attribute_id}. Status code: {response.status_code}, Response: {response.text}")
