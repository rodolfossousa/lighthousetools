from lighthouse import connect

client_name = "prio"
environment = "prod"
ws = connect(client_name, environment, debug=False)

attribute_ids = []
with open("id_templates_del.txt", "r") as f:
    for line in f:
        line = line.strip()
        if line:
            attribute_ids.append(line)

print(f"Total de atributos para deletar: {len(attribute_ids)}")

success = 0
failed = 0

for i, attribute_id in enumerate(attribute_ids, 1):
    print(f"[{i}/{len(attribute_ids)}] Deletando atributo {attribute_id}...", end='\r')
    response = ws.delete_template_attribute(attribute_id)
    if response.status_code in [200, 204]:
        success += 1
        print(f"[{i}/{len(attribute_ids)}] OK - {attribute_id}                    ")
    else:
        failed += 1
        print(f"[{i}/{len(attribute_ids)}] FALHOU - {attribute_id} | Status: {response.status_code} | {response.text}")

print(f"\nFinalizado. Sucesso: {success} | Falhas: {failed}")
