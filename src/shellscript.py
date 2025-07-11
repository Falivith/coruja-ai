import subprocess

model = "gemma3:1b"

prompt_file = "prompts.txt"

output_file = "resultados_verbose.txt"

with open(prompt_file, "r", encoding="utf-8") as f:
    prompts = [line.strip() for line in f if line.strip()]

with open(output_file, "w", encoding="utf-8") as out:
    for idx, prompt in enumerate(prompts, 1):
        print(f"Executando prompt {idx}/{len(prompts)}...")

        command = ["ollama", "run", model, "--verbose"]

        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        try:
            output, _ = process.communicate(input=prompt, timeout=120)

            out.write(f"==== PROMPT {idx} ====\n")
            out.write(prompt + "\n")
            out.write("==== OUTPUT ====\n")
            out.write(output + "\n\n")

        except subprocess.TimeoutExpired:
            process.kill()
            out.write(f"==== PROMPT {idx} ====\n")
            out.write(prompt + "\n")
            out.write("==== OUTPUT ====\n")
            out.write("Erro: execução excedeu o tempo limite\n\n")

print("Finalizado. Resultados salvos em", output_file)
