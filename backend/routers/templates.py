from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user
from connections import get_connection, connect_environment
from db_lighthouse import get_template_list, get_template_attributes_from_db

router = APIRouter()


class CreateTemplateRequest(BaseModel):
    name: str
    description: str = ""
    attributes: list[dict]
    environment: str
    client_name: str


class CopyAnalyzeRequest(BaseModel):
    template_ids: list[str]
    source_environment: str
    source_client: str
    target_environment: str
    target_client: str


class CopyExecuteRequest(BaseModel):
    templates: list[dict]
    source_environment: str
    source_client: str
    target_environment: str
    target_client: str


def _get_or_connect(user_id: int, environment: str, client_name: str):
    ws = get_connection(user_id, environment, client_name)
    if not ws:
        ws = connect_environment(user_id, environment, client_name)
    return ws


@router.get("")
async def list_templates(
    environment: str = None, client_name: str = None,
    _: dict = Depends(get_current_user),
):
    return get_template_list(environment, client_name) if environment and client_name else []


@router.get("/attributes")
async def template_attributes(
    environment: str = None, client_name: str = None,
    _: dict = Depends(get_current_user),
):
    return get_template_attributes_from_db(environment=environment, client=client_name)


@router.post("")
async def create_template(body: CreateTemplateRequest, user: dict = Depends(get_current_user)):
    ws = get_connection(user["id"], body.environment, body.client_name)
    if not ws:
        raise HTTPException(status_code=400, detail="Ambiente não conectado.")
    template_content = {
        "name": body.name,
        "description": body.description,
        "attributes": body.attributes,
    }
    response = ws.post_template(template_content)
    if hasattr(response, "status_code") and response.status_code not in (200, 201):
        raise HTTPException(status_code=response.status_code, detail=getattr(response, "text", "Erro ao criar template."))
    return {"message": "Template criado.", "response": response.json() if hasattr(response, "json") else response}


@router.get("/source-templates")
async def list_source_templates(
    environment: str, client_name: str,
    user: dict = Depends(get_current_user),
):
    """Lista templates de um ambiente de origem (conecta automaticamente)."""
    ws = _get_or_connect(user["id"], environment, client_name)
    templates = ws.get_templates()
    return templates


@router.post("/copy/analyze")
async def analyze_copy(body: CopyAnalyzeRequest, user: dict = Depends(get_current_user)):
    """Analisa templates selecionados: busca atributos, subatributos, verifica duplicados e categorias."""
    src_ws = _get_or_connect(user["id"], body.source_environment, body.source_client)
    dst_ws = _get_or_connect(user["id"], body.target_environment, body.target_client)

    dst_templates = dst_ws.get_templates()
    dst_template_names = {v.strip().lower() for v in dst_templates.values()}

    dst_category_names = set()
    dst_categories_raw = dst_ws.get_categories()
    if isinstance(dst_categories_raw, list):
        for cat in dst_categories_raw:
            if isinstance(cat, dict) and "name" in cat:
                dst_category_names.add(cat["name"].strip().lower())

    src_templates = src_ws.get_templates()

    all_missing_categories = set()
    templates_to_copy = []
    duplicates = []

    for tid in body.template_ids:
        tname = src_templates.get(tid, "Unnamed")

        if tname.strip().lower() in dst_template_names:
            duplicates.append(tname)
            continue

        attrs_response = src_ws.get_template_attributes(tid)
        attrs = attrs_response.get("attributes", []) if isinstance(attrs_response, dict) else []

        all_attrs = []
        for attr in attrs:
            cats = [c["name"] for c in attr.get("categories", []) if isinstance(c, dict)]
            for cat_name in cats:
                if cat_name.strip().lower() not in dst_category_names:
                    all_missing_categories.add(cat_name)

            all_attrs.append({**attr, "_is_sub": False})

            attr_id = attr.get("id")
            if attr_id:
                try:
                    sub_resp = src_ws.get_template_attribute_subattributes(attr_id)
                    subs = sub_resp if isinstance(sub_resp, list) else sub_resp.get("attributes", [])
                    for sub in subs:
                        sub_cats = [c["name"] for c in sub.get("categories", []) if isinstance(c, dict)]
                        for cat_name in sub_cats:
                            if cat_name.strip().lower() not in dst_category_names:
                                all_missing_categories.add(cat_name)
                        all_attrs.append({**sub, "_is_sub": True, "_parent_name": attr["name"]})
                except Exception:
                    pass

        root_count = sum(1 for a in all_attrs if not a.get("_is_sub"))
        sub_count = sum(1 for a in all_attrs if a.get("_is_sub"))

        templates_to_copy.append({
            "id": tid,
            "name": tname,
            "attrs": all_attrs,
            "root_count": root_count,
            "sub_count": sub_count,
        })

    return {
        "templates_to_copy": templates_to_copy,
        "duplicates": duplicates,
        "missing_categories": sorted(all_missing_categories),
    }


