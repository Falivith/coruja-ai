from fastapi import FastAPI
from pydantic import BaseModel
import requests

app = FastAPI()

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen3:4b"

class Prompt(BaseModel):
    text: str
    pre_prompt: str = ""
    remove_think_tags: bool = True

@app.post("/ask")
def ask(prompt: Prompt):
    full_prompt = f"{prompt.pre_prompt.strip()}\n{prompt.text.strip()}".strip()

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
