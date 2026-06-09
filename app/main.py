import streamlit as st
from lighthouse import connect, clients
from db import init_db, authenticate, list_users, create_user, delete_user, reset_password
from db_lighthouse import init_lighthouse_db
from pages.modelos import render as modelos_page
from pages.sincronizacao import render as sincronizacao_page
from pages.explorador import render as explorador_page
from pages.biblioteca import render as biblioteca_page
from pages.dicionario import render as dicionario_page
from pages.templates import render as templates_page

init_db()
init_lighthouse_db()

st.set_page_config(page_title="Lighthouse Tools", page_icon=":wrench:", layout="wide")


# --------------- sessão ---------------
if "user" not in st.session_state:
    st.session_state.user = None
if "environment" not in st.session_state:
    st.session_state.environment = None
if "client_name" not in st.session_state:
    st.session_state.client_name = None
if "ws" not in st.session_state:
    st.session_state.ws = None


def logout():
    st.session_state.user = None
    st.session_state.environment = None
    st.session_state.client_name = None
    st.session_state.ws = None


def set_environment(environment: str, client_name: str):
    st.session_state.environment = environment
    st.session_state.client_name = client_name
    st.session_state.client = client_name
    st.session_state.ws = connect(client_name, environment, debug=False)


# --------------- tela de login ---------------
def login_page():
    st.title("Lighthouse Tools")
    st.subheader("Login")

    with st.form("login_form"):
        username = st.text_input("Utilizador")
        password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar")

    if submitted:
        user = authenticate(username, password)
        if user:
            st.session_state.user = user
            st.rerun()
        else:
            st.error("Utilizador ou senha incorretos.")


# --------------- tela de seleção de ambiente ---------------
def select_environment_page():
    st.title("Selecionar Ambiente")
    st.write("Escolhe o ambiente e o cliente para esta sessão.")

    environments = list(clients.keys())
    environment = st.selectbox("Ambiente", environments)

    client_names = list(clients[environment].keys())
    client_name = st.selectbox("Cliente", client_names)

    if st.button("Confirmar"):
        set_environment(environment, client_name)
        st.rerun()


# --------------- tela de trocar ambiente ---------------
def environment_page():
    st.title("Ambiente")

    env = st.session_state.environment
    cli = st.session_state.client_name
    st.success(f"Ambiente atual: **{env}** / **{cli}**")

    st.divider()
    st.subheader("Trocar ambiente")

    environments = list(clients.keys())
    new_env = st.selectbox("Ambiente", environments, index=environments.index(env))

    client_names = list(clients[new_env].keys())
    default_idx = client_names.index(cli) if cli in client_names else 0
    new_client = st.selectbox("Cliente", client_names, index=default_idx)

    if st.button("Trocar"):
        set_environment(new_env, new_client)
        st.rerun()


# --------------- tela admin: gestão de utilizadores ---------------
def admin_page():
    st.title("Gestão de Utilizadores")

    users = list_users()
    st.dataframe(
        [{"Nome": u["name"], "Username": u["username"], "Admin": "Sim" if u["is_admin"] else "Não"} for u in users],
        use_container_width=True,
        hide_index=True,
    )

    st.divider()
    st.subheader("Novo utilizador")
    with st.form("new_user_form", clear_on_submit=True):
        name = st.text_input("Nome completo")
        username = st.text_input("Username")
        password = st.text_input("Senha", type="password")
        is_admin = st.checkbox("Administrador")
        submitted = st.form_submit_button("Criar")

    if submitted:
        if not username or not password or not name:
            st.warning("Preenche todos os campos.")
        elif create_user(username, password, name, is_admin):
            st.success(f"Utilizador **{username}** criado.")
            st.rerun()
        else:
            st.error(f"Username **{username}** já existe.")

    st.divider()
    st.subheader("Resetar senha")
    user_options = {f"{u['name']} ({u['username']})": u["id"] for u in users}
    with st.form("reset_pw_form", clear_on_submit=True):
        selected = st.selectbox("Utilizador", options=user_options.keys())
        new_pw = st.text_input("Nova senha", type="password")
        reset_submitted = st.form_submit_button("Resetar")

    if reset_submitted:
        if not new_pw:
            st.warning("Informa a nova senha.")
        else:
            reset_password(user_options[selected], new_pw)
            st.success("Senha atualizada.")

    st.divider()
    st.subheader("Remover utilizador")
    non_admin_users = {f"{u['name']} ({u['username']})": u["id"] for u in users if u["username"] != "admin"}
    if non_admin_users:
        with st.form("delete_user_form"):
            del_selected = st.selectbox("Utilizador", options=non_admin_users.keys())
            del_submitted = st.form_submit_button("Remover")
        if del_submitted:
            delete_user(non_admin_users[del_selected])
            st.success("Utilizador removido.")
            st.rerun()
    else:
        st.info("Não há utilizadores para remover (apenas o admin existe).")


# --------------- tela principal (pós-login) ---------------
def home_page():
    st.title("Lighthouse Tools")
    st.write(f"Bem-vindo, **{st.session_state.user['name']}**!")
    st.info("Novas telas serão adicionadas aqui.")


# --------------- navegação ---------------
if st.session_state.user is None:
    login_page()
elif st.session_state.environment is None:
    select_environment_page()
else:
    with st.sidebar:
        st.write(f"**{st.session_state.user['name']}**")
        env_label = f"{st.session_state.environment} / {st.session_state.client_name}"
        st.caption(f"Ambiente: {env_label}")
        st.divider()
        pages = ["Inicio", "Dicionário de Dados", "Cadastro de Templates", "Explorador", "Biblioteca de Templates", "Modelos", "Sincronização", "Ambiente"]
        if st.session_state.user["is_admin"]:
            pages.append("Utilizadores")
        page = st.radio("Menu", pages, label_visibility="collapsed")
        st.button("Sair", on_click=logout)

    if page == "Inicio":
        home_page()
    elif page == "Dicionário de Dados":
        dicionario_page()
    elif page == "Cadastro de Templates":
        templates_page()
    elif page == "Explorador":
        explorador_page()
    elif page == "Biblioteca de Templates":
        biblioteca_page()
    elif page == "Modelos":
        modelos_page()
    elif page == "Sincronização":
        sincronizacao_page()
    elif page == "Ambiente":
        environment_page()
    elif page == "Utilizadores":
        admin_page()
