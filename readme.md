# LLMRasp Prototype — Interface de Voz com LLM via Ollama

Este é um protótipo desenvolvido como parte do Trabalho de Conclusão de Curso em Ciência da Computação, com o objetivo de permitir interações por voz com modelos de linguagem (LLMs), executando localmente com foco em uso offline em ambientes de infraestrutura limitada (como escolas em áreas remotas), utilizando um **Raspberry Pi**.

---

## 📦 Requisitos

- [Python](https://www.python.org/) 3.11.9 (gerenciado com [pyenv](https://github.com/pyenv/pyenv))
- [Poetry](https://python-poetry.org/)
- [Ollama](https://ollama.com/) instalado e rodando localmente
- Linux (desenvolvido e testado em ambiente Debian-based)

---

## 🚀 Configuração do Ambiente

### 1. Instale e selecione a versão correta do Python com `pyenv`:

```bash
pyenv install 3.11.9
pyenv local 3.11.9
```

# 2. Dependências, Ollama + Poetry
```bash
sudo apt update
sudo apt install libportaudio2 portaudio19-dev libportaudiocpp0 ffmpeg
curl -sSf https://ollama.com/install.sh | sh
poetry env use 3.11.9
poetry install
```

# 3. Execute os dois serviços
source .venv/bin/activate
sudo env "PATH=$PATH" poetry run python main.py 
poetry run uvicorn ollama_handler:app --reload

# 4. Testa API Handler Individualmente (ajustar PORT)
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Fale quanto é 5+5",
    "pre-prompt": "Be clear, serious, and answer fast: ",
    "model": "qwen3:4b"
  }'

## 4.1 Liberar Memória do Modelo (ajustar PORT ollama)
curl http://localhost:11434/api/generate \
  -d '{
    "model": "gemma3:1b",
    "keep_alive": 0
  }'

# Autor
Ulian Gabriel Alff Ramires - 2025
ugaramires@inf.ufpel.edu.br