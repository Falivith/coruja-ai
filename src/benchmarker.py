import time
import psutil
import requests
import json
from datasets import load_dataset
from threading import Thread

# Configuração
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "gemma3n:e2b"
OLLAMA_PROCESS_NAME = "ollama"

ds = load_dataset("maritaca-ai/enem", "2024")
questoes = ds['train']

def get_ollama_process():
    for proc in psutil.process_iter(['pid', 'name']):
        if OLLAMA_PROCESS_NAME in proc.info['name']:
            return psutil.Process(proc.info['pid'])
    raise RuntimeError("Processo do Ollama não encontrado")

def monitor_memory(process, mem_log):
    while process.is_running():
        try:
            mem = process.memory_info().rss / (1024 * 1024)  # em MB
            mem_log.append(mem)
            time.sleep(0.1)
        except psutil.NoSuchProcess:
            break

def perguntar_ollama(prompt):
    try:
        process = get_ollama_process()
    except RuntimeError as e:
        print(e)
        return "", 0, 0

    mem_log = []
    monitor_thread = Thread(target=monitor_memory, args=(process, mem_log))
    monitor_thread.daemon = True
    monitor_thread.start()

    inicio = time.time()
    try:
        response = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False
        }, timeout=300)
        fim = time.time()
        tempo = fim - inicio
        resposta = response.json().get("response", "").strip()
    except Exception as e:
        print("Erro ao enviar requisição:", e)
        resposta = ""
        tempo = 0

    memoria_max = max(mem_log) if mem_log else 0
    return resposta, tempo, memoria_max

resultados = []
num_questoes = 3

for i in range(num_questoes):
    questao = questoes[i]
    texto = questao["question"]
    alternativas = questao.get("alternatives", [])
    descricao = questao.get("description", "")
    correta = questao.get("label", "")

    full_question = "Eu vou te passar uma questão de múltipla escolha.\n"
    if descricao:
        full_question += f"A seguinte descrição pode te ajudar: {descricao}\n\n"
    full_question += f"{texto}\n\n" + "\n".join([f"{chr(65 + i)}. {alt}" for i, alt in enumerate(alternativas)])
    full_question += "\n\nEscolha a alternativa correta."

    print(f"[{i+1}/{num_questoes}] Enviando questão...")
    resposta, tempo, memoria = perguntar_ollama(full_question)

    resultado = {
        "index": i,
        "pergunta": texto,
        "descricao": descricao,
        "alternativas": alternativas,
        "resposta_modelo": resposta,
        "resposta_correta": chr(65 + correta) if isinstance(correta, int) else "",
        "tempo_resposta_s": round(tempo, 2),
        "memoria_MB": round(memoria, 2)
    }

    resultados.append(resultado)

    with open("resultados_enem_ollama.json", "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)

print("Fim da execução.")
