# Lighthouse API - Enroll Templates & Items

Este repositório contém utilitários em Python para automatizar o processo de cadastro (enrollment) de templates, atributos e atualização de itens no ecossistema da Lighthouse API.

O objetivo principal é sincronizar dados provenientes de "Dicionários de Dados" (arquivos Excel) com workspaces específicos do Lighthouse de forma massiva, segura e padronizada.

## Começando

### Pré-requisitos

Certifique-se de ter o Python 3.8+ instalado e as seguintes dependências:

```bash
pip install pandas openpyxl tqdm xlsxwriter numpy pytest
```

> **Nota:** Este projeto depende da biblioteca interna `lighthouse`. Certifique-se de que ela está acessível no seu ambiente Python.

### Estrutura do Projeto

- `templates.py`: Script para criar/atualizar Templates e seus Atributos.
- `items.py`: Script para atualizar os valores dos atributos nos Itens (equipamentos) já existentes.
- `verify_enrollment.py`: Script de verificação — compara o que está cadastrado em templates e atributos na API com o dicionário de dados.
- `verify_items.py`: Script de verificação — compara o que está cadastrado nos equipamentos (referências, valores manuais) com o dicionário de dados.
- `config.py`: Centraliza a configuração do cliente API e o sistema de logs.
- `dictionaries.py`: Arquivo de configuração que mapeia onde estão os arquivos Excel de cada cliente.
- `data_processor.py`: Motor de ingestão que detecta a versão da planilha e normaliza os dados para um schema único.
- `utils.py`: Funções auxiliares para normalização de nomes, unidades e travessia de atributos.
- `logs/`: Diretório gerado automaticamente para armazenar os logs de execução e relatórios.
- `tests/`: Testes unitários (pytest) cobrindo o pipeline de ETL, funções utilitárias e lógica de templates.

---

## Configuração de Novos Clientes

### 1. Configurar as credenciais no `lighthouse` library
Certifique-se de que o cliente está cadastrado no dicionário `clients` da biblioteca interna para os ambientes `dev` e/ou `prod`.

### 2. Configurar o caminho base das planilhas

Copie o arquivo `.env.example` para `.env` e preencha com o caminho da pasta de implementação sincronizada localmente no seu computador:

```bash
cp .env.example .env
```

Edite o `.env`:
```
SHAPE_DOCS_PATH=C:\Users\SeuNome\Shape Digital\Implementation & Diagnostics - Documentos\General\2. Implementation
```

> **Nota:** O arquivo `.env` é ignorado pelo git

### 3. Mapear as planilhas em `dictionaries.py`
Defina as abas que devem ser processadas. Os caminhos das planilhas são construídos automaticamente a partir do `SHAPE_DOCS_PATH`. O script detectará automaticamente se a planilha segue o padrão V1 ou V2.

---

## Testes

Os testes unitários cobrem o pipeline de ETL (`data_processor.py`) e funções utilitárias (`utils.py`), sem depender de arquivos Excel reais nem da API.

```bash
python -m pytest tests/ -v
```

Um pre-commit hook está configurado em `.git/hooks/pre-commit` e executa os testes automaticamente antes de cada `git commit`. Se algum teste falhar, o commit é bloqueado.

---

## Como Usar

Os scripts aceitam dois argumentos: `cliente` (obrigatório) e `ambiente` (opcional, padrão é `dev`).

### 1. Cadastrar Templates e Atributos
Lê o dicionário, cria templates/categorias ausentes e cadastra atributos/subatributos.

```bash
python shape_workspace_wrapper/templates.py <cliente> [ambiente]
```

### 2. Atualizar Valores dos Itens
Envia os valores reais (tags ou constantes) para os equipamentos existentes.

```bash
python items.py <cliente> [ambiente]
```

### 3. Verificar Cadastro de Templates
Compara o que está cadastrado nos templates da API (atributos, subatributos, categorias, unidades) com o dicionário de dados. Gera um relatório `.xlsx` em `logs/` com todas as divergências.

```bash
python verify_enrollment.py <cliente> [ambiente]
```

### 4. Verificar Cadastro de Equipamentos
Compara o que está cadastrado nos itens do workspace (presença de atributos, referências de tags, valores manuais) com o dicionário de dados. Gera um relatório `.xlsx` em `logs/`.

```bash
python verify_items.py <cliente> [ambiente]
```

---

## Scripts Auxiliares (`other_scripts/`)

Scripts interativos (blocos `#%%`) para tarefas pontuais que não fazem parte do pipeline principal. Cada um deve ter o `CLIENT` e o `ENVIRONMENT` ajustados antes de executar.

### `audit_health_score.py`
Audita e corrige os atributos de **Health Score** de todos os itens de um workspace.

