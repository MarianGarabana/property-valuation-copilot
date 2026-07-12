import importlib.util
import json
import os
import urllib.request

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
TEMPERATURE = 0.1


def _ollama_models():
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=2) as resp:
            return [m["name"] for m in json.load(resp).get("models", [])]
    except Exception:
        return []


def detect_backend():
    if os.environ.get("COPILOT_DISABLE_LLM") == "1":
        return None
    if _ollama_models():
        return "ollama"
    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") and importlib.util.find_spec("google.genai"):
        return "gemini"
    return None


def generate(prompt, backend):
    if backend == "ollama":
        return _ollama_generate(prompt)
    if backend == "gemini":
        return _gemini_generate(prompt)
    raise ValueError(f"unknown LLM backend {backend!r}")


def _ollama_generate(prompt):
    model = os.environ.get("OLLAMA_MODEL") or _ollama_models()[0]
    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": TEMPERATURE},
        }
    ).encode()
    request = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=180) as resp:
        return json.load(resp)["response"].strip()


def _gemini_generate(prompt):
    from google import genai
    from google.genai import types

    client = genai.Client(
        vertexai=True,
        project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
        location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
    )
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=TEMPERATURE, max_output_tokens=1024),
    )
    return response.text.strip()
