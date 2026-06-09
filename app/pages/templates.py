import streamlit as st
import pandas as pd
from db_lighthouse import get_template_list, get_template_attr_tree, save_template_attributes_to_db
from lighthouse import Lighthouse, clients

ATTRIBUTE_TYPES = [
    "Manual Text",
    "Manual Integer",
    "Manual Float",
    "Manual Boolean",
    "Time Series",
    "Time Series Text",
    "Time Series Integer",
    "Time Series Float",
    "Relational Text",
]


def render():
    st.title("Cadastro de Templates")

    ws = st.session_state.get("ws")
    if ws is None:
        st.warning("Seleciona um ambiente primeiro.")
        return

    tab_create, tab_import, tab_copy = st.tabs([
        "Criar Template",
        "Importar de Excel/CSV",
        "Copiar entre Ambientes",
    ])

    with tab_create:
        _create_template_section(ws)

    with tab_import:
        _import_template_section(ws)

    with tab_copy:
        _copy_template_section(ws)


# --------------- criar template ---------------

def _create_template_section(ws: Lighthouse):
    st.subheader("Novo Template")

    with st.form("create_template", clear_on_submit=False):
        name = st.text_input("Nome do template")
        description = st.text_input("Descricao (opcional)")

        st.markdown("**Atributos**")
        st.caption("Preenche a tabela abaixo. Uma linha por atributo.")

        num_attrs = st.number_input("Numero de atributos", min_value=1, max_value=200, value=5, step=1)
        submitted = st.form_submit_button("Proximo: definir atributos", type="primary")

    if submitted and name:
        st.session_state["_tmpl_create_name"] = name
        st.session_state["_tmpl_create_desc"] = description
        st.session_state["_tmpl_create_num"] = int(num_attrs)

    if "_tmpl_create_name" not in st.session_state:
        return

    _show_attribute_editor(ws)


def _show_attribute_editor(ws: Lighthouse):
    num = st.session_state["_tmpl_create_num"]
    tmpl_name = st.session_state["_tmpl_create_name"]

    st.markdown(f"### Atributos para **{tmpl_name}**")

    default_data = {
        "Nome": [""] * num,
        "Tipo": [ATTRIBUTE_TYPES[0]] * num,
        "Unidade": [""] * num,
        "Casas Decimais": [2] * num,
        "Valor Padrao": [""] * num,
        "Descricao": [""] * num,
    }

    edited = st.data_editor(
        pd.DataFrame(default_data),
        column_config={
            "Tipo": st.column_config.SelectboxColumn(options=ATTRIBUTE_TYPES, required=True),
            "Casas Decimais": st.column_config.NumberColumn(min_value=0, max_value=10, step=1),
        },
        num_rows="dynamic",
        use_container_width=True,
        key="tmpl_attr_editor",
    )

    if st.button("Cadastrar Template", type="primary", key="btn_create_template"):
        attrs = _build_attributes_from_df(edited)
        valid_attrs = [a for a in attrs if a["name"].strip()]

        if not valid_attrs:
            st.warning("Adiciona pelo menos um atributo com nome.")
            return

        payload = {
            "name": tmpl_name,
            "description": st.session_state.get("_tmpl_create_desc", ""),
            "attributes": valid_attrs,
        }

        response = ws.post_template(payload)
        if hasattr(response, "status_code") and response.status_code in (200, 201):
            st.success(f"Template **{tmpl_name}** criado com {len(valid_attrs)} atributo(s).")
            _clear_create_state()
        else:
            status = getattr(response, "status_code", "?")
            text = getattr(response, "text", str(response))
            st.error(f"Erro: HTTP {status} — {text}")


def _build_attributes_from_df(df: pd.DataFrame) -> list[dict]:
    attrs = []
    for _, row in df.iterrows():
        name = str(row.get("Nome", "")).strip()
        if not name:
            continue
        attr = {
            "name": name,
            "type": row.get("Tipo", "Manual Text"),
            "description": str(row.get("Descricao", "") or ""),
            "unit_of_measurement": str(row.get("Unidade", "") or ""),
            "decimal_places": int(row.get("Casas Decimais", 2) or 2),
            "default_value": str(row.get("Valor Padrao", "") or "") or None,
        }
        attrs.append(attr)
    return attrs


def _clear_create_state():
    for k in list(st.session_state.keys()):
        if k.startswith("_tmpl_create"):
            st.session_state.pop(k, None)


# --------------- importar de Excel/CSV ---------------

