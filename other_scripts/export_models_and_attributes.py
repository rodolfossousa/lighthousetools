

import pandas as pd
from lighthouse import connect
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import traceback

client_name = "prio"
ws = connect(client_name, 'prod', True)
ROOT_NODE = "416dd47d-5a5b-4557-90f7-683db7bb4445"  # nó raiz PRIO
# ROOT_NODE = "a5312cf5-022d-4821-8631-112b2e875b44"  # nó raiz petroreconcavo
# ROOT_NODE = "1cc8ee3a-9eb0-4219-b1f5-59ac3d1f8cdb"  # nó raiz MODEC do Brasil
# ROOT_NODE = "2e512cfd-609d-48df-bc87-573ce6c2ef48"  # nó raiz BACALHAU
# ROOT_NODE = "4a5468c5-990e-49d9-afd4-e316e419aebd" # JIRAU - nó raiz
# ROOT_NODE = "e9df90a5-84b2-4ce4-9e47-e8282a781616" # TAG



def safe_api_call(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except Exception as e:
        print(f"Erro ao chamar {func.__name__} para args={args}, kwargs={kwargs}: {e}")
        traceback.print_exc()
        return None

def fetch_subitem_data(subitem, root_id):
    tree = []
    try:
        item_metadata = safe_api_call(ws.get, f"{ws.root_url}/items/{subitem['id']}")
        if not item_metadata or 'template' not in item_metadata:
            print(f"[WARN] Falha ao obter metadados do item {subitem['id']}")
            subitem['template_name'] = ''
        else:
            subitem['template_name'] = item_metadata['template']['name']
        is_leaf = not subitem["has_subitems"]

        with ThreadPoolExecutor(max_workers=4) as executor:
            future_generators = executor.submit(safe_api_call, ws.get_item_generators, subitem["id"])
            future_attributes = executor.submit(safe_api_call, ws.get_item_attributes, subitem["id"])
            generators = future_generators.result() or {"generators": []}
            attributes_resp = future_attributes.result() or {"attributes": []}
            attributes = attributes_resp.get("attributes", [])

        for generator in generators.get('generators', []):
            categories = generator.get("categories", "")
            if not categories:
                categories = ""
            tree.append([
                subitem["id"],
                subitem["name"],
                subitem['template_name'],
                "generator",
                generator.get("id", ""),
                generator.get("name", ""),
                "",
                generator.get("label", ""),
                generator.get("type", ""),
                "",
                categories,
                is_leaf,
                root_id,
                ""
            ])

        for attribute in attributes:
            attribute_name = attribute.get("name", "")
            categories = attribute.get("categories", "")
            if not categories:
                categories = ""
            tree.append([
                subitem["id"], subitem["name"], subitem['template_name'], "attribute", attribute.get("id", ""), attribute_name, "",
                attribute.get("value", ""), f'{attribute.get("data_source", "")}_{attribute.get("data_type", "")}', attribute.get("reference", ""), categories, is_leaf, root_id, attribute.get("unit_of_measurement", "")
            ])
            for subattribute in attribute.get("sub_attributes", []):
                subattribute_name = subattribute.get("name", "")
                categories = subattribute.get("categories", "")
                if not categories:
                    categories = ""
                tree.append([
                    subitem["id"], subitem["name"], subitem['template_name'], "subattribute", subattribute.get("id", ""), attribute_name, subattribute_name,
                    subattribute.get("value", ""), f'{subattribute.get("data_source", "")}_{subattribute.get("data_type", "")}', subattribute.get("reference", ""), categories, is_leaf, root_id, subattribute.get("unit_of_measurement", "")
                ])
    except Exception as e:
        print(f"[ERRO] Falha ao processar subitem {subitem.get('id', '')}: {e}")
        traceback.print_exc()
    return tree, subitem


def traverse_nodes(root_id, level=0, save_every=1000, temp_path="progress_temp.parquet"):
    subitems = safe_api_call(ws.get_subitems, root_id, traverse=False)
    if not subitems or "subitems" not in subitems:
        print(f"[WARN] Falha ao obter subitens de {root_id}")
        return []
    subitems = subitems["subitems"]
    tree = []
    iterator = tqdm(subitems, desc=f"Level {level} - Subitems", leave=True) if level == 0 else subitems

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(fetch_subitem_data, subitem, root_id) for subitem in iterator]
        for future in as_completed(futures):
            sub_tree, subitem = future.result()
            tree.extend(sub_tree)
            # Salvamento incremental
            if len(tree) % save_every == 0:
                try:
                    pd.DataFrame(tree).to_parquet(temp_path, index=False)
                    print(f"[INFO] Progresso salvo em {temp_path} ({len(tree)} linhas)")
                except Exception as e:
                    print(f"[ERRO] Falha ao salvar progresso: {e}")
            if subitem.get("has_subitems"):
                tree.extend(traverse_nodes(subitem["id"], level + 1, save_every, temp_path))
    return tree



def main():
    result = traverse_nodes(ROOT_NODE)

    columns = [
        "id", "name", "template_name", "type", "id_attribute",  "name_attribute", "name_subattribute", "value", "specification", "reference", "category", "is_leaf", "parent_id", "unit_of_measurement"
    ]
    df = pd.DataFrame(result, columns=columns)
    now = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"models_and_attributes_{client_name}_{now}.xlsx"
    df.to_excel(output_path, index=False)
    print(f"Data saved to {output_path}")
    # Remove arquivo temporário ao final
    import os
    if os.path.exists("progress_temp.parquet"):
        os.remove("progress_temp.parquet")


if __name__ == "__main__":
    main()
