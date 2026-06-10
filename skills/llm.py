import json
import logging
from google import genai
from google.genai import types
from config import settings

log = logging.getLogger(__name__)

_gemini_client: genai.Client | None = None
_groq_client = None

GROQ_MODEL = "llama-3.3-70b-versatile"


def get_gemini() -> genai.Client:
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=settings.gemini_api_key)
    return _gemini_client


def get_groq():
    global _groq_client
    if _groq_client is None:
        from groq import Groq
        _groq_client = Groq(api_key=settings.groq_api_key)
    return _groq_client


def _groq_available() -> bool:
    return bool(getattr(settings, "groq_api_key", ""))


def _gemini_available() -> bool:
    return bool(getattr(settings, "gemini_api_key", ""))


# ── Plain text call ───────────────────────────────────────────────────────────

def call(system: str, user: str, max_tokens: int = 2048) -> str:
    # Primary: Groq
    if _groq_available():
        try:
            resp = get_groq().chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content
        except Exception as e:
            log.warning(f"Groq text call failed: {e}. Falling back to Gemini.")

    # Fallback: Gemini
    response = get_gemini().models.generate_content(
        model=settings.gemini_model,
        contents=user,
        config=types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max_tokens,
        ),
    )
    return response.text


# ── JSON call ─────────────────────────────────────────────────────────────────

def call_json(system: str, user: str, max_tokens: int = 4096) -> dict | list:
    # Primary: Groq — plain text mode so it can return both dicts AND lists
    if _groq_available():
        try:
            resp = get_groq().chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user + "\n\nRespond with valid JSON only. No markdown fences, no explanation."},
                ],
                max_tokens=max_tokens,
            )
            raw = resp.choices[0].message.content.strip()
            # Strip markdown code fences if model added them
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1]
                raw = raw.rsplit("```", 1)[0]
            return json.loads(raw.strip())
        except Exception as e:
            log.warning(f"Groq JSON call failed: {e}. Falling back to Gemini.")

    # Fallback: Gemini with JSON mime type
    try:
        response = get_gemini().models.generate_content(
            model=settings.gemini_model,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=max_tokens,
                response_mime_type="application/json",
            ),
        )
        return json.loads(response.text)
    except json.JSONDecodeError as e:
        log.error(f"Gemini returned invalid JSON: {e}")
        raise


# ── Embeddings ────────────────────────────────────────────────────────────────

EMBED_MODEL = "gemini-embedding-001"
_EMBED_BATCH = 100   # Gemini embed_content limit per request


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed texts with Gemini's embedding model. Raises on failure —
    callers decide whether to degrade (e.g. scorer falls back to full LLM pass)."""
    vectors: list[list[float]] = []
    client = get_gemini()
    for i in range(0, len(texts), _EMBED_BATCH):
        batch = texts[i : i + _EMBED_BATCH]
        resp = client.models.embed_content(model=EMBED_MODEL, contents=batch)
        vectors.extend(e.values for e in resp.embeddings)
    return vectors


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
