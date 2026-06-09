import streamlit as st
import streamlit_antd_components as sac
from db_lighthouse import (
    get_dd_projects, get_dd_project, create_dd_project, update_dd_project, delete_dd_project,
    get_dd_items, get_dd_item, create_dd_item, rename_dd_item, delete_dd_item, set_dd_item_ws_id,
    get_dd_attributes, get_dd_subattributes, populate_dd_attributes_from_template,
    bulk_update_dd_attributes, get_dd_project_summary, get_all_dd_attributes,
    get_template_list, get_template_attr_tree,
)


def _invalidate_dd_tree():
    st.session_state.pop("_dd_tree", None)
    st.session_state.pop("dd_tree", None)
    st.session_state.pop("_dd_selected_item", None)


def render():
    st.title("Dicionário de Dados")

    project = _project_selector()
    if project is None:
        return

    is_editable = project["status"] != "Cancelado"

    col_tree, col_detail = st.columns([2, 3])

    with col_tree:
        _show_tree_panel(project, is_editable)

    with col_detail:
        if st.session_state.pop("_dd_enrolling", False):
            _enroll_project(project)
            return

        selected_id = st.session_state.get("_dd_selected_item")
        if not selected_id:
            _show_project_overview(project)
            return

        if st.button("← Voltar ao resumo do projeto", key="dd_back_overview"):
            st.session_state.pop("_dd_selected_item", None)
            st.session_state.pop("dd_tree", None)
            st.rerun()

        item = get_dd_item(selected_id)
        if item is None:
            st.session_state.pop("_dd_selected_item", None)
            _show_project_overview(project)
            return

        _show_item_detail(item, project, is_editable)


# --------------- seletor de projeto ---------------

def _project_selector():
    projects = get_dd_projects()
    col_sel, col_new, col_cancel = st.columns([4, 1, 1])

    with col_sel:
        if not projects:
            st.info("Nenhum dicionário criado. Cria um novo para começar.")

        options = {p["id"]: f'{p["name"]}  [{p["status"]}]' for p in projects}
        selected_id = st.selectbox(
            "Dicionário",
            options.keys(),
            format_func=lambda x: options[x],
            key="dd_project_select",
        ) if projects else None

    with col_new:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Novo", key="dd_new_project", use_container_width=True):
            st.session_state["_dd_show_create"] = True

    with col_cancel:
        st.markdown("<br>", unsafe_allow_html=True)
        if selected_id:
            project = get_dd_project(selected_id)
            if project and project["status"] == "Rascunho":
                if st.button("Cancelar", key="dd_cancel_project", use_container_width=True):
                    update_dd_project(selected_id, status="Cancelado")
                    st.rerun()

    if st.session_state.get("_dd_show_create"):
        _create_project_form()
        return None

    if not selected_id:
        return None

    return get_dd_project(selected_id)


def _create_project_form():
    st.subheader("Novo Dicionário de Dados")
    with st.form("dd_create_project", clear_on_submit=True):
        name = st.text_input("Nome do dicionário (ex: PRIO Expansion - Compressores)")
        environment = st.session_state.get("environment", "dev")
        client = st.session_state.get("client", "")
        st.caption(f"Ambiente: **{environment}** | Cliente: **{client}**")
        submitted = st.form_submit_button("Criar", type="primary")

    if submitted:
        if not name:
            st.warning("Informa o nome.")
        elif not client:
            st.warning("Conecta-te a um ambiente primeiro.")
        else:
            create_dd_project(name, client, environment)
            st.session_state.pop("_dd_show_create", None)
            st.success(f"Dicionário **{name}** criado.")
            st.rerun()

    if st.button("Voltar"):
        st.session_state.pop("_dd_show_create", None)
        st.rerun()


# --------------- visão geral do projeto ---------------

