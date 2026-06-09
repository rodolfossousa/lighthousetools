import streamlit as st
import streamlit_antd_components as sac
import pandas as pd
from db_lighthouse import (
    get_vessels, get_item_tree, get_item_attributes,
    get_item_generators_from_db, get_item_meta, update_attribute_value_in_db,
    insert_item_in_db, rename_item_in_db, delete_item_from_db,
    get_item_subattributes, update_subattribute_value_in_db,
)


def _invalidate_tree_cache(vessel: str):
    cache_key = f"_explorer_tree_{vessel}"
    st.session_state.pop(cache_key, None)


def render():
    st.title("Explorador de Ativos")

    vessels = get_vessels()
    if not vessels:
        st.warning("Nenhum vessel sincronizado. Vai à tela de Sincronização primeiro.")
        return

    col_tree, col_detail = st.columns([2, 3])

    with col_tree:
        vessel = st.selectbox("Vessel", vessels, key="explorer_vessel")
        tree_items, id_map = _build_tree(vessel)

        if not tree_items:
            st.info("Nenhum item encontrado para este vessel.")
            return

        selected = sac.tree(
            items=tree_items,
            open_all=False,
            show_line=True,
            return_index=True,
            height=600,
            key=f"tree_{vessel}",
        )

    with col_detail:
        if not selected:
            st.info("Seleciona um item na árvore para ver os detalhes.")
            return

        idx = selected[0] if isinstance(selected, list) else selected
        item_id = id_map.get(idx)
        if item_id is None:
            return

        _show_item_detail(item_id, vessel)


def _build_tree(vessel: str):
    cache_key = f"_explorer_tree_{vessel}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]

    items = get_item_tree(vessel)

    children_map: dict[str | None, list[dict]] = {}
    for item in items:
        pid = item["parent_id"]
        children_map.setdefault(pid, []).append(item)

    id_map = {}
    counter = [0]

    def build_node(item: dict) -> sac.TreeItem:
        idx = counter[0]
        counter[0] += 1
        id_map[idx] = item["id"]

        children = children_map.get(item["id"], [])
        child_nodes = [build_node(c) for c in children] if children else None

        icon = "gear-fill" if item["is_leaf"] else "folder2-open"

        return sac.TreeItem(
            label=item["name"],
            icon=icon,
            children=child_nodes,
        )

    root_items = children_map.get(None, [])
    tree = [build_node(r) for r in root_items]

    st.session_state[cache_key] = (tree, id_map)
    return tree, id_map


# --------------- detalhe do item ---------------

def _show_item_detail(item_id: str, vessel: str):
    meta = get_item_meta(item_id)
    if meta is None:
        st.warning("Item não encontrado no banco.")
        return

    st.subheader(meta["name"])
    st.caption(f"Template: **{meta['template_name']}** | ID: `{meta['id']}`")

    tab_attrs, tab_gens, tab_actions = st.tabs(
        ["Atributos", "Modelos", "Ações"]
    )

    with tab_attrs:
        _show_hierarchical_view(item_id)

    with tab_gens:
        gens = get_item_generators_from_db(item_id)
        if not gens:
            st.info("Nenhum modelo encontrado.")
        else:
            df = pd.DataFrame(gens).rename(columns={
                "id_attribute": "Generator ID",
                "name_attribute": "Nome Interno",
                "value": "Modelo",
                "specification": "Tipo",
            })
            st.caption(f"{len(df)} modelo(s)")
            st.dataframe(df, use_container_width=True, hide_index=True)

    with tab_actions:
        _show_actions(item_id, meta, vessel)


# --------------- ações: criar, renomear, deletar ---------------

