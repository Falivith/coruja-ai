pyenv versions
pyenv local 3.11.9
poetry env use 3.11.9

sudo /home/ulian/Desktop/LLMRasp-5/Prototype/.venv/bin/python src/main.py

poetry run uvicorn src.llm_api:app --reload

curl -X POST http://localhost:8000/ask \
 -H "Content-Type: application/json" \
 -d '{"text": "Fale quanto é 5+5", "pre-prompt": "Be clear, serious, and answer fast: ", "model": "qwen3:4b"}'

# to remove model from memory

curl http://localhost:11434/api/generate -d '{"model": "gemma3:1b", "keep_alive": 0}'

"Qual a capital do Canadá?"

"Quantos segundos tem uma hora?"

"Me diga o nome de um compositor brasileiro famoso."

"Qual é a função da camada de transporte no modelo OSI?"

"Explique brevemente o que é inteligência artificial."