def _show_project_overview(project):
    st.subheader(project["name"])

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.caption(f"Status: **{project['status']}**")
        st.caption(f"Cliente: **{project['client']}** | Ambiente: **{project['environment']}**")
        if project.get("ws_parent_id"):
            st.caption(f"Parent no Workspace: `{project['ws_parent_id']}`")
    with col_s2:
        st.caption(f"Criado: {project['created_at']}")
        st.caption(f"Atualizado: {project['updated_at']}")

    summary = get_dd_project_summary(project["id"])
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Equipamentos", summary["items_with_template"])
    m2.metric("Containers", summary["items"] - summary["items_with_template"])
    m3.metric("Atributos", summary["attributes"])
    m4.metric("Subatributos", summary["subattributes"])

    if summary["attributes"] > 0:
        pct = int(summary["attributes_with_reference"] / summary["attributes"] * 100)
        st.progress(pct / 100, text=f"Atributos com tag preenchida: {summary['attributes_with_reference']}/{summary['attributes']} ({pct}%)")

    if project["status"] != "Cancelado":
        st.divider()
        _show_enrollment_section(project, summary)

    st.divider()

    with st.form("dd_rename_project", clear_on_submit=False):
        new_name = st.text_input("Renomear dicionário", value=project["name"])
        if st.form_submit_button("Renomear"):
            if new_name and new_name != project["name"]:
                update_dd_project(project["id"], name=new_name)
                st.rerun()


# --------------- árvore ---------------

PLANT_TEMPLATE_NAME = "Plant"

def _show_tree_panel(project, is_editable: bool):
    items = get_dd_items(project["id"])

    if is_editable and not items:
        st.info("O primeiro item deve ser do template **Plant**.")
        _create_plant_form(project)
        return

    if is_editable:
        if st.button("Adicionar item raiz", key="dd_add_root", use_container_width=True):
            st.session_state["_dd_adding_root"] = True
            st.rerun()

        if st.session_state.get("_dd_adding_root"):
            _create_item_form(project, parent_id=None)

    if not items:
        st.info("Árvore vazia.")
        return

    tree_items, id_map = _build_dd_tree(items)

    selected = sac.tree(
        items=tree_items,
        open_all=True,
        show_line=True,
        return_index=True,
        height=500,
        key="dd_tree",
    )

    if selected is not None and selected != []:
        idx = selected[0] if isinstance(selected, list) else selected
        item_id = id_map.get(idx)
        if item_id:
            st.session_state["_dd_selected_item"] = item_id


def _build_dd_tree(items: list[dict]):
    children_map: dict[str | None, list[dict]] = {}
    for item in items:
        pid = item["parent_item_id"]
        children_map.setdefault(pid, []).append(item)

    id_map = {}
    counter = [0]

    def build_node(item: dict) -> sac.TreeItem:
        idx = counter[0]
        counter[0] += 1
        id_map[idx] = item["id"]

        children = children_map.get(item["id"], [])
        child_nodes = [build_node(c) for c in children] if children else None

        has_template = item["template_id"] is not None
        icon = "gear-fill" if has_template else "folder2-open"

        return sac.TreeItem(
            label=item["name"],
            icon=icon,
            children=child_nodes,
        )

    root_items = children_map.get(None, [])
    tree = [build_node(r) for r in root_items]
    return tree, id_map


def _create_plant_form(project):
    env = project["environment"]
    client = project["client"]

    templates_db = get_template_list(env, client)
    plant_template = next((t for t in templates_db if t["template_name"] == PLANT_TEMPLATE_NAME), None)

    if plant_template is None:
        st.error(f"Template **{PLANT_TEMPLATE_NAME}** não encontrado. Sincroniza os templates primeiro.")
        return

    with st.form("dd_create_plant", clear_on_submit=True):
        name = st.text_input("Nome do item (ex: FPSO Peregrino)")
        st.text_input("Template", value=PLANT_TEMPLATE_NAME, disabled=True)
        ws_parent_id = st.text_input(
            "ID do item pai no Workspace",
            help="ID do item existente no Lighthouse onde este Plant será cadastrado como filho.",
        )
        submitted = st.form_submit_button("Criar", type="primary")

    if submitted:
        if not name:
            st.warning("Informa o nome.")
        elif not ws_parent_id or not ws_parent_id.strip():
            st.warning("Informa o ID do item pai no Workspace.")
        else:
            ws_parent_id = ws_parent_id.strip()
            update_dd_project(project["id"], ws_parent_id=ws_parent_id)
            item_id = create_dd_item(
                project["id"], name,
                plant_template["template_id"], PLANT_TEMPLATE_NAME,
                parent_item_id=None,
            )
            populate_dd_attributes_from_template(
                item_id, plant_template["template_id"], env, client,
            )
            _invalidate_dd_tree()
            st.success(f"Item **{name}** criado com template Plant.")
            st.rerun()


