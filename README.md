# Lighthouse API - Enroll Templates & Items

Este repositório contém utilitários em Python para automatizar o processo de cadastro (enrollment) de templates, atributos e atualização de itens no ecossistema da Lighthouse API.

O objetivo principal é sincronizar dados provenientes de "Dicionários de Dados" (arquivos Excel) com workspaces específicos do Lighthouse de forma massiva, segura e padronizada.

## Começando

### Pré-requisitos

Certifique-se de ter o Python 3.8+ instalado e as seguintes dependências:

```bash
pip install pandas openpyxl tqdm xlsxwriter numpy
```

> **Nota:** Este projeto depende da biblioteca interna `lighthouse`. Certifique-se de que ela está acessível no seu ambiente Python.

### Estrutura do Projeto

- `templates.py`: Script para criar/atualizar Templates e seus Atributos.
- `items.py`: Script para atualizar os valores dos atributos nos Itens (equipamentos) já existentes.
- `config.py`: Centraliza a configuração do cliente API e o sistema de logs.
- `dictionaries.py`: Arquivo de configuração que mapeia onde estão os arquivos Excel de cada cliente.
- `data_processor.py`: Motor de ingestão que detecta a versão da planilha e normaliza os dados para um schema único.
- `utils.py`: Funções auxiliares para normalização de nomes, unidades e travessia de atributos.
- `logs/`: Diretório gerado automaticamente para armazenar os logs de execução e relatórios.

---

## Configuração de Novos Clientes

### 1. Configurar as credenciais no `lighthouse` library
Certifique-se de que o cliente está cadastrado no dicionário `clients` da biblioteca interna para os ambientes `dev` e/ou `prod`.

### 2. Mapear as planilhas em `dictionaries.py`
Defina o caminho absoluto e as abas (sheets) que devem ser processadas. O script detectará automaticamente se a planilha segue o padrão V1 ou V2.

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
python shape_workspace_wrapper/items.py <cliente> [ambiente]
```

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
