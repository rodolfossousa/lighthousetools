import streamlit as st
import streamlit_antd_components as sac
import pandas as pd
from db_lighthouse import get_template_list, get_template_attr_tree


def render():
    st.title("Biblioteca de Templates")

    env = st.session_state.get("environment")
    client = st.session_state.get("client_name")

    if not env or not client:
        st.warning("Seleciona um ambiente primeiro.")
        return

    templates = get_template_list(env, client)

    if not templates:
        st.info(f"Nenhum template sincronizado para **{env} / {client}**. Sincroniza na tela de Sincronização.")
        return

    col_tree, col_detail = st.columns([2, 3])

    with col_tree:
        tree_items, id_map, type_map = _build_tree(templates, env, client)

        if not tree_items:
            st.info("Nenhum dado encontrado.")
            return

        selected = sac.tree(
            items=tree_items,
            open_all=False,
            show_line=True,
            return_index=True,
            height=600,
        )

    with col_detail:
        if not selected:
            st.info("Seleciona um template ou atributo na árvore para ver os detalhes.")
            return

        idx = selected[0] if isinstance(selected, list) else selected
        node_id = id_map.get(idx)
        node_type = type_map.get(idx)

        if node_id is None:
            return

        if node_type == "template":
            _show_template_detail(node_id, templates, env, client)
        elif node_type == "category":
            _show_category_detail(node_id, env, client)
        else:
            _show_attribute_detail(node_id, env, client)


def _build_tree(templates: list[dict], env: str, client: str):
    id_map = {}
    type_map = {}
    counter = [0]

    tree_items = []

    for tmpl in templates:
        tid = tmpl["template_id"]
        tname = tmpl["template_name"]

        attrs = get_template_attr_tree(env, client, tid)

        children_map: dict[str, list[dict]] = {}
        root_attrs = []
        for a in attrs:
            pid = a["parent_id"]
            if pid:
                children_map.setdefault(pid, []).append(a)
            else:
                root_attrs.append(a)

        tmpl_idx = counter[0]
        counter[0] += 1
        id_map[tmpl_idx] = tid
        type_map[tmpl_idx] = "template"

        def build_attr_node(attr: dict) -> sac.TreeItem:
            idx = counter[0]
            counter[0] += 1
            id_map[idx] = attr["id"]
            type_map[idx] = "attribute"

            children = children_map.get(attr["id"], [])
            child_nodes = [build_attr_node(c) for c in children] if children else None

            source = attr.get("data_source", "")
            dtype = attr.get("data_type", "")
            icon = "pencil-square" if "Manual" in source else "graph-up"

            return sac.TreeItem(
                label=attr["name"],
                icon=icon,
                tag=f"{source} {dtype}".strip() if source else None,
                children=child_nodes,
            )

        cats_map: dict[str, list[dict]] = {}
        for a in root_attrs:
            cat = a.get("categories", "").strip() or "Sem Categoria"
            cats_map.setdefault(cat, []).append(a)

        category_nodes = []
        for cat_name in sorted(cats_map.keys()):
            cat_idx = counter[0]
            counter[0] += 1
            id_map[cat_idx] = f"cat__{tid}__{cat_name}"
            type_map[cat_idx] = "category"

            attr_nodes = [build_attr_node(a) for a in cats_map[cat_name]]
            category_nodes.append(sac.TreeItem(
                label=cat_name,
                icon="tag",
                children=attr_nodes,
            ))

        tree_items.append(sac.TreeItem(
            label=tname,
            icon="file-earmark-ruled",
            children=category_nodes if category_nodes else None,
        ))

    return tree_items, id_map, type_map


def _show_template_detail(template_id: str, templates: list[dict], env: str, client: str):
    tmpl = next((t for t in templates if t["template_id"] == template_id), None)
    if tmpl is None:
        return

    st.subheader(tmpl["template_name"])
    st.caption(f"Template ID: `{template_id}`")

    attrs = get_template_attr_tree(env, client, template_id)
    root_attrs = [a for a in attrs if not a["parent_id"]]
    sub_attrs = [a for a in attrs if a["parent_id"]]

    st.metric("Total de atributos", len(root_attrs))
    st.metric("Total de subatributos", len(sub_attrs))

    st.divider()
    st.markdown("**Resumo por tipo**")

    if attrs:
        df = pd.DataFrame(root_attrs)
        summary = df.groupby(["data_source", "data_type"]).size().reset_index(name="Qtd")
        summary = summary.rename(columns={"data_source": "Data Source", "data_type": "Data Type"})
        st.dataframe(summary, use_container_width=True, hide_index=True)