def _create_item_form(project, parent_id: str = None):
    env = project["environment"]
    client = project["client"]

    templates_db = get_template_list(env, client)
    template_options = {"": "(Container — sem template)"} | {t["template_id"]: t["template_name"] for t in templates_db}

    with st.form(f"dd_create_item_{parent_id}", clear_on_submit=True):
        name = st.text_input("Nome do item")
        selected_template = st.selectbox("Template", template_options.keys(), format_func=lambda x: template_options[x])
        submitted = st.form_submit_button("Criar", type="primary")

    if submitted:
        if not name:
            st.warning("Informa o nome.")
        else:
            tmpl_id = selected_template if selected_template else None
            tmpl_name = template_options.get(selected_template, "") if tmpl_id else None
            item_id = create_dd_item(project["id"], name, tmpl_id, tmpl_name, parent_id)

            if tmpl_id:
                populate_dd_attributes_from_template(item_id, tmpl_id, env, client)

            _invalidate_dd_tree()
            st.session_state.pop("_dd_adding_root", None)
            st.session_state.pop(f"_dd_adding_child_{parent_id}", None)
            st.success(f"Item **{name}** criado.")
            st.rerun()


# --------------- detalhe do item ---------------

def _show_item_detail(item: dict, project: dict, is_editable: bool):
    st.subheader(item["name"])
    tmpl_label = item["template_name"] or "Container (sem template)"
    st.caption(f"Template: **{tmpl_label}**")

    if is_editable:
        _show_dd_actions(item, project)
        st.divider()

    if item["template_id"]:
        _show_dd_hierarchical_view(item, is_editable)
    else:
        st.info("Este item é um container — não possui atributos.")


# --------------- visualização hierárquica (categoria → atributo → limiares) ---------------

def _show_dd_hierarchical_view(item: dict, is_editable: bool):
    attrs = get_dd_attributes(item["id"])
    subattrs = get_dd_subattributes(item["id"])

    if not attrs:
        st.info("Nenhum atributo. Verifica se os templates estão sincronizados.")
        return

    save_key = f"_dd_pending_save_{item['id']}"
    pending = st.session_state.pop(save_key, None)
    if pending:
        bulk_update_dd_attributes(pending)
        st.success("Alterações salvas com sucesso.")
        attrs = get_dd_attributes(item["id"])
        subattrs = get_dd_subattributes(item["id"])

    sub_by_parent: dict[int, list[dict]] = {}
    for sa in subattrs:
        sub_by_parent.setdefault(sa["parent_attribute_id"], []).append(sa)

    by_category: dict[str, list[dict]] = {}
    for a in attrs:
        cat = a["categories"] or "Sem Categoria"
        by_category.setdefault(cat, []).append(a)

    save_bar = st.container()

    attr_changes: dict[int, dict] = {}
    sub_changes: dict[int, dict] = {}

    for cat_name in sorted(by_category.keys()):
        cat_attrs = by_category[cat_name]
        n_subs = sum(len(sub_by_parent.get(a["id"], [])) for a in cat_attrs)
        label = f"{cat_name}  —  {len(cat_attrs)} atributo(s)"
        if n_subs:
            label += f", {n_subs} limiar(es)"

        with st.expander(label, expanded=False):
            for attr in cat_attrs:
                is_ts = attr["data_source"] and "Time" in attr["data_source"]
                is_manual = attr["data_source"] and "Manual" in (attr["data_source"] or "")
                subs = sub_by_parent.get(attr["id"], [])

                st.markdown(f"**{attr['name']}**")

                if is_ts:
                    col_ref, col_unit, col_dec = st.columns([3, 1, 1])
                    with col_ref:
                        if is_editable:
                            new_ref = st.text_input(
                                "Tag / Referência",
                                value=attr["reference"] or "",
                                key=f"dd_ref_{item['id']}_{attr['id']}",
                                label_visibility="collapsed",
                                placeholder="Tag / Referência",
                            )
                            if new_ref != (attr["reference"] or ""):
                                attr_changes.setdefault(attr["id"], {})["reference"] = new_ref
                        else:
                            st.text(attr["reference"] or "—")
                    with col_unit:
                        if is_editable:
                            new_unit = st.text_input(
                                "Unidade",
                                value=attr["unit_of_measurement"] or "",
                                key=f"dd_unit_{item['id']}_{attr['id']}",
                                label_visibility="collapsed",
                                placeholder="Unid.",
                            )
                            if new_unit != (attr["unit_of_measurement"] or ""):
                                attr_changes.setdefault(attr["id"], {})["unit_of_measurement"] = new_unit
                        else:
                            st.text(attr["unit_of_measurement"] or "—")
                    with col_dec:
                        if is_editable:
                            new_dec = st.number_input(
                                "Dec.",
                                value=attr["decimal_places"] or 2,
                                min_value=0, max_value=10,
                                key=f"dd_dec_{item['id']}_{attr['id']}",
                                label_visibility="collapsed",
                            )
                            if new_dec != (attr["decimal_places"] or 2):
                                attr_changes.setdefault(attr["id"], {})["decimal_places"] = new_dec
                        else:
                            st.text(str(attr["decimal_places"] or 2))

                elif is_manual:
                    if is_editable:
                        new_val = st.text_input(
                            "Valor",
                            value=attr["value"] or "",
                            key=f"dd_val_{item['id']}_{attr['id']}",
                            label_visibility="collapsed",
                            placeholder="Valor",
                        )
                        if new_val != (attr["value"] or ""):
                            attr_changes.setdefault(attr["id"], {})["value"] = new_val
                    else:
                        st.text(attr["value"] or "—")

                else:
                    st.caption(f"{attr['data_source'] or '—'} | {attr['data_type'] or '—'}")

                if subs:
                    st.caption("Limiares")
                    for sub in subs:
                        c1, c2 = st.columns([1, 1])
                        with c1:
                            st.text(f"  ↳ {sub['name']}")
                        with c2:
                            if is_editable:
                                new_sval = st.text_input(
                                    sub["name"],
                                    value=sub["value"] or "",
                                    key=f"dd_sub_{item['id']}_{sub['id']}",
                                    label_visibility="collapsed",
                                )
                                if new_sval != (sub["value"] or ""):
                                    sub_changes[sub["id"]] = {"value": new_sval}
                            else:
                                st.text(sub["value"] or "—")

                st.divider()

    total = len(attr_changes) + len(sub_changes)
    if total and is_editable:
        with save_bar:
            st.warning(f"**{total}** campo(s) alterado(s).")
            if st.button("Salvar alterações", key=f"dd_save_all_{item['id']}", type="primary"):
                updates = []
                for aid, vals in attr_changes.items():
                    updates.append({"id": aid, **vals})
                for sid, vals in sub_changes.items():
                    updates.append({"id": sid, **vals})
                st.session_state[save_key] = updates
                st.rerun()


