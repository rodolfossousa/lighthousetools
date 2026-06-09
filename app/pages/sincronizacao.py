import streamlit as st
import pandas as pd
from db_lighthouse import get_sync_history, init_lighthouse_db
from sync import find_root_candidates, sync_items, sync_templates


def render():
    init_lighthouse_db()
    st.title("Sincronização de Dados")

    _show_sync_status()

    st.divider()

    tab_items, tab_templates = st.tabs(["Items / Atributos / Generators", "Template Attributes"])

    with tab_items:
        _sync_items_section()

    with tab_templates:
        _sync_templates_section()


def _show_sync_status():
    st.subheader("Status das sincronizações")
    history = get_sync_history()

    if not history:
        st.info("Nenhuma sincronização realizada ainda.")
        return

    rows = []
    for h in history:
        tipo = "Items / Generators" if h["sync_type"] == "items" else "Templates"
        vessel = h["vessel"] or "—"
        rows.append({
            "Tipo": tipo,
            "Ambiente": h["environment"].upper(),
            "Cliente": h["client"].upper(),
            "Vessel": vessel,
            "Última atualização": h["last_updated"],
        })

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _sync_items_section():
    st.subheader("Sincronizar Items / Atributos / Generators")

    ws = st.session_state.get("ws")
    if ws is None:
        st.warning("Seleciona um ambiente primeiro.")
        return

    env = st.session_state.environment
    client = st.session_state.client_name

    st.caption(f"Ambiente: **{env} / {client}**")

    search_term = st.text_input("Nome do vessel (ex: MV32, BRAVO, PRIO)", key="sync_vessel_search")

    if not search_term:
        return

    if st.button("Buscar", key="btn_search_vessel"):
        with st.spinner("Buscando items..."):
            candidates = find_root_candidates(ws, search_term)
        st.session_state["_sync_candidates"] = candidates

    candidates = st.session_state.get("_sync_candidates", [])

    if not candidates:
        if "_sync_candidates" in st.session_state:
            st.warning(f"Nenhum item encontrado com '{search_term}'.")
        return

    options = {f"{name} ({iid[:8]}...)": iid for iid, name in candidates}
    selected = st.selectbox("Seleciona o item raiz", options.keys())
    root_id = options[selected]

    vessel_name = st.text_input("Nome do vessel para gravar no banco", value=search_term.upper(), key="sync_vessel_name")

    if st.button("Sincronizar Items", key="btn_sync_items", type="primary"):
        progress = st.progress(0, text="Iniciando...")
        status_text = st.empty()

        def on_progress(current, total, name):
            progress.progress(current / total, text=f"({current}/{total}) {name}")

        try:
            total_rows = sync_items(ws, root_id, vessel_name, env, client, progress_callback=on_progress)
            progress.progress(1.0, text="Concluído!")
            st.success(f"Sincronização concluída: **{total_rows}** registros salvos para **{vessel_name}**.")
            st.session_state.pop("_sync_candidates", None)
        except Exception as e:
            st.error(f"Erro na sincronização: {e}")


def _sync_templates_section():
    st.subheader("Sincronizar Template Attributes")

    ws = st.session_state.get("ws")
    if ws is None:
        st.warning("Seleciona um ambiente primeiro.")
        return

    env = st.session_state.environment
    client = st.session_state.client_name

    st.caption(f"Ambiente: **{env} / {client}**")

    if st.button("Carregar templates", key="btn_load_templates"):
        with st.spinner("Buscando templates..."):
            templates = ws.get_templates()
        st.session_state["_sync_templates"] = templates

    templates = st.session_state.get("_sync_templates", {})

    if not templates:
        return

    template_options = {v: k for k, v in templates.items()}
    selected_names = st.multiselect(
        "Seleciona os templates (vazio = todos)",
        options=sorted(template_options.keys()),
    )

    selected_ids = [template_options[n] for n in selected_names] if selected_names else None

    label = f"Sincronizar {len(selected_names)} template(s)" if selected_names else "Sincronizar todos os templates"

    if st.button(label, key="btn_sync_templates", type="primary"):
        progress = st.progress(0, text="Iniciando...")

        def on_progress(current, total, name):
            progress.progress(current / total, text=f"({current}/{total}) {name}")

        try:
            total_rows = sync_templates(ws, env, client, template_ids=selected_ids, progress_callback=on_progress)
            progress.progress(1.0, text="Concluído!")
            st.success(f"Sincronização concluída: **{total_rows}** atributos de template salvos.")
            st.session_state.pop("_sync_templates", None)
        except Exception as e:
            st.error(f"Erro na sincronização: {e}")