- Determina se cada item é **folha** (sem filhos) ou **não-folha** usando o campo `has_children` da API.
- Verifica se o atributo `Health Score Method` está com o valor correto:
  - Folha → `"Complex Average"`
  - Não-folha → `"Weighted Average"`
- Identifica itens com atributos/subatributos de HS ausentes e os cadastra no template correspondente.
- Gera relatório `.xlsx` em `logs/` com o resultado de cada verificação e correção.

### `enroll_default_attrs_all_templates.py`
Garante que **todos os templates** do workspace possuem os atributos e subatributos padrão definidos em `default_attributes.json`.

- Itera sobre todos os templates e chama o mesmo mecanismo de cadastro do pipeline principal (`enroll_default_attributes` / `enroll_default_subattributes`).
- Ao final, faz uma verificação pós-cadastro e lista o que ainda estiver ausente.
- Gera relatório `.xlsx` em `logs/`.

### `update_item_categories_jirau.py`
Atualiza as **categorias de itens** com base no template ao qual pertencem.

- Mapeamento configurável no topo do script (`TEMPLATE_CATEGORY_MAP`).
- Encontra ou cria cada categoria necessária antes de atribuí-la.
- Usa `POST /items/{id}/categories` (adiciona sem remover categorias existentes).
- Verifica se o item já possui a categoria antes de fazer a chamada.
- Gera relatório `.xlsx` em `logs/` com status `updated` / `skipped` / `failed` por item.

### `get_template_attribute_ids.py`
Exporta os atributos de templates selecionados para um arquivo `template_attributes.csv`.

- Filtra por uma lista de nomes de templates e por `data_source` (por padrão, exclui atributos manuais para manter apenas os de time series).
- O CSV gerado deve ser **revisado manualmente** antes de ser usado como entrada do script de deleção.
- > ⚠️ Verifique com atenção: atributos cadastrados por outros dicionários de dados (ex: `Status`, `Tag SAP`, `Tag Oil Analysis`) **não devem** ser incluídos na deleção.

### `delete_template_attributes.py`
Deleta em lote os atributos de template listados em `template_attributes.csv` (gerado pelo script acima).

- Lê o CSV, extrai os IDs e chama `DELETE /template/attributes/{id}` para cada um.
- Deve ser executado **somente após revisão cuidadosa** do CSV de entrada.

### `export_models_and_attributes.py`
Exporta todos os modelos (generators) e atributos de todos os itens abaixo de um nó raiz para um arquivo `.xlsx`.

- Percorre a árvore de itens recursivamente a partir de um `ROOT_NODE` configurável.
- Para cada item, busca em paralelo os generators e os atributos (incluindo subatributos).
- Salva progresso incremental em `.parquet` para evitar perda de dados em execuções longas.
- Útil para auditorias gerais, análise de cobertura de modelos e exportação de inventário.

---

## Padrão das Planilhas (Ingestão Automática)

O sistema de ingestão (`ingest_pipeline`) é capaz de identificar e processar dois formatos de planilha:

### Dicionário V1 (Legado)
Utiliza cabeçalhos em português e separa subatributos usando o caractere `|`.
- **Colunas Obrigatórias**: `Template`, `Equipamento`, `attribute_name` (formato `Pai | Filho`), `Value`, `unit_of_measurement`, `decimal_places`, `Categories`.

### Dicionário V2 (Novo Padrão)
Utiliza cabeçalhos em inglês e colunas separadas para referências e valores.
- **Colunas Obrigatórias**: `template`, `asset_name`, `attribute_name`, `subattribute_name`, `reference` (tag), `value` (valor fixo), `type`, `categories`.
- **Tipos Suportados (`type`)**: `Time Series Float`, `Manual Text`, `Manual Float`, `Manual Integer`, `Time Series Integer`.

---

## Funcionalidades Avançadas

### Múltiplas Categorias
O campo de categorias (`Categories` ou `categories`) agora aceita múltiplas entradas separadas por vírgula.
- **Exemplo**: `Sensores, Termodinâmica, Critical`
- O script garantirá que cada categoria seja criada no workspace e vinculada ao atributo.

### Normalização de Unidades
Unidades de medida são automaticamente corrigidas para o padrão SI/Lighthouse (ex: `kpa` -> `kPa`, `°c` -> `°C`).

### Relatórios de Execução
Ao final de cada rodada, um relatório `.xlsx` é gerado em `logs/` contendo:
- **Summary**: Estatísticas globais de sucesso/falha.
- **Detailed_Report**: Status linha a linha da planilha original.
- **Not_Found_in_WS**: Itens que não foram localizados no workspace para atualização.
