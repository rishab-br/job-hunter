import httpx


async def search(query: str, num_results: int = 10) -> list[dict]:
    """
    Performs a web search and returns structured results.
    Uses a search API — configure endpoint in settings as needed.
    """
    # TODO: wire up to a search API (SerpAPI, Brave Search, etc.)
    raise NotImplementedError


async def fetch_page(url: str) -> str:
    """Fetches raw HTML content of a URL."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, headers={"User-Agent": "JobHunterBot/1.0"})
        response.raise_for_status()
        return response.text
