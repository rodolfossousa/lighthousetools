"""
Lógica de sincronização: busca dados da API Lighthouse e grava no SQLite local.
Adaptado de export_to_sqlite.py e get_template_attribute_ids.py.
"""
from lighthouse import Lighthouse
from db_lighthouse import save_items_to_db, save_template_attributes_to_db


# --------------- sync items/atributos/generators ---------------

def find_root_candidates(ws: Lighthouse, search_term: str) -> list[tuple[str, str]]:
    items = ws.get_items(traverse=True)
    return [
        (iid, name) for iid, name in items.items()
        if search_term.lower() in name.lower()
    ]


def sync_items(ws: Lighthouse, root_id: str, vessel_name: str, environment: str, client: str, progress_callback=None):
    rows = _traverse_nodes(ws, root_id, progress_callback=progress_callback)
    save_items_to_db(rows, vessel_name, environment, client)
    return len(rows)


def _traverse_nodes(ws: Lighthouse, root_id: str, level: int = 0, parent_id: str = None, progress_callback=None):
    response = ws.get_subitems(root_id, traverse=False)

    if not isinstance(response, dict) or "subitems" not in response:
        return []

    subitems = response["subitems"]
    tree = []

    for i, subitem in enumerate(subitems):
        item_metadata = ws.get(f"{ws.root_url}/items/{subitem['id']}")
        subitem["template_name"] = item_metadata.get("template", {}).get("name", "")

        attributes = ws.get_item_attributes(subitem["id"]).get("attributes", [])
        generators = ws.get_item_generators(subitem["id"]).get("generators", [])

        is_leaf = not subitem.get("has_subitems", False)

        for gen in generators:
            tree.append([
                subitem["id"], subitem["name"], subitem["template_name"], "generator",
                gen["id"], gen["name"], gen.get("label", ""), gen.get("type", ""),
                "", gen.get("category", ""), is_leaf, parent_id, "",
            ])

        for attr in attributes:
            category = ""
            if attr.get("categories") and len(attr["categories"]):
                category = attr["categories"][0]["name"]
            tree.append([
                subitem["id"], subitem["name"], subitem["template_name"], "attribute",
                attr["id"], attr["name"], attr.get("value", ""),
                f'{attr.get("data_source", "")}_{attr.get("data_type", "")}',
                attr.get("reference", ""), category, is_leaf, parent_id, "",
            ])

            for sub_attr in attr.get("sub_attributes", []):
                sub_category = ""
                if sub_attr.get("categories") and len(sub_attr["categories"]):
                    sub_category = sub_attr["categories"][0]["name"]
                tree.append([
                    subitem["id"], subitem["name"], subitem["template_name"], "subattribute",
                    sub_attr["id"], sub_attr["name"], sub_attr.get("value", ""),
                    f'{sub_attr.get("data_source", "")}_{sub_attr.get("data_type", "")}',
                    sub_attr.get("reference", ""), sub_category, is_leaf, parent_id,
                    attr["id"],
                ])

        if progress_callback and level == 0:
            progress_callback(i + 1, len(subitems), subitem["name"])

        if subitem.get("has_subitems"):
            tree.extend(_traverse_nodes(ws, subitem["id"], level + 1, subitem["id"], progress_callback))

    return tree


def _format_categories(attr: dict) -> str:
    cats = attr.get("categories", [])
    if cats and isinstance(cats, list):
        return ", ".join(c.get("name", "") for c in cats if isinstance(c, dict))
    return ""


# --------------- sync template attributes ---------------

def sync_templates(ws: Lighthouse, environment: str, client: str, template_ids: list[str] = None, progress_callback=None):
    templates = ws.get_templates()

    if template_ids:
        templates = {k: v for k, v in templates.items() if k in template_ids}

    rows = []
    template_list = list(templates.items())

    for i, (tid, tname) in enumerate(template_list):
        if progress_callback:
            progress_callback(i + 1, len(template_list), tname)

        response = ws.get_template_attributes(tid)
        attrs = response.get("attributes", []) if isinstance(response, dict) else response

        for attr in attrs:
            attr_id = attr.get("id", "")
            categories = _format_categories(attr)

            rows.append({
                "template_id": tid,
                "template_name": tname,
                "id": attr_id,
                "name": attr.get("name", ""),
                "description": attr.get("description", ""),
                "data_source": attr.get("data_source", ""),
                "data_type": attr.get("data_type", ""),
                "unit_of_measurement": attr.get("unit_of_measurement", ""),
                "default_value": str(attr.get("default_value", "")),
                "categories": categories,
                "parent_id": attr.get("parent_id", ""),
            })

            if attr_id:
                try:
                    sub_resp = ws.get_template_attribute_subattributes(attr_id)
                    subs = sub_resp if isinstance(sub_resp, list) else sub_resp.get("attributes", [])
                    for sub in subs:
                        rows.append({
                            "template_id": tid,
                            "template_name": tname,
                            "id": sub.get("id", ""),
                            "name": sub.get("name", ""),
                            "description": sub.get("description", ""),
                            "data_source": sub.get("data_source", ""),
                            "data_type": sub.get("data_type", ""),
                            "unit_of_measurement": sub.get("unit_of_measurement", ""),
                            "default_value": str(sub.get("default_value", "")),
                            "categories": _format_categories(sub),
                            "parent_id": attr_id,
                        })
                except Exception:
                    pass

    save_template_attributes_to_db(rows, environment, client)
    return len(rows)
