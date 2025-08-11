from fastapi import FastAPI
from pydantic import BaseModel
import requests

app = FastAPI()

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gemma3:1b"
#MODEL = "gemma3n:e2b"

class Prompt(BaseModel):
    text: str
    pre_prompt: str = ""
    remove_think_tags: bool = True

@app.post("/ask")
def ask(prompt: Prompt):
    full_prompt = f"[INSTRUÇÃO]\n{prompt.pre_prompt.strip()}\n\n[PERGUNTA]\n{prompt.text.strip()}"


    payload = {
        "model": MODEL_NAME,
        "prompt": full_prompt,
        "stream": False
    }

    response = requests.post(OLLAMA_URL, json=payload)
    result = response.json()["response"]

    if prompt.remove_think_tags:
        import re
        result = re.sub(r"<think>.*?</think>", "", result, flags=re.DOTALL).strip()

    return {"response": result}
