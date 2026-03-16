# Lighthouse API - Enroll Templates & Items

Este repositório contém utilitários em Python para automatizar o processo de cadastro (enrollment) de templates, atributos e atualização de itens no ecossistema da Lighthouse API.

O objetivo principal é sincronizar dados provenientes de "Dicionários de Dados" (arquivos Excel) com workspaces específicos do Lighthouse de forma massiva e segura.

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
- `data_processor.py`: Módulo que lê e limpa os dados das planilhas.
- `logs/`: Diretório gerado automaticamente para armazenar os logs de execução e relatórios.

---

## Configuração de Novos Clientes

Para adicionar um novo cliente ao utilitário, você precisa seguir dois passos:

### 1. Configurar as credenciais no `lighthouse` library
O script utiliza a função `get_lighthouse_client` que busca as credenciais (API Key, Workspace ID, URL) na biblioteca `lighthouse`. Certifique-se de que o cliente está cadastrado no dicionário `clients` da biblioteca para os ambientes `dev` e/ou `prod`.

### 2. Mapear as planilhas em `dictionaries.py`
Neste arquivo, você define o caminho absoluto das planilhas e quais abas (sheets) devem ser lidas.

```python
# Exemplo no dictionaries.py
DICTIONARIES = {
    "nome_do_cliente": [
        {
            "spreadsheet": r"C:\Caminho\Para\O\Dicionario_V1.xlsx",
            "tabs": ["Nome_da_Aba1", "Nome_da_Aba2"],
        },
    ],
}
```

---

## Como Usar

Os scripts são executados via linha de comando e aceitam dois argumentos: `cliente` (obrigatório) e `ambiente` (opcional, padrão é `dev`).

### 1. Cadastrar Templates e Atributos
Este script lê o dicionário, verifica se o template existe (senão, cria), cadastra as categorias necessárias e cadastra todos os atributos e subatributos definidos.

```bash
python templates.py <cliente> [ambiente]
# Exemplo:
python templates.py petroreconcavo prod
```

**O que ele faz:**
- Cria Categorias ausentes.
- Cria Templates ausentes.
- Adiciona Atributos padrão (definidos em `default_attributes.json`).
- Adiciona Atributos específicos da planilha.
- Configura Subatributos (aninhamento).

### 2. Atualizar Valores dos Itens
Após os templates estarem configurados, use este script para enviar os valores reais dos equipamentos.

```bash
python items.py <cliente> [ambiente]
# Exemplo:
python items.py petroreconcavo prod
```

**O que ele faz:**
- Busca os itens no workspace pelo nome (coluna `Equipamento`).
- Identifica os IDs dos atributos e subatributos.
- Realiza atualizações em lote (batch update) para performance.
- Gera um relatório detalhado em Excel na pasta `logs/`.

---

## Logs e Relatórios

Cada execução gera dois tipos de rastro:

1.  **Arquivo de Log (.log):** Localizado em `logs/items_TIMESTAMP.log` ou `logs/templates_TIMESTAMP.log`. Contém o histórico detalhado de cada chamada à API, erros e avisos.
2.  **Relatório de Execução (.xlsx):** Para o script de itens, um relatório detalhado é gerado mostrando exatamente o que foi atualizado, o que não foi encontrado e quais erros ocorreram por item/atributo.

---

## Padrão das Planilhas (Excel)

Para que o `data_processor.py` funcione corretamente, as planilhas devem conter as seguintes colunas (mínimo):

- **Template**: Nome do template do Lighthouse.
- **Equipamento**: Nome do item/equipamento no workspace.
- **attribute_name**: Nome do atributo. Use o formato `Pai | Filho` para subatributos.
- **Value**: Valor atual do atributo (para `items.py`).
- **unit_of_measurement**: Unidade (ex: ºC, bar, kPa).
- **decimal_places**: Quantidade de casas decimais (padrão 2).
- **Categories**: Categorias do template (separadas por vírgula).
