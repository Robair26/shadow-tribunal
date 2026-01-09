import httpx

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
DEFAULT_MODEL = "llama3.2:3b"

SYSTEM_GUARDRAILS = (
    "You are Shadow Tribunal, a psychological analysis experience.\n"
    "Stay grounded in psychology and behavior patterns.\n"
    "Do NOT mention anything spiritual, occult, demons, prophecy, or religion.\n"
    "Do NOT provide medical/clinical diagnosis or therapy.\n"
    "Do NOT produce threats, self-harm content, or illegal instructions.\n"
    "Tone: eerie-but-professional, minimalist, calm.\n"
)

def ollama_generate(prompt: str, model: str = DEFAULT_MODEL, timeout_s: int = 180) -> str:
    full_prompt = SYSTEM_GUARDRAILS + "\n\n" + prompt

    payload = {
        "model": model,
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "top_p": 0.9,
            "num_predict": 700,
        },
    }

    with httpx.Client(timeout=timeout_s) as client:
        r = client.post(OLLAMA_URL, json=payload)
        r.raise_for_status()
        data = r.json()
        return (data.get("response") or "").strip()

