from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from auth import get_current_user
from connections import get_connection, connect_environment
from db_lighthouse import (
    get_dd_projects, get_dd_project, create_dd_project, update_dd_project, delete_dd_project,
    get_dd_items, get_dd_item, create_dd_item, rename_dd_item, delete_dd_item, set_dd_item_ws_id,
    get_dd_attributes, get_dd_subattributes, get_all_dd_attributes,
    populate_dd_attributes_from_template, update_dd_attribute, bulk_update_dd_attributes,
    get_dd_project_summary,
)

router = APIRouter()


# --- Projects ---

class CreateProjectRequest(BaseModel):
    name: str
    client: str
    environment: str


class UpdateProjectRequest(BaseModel):
    name: str | None = None
    status: str | None = None
    ws_parent_id: str | None = None


@router.get("/projects")
async def list_projects(status: str = None, _: dict = Depends(get_current_user)):
    return get_dd_projects(status=status)


@router.get("/projects/{project_id}")
async def get_project(project_id: str, _: dict = Depends(get_current_user)):
    p = get_dd_project(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")
    return p


@router.get("/projects/{project_id}/summary")
async def project_summary(project_id: str, _: dict = Depends(get_current_user)):
    return get_dd_project_summary(project_id)


@router.post("/projects")
async def post_project(body: CreateProjectRequest, _: dict = Depends(get_current_user)):
    pid = create_dd_project(body.name, body.client, body.environment)
    return {"id": pid, "message": "Projeto criado."}


@router.patch("/projects/{project_id}")
async def patch_project(project_id: str, body: UpdateProjectRequest, _: dict = Depends(get_current_user)):
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar.")
    update_dd_project(project_id, **fields)
    return {"message": "Projeto atualizado."}


@router.delete("/projects/{project_id}")
async def remove_project(project_id: str, _: dict = Depends(get_current_user)):
    delete_dd_project(project_id)
    return {"message": "Projeto removido."}


# --- Items ---

class CreateItemRequest(BaseModel):
    name: str
    template_id: str | None = None
    template_name: str | None = None
    parent_item_id: str | None = None


class RenameItemRequest(BaseModel):
    name: str


@router.get("/projects/{project_id}/items")
async def list_items(project_id: str, _: dict = Depends(get_current_user)):
    return get_dd_items(project_id)


@router.post("/projects/{project_id}/items")
async def post_item(project_id: str, body: CreateItemRequest, _: dict = Depends(get_current_user)):
    item_id = create_dd_item(project_id, body.name, body.template_id, body.template_name, body.parent_item_id)
    return {"id": item_id, "message": "Item criado."}


@router.patch("/items/{item_id}/rename")
async def patch_item_rename(item_id: str, body: RenameItemRequest, _: dict = Depends(get_current_user)):
    rename_dd_item(item_id, body.name)
    return {"message": "Item renomeado."}


@router.delete("/items/{item_id}")
async def remove_item(item_id: str, _: dict = Depends(get_current_user)):
    delete_dd_item(item_id)
    return {"message": "Item removido."}


@router.patch("/items/{item_id}/ws-id")
async def patch_item_ws_id(item_id: str, ws_item_id: str, _: dict = Depends(get_current_user)):
    set_dd_item_ws_id(item_id, ws_item_id)
    return {"message": "ws_item_id atualizado."}


# --- Attributes ---

class PopulateAttributesRequest(BaseModel):
    template_id: str
    environment: str
    client: str


class UpdateAttributeRequest(BaseModel):
    id: int
    reference: str | None = None
    value: str | None = None
    unit_of_measurement: str | None = None
    decimal_places: int | None = None


@router.get("/items/{item_id}/attributes")
async def list_attributes(item_id: str, _: dict = Depends(get_current_user)):
    return get_dd_attributes(item_id)


@router.get("/items/{item_id}/subattributes")
async def list_subattributes(item_id: str, _: dict = Depends(get_current_user)):
    return get_dd_subattributes(item_id)


@router.get("/items/{item_id}/all-attributes")
async def list_all_attributes(item_id: str, _: dict = Depends(get_current_user)):
    return get_all_dd_attributes(item_id)


@router.post("/items/{item_id}/populate")
async def populate_attributes(item_id: str, body: PopulateAttributesRequest, _: dict = Depends(get_current_user)):
    populate_dd_attributes_from_template(item_id, body.template_id, body.environment, body.client)
    return {"message": "Atributos populados a partir do template."}


@router.patch("/attributes")
async def patch_attributes(updates: list[UpdateAttributeRequest], _: dict = Depends(get_current_user)):
    data = [u.model_dump(exclude_none=True) for u in updates]
    bulk_update_dd_attributes(data)
    return {"message": f"{len(data)} atributo(s) atualizado(s)."}


# --- Enrollment (Cadastrar no Workspace) ---

def _get_or_connect(user_id: int, environment: str, client_name: str):
    ws = get_connection(user_id, environment, client_name)
    if ws:
        return ws
    try:
        return connect_environment(user_id, environment, client_name)
    except KeyError:
        raise HTTPException(status_code=400, detail="Ambiente ou cliente inválido.")


class SetWsParentRequest(BaseModel):
    ws_parent_id: str


class EnrollRequest(BaseModel):
    environment: str
    client_name: str


@router.patch("/projects/{project_id}/ws-parent")
async def set_project_ws_parent(
    project_id: str, body: SetWsParentRequest, _: dict = Depends(get_current_user),
):
    project = get_dd_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")
    update_dd_project(project_id, ws_parent_id=body.ws_parent_id.strip())
    return {"message": "ws_parent_id atualizado."}


@router.post("/projects/{project_id}/enroll")
async def enroll_project(
    project_id: str, body: EnrollRequest, user: dict = Depends(get_current_user),
):
    project = get_dd_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")
    if not project.get("ws_parent_id"):
        raise HTTPException(status_code=400, detail="ID do item pai no Workspace não definido.")

    ws = _get_or_connect(user["id"], body.environment, body.client_name)

    items = get_dd_items(project_id)
    if not items:
        raise HTTPException(status_code=400, detail="Nenhum item para cadastrar.")

    items_with_template = [i for i in items if i["template_id"]]
    if not items_with_template:
        raise HTTPException(status_code=400, detail="Nenhum item com template para cadastrar.")

    children_map: dict[str | None, list[dict]] = {}
    for item in items:
        children_map.setdefault(item["parent_item_id"], []).append(item)

    dd_to_ws: dict[str, str] = {}
    created = 0
    updated = 0
    errors = []

    def ws_item_exists(ws_item_id: str) -> bool:
        response = ws.get_item(ws_item_id)
        return isinstance(response, dict) and "id" in response

    def update_item_attributes(ws_item_id: str, dd_item_id: str):
        ws_attrs_response = ws.get_item_attributes(ws_item_id)
        ws_attrs = ws_attrs_response.get("attributes", []) if isinstance(ws_attrs_response, dict) else []

        ws_attr_map = {}
        ws_subattr_map = {}
        for wa in ws_attrs:
            ws_attr_map[wa["name"].strip().lower()] = wa
            for sub in wa.get("sub_attributes", []):
                ws_subattr_map[(wa["name"].strip().lower(), sub["name"].strip().lower())] = sub

        dd_attrs = get_dd_attributes(dd_item_id)
        dd_subs = get_dd_subattributes(dd_item_id)

        ts_batch = []
        manual_batch = []

        for attr in dd_attrs:
            key = attr["name"].strip().lower()
            ws_attr = ws_attr_map.get(key)
            if not ws_attr:
                continue
            is_ts = attr.get("data_source") and "Time" in attr["data_source"]
            if is_ts and attr.get("reference"):
                ts_batch.append({
                    "id": ws_attr["id"],
                    "reference": attr["reference"],
                    "unit_of_measurement": attr.get("unit_of_measurement") or "",
                    "engineering_unit": attr.get("unit_of_measurement") or "",
                    "decimal_places": str(attr.get("decimal_places") or 2),
                })
            elif not is_ts and attr.get("value"):
                manual_batch.append({"id": ws_attr["id"], "value": str(attr["value"])})

        for sub in dd_subs:
            parent_name = (sub.get("parent_name") or "").strip().lower()
            sub_name = sub["name"].strip().lower()
            ws_sub = ws_subattr_map.get((parent_name, sub_name))
            if ws_sub and sub.get("value"):
                manual_batch.append({"id": ws_sub["id"], "value": str(sub["value"])})

        if ts_batch:
            ws.update_attribute_batch(ws_item_id, ts_batch)
        if manual_batch:
            ws.update_manual_attributes(ws_item_id, manual_batch)

    def create_recursive(parent_dd_id: str | None, parent_ws_id: str | None):
        nonlocal created, updated
        children = children_map.get(parent_dd_id, [])

        for item in children:
            if item["template_id"]:
                try:
                    existing_ws_id = item.get("ws_item_id")
                    if existing_ws_id and ws_item_exists(existing_ws_id):
                        dd_to_ws[item["id"]] = existing_ws_id
                        update_item_attributes(existing_ws_id, item["id"])
                        updated += 1
                    else:
                        response = ws.create_item(item["template_id"], {
                            "name": item["name"],
                            "parent_id": parent_ws_id,
                        })
                        if hasattr(response, "status_code") and response.status_code in (200, 201):
                            new_item = response.json()
                            ws_item_id = new_item.get("id", "")
                            dd_to_ws[item["id"]] = ws_item_id
                            set_dd_item_ws_id(item["id"], ws_item_id)
                            update_item_attributes(ws_item_id, item["id"])
                            created += 1
                        else:
                            status = getattr(response, "status_code", "?")
                            text = getattr(response, "text", str(response))
                            errors.append(f"{item['name']}: HTTP {status} — {text}")
                except Exception as e:
                    errors.append(f"{item['name']}: {e}")

                create_recursive(item["id"], dd_to_ws.get(item["id"], parent_ws_id))
            else:
                create_recursive(item["id"], parent_ws_id)

    try:
        create_recursive(None, project["ws_parent_id"])
    except Exception as e:
        errors.append(f"Erro geral: {e}")

    if created + updated > 0:
        update_dd_project(project_id, status="Cadastrado")

    parts = []
    if created:
        parts.append(f"{created} criado(s)")
    if updated:
        parts.append(f"{updated} atualizado(s)")

    return {
        "message": f"Cadastro concluído: {', '.join(parts)}." if parts else "Nenhum item processado.",
        "created": created,
        "updated": updated,
        "errors": errors,
    }