def _show_actions(item_id: str, meta: dict, vessel: str):
    ws = st.session_state.get("ws")
    if ws is None:
        st.warning("Nenhum ambiente conectado.")
        return

    # --- Criar sub-item ---
    st.markdown("**Criar equipamento filho**")
    with st.form(f"create_item_{item_id}", clear_on_submit=True):
        new_name = st.text_input("Nome do novo item")

        templates = ws.get_templates()
        template_options = {v: k for k, v in templates.items()}
        selected_template = st.selectbox("Template", sorted(template_options.keys()))

        create_submitted = st.form_submit_button("Criar", type="primary")

    if create_submitted:
        if not new_name:
            st.warning("Informa o nome do item.")
        else:
            template_id = template_options[selected_template]
            _create_item(ws, vessel, item_id, new_name, template_id, selected_template)

    st.divider()

    # --- Renomear ---
    st.markdown("**Renomear item**")
    with st.form(f"rename_item_{item_id}", clear_on_submit=True):
        rename_value = st.text_input("Novo nome", value=meta["name"])
        rename_submitted = st.form_submit_button("Renomear")

    if rename_submitted:
        if not rename_value or rename_value == meta["name"]:
            st.info("Nenhuma alteração.")
        else:
            _rename_item(ws, item_id, rename_value, vessel)

    st.divider()

    # --- Deletar ---
    st.markdown("**Remover item**")
    st.warning(f"Isto vai remover **{meta['name']}** permanentemente da API e do banco local.")
    if st.button("Remover item", key=f"delete_{item_id}", type="primary"):
        _delete_item(ws, item_id, vessel)


def _create_item(ws, vessel: str, parent_id: str, name: str, template_id: str, template_name: str):
    try:
        response = ws.create_item(template_id, {
            "name": name,
            "parent_id": parent_id,
        })

        if hasattr(response, "status_code") and response.status_code in (200, 201):
            new_item = response.json()
            new_item_id = new_item.get("id", "")

            attrs_response = ws.get_item_attributes(new_item_id)
            attrs = attrs_response.get("attributes", []) if isinstance(attrs_response, dict) else []

            insert_item_in_db(vessel, new_item_id, name, template_name, parent_id, attrs)
            _invalidate_tree_cache(vessel)
            st.success(f"Item **{name}** criado com {len(attrs)} atributo(s).")
            st.rerun()
        else:
            status = getattr(response, "status_code", "?")
            text = getattr(response, "text", str(response))
            st.error(f"Erro na API: HTTP {status} — {text}")
    except Exception as e:
        st.error(f"Erro: {e}")


def _rename_item(ws, item_id: str, new_name: str, vessel: str):
    try:
        response = ws.update_item(item_id, {"name": new_name})
        if hasattr(response, "status_code") and response.status_code in (200, 201, 204):
            rename_item_in_db(item_id, new_name)
            _invalidate_tree_cache(vessel)
            st.success(f"Item renomeado para **{new_name}**.")
            st.rerun()
        else:
            status = getattr(response, "status_code", "?")
            text = getattr(response, "text", str(response))
            st.error(f"Erro na API: HTTP {status} — {text}")
    except Exception as e:
        st.error(f"Erro: {e}")


def _delete_item(ws, item_id: str, vessel: str):
    try:
        response = ws.delete_item(item_id)
        if hasattr(response, "status_code") and response.status_code in (200, 204):
            delete_item_from_db(item_id)
            _invalidate_tree_cache(vessel)
            st.success("Item removido.")
            st.rerun()
        else:
            status = getattr(response, "status_code", "?")
            text = getattr(response, "text", str(response))
            st.error(f"Erro na API: HTTP {status} — {text}")
    except Exception as e:
        st.error(f"Erro: {e}")


# --------------- visualização hierárquica (categoria → atributo → limiares) ---------------

