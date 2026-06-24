from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from auth import get_current_user
from connections import get_connection, connect_environment

router = APIRouter()


def _get_or_connect(user_id: int, environment: str, client_name: str):
    ws = get_connection(user_id, environment, client_name)
    if ws:
        return ws
    try:
        return connect_environment(user_id, environment, client_name)
    except KeyError:
        raise HTTPException(status_code=400, detail="Ambiente ou cliente inválido.")


def _flatten_tree(items: list[dict], parent_id: str | None = None, depth: int = 0) -> list[dict]:
    result = []
    for item in items:
        children = item.get("children") or []
        template = item.get("template") or {}
        result.append({
            "id": item["id"],
            "name": item["name"],
            "template_name": template.get("name", "") if isinstance(template, dict) else "",
            "parent_id": parent_id,
            "has_children": len(children) > 0,
            "depth": depth,
        })
        if children:
            result.extend(_flatten_tree(children, item["id"], depth + 1))
    return result


def _transform_attribute(attr: dict) -> dict:
    cats = attr.get("categories") or []
    category = cats[0]["name"] if cats else ""
    ds = attr.get("data_source", "")
    dt = attr.get("data_type", "")
    spec = f"{ds}_{dt}" if ds or dt else attr.get("specification", "")
    return {
        "id_attribute": attr["id"],
        "name_attribute": attr["name"],
        "value": attr.get("value") or "",
        "specification": spec,
        "reference": attr.get("reference") or "",
        "category": category,
        "unit_of_measurement": attr.get("unit_of_measurement") or "",
        "decimal_places": str(attr.get("decimal_places", "")),
        "description": attr.get("description") or "",
    }


def _extract_subattributes(ws_attrs: list[dict]) -> list[dict]:
    result = []
    for attr in ws_attrs:
        parent_id = attr["id"]
        parent_name = attr["name"]
        parent_ref = attr.get("reference") or ""
        cats = attr.get("categories") or []
        category = cats[0]["name"] if cats else ""
        for sub in attr.get("sub_attributes") or []:
            ds = sub.get("data_source", "")
            dt = sub.get("data_type", "")
            spec = f"{ds}_{dt}" if ds or dt else sub.get("specification", "")
            result.append({
                "id_attribute": sub["id"],
                "name_attribute": sub["name"],
                "value": sub.get("value") or "",
                "specification": spec,
                "parent_attribute_id": parent_id,
                "category": category,
                "parent_name": parent_name,
                "parent_reference": parent_ref,
                "unit_of_measurement": sub.get("unit_of_measurement") or "",
                "decimal_places": str(sub.get("decimal_places", "")),
                "description": sub.get("description") or "",
            })
    return result


# ── READ ────────────────────────────────────────────

class UpdateAttributeRequest(BaseModel):
    attribute_id: str
    value: str


class FullAttributeUpdate(BaseModel):
    attribute_id: str
    attr_type: str = "attribute"
    value: str | None = None
    reference: str | None = None
    unit_of_measurement: str | None = None
    decimal_places: str | None = None
    description: str | None = None


class CreateItemRequest(BaseModel):
    name: str
    template_id: str
    parent_id: str
    environment: str
    client_name: str


class RenameItemRequest(BaseModel):
    name: str


@router.get("/items/tree")
async def get_item_tree(
    environment: str = Query(...),
    client_name: str = Query(...),
    user: dict = Depends(get_current_user),
):
    ws = _get_or_connect(user["id"], environment, client_name)
    url = f"{ws.root_url}/workspaces/{ws.workspace_id}/items/tree"
    response = ws.get(url)
    if isinstance(response, dict) and "detail" in response:
        raise HTTPException(status_code=502, detail=f"Erro da API Lighthouse: {response['detail']}")
    raw_items = response.get("items", []) if isinstance(response, dict) else []
    return _flatten_tree(raw_items)


@router.get("/items/{item_id}/attributes")
async def item_attributes(
    item_id: str,
    environment: str = Query(...),
    client_name: str = Query(...),
    user: dict = Depends(get_current_user),
):
    ws = _get_or_connect(user["id"], environment, client_name)
    response = ws.get_item_attributes(item_id)
    ws_attrs = response.get("attributes", []) if isinstance(response, dict) else []
    return [_transform_attribute(a) for a in ws_attrs]


@router.get("/items/{item_id}/subattributes")
async def item_subattributes(
    item_id: str,
    environment: str = Query(...),
    client_name: str = Query(...),
    user: dict = Depends(get_current_user),
):
    ws = _get_or_connect(user["id"], environment, client_name)
    response = ws.get_item_attributes(item_id)
    ws_attrs = response.get("attributes", []) if isinstance(response, dict) else []
    return _extract_subattributes(ws_attrs)


@router.get("/items/{item_id}/generators")
async def item_generators(
    item_id: str,
    environment: str = Query(...),
    client_name: str = Query(...),
    user: dict = Depends(get_current_user),
):
    ws = _get_or_connect(user["id"], environment, client_name)
    response = ws.get_item_generators(item_id)
    raw = response.get("generators", []) if isinstance(response, dict) else (response if isinstance(response, list) else [])
    return [
        {
            "id_attribute": g.get("id", ""),
            "name_attribute": g.get("name", ""),
            "value": g.get("value") or g.get("name", ""),
            "specification": g.get("specification") or g.get("type", ""),
        }
        for g in raw
    ]


