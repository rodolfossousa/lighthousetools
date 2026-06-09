import sqlite3
from tqdm import tqdm
from Lighthouse.lighthouse import clients, connect

# ---------------------------------------
# CONFIGURAÇÃO DO CLIENTE E SEARCH
# ---------------------------------------
available_clients = list(clients.get("prod", {}).keys())
print(f"\nClientes disponíveis: {', '.join(available_clients)}")
client_name = input("Digite o nome do cliente: ").strip().lower()

if client_name not in available_clients:
    print(f"Cliente '{client_name}' não encontrado. Encerrando execução.")
    exit(1)

environment = input("Digite o ambiente (prod/dev/homol) [prod]: ").strip().lower() or "prod"

# Texto que você quer usar para buscar o vessel
# e que será gravado na coluna 'vessel'
# Pergunta ao usuário qual vessel deve ser processado
SEARCH_TERM = input("\nDigite o nome do vessel (ex.: MV32, BAC, PRIO): ").strip().upper()

if not SEARCH_TERM:
    print("Nenhum vessel informado. Encerrando execução.")
    exit(1)

ws = connect(client_name=client_name, environment=environment, debug=False)

DB_PATH = "lighthouse_attributes.db"


# ---------------------------------------
#   BANCO DE DADOS (UMA ÚNICA TABELA)
# ---------------------------------------
def init_db(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    # Cria tabela exatamente com o layout do arquivo + coluna 'vessel'
    cur.execute("""
    CREATE TABLE IF NOT EXISTS lighthouse_attributes (
        vessel TEXT,
        id TEXT,
        name TEXT,
        template_name TEXT,
        type TEXT,
        id_attribute TEXT,
        name_attribute TEXT,
        value TEXT,
        specification TEXT,
        reference TEXT,
        category TEXT,
        is_leaf INTEGER,
        parent_id TEXT
    );
    """)

    conn.commit()


# ---------------------------------------
#   BUSCAR ROOT PELO NOME (SEARCH_TERM)
# ---------------------------------------
def find_root_candidates(search_term: str):
    """
    Procura itens cujo nome contenha search_term na árvore inteira.
    Retorna lista [(id, name)].
    """
    items = ws.get_items(traverse=True)
    candidates = [
        (iid, name) for iid, name in items.items()
        if search_term.lower() in name.lower()
    ]

    if not candidates:
        print(f"[ERRO] Nenhum item encontrado contendo '{search_term}'")

    return candidates


def choose_root_interactively(candidates):
    """
    Exibe a lista de candidatos e deixa você escolher pelo índice.
    Retorna o id do item escolhido.
    """
    print("\n=== CANDIDATOS ENCONTRADOS ===")
    for i, (iid, name) in enumerate(candidates):
        print(f"[{i}] {name} -> {iid}")

    while True:
        try:
            idx = int(input("\nSelecione o índice desejado: "))
            if 0 <= idx < len(candidates):
                chosen_id, chosen_name = candidates[idx]
                print(f"\n[INFO] Root selecionado: {chosen_name} ({chosen_id})")
                return chosen_id
            print("Índice inválido, tente novamente.")
        except ValueError:
            print("Entrada inválida, digite um número inteiro.")


# ---------------------------------------
#   TRAVERSAL DA ÁRVORE (MESMO LAYOUT DO EXCEL)
# ---------------------------------------
def traverse_nodes(root_id, level=0, parent_id=None):
    """
    Retorna uma lista de linhas com a estrutura:

    [id, name, template_name, type,
     id_attribute, name_attribute,
     value, specification, reference,
     category, is_leaf, parent_id]
    """
    response = ws.get_subitems(root_id, traverse=False)

    if not isinstance(response, dict) or "subitems" not in response:
        print(f"[ERRO] Resposta inesperada do get_subitems({root_id}):")
        print(response)
        return []

    subitems = response["subitems"]
    print(f"[DEBUG] Level {level} | root={root_id} | subitems={len(subitems)}")

    tree = []

    for subitem in tqdm(subitems, desc=f"Level {level} - Subitems", leave=True):
        # Metadados do item
        item_metadata = ws.get(f"{ws.root_url}/items/{subitem['id']}")
        subitem["template_name"] = item_metadata["template"]["name"]

        # Atributos
        attributes = ws.get_item_attributes(subitem["id"])["attributes"]

        # Generators (modelos)
        generators = ws.get_item_generators(subitem["id"])

        is_leaf = not subitem["has_subitems"]

        # --- GENERATORS ---
        for generator in generators["generators"]:
            tree.append([
                subitem["id"],              # id (item_id)
                subitem["name"],            # name (nome do asset)
                subitem["template_name"],   # template_name
                "generator",                # type
                generator["id"],            # id_attribute
                generator["name"],          # name_attribute
                generator["label"],         # value
                generator["type"],          # specification (ex.: PreBuilt / External)
                "",                         # reference
                generator.get("category", ""),  # category
                is_leaf,                    # is_leaf
                parent_id                   # parent_id
            ])

        # --- ATTRIBUTES ---
        for attribute in attributes:
            category = ""
            if attribute.get("categories") and len(attribute["categories"]):
                category = attribute["categories"][0]["name"]

            tree.append([
                subitem["id"],                 # id (item_id)
                subitem["name"],               # name (nome do asset)
                subitem["template_name"],      # template_name
                "attribute",                   # type
                attribute["id"],               # id_attribute
                attribute["name"],             # name_attribute
                attribute["value"],            # value
                f'{attribute["data_source"]}_{attribute["data_type"]}',  # specification
                attribute.get("reference", ""),  # reference
                category,                      # category
                is_leaf,                       # is_leaf
                parent_id                      # parent_id
            ])

        # Se tiver filhos, desce recursivamente
        if subitem["has_subitems"]:
            tree.extend(traverse_nodes(subitem["id"], level + 1, subitem["id"]))

    return tree


# ---------------------------------------
#   SALVAR NO BANCO (ÚNICA TABELA + VESSEL)
# ---------------------------------------
def save_to_sqlite(rows, vessel_name: str) -> None:
    """
    rows vem no formato:
    [id, name, template_name, type,
     id_attribute, name_attribute,
     value, specification, reference,
     category, is_leaf, parent_id]

    vessel_name é o valor que será gravado na coluna 'vessel'
    (mesmo texto do SEARCH_TERM).
    """
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    cur = conn.cursor()

    # 1) Apaga apenas os dados do vessel atual
    cur.execute(
        "DELETE FROM lighthouse_attributes WHERE vessel = ?",
        (vessel_name,),
    )

    # 2) Insere as linhas novas para esse vessel
    for row in rows:
        (
            item_id,
            item_name,
            template_name,
            row_type,  # "attribute" ou "generator"
            obj_id,
            obj_name,
            value,
            specification,
            reference,
            category,
            is_leaf,
            parent_id,
        ) = row

        cur.execute(
            """
            INSERT INTO lighthouse_attributes (
                vessel,
                id, name, template_name, type,
                id_attribute, name_attribute,
                value, specification, reference,
                category, is_leaf, parent_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                vessel_name,
                item_id,
                item_name,
                template_name,
                row_type,
                obj_id,
                obj_name,
                value,
                specification,
                reference,
                category,
                int(bool(is_leaf)),
                parent_id,
            ),
        )

    conn.commit()
    conn.close()


# ---------------------------------------
#   MAIN
# ---------------------------------------
def main():
    # 1) Localiza candidatos pelo SEARCH_TERM
    candidates = find_root_candidates(SEARCH_TERM)
    if not candidates:
        return

    # 2) Escolhe interativamente qual item usar como root
    root_id = choose_root_interactively(candidates)

    # 3) Percorre a árvore a partir do root escolhido
    rows = traverse_nodes(root_id)
    print(f"\nTotal de linhas retornadas: {len(rows)}")

    if not rows:
        print("Nenhum dado retornado. Verifique se esse root_id possui subitems.")
        return

    # 4) Salva tudo no SQLite, com a coluna 'vessel' = SEARCH_TERM
    save_to_sqlite(rows, SEARCH_TERM)
    print(f"\n[OK] Dados de {SEARCH_TERM} salvos/atualizados em {DB_PATH}")


if __name__ == "__main__":
    main()