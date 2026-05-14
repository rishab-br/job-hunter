from supabase import create_client, Client
from config.settings import settings

_client: Client | None = None


def get_supabase() -> Client | None:
    global _client
    if not settings.supabase_url or not settings.supabase_key:
        return None
    if _client is None:
        _client = create_client(settings.supabase_url, settings.supabase_key)
    return _client