def _import_template_section(ws: Lighthouse):
    st.subheader("Importar Template de Excel/CSV")

    st.markdown("""
**Formato esperado do ficheiro:**

| Nome | Tipo | Unidade | Casas Decimais | Valor Padrao | Descricao | Parent |
|------|------|---------|----------------|--------------|-----------|--------|
| Temperature | Time Series Float | °C | 2 | | Temperatura | |
| High Limit | Manual Float | °C | 1 | 100 | Limiar alto | Temperature |

- **Tipo**: `Manual Text`, `Manual Integer`, `Manual Float`, `Manual Boolean`, `Time Series`, `Time Series Float`, etc.
- **Parent**: nome do atributo pai (para subatributos). Deixar vazio para atributos raiz.
    """)

    template_name = st.text_input("Nome do template", key="import_tmpl_name")
    template_desc = st.text_input("Descricao (opcional)", key="import_tmpl_desc")

    uploaded = st.file_uploader("Ficheiro Excel (.xlsx) ou CSV (.csv)", type=["xlsx", "csv"], key="import_file")

    if not uploaded or not template_name:
        return

    try:
        if uploaded.name.endswith(".csv"):
            df = pd.read_csv(uploaded)
        else:
            df = pd.read_excel(uploaded)
    except Exception as e:
        st.error(f"Erro ao ler ficheiro: {e}")
        return

    required_cols = ["Nome", "Tipo"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error(f"Colunas obrigatorias em falta: {', '.join(missing)}")
        return

    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption(f"{len(df)} linha(s) encontrada(s)")

    if st.button("Cadastrar Template", type="primary", key="btn_import_template"):
        _import_and_create(ws, template_name, template_desc, df)


def _import_and_create(ws: Lighthouse, name: str, description: str, df: pd.DataFrame):
    root_attrs = []
    sub_attrs = []
    parent_col = "Parent" if "Parent" in df.columns else None

    for _, row in df.iterrows():
        attr_name = str(row.get("Nome", "")).strip()
        if not attr_name:
            continue
        attr = {
            "name": attr_name,
            "type": row.get("Tipo", "Manual Text"),
            "description": str(row.get("Descricao", "") or ""),
            "unit_of_measurement": str(row.get("Unidade", "") or ""),
            "decimal_places": int(row.get("Casas Decimais", 2) if pd.notna(row.get("Casas Decimais")) else 2),
            "default_value": str(row.get("Valor Padrao", "") or "") or None,
        }
        parent_name = str(row.get(parent_col, "") or "").strip() if parent_col else ""

        if parent_name:
            sub_attrs.append((attr, parent_name))
        else:
            root_attrs.append(attr)

    if not root_attrs:
        st.warning("Nenhum atributo raiz encontrado.")
        return

    payload = {
        "name": name,
        "description": description or "",
        "attributes": root_attrs,
    }

    progress = st.progress(0, text="Criando template...")
    response = ws.post_template(payload)

    if not (hasattr(response, "status_code") and response.status_code in (200, 201)):
        status = getattr(response, "status_code", "?")
        text = getattr(response, "text", str(response))
        st.error(f"Erro ao criar template: HTTP {status} — {text}")
        return

    template_data = response.json()
    template_id = template_data.get("id", "")
    progress.progress(0.5, text="Template criado. Cadastrando subatributos...")

    if sub_attrs and template_id:
        attrs_response = ws.get_template_attributes(template_id)
        ws_attrs = attrs_response.get("attributes", []) if isinstance(attrs_response, dict) else []
        name_to_id = {a["name"].strip().lower(): a["id"] for a in ws_attrs}

        created_subs = 0
        for sub_attr, parent_name in sub_attrs:
            parent_id = name_to_id.get(parent_name.strip().lower())
            if parent_id:
                sub_attr["parent_id"] = parent_id
                resp = ws.post_template_attribute(template_id, sub_attr)
                if hasattr(resp, "status_code") and resp.status_code in (200, 201):
                    created_subs += 1
                else:
                    st.warning(f"Erro ao criar subatributo **{sub_attr['name']}**: {getattr(resp, 'text', '')}")
            else:
                st.warning(f"Parent **{parent_name}** nao encontrado para subatributo **{sub_attr['name']}**.")

    progress.progress(1.0, text="Concluido!")
    total = len(root_attrs) + len(sub_attrs)
    st.success(f"Template **{name}** criado com {total} atributo(s).")


# --------------- copiar entre ambientes ---------------

def _copy_template_section(ws: Lighthouse):
    st.subheader("Copiar Template entre Ambientes")

    env_atual = st.session_state.get("environment")
    client_atual = st.session_state.get("client_name")
    st.caption(f"Ambiente atual (destino): **{env_atual} / {client_atual}**")

    st.markdown("**Origem**")
    col_env, col_client = st.columns(2)

    with col_env:
        environments = list(clients.keys())
        src_env = st.selectbox("Ambiente de origem", environments, key="copy_src_env")

    with col_client:
        client_names = list(clients[src_env].keys())
        src_client = st.selectbox("Cliente de origem", client_names, key="copy_src_client")

    if src_env == env_atual and src_client == client_atual:
        st.info("Origem e destino sao o mesmo ambiente.")
        return

    if st.button("Carregar templates da origem", key="btn_load_src_templates"):
        with st.spinner("Conectando ao ambiente de origem..."):
            src_ws = _connect_to(src_env, src_client)
            templates = src_ws.get_templates()
        st.session_state["_copy_src_templates"] = templates
        st.session_state["_copy_src_env"] = src_env
        st.session_state["_copy_src_client"] = src_client

    templates = st.session_state.get("_copy_src_templates", {})
    if not templates:
        return

    selected_names = st.multiselect(
        "Seleciona os templates a copiar",
        options=sorted(templates.values()),
        key="copy_selected_templates",
    )

    if not selected_names:
        return

    name_to_id = {v: k for k, v in templates.items()}
    selected_ids = [name_to_id[n] for n in selected_names]

    if st.button(f"Analisar {len(selected_ids)} template(s)", type="primary", key="btn_analyze_copy"):
        _analyze_and_copy(ws, src_env, src_client, selected_ids, selected_names)


def _analyze_and_copy(ws: Lighthouse, src_env: str, src_client: str,
                      template_ids: list[str], template_names: list[str]):
    env_atual = st.session_state.get("environment")
    client_atual = st.session_state.get("client_name")

    src_ws = _connect_to(src_env, src_client)

    dst_templates = ws.get_templates()
    dst_template_names = {v.strip().lower() for v in dst_templates.values()}

    dst_categories_raw = ws.get_categories()
    dst_category_names = set()
    if isinstance(dst_categories_raw, list):
        for cat in dst_categories_raw:
            if isinstance(cat, dict) and "name" in cat:
                dst_category_names.add(cat["name"].strip().lower())

    all_missing_categories = set()
    templates_to_copy = []
    duplicates = []

    progress = st.progress(0, text="Analisando templates...")

    for i, (tid, tname) in enumerate(zip(template_ids, template_names)):
        progress.progress((i + 1) / len(template_ids), text=f"Analisando: {tname}")

        if tname.strip().lower() in dst_template_names:
            duplicates.append(tname)
            continue

        attrs_response = src_ws.get_template_attributes(tid)
        attrs = attrs_response.get("attributes", []) if isinstance(attrs_response, dict) else []

        all_attrs = []
        for attr in attrs:
            cats = [c["name"] for c in attr.get("categories", []) if isinstance(c, dict)]
            for cat_name in cats:
                if cat_name.strip().lower() not in dst_category_names:
                    all_missing_categories.add(cat_name)

            all_attrs.append(attr)

            attr_id = attr.get("id")
            if attr_id:
                try:
                    sub_resp = src_ws.get_template_attribute_subattributes(attr_id)
                    subs = sub_resp if isinstance(sub_resp, list) else sub_resp.get("attributes", [])
                    for sub in subs:
                        sub["_parent_name"] = attr["name"]
                        sub_cats = [c["name"] for c in sub.get("categories", []) if isinstance(c, dict)]
                        for cat_name in sub_cats:
                            if cat_name.strip().lower() not in dst_category_names:
                                all_missing_categories.add(cat_name)
                        all_attrs.append(sub)
                except Exception:
                    pass

        templates_to_copy.append({"id": tid, "name": tname, "attrs": all_attrs})

    progress.progress(1.0, text="Analise concluida!")

    if duplicates:
        st.warning(f"Templates ja existem no destino (serao ignorados): **{', '.join(duplicates)}**")

    if all_missing_categories:
        st.error(f"**Categorias nao encontradas no destino ({env_atual}/{client_atual}):**")
        for cat in sorted(all_missing_categories):
            st.text(f"  • {cat}")
        st.info("Cria estas categorias no ambiente de destino antes de copiar, ou os atributos serao copiados sem categoria.")

    if not templates_to_copy:
        st.info("Nenhum template novo para copiar.")
        return

    st.markdown("**Templates a copiar:**")
    for t in templates_to_copy:
        root = [a for a in t["attrs"] if "_parent_name" not in a]
        subs = [a for a in t["attrs"] if "_parent_name" in a]
        st.text(f"  • {t['name']}  ({len(root)} atributos, {len(subs)} subatributos)")

    st.session_state["_copy_ready"] = templates_to_copy
    st.session_state["_copy_missing_cats"] = all_missing_categories

    if all_missing_categories:
        proceed = st.checkbox(
            "Continuar mesmo assim (atributos com categorias em falta serao copiados sem categoria)",
            key="copy_proceed_anyway",
        )
        if not proceed:
            return

    if st.button("Copiar Templates", type="primary", key="btn_execute_copy"):
        _execute_copy(ws, templates_to_copy, dst_category_names)


def _execute_copy(ws: Lighthouse, templates_to_copy: list[dict], dst_category_names: set):
    dst_categories_raw = ws.get_categories()
    cat_name_to_id = {}
    if isinstance(dst_categories_raw, list):
        for cat in dst_categories_raw:
            if isinstance(cat, dict):
                cat_name_to_id[cat["name"].strip().lower()] = cat["id"]

    total = len(templates_to_copy)
    progress = st.progress(0, text="Copiando templates...")
    created = 0
    errors = []

    for i, tmpl in enumerate(templates_to_copy):
        progress.progress((i + 1) / total, text=f"Copiando: {tmpl['name']}")

        root_attrs = [a for a in tmpl["attrs"] if "_parent_name" not in a]
        sub_attrs = [a for a in tmpl["attrs"] if "_parent_name" in a]

        api_attrs = []
        for attr in root_attrs:
            a = _convert_attr_for_creation(attr, cat_name_to_id)
            api_attrs.append(a)

        payload = {
            "name": tmpl["name"],
            "description": "",
            "attributes": api_attrs,
        }

        response = ws.post_template(payload)
        if not (hasattr(response, "status_code") and response.status_code in (200, 201)):
            errors.append(f"{tmpl['name']}: HTTP {getattr(response, 'status_code', '?')} — {getattr(response, 'text', '')[:100]}")
            continue

        new_template = response.json()
        new_template_id = new_template.get("id", "")

        if sub_attrs and new_template_id:
            new_attrs_resp = ws.get_template_attributes(new_template_id)
            new_attrs = new_attrs_resp.get("attributes", []) if isinstance(new_attrs_resp, dict) else []
            name_to_new_id = {a["name"].strip().lower(): a["id"] for a in new_attrs}

            for sub in sub_attrs:
                parent_name = sub.pop("_parent_name", "")
                parent_id = name_to_new_id.get(parent_name.strip().lower())
                if parent_id:
                    sa = _convert_attr_for_creation(sub, cat_name_to_id)
                    sa["parent_id"] = parent_id
                    ws.post_template_attribute(new_template_id, sa)

        created += 1

    progress.progress(1.0, text="Concluido!")

    if created:
        st.success(f"{created} template(s) copiado(s) com sucesso.")
    if errors:
        st.error(f"{len(errors)} erro(s):")
        for e in errors:
            st.text(f"  • {e}")


def _convert_attr_for_creation(attr: dict, cat_name_to_id: dict) -> dict:
    data_source = attr.get("data_source", "Manual")
    data_type = attr.get("data_type", "Text")

    type_mapping = {
        ("Manual", "Text"): "Manual Text",
        ("Manual", "Integer"): "Manual Integer",
        ("Manual", "Float"): "Manual Float",
        ("Manual", "Boolean"): "Manual Boolean",
        ("TimeSeries", "Float"): "Time Series Float",
        ("TimeSeries", "Integer"): "Time Series Integer",
        ("TimeSeries", "Text"): "Time Series Text",
        ("TimeSeries", ""): "Time Series",
        ("Relational", "Text"): "Relational Text",
    }
    attr_type = type_mapping.get((data_source, data_type), f"{data_source} {data_type}".strip())

    category_ids = []
    for cat in attr.get("categories", []):
        if isinstance(cat, dict):
            cat_id = cat_name_to_id.get(cat["name"].strip().lower())
            if cat_id:
                category_ids.append(cat_id)

    result = {
        "name": attr["name"],
        "description": attr.get("description", "") or "",
        "type": attr_type,
        "unit_of_measurement": attr.get("unit_of_measurement", "") or "",
        "decimal_places": attr.get("decimal_places", 2) if "Float" in attr_type else 0,
        "default_value": str(attr.get("default_value", "") or "") or None,
    }

    if category_ids:
        result["categories"] = category_ids

    return result


def _connect_to(environment: str, client_name: str) -> Lighthouse:
    from lighthouse import connect
    return connect(client_name, environment, debug=False)