# --------------- ações ---------------

def _show_dd_actions(item: dict, project: dict):
    st.markdown("**Criar item filho**")
    add_key = f"_dd_adding_child_{item['id']}"
    if st.button("Adicionar filho", key=f"dd_add_child_{item['id']}"):
        st.session_state[add_key] = True
        st.rerun()

    if st.session_state.get(add_key):
        _create_item_form(project, parent_id=item["id"])

    st.divider()

    st.markdown("**Renomear item**")
    with st.form(f"dd_rename_{item['id']}", clear_on_submit=False):
        new_name = st.text_input("Novo nome", value=item["name"])
        if st.form_submit_button("Renomear"):
            if new_name and new_name != item["name"]:
                rename_dd_item(item["id"], new_name)
                _invalidate_dd_tree()
                st.success(f"Renomeado para **{new_name}**.")
                st.rerun()

    st.divider()

    st.markdown("**Remover item**")
    st.warning(f"Remove **{item['name']}** e todos os seus filhos permanentemente.")
    if st.button("Remover item", key=f"dd_delete_{item['id']}", type="primary"):
        delete_dd_item(item["id"])
        _invalidate_dd_tree()
        st.session_state.pop("_dd_selected_item", None)
        st.success("Item removido.")
        st.rerun()


# --------------- cadastrar no workspace ---------------

def _show_enrollment_section(project, summary):
    st.markdown("### Cadastrar no Workspace")

    if not project.get("ws_parent_id"):
        st.warning("ID do item pai no Workspace não definido.")
        with st.form("dd_set_ws_parent", clear_on_submit=False):
            ws_parent_id = st.text_input(
                "ID do item pai no Workspace",
                help="ID do item existente no Lighthouse onde o Plant será cadastrado como filho.",
            )
            if st.form_submit_button("Guardar"):
                if ws_parent_id and ws_parent_id.strip():
                    update_dd_project(project["id"], ws_parent_id=ws_parent_id.strip())
                    st.rerun()
                else:
                    st.warning("Informa o ID.")
        return

    if summary["items_with_template"] == 0:
        st.warning("Nenhum equipamento com template definido.")
        return

    if summary["attributes"] > 0 and summary["attributes_with_reference"] == 0:
        st.info("Nenhum atributo time series possui tag preenchida. Os atributos podem ser atualizados depois.")

    if st.button("Cadastrar no Workspace", type="primary", key="dd_enroll"):
        st.session_state["_dd_enrolling"] = True
        st.rerun()


