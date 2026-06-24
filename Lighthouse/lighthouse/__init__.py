"""
Wrapper da API do workspace do Lighthouse

Instalar este pacote usando `pip install -e .` estando na pasta Lighthouse/
Exemplo de uso:

```
from lighthouse import connect

workspace = connect(client_name="prio", environment="dev", debug=True)

events = workspace.get_events(type="Alarm") # pega todos os alarmes
modelos = workspace.get_item_generators(item_id="3fa85f64-5717-4562-b3fc-2c963f66afa6") # pega todos os modelos
```
"""
import requests
import copy
import json
import os
import time
from pathlib import Path
from typing import List, Dict

class Lighthouse:
    def __init__(self, api_key, workspace_id, *args, **kwargs):
        self.api_key = api_key
        self.workspace_id = workspace_id
        self.root_url = kwargs.get("url")
        self.debug = kwargs.get("debug", False)
        self._cache = {
            "categories": {}
        }

        # OAuth2 support
        self._oauth2_config = kwargs.get("oauth2")
        self._access_token = None
        self._token_expires_at = 0

        if self.debug:
            print("Lighthouse initialized in DEBUG mode. No data will be posted, patched, deleted or put.")

    def _fetch_oauth2_token(self):
        cfg = self._oauth2_config
        resp = requests.post(cfg["token_url"], data={
            "grant_type": "client_credentials",
            "client_id": cfg["client_id"],
            "client_secret": cfg["client_secret"],
            "scope": cfg["scope"],
        }, headers={"Content-Type": "application/x-www-form-urlencoded"})
        resp.raise_for_status()
        data = resp.json()
        self._access_token = data["access_token"]
        self._token_expires_at = time.time() + data.get("expires_in", 3600) - 60

    def _auth_headers(self):
        if self._oauth2_config:
            if not self._access_token or time.time() >= self._token_expires_at:
                self._fetch_oauth2_token()
            return {
                "content-type": "application/json",
                "Authorization": f"Bearer {self._access_token}",
            }
        return {
            "content-type": "application/json",
            "X-Api-Key": self.api_key,
        }

    def _get_cached(self, cache_name, cache_key):
        value = self._cache.get(cache_name, {}).get(cache_key)
        if value is None:
            return None
        return copy.deepcopy(value)

    def _set_cached(self, cache_name, cache_key, value):
        self._cache.setdefault(cache_name, {})[cache_key] = copy.deepcopy(value)

    def _clear_cache(self, cache_name):
        self._cache[cache_name] = {}


    def get(self, url, data=None):
        headers = self._auth_headers()
        if data:
            result = requests.get(url, headers=headers, params=data)
        else:
            result = requests.get(url, headers=headers)
        return result.json()

    def post(self, url, data):
        """
        Método genérico para fazer requisições POST.
        """
        if self.debug:
            return DummyResponse()
        response = requests.post(url, headers=self._auth_headers(), json=data)
        return response

    def put(self, url, data):
        if self.debug:
            return DummyResponse()
        result = requests.put(url, headers=self._auth_headers(), json=data)
        return result.json()

    def patch(self, url, data):
        if self.debug:
            return DummyResponse()
        result = requests.patch(url, headers=self._auth_headers(), json=data)
        return result

    def delete(self, url, data):
        if self.debug:
            return DummyResponse()
        result = requests.delete(url, headers=self._auth_headers(), json=data)
        return result


    def traverse(self, node, result):
        # Verifica se o nó tem um 'id' e 'name' e adiciona à lista de resultados
        if 'id' in node and 'name' in node:
            result.append((node['id'], node['name']))
        # Percorre os filhos, se existirem
        if 'children' in node and isinstance(node['children'], list):
            for child in node['children']:
                self.traverse(child, result)

    def get_items(self, traverse=True, template_name=None):
        url = f"{self.root_url}/workspaces/{self.workspace_id}/items/tree"
        query = {}
        if template_name:
            query["template_name"] = template_name
        query["with_attributes"] = 'true'
        response = self.get(url, data=query)

        # Se não precisar transformar em um dict de id:name, retorna o response original (quando quer a árvore completa)
        if not traverse:
            return response

        result = []
        if 'items' in response and isinstance(response['items'], list):
            for item in response['items']:
                self.traverse(item, result)

        return dict(result)
    
    def get_template_items(self, traverse=True, template_name=None):
        """
        Retorna itens filtrados por template usando GET /workspaces/{id}/items.
        Usa only_root=False para retornar todos os níveis da hierarquia.
        Nota: get_items() usa o endpoint /items/tree que NÃO suporta filtro por template_name.
        """
        url = f"{self.root_url}/workspaces/{self.workspace_id}/items"
        query = {"only_root": "false"}
        if template_name:
            query["template_name"] = template_name
        response = self.get(url, data=query)

        if not traverse:
            return response

        result = []
        if 'items' in response and isinstance(response['items'], list):
            for item in response['items']:
                self.traverse(item, result)

        return dict(result)
    
    def get_item_details(self, item_id):
        url = f"{self.root_url}/items/{item_id}"
        response = self.get(url)
        return response

    def get_item(self, item_id):
        """
        Retorna os detalhes completos de um item, incluindo template e has_children.

        Resposta relevante:
        {
            "id": "...",
            "name": "...",
            "template": {"id": "...", "name": "...", "categories": [...]},
            "has_children": true,
            "path": "...",
            "attributes": [...],
            ...
        }
        """
        url = f"{self.root_url}/items/{item_id}"
        response = self.get(url)
        return response

    def get_subitems(self, item_id, traverse=True):
        url = f"{self.root_url}/items/{item_id}/subitems"
        response = self.get(url)

        # Se não precisar transformar em um dict de id:name, retorna o response original (quando quer a árvore completa)
        if not traverse:
            return response

        result = []
        if 'subitems' in response and isinstance(response['subitems'], list):
            for item in response['subitems']:
                self.traverse(item, result)

        return dict(result)

    def get_item_attributes(self, item_id):
        url = f"{self.root_url}/items/{item_id}/attributes"
        response = self.get(url)
        return response

    def get_item_attribute_subattributes(self, parent_attribute_id):
        """
        Retorna os subatributos de um atributo específico de um item.
        """
        url = f"{self.root_url}/items/attributes/{parent_attribute_id}/attributes"
        response = self.get(url)
        return response

    def get_templates(self):
        """
        Returns all templates in the specified workspace in the format
        {
            "id1": "name2",
            "id2": "name2"
        }

        """
        url = f"{self.root_url}/workspaces/{self.workspace_id}/templates"
        response = self.get(url)

        templates = {}
        for element in response:
            templates[element['id']] = element['name']
        return templates
    
    def post_template(self, template_content:dict):
        """
        Create a new template in the specified workspace.

        template_content example:

        {
            "name": "string",
            "description": "string",
            "categories": [
                "3fa85f64-5717-4562-b3fc-2c963f66afa6"
            ],
            "attributes": [
                {
                    "name": "string",
                    "description": "string",
                    "categories": [
                        "3fa85f64-5717-4562-b3fc-2c963f66afa6"
                    ],
                    "default_value": "string",
                    "type": "Manual Text", // Manual Float, Timeseries Float ...
                    "decimal_places": 0,
                    "unit_of_measurement": "string",
                    "parent_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
                }
            ]
        }
        """
        url = f"{self.root_url}/workspaces/{self.workspace_id}/templates"
        response = self.post(url, template_content)
        return response
    

    def get_template_attributes(self, template_id) -> List[Dict]:
        """
        Returns all attributes of a specific template in the format
        
        [{
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "name": "string",
                "description": "string",
                "categories": [
                    {
                    "name": "string"
                    }
                ],
                "unit_of_measurement": "string",
                "default_value": 0,
                "data_source": "Manual",
                "data_type": "Integer"
            }, ...]
        """
        url = f"{self.root_url}/workspaces/{self.workspace_id}/templates/{template_id}/attributes"
        response = self.get(url)
        return response

    def get_template_attribute_subattributes(self, attribute_id) -> List[Dict]:
        """
        Returns all subattributes of a specific template attribute in the format

        {
        "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "name": "string",
        "description": "string",
        "categories": [
            {
            "name": "string"
            }
        ],
        "unit_of_measurement": "string",
        "default_value": 0,
        "data_source": "Manual",
        "data_type": "Integer"
        },
        """
        url = f"{self.root_url}/template/attributes/{attribute_id}/subattributes"
        response = self.get(url)
        return response

    def get_item_generators(self, item_id) -> requests.Response:
        """
        Retorna os modelos/generators de um item específico.
        """

        url = f"{self.root_url}/items/{item_id}/generators"
        response = self.get(url)
        return response

    def get_categories(self, category_name=None):
        """
        Retorna as categorias disponíveis.
        """
        cache_key = category_name or "__all__"
        cached_response = self._get_cached("categories", cache_key)
        if cached_response is not None:
            return cached_response

        url = f"{self.root_url}/categories"
        if category_name:
            url += f"?category_name={category_name}"
        response = self.get(url)
        self._set_cached("categories", cache_key, response)
        return response
    
    def post_category(self, data) -> requests.Response:
        """
        Cadatra uma categoria
        data = {
                "name": "string",
                "group_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
            }
        """
        url = f"{self.root_url}/categories"
        response = self.post(url, data)
        if getattr(response, "status_code", None) in (200, 201):
            self._clear_cache("categories")
        return response
    
    def get_groups(self) -> requests.Response:
        url = f"{self.root_url}/groups"
        response = self.get(url)
        return response
    
    def post_group(self, data) -> requests.Response:
        """
        Cadastra novo grupo
        data = { "name": "string" }
        """
        url = f"{self.root_url}/groups"
        response = self.post(url, data)
        return response

    def set_template_attribute_category(self, template_attribute_id: str, category_ids: list):
        """
        Define categorias para um template attribute.
        template_attribute_id: ID do atributo do template.
        category_ids: Lista de IDs das categorias a serem atribuídas (Não funciona com nomes de categorias).
        Exemplo de category_ids: ["3fa85f64-5717-4562-b3fc-2c963f66afa6"]
        """
        url = f"{self.root_url}/template/attributes/{template_attribute_id}/category"
        data = {
            "category_ids": category_ids
        }
        response = self.post(url, data)
        return response

    def get_events(
        self,
        type: str = None,
        end_date_from: str = None,
        end_date_to: str = None,
        end_date__isnull: bool = None,
        changed_since: str = None,
        cursor: str = None,
        limit: int = None,
        **kwargs
    ) -> requests.Response:
        
        url = f"{self.root_url}/events"
        params = {
            "type": type,
            "end_date_from": end_date_from,
            "end_date_to": end_date_to,
            "end_date__isnull": end_date__isnull,
            "changed_since": changed_since,
            "cursor": cursor,
            "limit": limit,
            **kwargs
        }
        params = {key: value for key, value in params.items() if value is not None}
        response = self.get(url, data=params)
        return response

    def get_item_events_summary(self, item_id) -> requests.Response:
        url = f"{self.root_url}/items/{item_id}/events/summary"
        response = self.get(url)
        return response

    def get_events_summary(self) -> requests.Response:
        url = f"{self.root_url}/workspaces/{self.workspace_id}/events/summary"
        response = self.get(url)
        return response

    def get_root_events(self, ancestor_item_id=None, **kwargs) -> requests.Response:
        url = f"{self.root_url}/workspaces/{self.workspace_id}/events"
        if ancestor_item_id:
            url += f"?ancestor_item_id={ancestor_item_id}"
        response = self.get(url, data=kwargs)
        return response

    def get_alarms(self):
        response = self.get_events(type="Alarm")
        alarms = [event for event in response['events'] if event['event_type'] == "Alarm"]
        return alarms

    def get_condition_deviations(self):
        response = self.get_events(type="ConditionDeviation")
        condition_deviations = [
            event for event in response['events'] if event['event_type'] == "ConditionDeviation"]
        return condition_deviations

    def update_manual_attribute(self, attribute_id, value):
        url = f"{self.root_url}/items/attributes/manual/value"
        data = [
            {
                "id": attribute_id,
                "value": value
            }
        ]
        response = self.patch(url, data)
        # print(response)
        return response
    
    def get_manual_attribute_value(self, item_id) -> requests.Response:
        url = f"{self.root_url}/items/attributes/manual"
        payload = {"item_id": item_id}
        response = self.get(url, payload)
        return response
    
    def update_manual_attributes(self, item_id, attributes) -> requests.Response:
        """
        Atualiza múltiplos atributos manuais de um item.

        item_id: ID do item.
        attributes: Lista de dicionários, cada um contendo:
            - "id": str, o ID do atributo.
            - "value": str, o valor a ser definido.

        Exemplo:
        [
            {
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",  # ID do atributo
                "value": "novo_valor"
            },
            ...
        ]
        """
        url = f"{self.root_url}/items/attributes/manual/value"
        response = self.patch(url, attributes)
        # print(response.text)
        return response

    def post_template_attribute(self, template_id, attribute):
        """
        Cadastro de atributos de templates. O atributo precisa ter o seguinte formato:
            {
            "name": "string",
            "description": "string",
            "categories": ["id do atributo"],
            "default_value": "string" | None,
            "type": "Manual Text",  // Válidos: 'Manual Text', 'Manual Integer', 'Manual Float', 'Manual Boolean', 'Time Series', 'Time Series Text', 'Time Series Integer', 'Time Series Float' or 'Relational Text'
            "decimal_places": 0,
            "unit_of_measurement": "string",
            "parent_id": "id do parent"
            }
        """
        url = f"{self.root_url}/workspaces/{self.workspace_id}/templates/{template_id}/attributes"
        response = self.post(url, attribute)
        """
        Retorna {"id": "id do atributo cadastrado"}
        """
        return response

    def update_reference(self, item_id, attribute_references):
        """
        Updates the reference for timeseries attributes of an item.

        attribute_references: List of dictionaries, each containing:
            - "id": str, the attribute ID.
            - "reference": str, the reference value to set.

        Example:
        [
            {
            "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",  # Attribute ID
            "reference": "reference_string"
            }
        ]
        """
        url = f"{self.root_url}/items/{item_id}/attributes/timeseries/reference"
        response = self.put(url, attribute_references)
        return response
    
    def update_attribute_batch(self, item_id, attributes:list) -> requests.Response:
        """
        Atualiza múltiplos atributos de um item.

        item_id: ID do item.
        attributes: lista de dicionários, cada um contendo:
            - "id": str, o ID do atributo.
            - "unit_of_measurement": str, a unidade de medida a ser definida.
            - "engineering_unit": str, a unidade de engenharia a ser definida.
            - "decimal_places": int, o número de casas decimais a ser definido.
            - "reference": str, o valor de referência a ser definido.

        Exemplo:
        [
            {
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "unit_of_measurement": "string",
                "engineering_unit": "string",
                "decimal_places": 0,
                "reference": "string"
            }
        ]
        """
        attributes = {"attributes": attributes}
        url = f"{self.root_url}/items/{item_id}/attributes/batch"
        response = self.patch(url, attributes)
        return response
    
    def get_timeseries_attributes(self, item_id:str) -> requests.Response:
        """
        Retorna os atributos do tipo timeseries de um item específico.
        """
        url = f"{self.root_url}/items/{item_id}/attributes/timeseries"
        response = self.get(url)
        return response
    
    def get_timeseries_values(self, item_id:str, tags:str=None, start_date:str=None, end_date:str=None, window:str='1h') -> requests.Response:
        """
        Retorna os valores de uma timeseries de um item específico.
        tags = "tag1,tag2,tag3"
        """
        url = f"{self.root_url}/items/{item_id}/attributes/timeseries/values?"
        payload = {"item_id": item_id, "window": window}
        if tags:
            url += f"tags={tags}&"
        if start_date:
            url += f"start_date={start_date}&"
        if end_date:
            url += f"end_date={end_date}&"
        response = self.get(url, payload)
        return response

    def get_external_oil_analysis(
        self,
        item_id: str,
        start_date: str = None,
        end_date: str = None,
    ) -> requests.Response:
        """
        Retorna a análise externa de óleo de um item específico.

        Endpoint: GET /items/{item_id}/external/oil/analysis
        Query params opcionais: start_date, end_date
        """
        url = f"{self.root_url}/items/{item_id}/external/oil/analysis"
        payload = {}
        if start_date:
            payload["start_date"] = start_date
        if end_date:
            payload["end_date"] = end_date

        response = self.get(url, data=payload or None)
        return response
    
    def get_item_categories(self, item_id: str) -> dict:
        """
        Retorna todas as categorias de um item.
        Resposta: {"categories": [{"id": "...", "name": "..."}, ...]}
        """
        url = f"{self.root_url}/items/{item_id}/categories"
        return self.get(url)

    def add_item_categories(self, item_id: str, category_ids: list) -> requests.Response:
        """
        Adiciona categorias a um item sem remover as existentes.
        category_ids: lista de UUIDs. Exemplo: ["3fa85f64-5717-4562-b3fc-2c963f66afa6"]
        """
        url = f"{self.root_url}/items/{item_id}/categories"
        return self.post(url, {"category_ids": category_ids})

    def replace_item_categories(self, item_id: str, category_ids: list) -> requests.Response:
        """
        Substitui todas as categorias de um item pelas fornecidas.
        category_ids: lista de UUIDs.
        """
        url = f"{self.root_url}/items/{item_id}/categories"
        return self.put(url, {"category_ids": category_ids})

    def create_item(self, template_id, item_data:dict) -> requests.Response:
        """
        Creates a new item based on a specified template.
        
        Example of item_data:
        {
            "name": "string",
            "description": "string",
            "parent_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "categories": [
                "3fa85f64-5717-4562-b3fc-2c963f66afa6"
            ]
        }


        """
        url = f"{self.root_url}/workspaces/{self.workspace_id}/templates/{template_id}/items"
        response = self.post(url, item_data)

        """
        response
        {
        "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "name": "string",
        "description": "string"
        }
        """
        return response
    
    def delete_template_attribute(self, attribute_id:str) -> requests.Response:
        url = f"{self.root_url}/template/attributes/{attribute_id}"
        return self.delete(url, data={})
    

    def update_item(self, item_id: str, data: dict) -> requests.Response:
        url = f"{self.root_url}/items/{item_id}"
        return self.patch(url, data)

    def delete_item(self, item_id: str) -> requests.Response:
        url = f"{self.root_url}/items/{item_id}"
        return self.delete(url, data={})

    def change_generator_status(self, generator_id:str, status:str) -> requests.Response:
        """
        Change the status of a generator for a specific item. From ONLINE to OFFLINE or vice versa.

        status: "ONLINE" or "OFFLINE"
        """
        if status not in ["ONLINE", "OFFLINE"]:
            raise ValueError("Status must be either 'ONLINE' or 'OFFLINE'.")
        endpoint = 'activate' if status == "ONLINE" else 'deactivate'

        url = f"{self.root_url}/generators/{generator_id}/{endpoint}"
        response = self.post(url, data={})
        return response

    def post_event(self, payload):
        """
        Create a new event. Payload example:
        {
            "item_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6", # ID do item
            "template_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6", # template do evento "Alarm"
            "parent_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6", # ???
            "name": "string",
            "start_date": "2025-12-17T17:50:41.871Z",
            "end_date": "2025-12-17T17:50:41.872Z",
            "data": {}
        }

        data pode ser para alarmes ou cases

        Alarmes:
        data = {
            'method': 'KB',
            'status': 'OPEN',
            'category': None,
            'end_date': '2026-02-26T13:46:00+00:00',
            'severity': 'Minor',
            'prognosis': "Identificado:\n'Diferença de Pressão - Filtro de Injeção de Gás de Selagem Primária' (FRTS_OPC_PDIT_1356) atingiu o limiar alto (1.0 kPa) Thresholds setados: pré alarme alto = 0.9, alto = 1.0\nRecomendações: 1) Checar se há falha de instrumentação (medição de pressão incorreta); 2) Realizar inspeção ou troca do filtro, pois essa condição pode comprometer a eficiência do sistema de selagem, aumentando o risco de vazamentos e desgaste nas partes internas.",
            'model_name': 'FCAltaPressaoDiferencialnoFiltrodeGasdeSelagemParaFRADECAE1350_HPCompressorTrem1',
            'description': 'FC - Alta Pressão Diferencial no Filtro de Gás de Selagem',
            'classification': None,
            'recommendation': 'Recomendações: 1) Checar se há falha de instrumentação (medição de pressão incorreta); 2) Realizar inspeção ou troca do filtro, pois essa condição pode comprometer a eficiência do sistema de selagem, aumentando o risco de vazamentos e desgaste nas partes internas.',
            'not_useful_reason': None
        }

        Cases:
        data = {
            'status': 'INVESTIGATING',
            'subunit': '',
            'sap_note': '',
            'detailing': 'Modelo de alto consumo de óleo para Turbinas detectou uma taxa diária negativa acima do comum para esse tipo de máquina. Analisando o histórico do equipamento foi possível constatar que essa condição já existia desde 10/2023.',
            'diagnosis': 'Queda acentuada e contínua no nível de óleo sintético',
            'dimension': 'AUXILIARY_SYSTEM',
            'pi_web_id': '',
            'created_at': '2025-02-27T14:26:39.441988+00:00',
            'created_by': 'matheus.dias@shapedigital.com',
            'description': '',
            'failure_mode': '',
            'deviation_end': '',
            'linked_alarms': [],
            'deviation_start': '2025-02-25T00:00:00+00:00',
            'equipment_class': '',
            'detection_method': 'LIGHTHOUSE',
            'savings_required': False,
            'failure_mechanism': '',
            'is_out_of_service': False,
            'maintainable_item': '',
            'maintenance_scope': '',
            'recommended_action': 'Inspecionar sistema de óleo e procurar por vazamentos.\nInspecionar turbina e mancais.\nSanar vazamentos ou folgas excessivas que possam estar causando a queda no nível de óleo.',
            'condition_evaluation': 'POTENTIAL_PROBLEM'
        }
        """
        url = f"{self.root_url}/events"
        response = self.post(url, payload)
        return response
    
    def post_concept_name(self, template_attribute_id: str, concept_name: str) -> requests.Response:
        """
        Define o nome do conceito para um atributo de template específico.
        """
        url = f"{self.root_url}/template/attributes/{template_attribute_id}/rename"
        data = {
            "new_concept_id": concept_name
        }
        response = self.post(url, data)
        return response