def _show_hierarchical_view(item_id: str):
    attrs = get_item_attributes(item_id)
    subattrs = get_item_subattributes(item_id)

    if not attrs:
        st.info("Nenhum atributo encontrado.")
        return

    save_key = f"_pending_save_{item_id}"
    pending = st.session_state.pop(save_key, None)
    if pending:
        _save_all_changes(item_id, pending["attr"], pending["thr"])
        attrs = get_item_attributes(item_id)
        subattrs = get_item_subattributes(item_id)

    sub_by_parent: dict[str, list[dict]] = {}
    for sa in subattrs:
        sub_by_parent.setdefault(sa["parent_attribute_id"], []).append(sa)

    by_category: dict[str, list[dict]] = {}
    for a in attrs:
        cat = a["category"] or "Sem Categoria"
        by_category.setdefault(cat, []).append(a)

    save_bar = st.container()

    attr_changes: dict[str, dict] = {}
    thr_changes: dict[str, dict] = {}

    for cat_name in sorted(by_category.keys()):
        cat_attrs = by_category[cat_name]
        n_subs = sum(len(sub_by_parent.get(a["id_attribute"], [])) for a in cat_attrs)
        label = f"{cat_name}  —  {len(cat_attrs)} atributo(s)"
        if n_subs:
            label += f", {n_subs} limiar(es)"

        with st.expander(label, expanded=False):
            for attr in cat_attrs:
                attr_id = attr["id_attribute"]
                attr_name = attr["name_attribute"]
                is_manual = attr["specification"].startswith("Manual")
                current_value = attr["value"] if attr["value"] else ""
                subs = sub_by_parent.get(attr_id, [])

                st.markdown(f"**{attr_name}**")

                col_val, col_type, col_ref = st.columns([2, 1, 2])
                with col_val:
                    if is_manual:
                        new_val = st.text_input(
                            f"Valor de {attr_name}",
                            value=str(current_value),
                            key=f"edit_{item_id}_{attr_id}",
                            label_visibility="collapsed",
                        )
                        if new_val != str(current_value):
                            attr_changes[attr_id] = {"name": attr_name, "value": new_val}
                    else:
                        st.text(str(current_value) if current_value else "—")
                with col_type:
                    st.caption(attr["specification"])
                with col_ref:
                    if attr["reference"]:
                        st.caption(f"Ref: {attr['reference']}")

                if subs:
                    st.caption("Limiares")
                    for sub in subs:
                        sub_id = sub["id_attribute"]
                        sub_name = sub["name_attribute"]
                        sub_value = sub["value"] if sub["value"] else ""

                        c1, c2 = st.columns([1, 1])
                        with c1:
                            st.text(f"  ↳ {sub_name}")
                        with c2:
                            new_sval = st.text_input(
                                sub_name,
                                value=str(sub_value),
                                key=f"thr_{item_id}_{sub_id}",
                                label_visibility="collapsed",
                            )
                            if new_sval != str(sub_value):
                                thr_changes[sub_id] = {"name": sub_name, "value": new_sval}

                st.divider()

    total = len(attr_changes) + len(thr_changes)
    if total:
        with save_bar:
            st.warning(f"**{total}** valor(es) alterado(s).")
            if st.button("Salvar alterações", key=f"save_all_{item_id}", type="primary"):
                st.session_state[save_key] = {"attr": dict(attr_changes), "thr": dict(thr_changes)}
                st.rerun()


def _save_all_changes(item_id: str, attr_changes: dict, thr_changes: dict):
    ws = st.session_state.get("ws")
    if ws is None:
        st.error("Nenhum ambiente conectado.")
        return

    payload = []
    for attr_id, data in attr_changes.items():
        payload.append({"id": attr_id, "value": data["value"]})
    for sub_id, data in thr_changes.items():
        payload.append({"id": sub_id, "value": data["value"]})

    try:
        response = ws.update_manual_attributes(item_id, payload)
        if hasattr(response, "status_code") and response.status_code in (200, 201, 202):
            for attr_id, data in attr_changes.items():
                update_attribute_value_in_db(item_id, attr_id, data["value"])
            for sub_id, data in thr_changes.items():
                update_subattribute_value_in_db(item_id, sub_id, data["value"])
            st.success(f"{len(payload)} valor(es) atualizado(s) com sucesso.")
        else:
            status = getattr(response, "status_code", "?")
            text = getattr(response, "text", str(response))
            st.error(f"Erro na API: HTTP {status} — {text}")
    except Exception as e:
        st.error(f"Erro: {e}")
