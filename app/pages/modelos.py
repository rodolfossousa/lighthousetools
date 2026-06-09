import streamlit as st
import pandas as pd
import time
from db_lighthouse import get_vessels, get_generators


def render():
    st.title("Modelos (Generators)")

    # --------------- filtros ---------------
    col1, col2 = st.columns([1, 2])
    with col1:
        vessels = get_vessels()
        vessel_filter = st.selectbox("Vessel", ["Todos"] + vessels)
    with col2:
        search = st.text_input("Buscar (equipamento ou modelo)", placeholder="Ex: bomba, flatline...")

    vessel_arg = None if vessel_filter == "Todos" else vessel_filter
    generators = get_generators(vessel=vessel_arg, search=search or None)

    if not generators:
        st.warning("Nenhum modelo encontrado.")
        return

    # --------------- tabela com seleção ---------------
    df = pd.DataFrame(generators)
    df = df.rename(columns={
        "vessel": "Vessel",
        "name": "Equipamento",
        "value": "Modelo",
        "specification": "Tipo",
        "id_attribute": "Generator ID",
        "name_attribute": "Nome Interno",
        "id": "Item ID",
    })

    display_cols = ["Vessel", "Equipamento", "Modelo", "Tipo", "Generator ID"]
    st.caption(f"{len(df)} modelos encontrados")

    selection = st.dataframe(
        df[display_cols],
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="multi-row",
    )

    selected_rows = selection.selection.rows if selection.selection.rows else []

    if not selected_rows:
        st.info("Seleciona um ou mais modelos na tabela acima para alterar o status.")
        return

    selected_df = df.iloc[selected_rows]
    st.write(f"**{len(selected_rows)}** modelo(s) selecionado(s)")

    # --------------- ação ---------------
    col_action, col_btn = st.columns([1, 1])
    with col_action:
        new_status = st.selectbox("Novo status", ["OFFLINE", "ONLINE"])
    with col_btn:
        st.write("")
        st.write("")
        execute = st.button("Executar", type="primary")

    if execute:
        _execute_status_change(selected_df, new_status)


def _execute_status_change(selected_df: pd.DataFrame, new_status: str):
    ws = st.session_state.get("ws")
    if ws is None:
        st.error("Nenhum ambiente conectado. Seleciona um ambiente primeiro.")
        return

    generator_ids = selected_df["Generator ID"].tolist()
    total = len(generator_ids)

    results = {"success": 0, "error": 0, "errors": []}

    progress_bar = st.progress(0, text="Iniciando...")

    for i, gid in enumerate(generator_ids):
        model_name = selected_df.iloc[i]["Modelo"]
        progress_bar.progress((i + 1) / total, text=f"({i+1}/{total}) {model_name}")

        try:
            response = ws.change_generator_status(gid, new_status)
            if hasattr(response, "status_code") and response.status_code in (200, 201, 204):
                results["success"] += 1
            else:
                status = getattr(response, "status_code", "?")
                text = getattr(response, "text", str(response))
                results["error"] += 1
                results["errors"].append(f"{model_name}: HTTP {status} - {text}")
        except Exception as e:
            results["error"] += 1
            results["errors"].append(f"{model_name}: {e}")

    progress_bar.progress(1.0, text="Concluido!")

    if results["success"]:
        st.success(f"{results['success']} modelo(s) alterado(s) para **{new_status}** com sucesso.")
    if results["error"]:
        st.error(f"{results['error']} modelo(s) falharam:")
        for err in results["errors"]:
            st.caption(f"- {err}")
