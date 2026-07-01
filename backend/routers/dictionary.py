import io
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel

from auth import get_current_user
from connections import get_connection, connect_environment
from db_lighthouse import (
    _get_conn,
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
        ws_attrs = ws_attrs_response if isinstance(ws_attrs_response, list) else ws_attrs_response.get("attributes", []) if isinstance(ws_attrs_response, dict) else []

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


# --- Refresh (Atualizar do Workspace) ---

class RefreshRequest(BaseModel):
    environment: str
    client_name: str


def _insert_dd_attrs_from_ws(dd_item_id: str, ws_attrs: list[dict]):
    """Cria atributos no DD a partir dos atributos reais do workspace."""
    conn = _get_conn()
    conn.execute("DELETE FROM dd_attributes WHERE item_id = ?", (dd_item_id,))

    parent_map = {}
    root_attrs = [a for a in ws_attrs if not a.get("parent_id")]
    sub_attrs = []
    for a in ws_attrs:
        for sub in a.get("sub_attributes") or []:
            sub["_parent_ws_id"] = a["id"]
            sub["_parent_name"] = a["name"]
            sub_attrs.append(sub)

    for i, attr in enumerate(root_attrs):
        cats = attr.get("categories") or []
        cat_str = cats[0]["name"] if cats else ""
        ds = attr.get("data_source", "")
        dt = attr.get("data_type", "")
        cursor = conn.execute("""
            INSERT INTO dd_attributes
                (item_id, template_attribute_id, name, data_source, data_type,
                 unit_of_measurement, decimal_places, categories, reference, value,
                 parent_attribute_id, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)
        """, (
            dd_item_id, attr.get("id", ""), attr["name"], ds, dt,
            attr.get("unit_of_measurement") or "", attr.get("decimal_places") or 2,
            cat_str, attr.get("reference") or "",
            str(attr["value"]) if attr.get("value") is not None else "",
            i,
        ))
        parent_map[attr["id"]] = cursor.lastrowid

    for j, sub in enumerate(sub_attrs):
        parent_dd_id = parent_map.get(sub.get("_parent_ws_id"))
        if parent_dd_id is None:
            continue
        cats = sub.get("categories") or []
        cat_str = cats[0]["name"] if cats else ""
        ds = sub.get("data_source", "")
        dt = sub.get("data_type", "")
        conn.execute("""
            INSERT INTO dd_attributes
                (item_id, template_attribute_id, name, data_source, data_type,
                 unit_of_measurement, decimal_places, categories, reference, value,
                 parent_attribute_id, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            dd_item_id, sub.get("id", ""), sub["name"], ds, dt,
            sub.get("unit_of_measurement") or "", sub.get("decimal_places") or 2,
            cat_str, sub.get("reference") or "",
            str(sub["value"]) if sub.get("value") is not None else "",
            parent_dd_id, j,
        ))

    conn.commit()
    conn.close()


@router.post("/projects/{project_id}/refresh")
async def refresh_from_workspace(
    project_id: str, body: RefreshRequest, user: dict = Depends(get_current_user),
):
    project = get_dd_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")
    if project.get("status") != "Cadastrado":
        raise HTTPException(status_code=400, detail="Projeto ainda não foi cadastrado no Workspace.")

    ws = _get_or_connect(user["id"], body.environment, body.client_name)

    items = get_dd_items(project_id)
    enrolled_items = [i for i in items if i.get("ws_item_id")]
    if not enrolled_items:
        raise HTTPException(status_code=400, detail="Nenhum item cadastrado no Workspace para atualizar.")

    known_ws_ids = {i["ws_item_id"] for i in items if i.get("ws_item_id")}
    dd_by_ws_id = {i["ws_item_id"]: i for i in items if i.get("ws_item_id")}

    items_processed = 0
    updated_attrs = 0
    new_items = 0
    linked_items = 0
    removed_items = 0
    errors = []

    def _update_existing_attrs(dd_item_id: str, ws_attrs: list[dict]):
        nonlocal updated_attrs
        ws_attr_map = {}
        ws_subattr_map = {}
        for wa in ws_attrs:
            ws_attr_map[wa["name"].strip().lower()] = wa
            for sub in wa.get("sub_attributes", []):
                ws_subattr_map[(wa["name"].strip().lower(), sub["name"].strip().lower())] = sub

        dd_attrs = get_dd_attributes(dd_item_id)
        dd_subs = get_dd_subattributes(dd_item_id)
        updates = []

        for attr in dd_attrs:
            key = attr["name"].strip().lower()
            ws_attr = ws_attr_map.get(key)
            if not ws_attr:
                continue
            upd: dict = {"id": attr["id"]}
            ws_ref = ws_attr.get("reference") or ""
            if ws_ref != (attr.get("reference") or ""):
                upd["reference"] = ws_ref
            ws_val = ws_attr.get("value")
            ws_val_str = str(ws_val) if ws_val is not None else ""
            if ws_val_str != (attr.get("value") or ""):
                upd["value"] = ws_val_str
            ws_uom = ws_attr.get("unit_of_measurement") or ""
            if ws_uom != (attr.get("unit_of_measurement") or ""):
                upd["unit_of_measurement"] = ws_uom
            ws_dp = ws_attr.get("decimal_places")
            if ws_dp is not None and int(ws_dp) != (attr.get("decimal_places") or 2):
                upd["decimal_places"] = int(ws_dp)
            if len(upd) > 1:
                updates.append(upd)

        for sub in dd_subs:
            parent_name = (sub.get("parent_name") or "").strip().lower()
            sub_name = sub["name"].strip().lower()
            ws_sub = ws_subattr_map.get((parent_name, sub_name))
            if not ws_sub:
                continue
            upd = {"id": sub["id"]}
            ws_val = ws_sub.get("value")
            ws_val_str = str(ws_val) if ws_val is not None else ""
            if ws_val_str != (sub.get("value") or ""):
                upd["value"] = ws_val_str
            if len(upd) > 1:
                updates.append(upd)

        if updates:
            bulk_update_dd_attributes(updates)
            updated_attrs += len(updates)

    dd_children_by_parent: dict[str | None, dict[str, dict]] = {}
    for it in items:
        parent = it.get("parent_item_id")
        dd_children_by_parent.setdefault(parent, {})[it["name"].strip().lower()] = it

    def _discover_children(ws_parent_id: str, dd_parent_id: str):
        nonlocal new_items, updated_attrs, linked_items
        try:
            response = ws.get_subitems(ws_parent_id, traverse=False)
            subitems = response.get("subitems", []) if isinstance(response, dict) else []
        except Exception:
            return

        name_map = dd_children_by_parent.get(dd_parent_id, {})

        for child in subitems:
            child_ws_id = child["id"]
            if child_ws_id in known_ws_ids:
                continue

            child_name_key = child["name"].strip().lower()
            existing_dd = name_map.get(child_name_key)

            if existing_dd and not existing_dd.get("ws_item_id"):
                set_dd_item_ws_id(existing_dd["id"], child_ws_id)
                existing_dd["ws_item_id"] = child_ws_id
                known_ws_ids.add(child_ws_id)
                linked_items += 1
                try:
                    ws_response = ws.get_item_attributes(child_ws_id)
                    ws_attrs = ws_response if isinstance(ws_response, list) else ws_response.get("attributes", []) if isinstance(ws_response, dict) else []
                    _update_existing_attrs(existing_dd["id"], ws_attrs)
                except Exception:
                    pass
                _discover_children(child_ws_id, existing_dd["id"])
            elif existing_dd:
                continue
            else:
                template = child.get("template") or {}
                template_id = template.get("id") or ""
                template_name = template.get("name") or ""

                dd_item_id = create_dd_item(
                    project_id, child["name"], template_id, template_name, dd_parent_id,
                )
                set_dd_item_ws_id(dd_item_id, child_ws_id)
                known_ws_ids.add(child_ws_id)

                try:
                    ws_response = ws.get_item_attributes(child_ws_id)
                    ws_attrs = ws_response if isinstance(ws_response, list) else ws_response.get("attributes", []) if isinstance(ws_response, dict) else []
                    if ws_attrs:
                        _insert_dd_attrs_from_ws(dd_item_id, ws_attrs)
                except Exception:
                    pass

                new_items += 1
                _discover_children(child_ws_id, dd_item_id)

    def _remove_deleted_children(ws_parent_id: str, dd_parent_id: str):
        nonlocal removed_items
        try:
            response = ws.get_subitems(ws_parent_id, traverse=False)
            subitems = response.get("subitems", []) if isinstance(response, dict) else []
        except Exception:
            return
        ws_child_ids = {child["id"] for child in subitems}
        dd_children = [i for i in items if i.get("parent_item_id") == dd_parent_id]
        for dd_child in dd_children:
            child_ws_id = dd_child.get("ws_item_id")
            if child_ws_id and child_ws_id not in ws_child_ids:
                delete_dd_item(dd_child["id"])
                removed_items += 1
            elif child_ws_id:
                _remove_deleted_children(child_ws_id, dd_child["id"])

    for item in enrolled_items:
        ws_item_id = item["ws_item_id"]
        dd_item_id = item["id"]
        try:
            ws_response = ws.get_item_attributes(ws_item_id)
            ws_attrs = ws_response if isinstance(ws_response, list) else ws_response.get("attributes", []) if isinstance(ws_response, dict) else []
            _update_existing_attrs(dd_item_id, ws_attrs)
            items_processed += 1
        except Exception as e:
            errors.append(f"{item['name']}: {e}")

        _remove_deleted_children(ws_item_id, dd_item_id)
        _discover_children(ws_item_id, dd_item_id)

    parts = []
    if items_processed:
        parts.append(f"{items_processed} item(ns) atualizado(s)")
    if updated_attrs:
        parts.append(f"{updated_attrs} atributo(s) alterado(s)")
    if linked_items:
        parts.append(f"{linked_items} item(ns) vinculado(s) ao workspace")
    if new_items:
        parts.append(f"{new_items} item(ns) novo(s) descoberto(s)")
    if removed_items:
        parts.append(f"{removed_items} item(ns) removido(s)")

    return {
        "message": f"Atualização concluída: {', '.join(parts)}." if parts else "Nenhuma alteração.",
        "items_processed": items_processed,
        "updated_attributes": updated_attrs,
        "linked_items": linked_items,
        "new_items": new_items,
        "removed_items": removed_items,
        "errors": errors,
    }


# --- Import Excel ---

@router.post("/items/{item_id}/import-excel")
async def import_excel(
    item_id: str,
    file: UploadFile = File(...),
    _: dict = Depends(get_current_user),
):
    if not file.filename or not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Ficheiro deve ser .xlsx ou .xls")

    contents = await file.read()
    try:
        df = pd.read_excel(io.BytesIO(contents), engine="openpyxl")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao ler ficheiro: {e}")

    if "attribute_name" not in df.columns:
        raise HTTPException(status_code=400, detail="Coluna 'attribute_name' não encontrada na planilha.")

    df = df.replace({pd.NA: None, float("nan"): None})
    df = df.map(lambda x: x.strip() if isinstance(x, str) else x)

    has_sub_col = "subattribute_name" in df.columns

    dd_attrs = get_dd_attributes(item_id)
    dd_subs = get_dd_subattributes(item_id)

    attr_map: dict[str, dict] = {}
    for a in dd_attrs:
        attr_map[a["name"].strip().lower()] = a

    sub_map: dict[tuple[str, str], dict] = {}
    for s in dd_subs:
        parent_name = (s.get("parent_name") or "").strip().lower()
        sub_name = s["name"].strip().lower()
        sub_map[(parent_name, sub_name)] = s

    updates = []
    matched = 0
    skipped = 0

    for _, row in df.iterrows():
        attr_name = row.get("attribute_name")
        if not attr_name or not isinstance(attr_name, str):
            skipped += 1
            continue

        sub_name = row.get("subattribute_name") if has_sub_col else None
        is_sub = sub_name is not None and isinstance(sub_name, str) and sub_name.strip() != ""

        if is_sub:
            key = (attr_name.strip().lower(), sub_name.strip().lower())
            dd_rec = sub_map.get(key)
        else:
            dd_rec = attr_map.get(attr_name.strip().lower())

        if not dd_rec:
            skipped += 1
            continue

        upd: dict = {"id": dd_rec["id"]}
        changed = False

        for excel_col, dd_field in [
            ("reference", "reference"),
            ("value", "value"),
            ("unit_of_measurement", "unit_of_measurement"),
        ]:
            if excel_col in df.columns:
                excel_val = row.get(excel_col)
                if excel_val is not None:
                    excel_str = str(excel_val).strip()
                    if excel_str and excel_str != (dd_rec.get(dd_field) or ""):
                        upd[dd_field] = excel_str
                        changed = True

        if "decimal_places" in df.columns:
            dp = row.get("decimal_places")
            if dp is not None:
                try:
                    dp_int = int(float(dp))
                    if dp_int != (dd_rec.get("decimal_places") or 2):
                        upd["decimal_places"] = dp_int
                        changed = True
                except (ValueError, TypeError):
                    pass

        if changed:
            updates.append(upd)
            matched += 1

    if updates:
        bulk_update_dd_attributes(updates)

    return {
        "message": f"Importação concluída: {matched} atributo(s) atualizado(s), {skipped} linha(s) sem correspondência.",
        "updated": matched,
        "skipped": skipped,
        "total_rows": len(df),
    }
