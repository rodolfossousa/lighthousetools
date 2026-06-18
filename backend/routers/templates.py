from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel

from auth import get_current_user
from connections import get_connection
from db_lighthouse import get_template_list, get_template_attributes_from_db

router = APIRouter()


class CreateTemplateRequest(BaseModel):
    name: str
    description: str = ""
    attributes: list[dict]
    environment: str
    client_name: str


class CopyTemplateRequest(BaseModel):
    template_id: str
    source_environment: str
    source_client: str
    target_environment: str
    target_client: str


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


@router.post("/copy")
async def copy_template(body: CopyTemplateRequest, user: dict = Depends(get_current_user)):
    source_ws = get_connection(user["id"], body.source_environment, body.source_client)
    target_ws = get_connection(user["id"], body.target_environment, body.target_client)
    if not source_ws or not target_ws:
        raise HTTPException(status_code=400, detail="Ambientes de origem e destino devem estar conectados.")

    attrs_resp = source_ws.get_template_attributes(body.template_id)
    attrs = attrs_resp.get("attributes", []) if isinstance(attrs_resp, dict) else attrs_resp

    templates = source_ws.get_templates()
    template_name = templates.get(body.template_id, "Unnamed")

    template_content = {"name": template_name, "attributes": []}
    for attr in attrs:
        template_content["attributes"].append({
            "name": attr.get("name", ""),
            "description": attr.get("description", ""),
            "type": f'{attr.get("data_source", "Manual")} {attr.get("data_type", "Text")}',
            "unit_of_measurement": attr.get("unit_of_measurement", ""),
            "default_value": attr.get("default_value"),
            "decimal_places": attr.get("decimal_places", 0),
        })

    response = target_ws.post_template(template_content)
    if hasattr(response, "status_code") and response.status_code not in (200, 201):
        raise HTTPException(status_code=response.status_code, detail=getattr(response, "text", "Erro ao copiar."))
    return {"message": f"Template '{template_name}' copiado com sucesso."}