def connect(client_name: str, environment: str, debug: bool) -> Lighthouse:
    """
    Module-level factory that returns a `Lighthouse` instance for the
    specified `client_name` and `environment`.

    Example:
        from Lighthouse.lighthouse import connect
        client = connect('jirau', 'prod')
        client.get_items()
    """
    client_info = clients[environment][client_name]

    oauth2 = None
    if client_info.get("auth") == "oauth2":
        oauth2 = {
            "client_id": client_info["client_id"],
            "client_secret": client_info["client_secret"],
            "token_url": client_info["token_url"],
            "scope": client_info["scope"],
        }

    return Lighthouse(
        api_key=client_info.get("api_key", ""),
        workspace_id=client_info["workspace_id"],
        url=client_info["url"],
        debug=debug,
        oauth2=oauth2,
    )

class DummyResponse:
    def __init__(self):
        self.status_code = 200
        self.text = '{"message": "Debug mode - no data posted."}'

    def json(self):
        return {"message": "Debug mode - no data posted."}

def _load_clients() -> dict:
    candidates = [
        Path(os.environ.get("CLIENTS_JSON_PATH", "")),
        Path(__file__).resolve().parent.parent.parent / "clients.json",
        Path("/app/clients.json"),
    ]
    for path in candidates:
        if path.is_file():
            with open(path, encoding="utf-8") as f:
                return json.load(f)

    env_json = os.environ.get("LIGHTHOUSE_CLIENTS")
    if env_json:
        return json.loads(env_json)

    raise FileNotFoundError(
        "clients.json nao encontrado e variavel LIGHTHOUSE_CLIENTS nao definida."
    )

clients = _load_clients()

__all__ = ["Lighthouse", "connect", "clients"]
