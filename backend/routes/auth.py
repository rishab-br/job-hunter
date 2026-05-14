"""
GitHub OAuth endpoints.

Flow:
  1. User clicks "Connect GitHub" → GET /auth/github
  2. GitHub OAuth consent page shows
  3. User approves → GitHub calls GET /auth/callback?code=...
  4. We exchange code for token, fetch username/avatar, upsert in Supabase
  5. Redirect to frontend with user_id + username + avatar in URL params
  6. Frontend stores in localStorage, UI updates to show logged-in state

Scopes requested: public_repo, read:user  (no private repo access)
"""
import httpx
from fastapi import APIRouter
from fastapi.responses import RedirectResponse, JSONResponse
from config.settings import settings

router = APIRouter(tags=["auth"])

_GH_AUTHORIZE = "https://github.com/login/oauth/authorize"
_GH_TOKEN     = "https://github.com/login/oauth/access_token"
_GH_API       = "https://api.github.com"


@router.get("/auth/github")
async def github_login():
    if not settings.github_client_id:
        return JSONResponse(
            {"error": "GitHub OAuth not configured — set GITHUB_CLIENT_ID in .env"},
            status_code=503,
        )
    params = (
        f"client_id={settings.github_client_id}"
        f"&scope=public_repo+read:user"
    )
    return RedirectResponse(f"{_GH_AUTHORIZE}?{params}")


@router.get("/auth/callback")
async def github_callback(code: str):
    # 1. Exchange code for access token
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            _GH_TOKEN,
            headers={"Accept": "application/json"},
            data={
                "client_id":     settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code":          code,
            },
        )
    token_data = token_resp.json()
    access_token = token_data.get("access_token")

    if not access_token:
        return JSONResponse(
            {"error": "GitHub OAuth failed", "detail": token_data},
            status_code=400,
        )

    # 2. Fetch GitHub user info
    async with httpx.AsyncClient() as client:
        user_resp = await client.get(
            f"{_GH_API}/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept":        "application/vnd.github+json",
            },
        )
    gh_user    = user_resp.json()
    username   = gh_user.get("login", "")
    avatar_url = gh_user.get("avatar_url", "")

    # 3. Upsert user in Supabase
    from backend.supabase_client import get_supabase
    sb = get_supabase()
    if sb is None:
        return JSONResponse(
            {"error": "Supabase not configured — set SUPABASE_URL + SUPABASE_KEY in .env"},
            status_code=503,
        )

    result = sb.table("users").upsert(
        {
            "github_username": username,
            "github_token":    access_token,
            "avatar_url":      avatar_url,
        },
        on_conflict="github_username",
    ).execute()

    user_id = result.data[0]["id"]

    # 4. Redirect to frontend — JS picks up URL params
    return RedirectResponse(
        f"/?user_id={user_id}&username={username}&avatar={avatar_url}"
    )