# ── WRITE ───────────────────────────────────────────

@router.patch("/items/{item_id}/attributes")
async def update_attributes(
    item_id: str,
    updates: list[UpdateAttributeRequest],
    environment: str = Query(...),
    client_name: str = Query(...),
    user: dict = Depends(get_current_user),
):
    ws = _get_or_connect(user["id"], environment, client_name)
    api_payload = [{"id": upd.attribute_id, "value": upd.value} for upd in updates]
    response = ws.update_manual_attributes(item_id, api_payload)
    if hasattr(response, "status_code") and response.status_code not in (200, 201, 204):
        raise HTTPException(status_code=response.status_code, detail=getattr(response, "text", "Erro ao atualizar na API Lighthouse."))
    return {"message": f"{len(updates)} atributo(s) atualizado(s)."}


@router.patch("/items/{item_id}/attribute-full")
async def update_attribute_full(
    item_id: str,
    body: FullAttributeUpdate,
    environment: str = Query(...),
    client_name: str = Query(...),
    user: dict = Depends(get_current_user),
):
    ws = _get_or_connect(user["id"], environment, client_name)

    is_ts = body.reference is not None or body.unit_of_measurement is not None or body.decimal_places is not None

    if is_ts:
        batch_entry: dict = {"id": body.attribute_id}
        if body.reference is not None:
            batch_entry["reference"] = body.reference
        if body.unit_of_measurement is not None:
            batch_entry["unit_of_measurement"] = body.unit_of_measurement
            batch_entry["engineering_unit"] = body.unit_of_measurement
        if body.decimal_places is not None:
            batch_entry["decimal_places"] = body.decimal_places
        response = ws.update_attribute_batch(item_id, [batch_entry])
        if hasattr(response, "status_code") and response.status_code not in (200, 201, 204):
            raise HTTPException(
                status_code=response.status_code,
                detail=getattr(response, "text", "Erro ao atualizar atributo TimeSeries na API."),
            )

    if body.value is not None:
        response = ws.update_manual_attributes(item_id, [{"id": body.attribute_id, "value": body.value}])
        if hasattr(response, "status_code") and response.status_code not in (200, 201, 204):
            raise HTTPException(
                status_code=response.status_code,
                detail=getattr(response, "text", "Erro ao atualizar valor na API."),
            )

    return {"message": "Atributo atualizado."}


@router.patch("/items/{item_id}/subattributes")
async def update_subattributes(
    item_id: str,
    updates: list[UpdateAttributeRequest],
    environment: str = Query(...),
    client_name: str = Query(...),
    user: dict = Depends(get_current_user),
):
    ws = _get_or_connect(user["id"], environment, client_name)
    api_payload = [{"id": upd.attribute_id, "value": upd.value} for upd in updates]
    response = ws.update_manual_attributes(item_id, api_payload)
    if hasattr(response, "status_code") and response.status_code not in (200, 201, 204):
        raise HTTPException(status_code=response.status_code, detail=getattr(response, "text", "Erro ao atualizar na API Lighthouse."))
    return {"message": f"{len(updates)} subatributo(s) atualizado(s)."}


@router.post("/items")
async def create_item(body: CreateItemRequest, user: dict = Depends(get_current_user)):
    ws = _get_or_connect(user["id"], body.environment, body.client_name)
    response = ws.create_item(body.template_id, {"name": body.name, "parent_id": body.parent_id})
    if hasattr(response, "status_code") and response.status_code not in (200, 201):
        raise HTTPException(status_code=response.status_code, detail=response.text)
    new_id = response.json().get("id") if hasattr(response, "json") else response.get("id")
    return {"id": new_id, "message": "Item criado."}


@router.patch("/items/{item_id}/rename")
async def rename_item(
    item_id: str,
    body: RenameItemRequest,
    environment: str = Query(...),
    client_name: str = Query(...),
    user: dict = Depends(get_current_user),
):
    ws = _get_or_connect(user["id"], environment, client_name)
    response = ws.update_item(item_id, {"name": body.name})
    if hasattr(response, "status_code") and response.status_code not in (200, 201, 204):
        raise HTTPException(status_code=response.status_code, detail=getattr(response, "text", "Erro ao renomear na API Lighthouse."))
    return {"message": "Item renomeado."}


@router.delete("/items/{item_id}")
async def remove_item(
    item_id: str,
    environment: str = Query(...),
    client_name: str = Query(...),
    user: dict = Depends(get_current_user),
):
    ws = _get_or_connect(user["id"], environment, client_name)
    response = ws.delete_item(item_id)
    if hasattr(response, "status_code") and response.status_code not in (200, 201, 204):
        raise HTTPException(status_code=response.status_code, detail=getattr(response, "text", "Erro ao remover na API Lighthouse."))
    return {"message": "Item removido."}
