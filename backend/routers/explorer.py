from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from auth import get_current_user
from connections import get_connection, connect_environment
from db_lighthouse import (
    get_vessels, get_item_tree, get_item_attributes, get_item_subattributes,
    get_item_generators_from_db, get_item_meta, update_attribute_value_in_db,
    update_attribute_fields_in_db,
    insert_item_in_db, rename_item_in_db, delete_item_from_db,
    update_subattribute_value_in_db,
)

router = APIRouter()


def _get_or_connect(user_id: int, environment: str, client_name: str):
    ws = get_connection(user_id, environment, client_name)
    if ws:
        return ws
    try:
        return connect_environment(user_id, environment, client_name)
    except KeyError:
        raise HTTPException(status_code=400, detail="Ambiente ou cliente inválido.")


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
    vessel: str
    name: str
    template_id: str
    parent_id: str
    environment: str
    client_name: str


class RenameItemRequest(BaseModel):
    name: str


class DeleteItemRequest(BaseModel):
    environment: str
    client_name: str


@router.get("/vessels")
async def list_vessels(_: dict = Depends(get_current_user)):
    return get_vessels()


@router.get("/items/{vessel}")
async def list_items(vessel: str, _: dict = Depends(get_current_user)):
    return get_item_tree(vessel)


@router.get("/items/{item_id}/attributes")
async def item_attributes(item_id: str, _: dict = Depends(get_current_user)):
    return get_item_attributes(item_id)


@router.get("/items/{item_id}/subattributes")
async def item_subattributes(item_id: str, _: dict = Depends(get_current_user)):
    return get_item_subattributes(item_id)


@router.get("/items/{item_id}/generators")
async def item_generators(item_id: str, _: dict = Depends(get_current_user)):
    return get_item_generators_from_db(item_id)


@router.get("/items/{item_id}/meta")
async def item_meta(item_id: str, _: dict = Depends(get_current_user)):
    meta = get_item_meta(item_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Item não encontrado.")
    return meta


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

    for upd in updates:
        update_attribute_value_in_db(item_id, upd.attribute_id, upd.value)
    return {"message": f"{len(updates)} atributo(s) atualizado(s)."}


@router.patch("/items/{item_id}/attribute-full")
async def update_attribute_full(
    item_id: str,
    body: FullAttributeUpdate,
    environment: str = Query(...),
    client_name: str = Query(...),
    user: dict = Depends(get_current_user),
):
    """Update all fields of a single attribute (manual or timeseries)."""
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

    update_attribute_fields_in_db(
        item_id, body.attribute_id, body.attr_type,
        value=body.value,
        reference=body.reference,
        unit_of_measurement=body.unit_of_measurement,
        decimal_places=body.decimal_places,
        description=body.description,
    )

    return {"message": "Atributo atualizado na API e localmente."}


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

    for upd in updates:
        update_subattribute_value_in_db(item_id, upd.attribute_id, upd.value)
    return {"message": f"{len(updates)} subatributo(s) atualizado(s) na API e localmente."}


@router.post("/items")
async def create_item(body: CreateItemRequest, user: dict = Depends(get_current_user)):
    ws = _get_or_connect(user["id"], body.environment, body.client_name)
    response = ws.create_item(body.template_id, {"name": body.name, "parent_id": body.parent_id})
    if hasattr(response, "status_code") and response.status_code not in (200, 201):
        raise HTTPException(status_code=response.status_code, detail=response.text)
    new_id = response.json().get("id") if hasattr(response, "json") else response.get("id")
    attrs = ws.get_item_attributes(new_id).get("attributes", [])
    insert_item_in_db(body.vessel, new_id, body.name, "", body.parent_id, attrs)
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

    rename_item_in_db(item_id, body.name)
    return {"message": "Item renomeado na API e localmente."}


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

    delete_item_from_db(item_id)
    return {"message": "Item removido da API e localmente."}
