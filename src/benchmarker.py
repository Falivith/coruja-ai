import os
import re
import time
import json
import psutil
import subprocess
from threading import Thread
from datasets import load_dataset

# Constants and Regex
OLLAMA_URL = "http://localhost:11434/api/generate"
#MODEL = "gemma3:1b"
#MODEL = "gemma3n:e2b"
MODEL = "gemma3:4b"

OLLAMA_PROCESS_NAME = "ollama"
ANSI_ESCAPE = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
SPINNER_CHARS = re.compile(r'[⠋⠙⠸⠴⠦⠇⠏⠼⠹⠧]')

# Dataset loading
dataset = load_dataset("maritaca-ai/enem", "2022")
questions = dataset['train']

# Utility functions

# Useful for converting JSON (Enem 2022) to Maritaca modern format
def convert_to_maritaca_format(questions_detailed):
    maritaca_formatted = []
    for i, q in enumerate(questions_detailed):
        maritaca_formatted.append({
            "id": f"questao_{i+1:02d}",
            "exam": q["exam"],
            "question": f"[[placeholder]]\n{q['question']}",
            "alternatives": q["options"],
            "label": q["label"].upper(),  # 'a' → 'A'
            "figures": q.get("associated_images", []),
            "description": [q.get("context", "")],
            "IU": q.get("IU", False),
            "ledor": False
        })
    return maritaca_formatted

with open("data/2022.json", "r", encoding="utf-8") as f:
    questions_detailed = json.load(f)

enem_2022_questions = convert_to_maritaca_format(questions_detailed)

def remove_ansi(text):
    text = ANSI_ESCAPE.sub('', text)
    return SPINNER_CHARS.sub('', text)

def get_unique_filename(base_name, ext):
    counter = 0
    while True:
        filename = f"{base_name}{'' if counter == 0 else '_' + str(counter)}.{ext}"
        if not os.path.exists(filename):
            return filename
        counter += 1

def get_ollama_processes():
    return [psutil.Process(p.info['pid']) for p in psutil.process_iter(['pid', 'name']) if OLLAMA_PROCESS_NAME in p.info['name']]

def get_cpu_temperature():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            return int(f.read()) / 1000.0
    except:
        return None

def monitor_resources(processes, mem_log, temp_log, stop_flag):
    while all(p.is_running() for p in processes) and not stop_flag['stop']:
        try:
            mem_usage = sum(p.memory_info().rss for p in processes) / (1024 * 1024)
            mem_log.append(mem_usage)

            temp = get_cpu_temperature()
            if temp is not None:
                temp_log.append(temp)

            time.sleep(0.1)
        except psutil.NoSuchProcess:
            break

def extract_stats(text):
    pattern = re.compile(r"(total duration:.*eval rate:\s*[0-9.]+\s*tokens/s)", re.DOTALL)
    match = pattern.search(text)
    stats = {}
    clean_text = remove_ansi(text)

    if match:
        stats_block = match.group(1).strip()
        clean_text = clean_text.replace(stats_block, "").strip()

        patterns = {
            "total_duration_s": r"^total duration:\s+([\d.]+)s",
            "load_duration_ms": r"^load duration:\s+([\d.]+)ms",
            "prompt_eval_count": r"^prompt eval count:\s+(\d+)",
            "prompt_eval_duration_s": r"^prompt eval duration:\s+([\d.]+)ms",
            "prompt_eval_rate": r"^prompt eval rate:\s+([\d.]+)",
            "eval_count": r"^eval count:\s+(\d+)",
            "eval_duration_s": r"^eval duration:\s+([\d.]+)s",
            "eval_rate": r"^eval rate:\s+([\d.]+)"
        }


        for key, pat in patterns.items():
            match = re.search(pat, stats_block, re.MULTILINE)
            if match:
                value = match.group(1)
                stats[key] = float(value) if '.' in value else int(value)


    return clean_text, stats

def ask_ollama_verbose(prompt, max_retries=1, timeout=360):
    for attempt in range(max_retries + 1):
        print(f"Attempt {attempt + 1} of {max_retries + 1}...")
        processes = get_ollama_processes()
        if not processes:
            print("Ollama process not found")
            return "", 0, {}, 0, 0

        mem_log, temp_log = [], []
        stop_flag = {'stop': False}
        monitor = Thread(target=monitor_resources, args=(processes, mem_log, temp_log, stop_flag))
        monitor.daemon = True
        monitor.start()

        command = ["ollama", "run", MODEL, "--verbose"]
        start_time = time.time()

        try:
            proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            proc.stdin.write(prompt + "\n")
            proc.stdin.flush()
            proc.stdin.close()

            output = []
            while True:
                if time.time() - start_time > timeout:
                    print("\nTimeout reached. Terminating process...")
                    proc.kill()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.terminate()
                    break

                line = proc.stdout.readline()
                if line == '' and proc.poll() is not None:
                    break
                if line:
                    print(line, end="")
                    output.append(line)

            end_time = time.time()
            stop_flag['stop'] = True
            monitor.join()

            full_response = "".join(output)
            clean_text, stats = extract_stats(full_response)
            clean_text = remove_ansi(clean_text).strip()

            return clean_text, end_time - start_time, stats, max(mem_log, default=0), max(temp_log, default=0)

        except Exception as e:
            print(f"Error: {e}")
            stop_flag['stop'] = True
            monitor.join()

    return "", 0, {}, 0, 0

# Main benchmark loop
results = []
start_index = 157
end_index = 180
filename = get_unique_filename(f"ollama_benchmark_results_{MODEL}", "ndjson")

for i in range(start_index - 1, end_index):
    question = questions[i]
    #question = enem_2022_questions[i]  # Use the converted 2022 question format
    text = question["question"]
    choices = question.get("alternatives", [])
    description = question.get("description", "")
    correct_label = question.get("label", "")

    prompt = "Questão de Múltipla Escolha:\n"
    if description:
        prompt += f"Descrição para ajudar: {description}\n\n"
    prompt += f"{text}\n\n" + "\n".join([f"{chr(65 + j)}. {alt}" for j, alt in enumerate(choices)])
    prompt += "\nResponda com a alternativa correta.\n"

    print(f"[{i+1}/{end_index}] Sending question...")
    answer, elapsed, stats, max_mem, max_temp = ask_ollama_verbose(prompt)

    result = {
        "index": i + 1,
        "model_prompt": prompt,
        "model_response": answer,
        "label": correct_label,
        "response_time_s": round(elapsed, 2),
        "max_memory_MB": round(max_mem, 2),
        "max_temperature_C": round(max_temp, 2),
        **stats
    }

    print(f"Question result: {result}")
    results.append(result)

    with open(filename, "a", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")

    print(f"Saved to: {filename}")

print("Benchmark complete.")
