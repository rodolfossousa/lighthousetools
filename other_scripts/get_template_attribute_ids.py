"""
NOTA:

- Este script é para exportar os atributos das templates para um arquivo CSV, que será usado posteriormente para deletar os atributos indesejados.
- Ele filtra os atributos que possuem "Manual" na coluna "data_source", pois esses são os que queremos deletar.
- O arquivo CSV gerado tem o nome "template_attributes.csv" e é salvo no mesmo diretório do script. Ele contém os atributos que serão deletados,
e deve ser revisado antes de rodar o script de deleção para garantir que apenas os atributos indesejados estão listados.




!!!!!!  NOTA MUITO IMPORTANTE  !!!!!!
- Dado que os atributos que serão recadastrados podem estar em múltiplos arquivos de dicionários de dados, VEJAM COM MUITA ATENÇÃO o CSV para
remover aqueles atributos que podem estar em outros dicionários "perdidos"

Exemplo: Atributos como Dias de Operação, Status, Tag SAP, Tag Oil Analysis etc são geralmente cadastrados usando outros dicionários de dados,
e não devem ser deletados. 





"""

from lighthouse import connect
import pandas as pd

client_name = "prio"
environment = "prod"
templates_to_use = ['Electric Generator for GE LM2500 PLUS', 'Gas Turbine GE LM2500 PLUS', 'Electric Generator', 'Gas Turbine GE LM2500']



ws = connect(client_name, environment, debug=False)


# get all templates
templates = ws.get_templates()
templates = {k: v for k, v in templates.items() if v in templates_to_use}

# Get all template_attributes
all_template_attributes = pd.DataFrame()

for template_id in templates:
    template_attributes = ws.get_template_attributes(template_id)['attributes']
    template_attributes = pd.DataFrame(template_attributes)    
    # add template name column
    template_attributes['template_name'] = templates[template_id]
    all_template_attributes = pd.concat([all_template_attributes, template_attributes], ignore_index=True)

# remove rows where data_source has "Manual" substring
all_template_attributes = all_template_attributes[~all_template_attributes['data_source'].str.contains('Manual')]

# save to csv
all_template_attributes.to_csv('template_attributes.csv', index=False, encoding='utf-8-sig', sep=';')
