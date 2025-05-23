pyenv versions
pyenv local 3.11.9
poetry env use 3.11.9

sudo /home/ulian/Desktop/LLMRasp-5/Prototype/.venv/bin/python src/main.py

poetry run uvicorn src.llm_api:app --reload

curl -X POST http://localhost:8000/ask \
 -H "Content-Type: application/json" \
 -d '{"text": "Fale quanto é 5+5", "pre-prompt": "Be clear, serious, and answer fast: ", "model": "qwen3:4b"}'
