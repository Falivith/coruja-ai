import os
import subprocess
import time
import psutil
import requests
import json
from datasets import load_dataset
from threading import Thread
import re

ANSI_ESCAPE = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
SPINNER_CHARS = re.compile(r'[⠋⠙⠸⠴⠦⠇⠏⠼⠹⠧]')

def remove_ansi_codes(text):
    text = ANSI_ESCAPE.sub('', text)
    text = SPINNER_CHARS.sub('', text)
    return text


# Configuração
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "gemma3n:e2b"
#MODEL = "gemma3:1b"
OLLAMA_PROCESS_NAME = "ollama"

ds = load_dataset("maritaca-ai/enem", "2024")
questoes = ds['train']

def extrair_stats(texto_completo):
    # Expressão regular para capturar o bloco de stats entre 'total duration:' e o último 'rate: ...tokens/s'
    pattern = re.compile(
        r"(total duration:.*?rate:\s*[0-9.]+\s*tokens/s)",
        re.DOTALL
    )
    match = pattern.search(texto_completo)

    stats_dict = {}

    if match:
        stats_text = match.group(1).strip()

        # Remove o trecho de stats do texto original
        texto_limpo = texto_completo.replace(stats_text, "").strip()

        # Expressões regulares individuais para cada campo
        patterns = {
            "total_duration_s": r"total duration:\s+([\d.]+)s",
            "load_duration_ms": r"load duration:\s+([\d.]+)ms",
            "prompt_eval_count": r"prompt eval count:\s+(\d+)",
            "prompt_eval_duration_s": r"prompt eval duration:\s+([\d.]+)s",
            "prompt_eval_rate": r"prompt eval rate:\s+([\d.]+)",
            "eval_count": r"eval count:\s+(\d+)",
            "eval_duration_s": r"eval duration:\s+([\d.]+)s",
            "eval_rate": r"eval rate:\s+([\d.]+)"
        }

        for key, pat in patterns.items():
            m = re.search(pat, stats_text)
            if m:
                val = m.group(1)
                stats_dict[key] = float(val) if '.' in val else int(val)
    else:
        texto_limpo = texto_completo.strip()

    return texto_limpo, stats_dict

def get_unique_filename(base_name, ext):
    counter = 0
    while True:
        filename = f"{base_name}{'' if counter == 0 else '_' + str(counter)}.{ext}"
        if not os.path.exists(filename):
            return filename
        counter += 1

filename = get_unique_filename("resultados_enem_ollama_verbose", "json")

def get_ollama_processes():
    return [psutil.Process(p.info['pid']) for p in psutil.process_iter(['pid', 'name']) if OLLAMA_PROCESS_NAME in p.info['name']]

def get_cpu_temperature():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp_str = f.read()
            return int(temp_str) / 1000.0
    except:
        return None

def monitor_memory_and_temp(processes, mem_log, temp_log, stop_flag):
    while all(p.is_running() for p in processes) and not stop_flag['stop']:
        try:
            mem_total = sum(p.memory_info().rss for p in processes) / (1024 * 1024)  # MB
            mem_log.append(mem_total)

            temp = get_cpu_temperature()
            if temp is not None:
                temp_log.append(temp)

            time.sleep(0.1)
        except psutil.NoSuchProcess:
            break

def perguntar_ollama_verbose(prompt, max_retries=1, timeout_s=360):
    for attempt in range(max_retries + 1):
        print(f"Tentativa {attempt + 1} de {max_retries + 1}...")
        processes = get_ollama_processes()
        if not processes:
            print("Processo do Ollama não encontrado")
            return "", 0, {}, 0, 0

        mem_log = []
        temp_log = []
        stop_flag = {'stop': False}

        monitor_thread = Thread(target=monitor_memory_and_temp, args=(processes, mem_log, temp_log, stop_flag))
        monitor_thread.daemon = True
        monitor_thread.start()

        command = ["ollama", "run", MODEL, "--verbose"]

        inicio = time.time()
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            process.stdin.write(prompt + "\n")
            process.stdin.flush()
            process.stdin.close()

            output_lines = []
            while True:
                if time.time() - inicio > timeout_s:
                    print(f"\nTimeout de {timeout_s}s atingido. Matando o processo...")
                    process.kill()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.terminate()
                    break

                line = process.stdout.readline()
                if line == '' and process.poll() is not None:
                    break
                if line:
                    print(line, end="")
                    output_lines.append(line)

            fim = time.time()
            tempo = fim - inicio

            stop_flag['stop'] = True
            monitor_thread.join()

            resposta_completa = "".join(output_lines)
            model_answer, stats = extrair_stats(resposta_completa)
            texto_limpo = remove_ansi_codes(model_answer).strip()

            return texto_limpo, tempo, stats, max(mem_log) if mem_log else 0, max(temp_log) if temp_log else 0

        except Exception as e:
            print(f"Erro inesperado: {e}")
            stop_flag['stop'] = True
            monitor_thread.join()
            continue

    return "", 0, {}, 0, 0
    
def perguntar_ollama(prompt):
    processes = get_ollama_processes()
    if not processes:
        print("Processo do Ollama não encontrado")
        return "", 0, 0, 0

    mem_log = []
    temp_log = []

    monitor_thread = Thread(target=monitor_memory_and_temp, args=(processes, mem_log, temp_log))
    monitor_thread.daemon = True
    monitor_thread.start()

    inicio = time.time()
    try:
        response = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "verbose": True,
            "keep_alive": -1
        }, timeout=300)
        fim = time.time()
        tempo = fim - inicio
        resposta = response.json().get("response", "").strip()
    except Exception as e:
        print("Erro ao enviar requisição:", e)
        resposta = ""
        tempo = 0

    memoria_max = max(mem_log) if mem_log else 0
    temp_max = max(temp_log) if temp_log else 0

    return resposta, tempo, memoria_max, temp_max

# Execução principal
resultados = []
inicio_questao = 173
num_questoes = 180

for i in range(inicio_questao, num_questoes):
    questao = questoes[i]
    texto = questao["question"]
    alternativas = questao.get("alternatives", [])
    descricao = questao.get("description", "")
    correta = questao.get("label", "")

    full_question = "Eu vou te passar uma questão de múltipla escolha.\n"
    if descricao:
        full_question += f"A seguinte descrição pode te ajudar: {descricao}\n\n"
    full_question += f"{texto}\n\n" + "\n".join([f"{chr(65 + i)}. {alt}" for i, alt in enumerate(alternativas)])
    full_question += "\nResponda somente a alternativa correta\n"

    print(f"[{i+1}/{num_questoes}] Enviando questão...")
    #resposta, tempo, memoria, temp = perguntar_ollama(full_question)
    resposta, tempo, stats, memoria, temp = perguntar_ollama_verbose(full_question)
    
    resultado = {
        "index": i+1,
        "pergunta_modelo": full_question,
        "resposta_modelo": resposta,
        "label": correta,
        "tempo_resposta_s": round(tempo, 2),
        "memoria_max_MB": round(memoria, 2),
        "temperatura_max_C": round(temp, 2),
        **stats
    }
    
    print(f"Resultado da questão {resultado}:")

    resultados.append(resultado)

    with open(filename, "a", encoding="utf-8") as f:
        json.dump([resultado], f, ensure_ascii=False, indent=2)
        f.write(",\n")  # evita sobrescrever resultados anteriores e mantém formato válido com cuidado
    
    print(f"Arquivo salvo em: {filename}")

print("Fim da execução.")
