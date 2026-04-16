import os

def _load_env_file():
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, value = line.partition('=')
                    os.environ.setdefault(key.strip(), value.strip())

_load_env_file()

_base = os.environ.get('SHAPE_DOCS_PATH')
if not _base:
    raise EnvironmentError(
        "Variável de ambiente 'SHAPE_DOCS_PATH' não definida. "
        "Copie o arquivo .env.example para .env e preencha o caminho base."
    )

def _p(*parts):
    return os.path.join(_base, *parts)


DICTIONARIES = {
    "prio": [
        {
            "spreadsheet": _p(r"11. PRIO - Expansion\3. Parametrização e Cadastros\Dicionário de Dados - PRIO Expansion V3 - GTG.xlsx"),
            "tabs": [
                "Attributos Items (Dicionario)",
            ],
        },
        # {
        #     "spreadsheet": _p(r"11. PRIO - Expansion\3. Parametrização e Cadastros\Dicionário de Dados - PRIO Expansion - Variaveis Calculadas.xlsx"),
        #     "tabs": [
        #         "Variaveis Calculadas 2",
        #     ],
        # },
        # {
        #     "spreadsheet": _p(r"11. PRIO - Expansion\3. Parametrização e Cadastros\Dicionário de Dados - PRIO Expansion - Health Score.xlsx"),
        #     "tabs": [
        #         "Health Score",
        #     ],
        # },
        # {
        #     "spreadsheet": _p(r"11. PRIO - Expansion\3. Parametrização e Cadastros\Dicionário de Dados - PRIO Expansion Compressors v0.xlsx"),
        #     "tabs": [
        #          "FRADE Dicionário LP_IP_HP Comp",
                #  "FRADE Dicio Flash Gas Compres",
                #  "FORTE Dicio Gas Booster Compres",
                #  "BRAVO Dicionário Ariel Compress",
                #  "FORTE Dicionário Main",
                #  "FORTE - Dicionário DGS N2",
        #     ],
        # },
        # {
        #     "spreadsheet": _p(r"11. PRIO - Expansion\3. Parametrização e Cadastros\Dicionário de Dados - PRIO Expansion - Bombas.xlsx"),
        #     "tabs": [
        #         "Dicionario Bombas",
        #     ],
        # },
        # {
        #     "spreadsheet": _p(r"11. PRIO - Expansion\3. Parametrização e Cadastros\Dicionário de Dados - PRIO Expansion - Trafos.xlsx"),
        #     "tabs": [
        #         "Dicionario_FORTE_Trafo_Def A",
        #     ],
        # },
        # {
        #     "spreadsheet": _p(r"11. PRIO - Expansion\3. Parametrização e Cadastros\Dicionário de Dados - PRIO Expansion CompressorAr.xlsx"),
        #     "tabs": [
        #         "Dicionário_CompressorAr",
        #     ],
        # },
        # {
        #     "spreadsheet": _p(r"11. PRIO - Expansion\3. Parametrização e Cadastros\Dicionário de Dados - PRIO Expansion - Tags CMMS.xlsx"),
        #     "tabs": [
        #         "Tag SAP",
        #     ],
        # },
        # {
        #     "spreadsheet": _p(r"11. PRIO - Expansion\3. Parametrização e Cadastros\Dicionário de Dados - PRIO Expansion - Sotreq.xlsx"),
        #     "tabs": [
        #         "Dicionario Sotreq",
        #     ],
        # },
        # {
        #     "spreadsheet": _p(r"11. PRIO - Expansion\3. Parametrização e Cadastros\Dicionário de Dados - PRIO Expansion - Trocadores de Calor V1.xlsx"),
        #     "tabs": [
        #         "Bravo Trocadores de Calor",
        #         "Forte Trocadores de Calor",
        #         "Frade Trocadores de Calor"
        #     ],
        # },
        # {"spreadsheet": _p(r"11. PRIO - Expansion\3. Parametrização e Cadastros\Dicionário de Dados - PRIO Expansion - Trocadores de Calor O2.xlsx"),
        # "tabs": [
        #     "BRAVO Trocadores de Calor O2",
        #     "Forte Trocadores de Calor O2",
        #     "Frade Trocadores de Calor O2"
        # ],
        # }
    ],
    "jirau": [
        {
            "spreadsheet": _p(r"04. Jirau\Dicionário de Dados\Dicionario de Dados SMARTUG.xlsx"),
            "tabs": [
                # "Motoventiladores",
                # "Sensores IFM",
                # "Sensores IFM_Limiares",
                # "dicionario_planta",
                # "Dicionario Unidades Geradoras",
                "Status"
            ],
        },
    ],
    "petroreconcavo": [
        {
            "spreadsheet": _p(r"13. Petroreconcavo\3. Parametrização e Cadastros\Dicionario_Find_Final_PetroReconcavo.xlsx"),
            "tabs": [
                # "Consolidado",
                "harmonizado_orig_Limp"
            ],
        },
    ],
}