def _show_category_detail(node_id: str, env: str, client: str):
    parts = node_id.split("__", 2)
    if len(parts) != 3:
        return
    _, template_id, cat_name = parts

    from db_lighthouse import _get_conn
    conn = _get_conn()

    tmpl_row = conn.execute(
        "SELECT DISTINCT template_name FROM template_attributes WHERE template_id = ? AND environment = ? AND client = ? LIMIT 1",
        (template_id, env, client),
    ).fetchone()
    template_name = tmpl_row["template_name"] if tmpl_row else template_id

    if cat_name == "Sem Categoria":
        rows = conn.execute("""
            SELECT name, data_source, data_type, unit_of_measurement, default_value
            FROM template_attributes
            WHERE environment = ? AND client = ? AND template_id = ? AND (categories IS NULL OR categories = '') AND parent_id = ''
            ORDER BY name
        """, (env, client, template_id)).fetchall()
    else:
        rows = conn.execute("""
            SELECT name, data_source, data_type, unit_of_measurement, default_value
            FROM template_attributes
            WHERE environment = ? AND client = ? AND template_id = ? AND categories = ? AND parent_id = ''
            ORDER BY name
        """, (env, client, template_id, cat_name)).fetchall()
    conn.close()

    st.subheader(cat_name)
    st.caption(f"Template: **{template_name}** | {len(rows)} atributo(s)")

    if rows:
        df = pd.DataFrame([dict(r) for r in rows]).rename(columns={
            "name": "Nome",
            "data_source": "Data Source",
            "data_type": "Data Type",
            "unit_of_measurement": "Unidade",
            "default_value": "Valor Padrão",
        })
        st.dataframe(df, use_container_width=True, hide_index=True)


def _show_attribute_detail(attribute_id: str, env: str, client: str):
    from db_lighthouse import _get_conn
    conn = _get_conn()
    row = conn.execute("""
        SELECT id, name, description, data_source, data_type,
               unit_of_measurement, default_value, categories, parent_id, template_name
        FROM template_attributes
        WHERE environment = ? AND client = ? AND id = ?
        LIMIT 1
    """, (env, client, attribute_id)).fetchone()
    conn.close()

    if row is None:
        st.warning("Atributo não encontrado.")
        return

    attr = dict(row)

    st.subheader(attr["name"])
    st.caption(f"Template: **{attr['template_name']}** | ID: `{attr['id']}`")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Data Source:** {attr['data_source']}")
        st.markdown(f"**Data Type:** {attr['data_type']}")
        st.markdown(f"**Unidade:** {attr['unit_of_measurement'] or '—'}")
    with col2:
        st.markdown(f"**Valor padrão:** {attr['default_value'] or '—'}")
        st.markdown(f"**Categorias:** {attr['categories'] or '—'}")
        st.markdown(f"**Descrição:** {attr['description'] or '—'}")

    if attr["parent_id"]:
        parent = _get_conn()
        p_row = parent.execute(
            "SELECT name FROM template_attributes WHERE id = ? AND environment = ? AND client = ?",
            (attr["parent_id"], env, client),
        ).fetchone()
        parent.close()
        if p_row:
            st.markdown(f"**Atributo pai:** {p_row['name']}")

    sub_conn = _get_conn()
    subs = sub_conn.execute("""
        SELECT name, data_source, data_type, unit_of_measurement, default_value, categories
        FROM template_attributes
        WHERE environment = ? AND client = ? AND parent_id = ?
        ORDER BY name
    """, (env, client, attribute_id)).fetchall()
    sub_conn.close()

    if subs:
        st.divider()
        st.markdown(f"**Subatributos** ({len(subs)})")
        df = pd.DataFrame([dict(s) for s in subs]).rename(columns={
            "name": "Nome",
            "data_source": "Data Source",
            "data_type": "Data Type",
            "unit_of_measurement": "Unidade",
            "default_value": "Valor Padrão",
            "categories": "Categorias",
        })
        st.dataframe(df, use_container_width=True, hide_index=True)
