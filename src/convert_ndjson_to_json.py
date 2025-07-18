import json
import argparse
import os

def load_ndjson(filename):
    data = []
    with open(filename, "r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                data.append(obj)
            except json.JSONDecodeError as e:
                print(f"Erro ao decodificar JSON na linha {line_number}: {e}")
    return data

def save_as_json_array(data, output_filename):
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Arquivo salvo como JSON válido em: {output_filename}")

def main():
    parser = argparse.ArgumentParser(description="Converter NDJSON para JSON válido (array de objetos).")
    parser.add_argument("input", help="Arquivo NDJSON de entrada")
    parser.add_argument("-o", "--output", help="Arquivo JSON de saída (opcional)")

    args = parser.parse_args()
    input_file = args.input
    output_file = args.output or os.path.splitext(input_file)[0] + "_convertido.json"

    if not os.path.isfile(input_file):
        print(f"Arquivo não encontrado: {input_file}")
        return

    print(f"Carregando dados de {input_file}...")
    data = load_ndjson(input_file)
    print(f"Convertendo {len(data)} registros...")

    save_as_json_array(data, output_file)

if __name__ == "__main__":
    main()