@router.post("/copy/execute")
async def execute_copy(body: CopyExecuteRequest, user: dict = Depends(get_current_user)):
    """Executa a cópia dos templates analisados para o ambiente de destino."""
    dst_ws = _get_or_connect(user["id"], body.target_environment, body.target_client)

    dst_categories_raw = dst_ws.get_categories()
    cat_name_to_id = {}
    if isinstance(dst_categories_raw, list):
        for cat in dst_categories_raw:
            if isinstance(cat, dict):
                cat_name_to_id[cat["name"].strip().lower()] = cat["id"]

    created = 0
    errors = []

    for tmpl in body.templates:
        all_attrs = tmpl.get("attrs", [])
        root_attrs = [a for a in all_attrs if not a.get("_is_sub")]
        sub_attrs = [a for a in all_attrs if a.get("_is_sub")]

        api_attrs = [_convert_attr_for_creation(a, cat_name_to_id) for a in root_attrs]

        payload = {
            "name": tmpl["name"],
            "description": "",
            "attributes": api_attrs,
        }

        response = dst_ws.post_template(payload)
        if not (hasattr(response, "status_code") and response.status_code in (200, 201)):
            errors.append(f"{tmpl['name']}: HTTP {getattr(response, 'status_code', '?')}")
            continue

        new_template = response.json()
        new_template_id = new_template.get("id", "")

        if sub_attrs and new_template_id:
            new_attrs_resp = dst_ws.get_template_attributes(new_template_id)
            new_attrs = new_attrs_resp.get("attributes", []) if isinstance(new_attrs_resp, dict) else []
            name_to_new_id = {a["name"].strip().lower(): a["id"] for a in new_attrs}

            for sub in sub_attrs:
                parent_name = sub.get("_parent_name", "")
                parent_id = name_to_new_id.get(parent_name.strip().lower())
                if parent_id:
                    sa = _convert_attr_for_creation(sub, cat_name_to_id)
                    sa["parent_id"] = parent_id
                    dst_ws.post_template_attribute(new_template_id, sa)

        created += 1

    return {
        "message": f"{created} template(s) copiado(s) com sucesso.",
        "created": created,
        "errors": errors,
    }


def _convert_attr_for_creation(attr: dict, cat_name_to_id: dict) -> dict:
    data_source = attr.get("data_source", "Manual")
    data_type = attr.get("data_type", "Text")

    type_mapping = {
        ("Manual", "Text"): "Manual Text",
        ("Manual", "Integer"): "Manual Integer",
        ("Manual", "Float"): "Manual Float",
        ("Manual", "Boolean"): "Manual Boolean",
        ("TimeSeries", "Float"): "Time Series Float",
        ("TimeSeries", "Integer"): "Time Series Integer",
        ("TimeSeries", "Text"): "Time Series Text",
        ("TimeSeries", ""): "Time Series",
        ("Relational", "Text"): "Relational Text",
    }
    attr_type = type_mapping.get((data_source, data_type), f"{data_source} {data_type}".strip())

    category_ids = []
    for cat in attr.get("categories", []):
        if isinstance(cat, dict):
            cat_id = cat_name_to_id.get(cat["name"].strip().lower())
            if cat_id:
                category_ids.append(cat_id)

    result = {
        "name": attr["name"],
        "description": attr.get("description", "") or "",
        "type": attr_type,
        "unit_of_measurement": attr.get("unit_of_measurement", "") or "",
        "decimal_places": attr.get("decimal_places", 2) if "Float" in attr_type else 0,
        "default_value": str(attr.get("default_value", "") or "") or None,
    }

    if category_ids:
        result["categories"] = category_ids

    return result
