import json
import anthropic
from config import settings

_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


def call(system: str, user: str, max_tokens: int = 2048) -> str:
    response = get_client().messages.create(
        model=settings.claude_model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return response.content[0].text


def call_json(system: str, user: str, max_tokens: int = 2048) -> dict | list:
    raw = call(system, user + "\n\nRespond with valid JSON only. No markdown, no explanation.", max_tokens)
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]
    return json.loads(raw.strip())