def _enroll_project(project):
    ws = st.session_state.get("ws")
    if ws is None:
        st.error("Nenhum ambiente conectado.")
        return

    items = get_dd_items(project["id"])
    if not items:
        st.warning("Nenhum item para cadastrar.")
        return

    children_map: dict[str | None, list[dict]] = {}
    for item in items:
        children_map.setdefault(item["parent_item_id"], []).append(item)

    dd_to_ws: dict[str, str] = {}
    total_items = len([i for i in items if i["template_id"]])

    if total_items == 0:
        st.warning("Nenhum item com template para cadastrar.")
        return

    progress = st.progress(0, text="Iniciando cadastro...")
    created = 0
    updated = 0
    errors = []

    def _ws_item_exists(ws_item_id: str) -> bool:
        """Verifica se um item existe no workspace pela ID."""
        response = ws.get_item(ws_item_id)
        return isinstance(response, dict) and "id" in response

    def create_recursive(parent_dd_id: str | None, parent_ws_id: str | None):
        nonlocal created, updated
        children = children_map.get(parent_dd_id, [])

        for item in children:
            if item["template_id"]:
                try:
                    existing_ws_id = item.get("ws_item_id")

                    if existing_ws_id and _ws_item_exists(existing_ws_id):
                        dd_to_ws[item["id"]] = existing_ws_id
                        _update_item_attributes(ws, existing_ws_id, item["id"])
                        updated += 1
                        progress.progress(
                            (created + updated) / total_items,
                            text=f"Atualizado: {item['name']} ({created + updated}/{total_items})",
                        )
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
                            _update_item_attributes(ws, ws_item_id, item["id"])
                            created += 1
                            progress.progress(
                                (created + updated) / total_items,
                                text=f"Criado: {item['name']} ({created + updated}/{total_items})",
                            )
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
        root_ws_id = project.get("ws_parent_id")
        if not root_ws_id:
            st.error("Projeto sem ID de item pai no Workspace. Recria o item Plant.")
            return
        create_recursive(None, root_ws_id)
    except Exception as e:
        errors.append(f"Erro geral: {e}")

    progress.progress(1.0, text="Concluído!")

    if errors:
        st.error(f"{len(errors)} erro(s) durante o cadastro:")
        for err in errors:
            st.text(f"  • {err}")

    if created + updated > 0:
        update_dd_project(project["id"], status="Cadastrado")
        parts = []
        if created:
            parts.append(f"{created} criado(s)")
        if updated:
            parts.append(f"{updated} atualizado(s)")
        st.success(f"Cadastro concluído: {', '.join(parts)}.")


def _update_item_attributes(ws, ws_item_id: str, dd_item_id: str):
    ws_attrs_response = ws.get_item_attributes(ws_item_id)
    ws_attrs = ws_attrs_response.get("attributes", []) if isinstance(ws_attrs_response, dict) else []

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

        is_ts = attr["data_source"] and "Time" in attr["data_source"]
        if is_ts and attr["reference"]:
            ts_batch.append({
                "id": ws_attr["id"],
                "reference": attr["reference"],
                "unit_of_measurement": attr["unit_of_measurement"] or "",
                "engineering_unit": attr["unit_of_measurement"] or "",
                "decimal_places": str(attr["decimal_places"] or 2),
            })
        elif not is_ts and attr["value"]:
            manual_batch.append({"id": ws_attr["id"], "value": str(attr["value"])})

    for sub in dd_subs:
        parent_name = (sub.get("parent_name") or "").strip().lower()
        sub_name = sub["name"].strip().lower()
        ws_sub = ws_subattr_map.get((parent_name, sub_name))
        if ws_sub and sub["value"]:
            manual_batch.append({"id": ws_sub["id"], "value": str(sub["value"])})

    if ts_batch:
        ws.update_attribute_batch(ws_item_id, ts_batch)

    if manual_batch:
        ws.update_manual_attributes(ws_item_id, manual_batch)
