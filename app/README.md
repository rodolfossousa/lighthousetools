# Lighthouse Tools

Aplicacao web (Streamlit) para gestao de ativos, templates e dicionarios de dados integrada com a API do Lighthouse.

## Requisitos

- Python 3.10+
- Dependencias: `pip install -r requirements.txt`
- A biblioteca `lighthouse` deve estar instalada localmente: `pip install -e ../Lighthouse`

## Como executar

```bash
cd app
streamlit run main.py
```

Credenciais padrao: `admin` / `admin`

## Estrutura

```
app/
  main.py              # Ponto de entrada, login, selecao de ambiente, navegacao
  db.py                # Base de dados de utilizadores (users.db) - autenticacao, CRUD
  db_lighthouse.py     # Base de dados Lighthouse (lighthouse_attributes.db) - items, templates, dicionarios
  sync.py              # Logica de sincronizacao: busca dados da API e grava no SQLite local
  requirements.txt     # Dependencias Python
  users.db             # SQLite - utilizadores e credenciais
  pages/
    sincronizacao.py   # Pagina de sincronizacao de dados
    explorador.py      # Pagina de exploracao de ativos
    biblioteca.py      # Pagina de biblioteca de templates
    modelos.py         # Pagina de gestao de modelos/generators
    dicionario.py      # Pagina de dicionario de dados
```

## Funcionalidades

### Login e Ambiente

- Autenticacao por username/senha com hash bcrypt.
- Selecao de ambiente (prod, dev, homol) e cliente (prio, modec, jirau, etc.) ao iniciar sessao.
- Painel de administracao para criar, remover e resetar senhas de utilizadores.

### Sincronizacao de Dados

Pagina que importa dados da API do Lighthouse para a base de dados local SQLite.

**Items / Atributos / Generators:**
- Pesquisa um item raiz pelo nome no workspace.
- Percorre toda a arvore de subitems recursivamente.
- Grava items, atributos (manuais e timeseries), subatributos e generators no SQLite.

**Template Attributes:**
- Lista todos os templates do workspace.
- Permite selecionar templates especificos ou sincronizar todos.
- Grava atributos e subatributos de cada template no SQLite.

Ambas as sincronizacoes registam historico com data da ultima atualizacao.

### Explorador de Ativos

Navegacao em arvore dos items sincronizados, organizados por vessel.

- **Atributos:** visualizacao e edicao de atributos manuais. Alteracoes sao enviadas a API e gravadas localmente.
- **Limiares:** edicao de subatributos (thresholds) agrupados por atributo pai. Salvamento envia a API via PATCH.
- **Modelos:** lista de generators associados ao item.
- **Acoes:** criar item filho (via API + SQLite), renomear item, remover item.

### Biblioteca de Templates

Visualizacao dos templates sincronizados em formato de arvore hierarquica.

- Arvore organizada por template > categoria > atributo > subatributo.
- Detalhe de cada template mostra totais de atributos e resumo por tipo (Manual, TimeSeries).
- Detalhe de cada atributo mostra data source, data type, unidade, valor padrao, descricao e subatributos.

### Modelos (Generators)

Tabela de todos os generators sincronizados com filtro por vessel e busca textual.

- Selecao multipla de modelos na tabela.
- Alteracao de status em lote (ONLINE / OFFLINE) via API.
- Barra de progresso e relatorio de erros.

### Dicionario de Dados

Ferramenta para planear e cadastrar hierarquias de equipamentos no workspace do Lighthouse.

**Conceito:**
Um dicionario de dados e um projecto que define a estrutura de items (Plant > System > Equipamento) com os seus atributos e limiares antes de os cadastrar na API.

**Fluxo de trabalho:**
1. Criar novo dicionario (nome, cliente, ambiente).
2. O primeiro item deve ser do template **Plant**. Neste passo e obrigatorio informar o **ID do item pai no workspace** (o item existente no Lighthouse sob o qual a Plant sera criada).
3. Adicionar items filhos com templates (System/Subsystem, equipamentos, etc.).
4. Preencher atributos: tags/referencias para timeseries, valores para manuais, unidades, casas decimais.
5. Preencher limiares (subatributos) como alarmes e limites operacionais.
6. Cadastrar no Workspace: envia toda a hierarquia a API do Lighthouse.

**Regras de cadastro no workspace:**
- Items que ja foram cadastrados (possuem `ws_item_id` na base local) sao verificados via API. Se ainda existem, apenas os atributos sao atualizados. Se foram apagados, sao recriados.
- Items novos (sem `ws_item_id`) sao criados via API e o ID retornado e guardado localmente.
- A hierarquia pai-filho e respeitada: cada item e criado como filho do respectivo pai no workspace.
- O dicionario permanece editavel apos o cadastro. E possivel adicionar novos items e re-cadastrar.

**Atributos:**
- Atributos TimeSeries: campos de tag/referencia, unidade de medida e casas decimais.
- Atributos Manuais: campo de valor.
- Limiares: subatributos editaveis, agrupados pelo atributo pai.

## Base de Dados

A aplicacao usa dois ficheiros SQLite:

**users.db** — Gestao de utilizadores
- `users`: id, username, password_hash, name, is_admin

**lighthouse_attributes.db** — Dados do Lighthouse
- `lighthouse_attributes`: items, atributos, subatributos e generators sincronizados (por vessel)
- `template_attributes`: atributos de templates sincronizados (por ambiente/cliente)
- `sync_history`: registo de sincronizacoes realizadas
- `dd_projects`: dicionarios de dados (nome, cliente, ambiente, status, ws_parent_id)
- `dd_items`: items do dicionario (nome, template, hierarquia, ws_item_id)
- `dd_attributes`: atributos e subatributos dos items do dicionario
