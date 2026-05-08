import json
from google import genai
from google.genai import types
from config import settings

_client: genai.Client | None = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def call(system: str, user: str, max_tokens: int = 2048) -> str:
    response = get_client().models.generate_content(
        model=settings.gemini_model,
        contents=user,
        config=types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max_tokens,
        ),
    )
    return response.text


def call_json(system: str, user: str, max_tokens: int = 2048) -> dict | list:
    raw = call(system, user + "\n\nRespond with valid JSON only. No markdown, no explanation.", max_tokens)
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]
    return json.loads(raw.strip())
