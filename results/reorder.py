import json
import sys
import os

if len(sys.argv) < 2:
    print("Uso: python script.py caminho/para/arquivo.json")
    sys.exit(1)

caminho_arquivo = sys.argv[1]

nome_base, extensao = os.path.splitext(caminho_arquivo)
caminho_saida = f"{nome_base}_atualizado{extensao}"

with open(caminho_arquivo, 'r', encoding='utf-8') as f:
    questoes = json.load(f)

for q in questoes:
    if q['index'] >= 157:
        q['index'] += 1

with open(caminho_saida, 'w', encoding='utf-8') as f:
    json.dump(questoes, f, ensure_ascii=False, indent=2)

print(f"Índices atualizados com sucesso. Arquivo salvo em: {caminho_saida}")
