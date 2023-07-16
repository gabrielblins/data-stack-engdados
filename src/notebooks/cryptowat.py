import json, requests

# Caminho relativo para o arquivo JSON
path = 'data-stack-engdados/src/spark/assets/data/symbol_exchanges_dict.json'


with open(path, 'r') as json_file:
    symbol_exchanges_dict = json.load(json_file)


sumary_results = []

for exchange_name in symbol_exchanges_dict['btcbrl']:
    base_url = f"https://api.cryptowat.ch/markets/{exchange_name}/btcbrl/summary"
    response = requests.get(base_url)
    if response.status_code == 200:
        data = response.json()
        sumary_results.append(data)
    else:
        sumary_results.append(None)

print(sumary_results)
