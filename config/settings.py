from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Gemini
    gemini_api_key: str
    gemini_model: str = "gemini-2.5-flash"

    # GitHub OAuth App (for multi-user frontend auth)
    github_client_id: str = ""
    github_client_secret: str = ""

    # GitHub PAT (CLI / dev fallback — not needed when OAuth is active)
    github_token: str = ""
    github_username: str = ""

    # Supabase (multi-user session storage)
    supabase_url: str = ""
    supabase_key: str = ""

    # Job platforms
    linkedin_email: str = ""
    linkedin_password: str = ""
    indeed_email: str = ""
    indeed_password: str = ""

    # Target profile defaults
    target_role: str = ""
    target_market: str = ""
    target_niche: str = ""

    # App behaviour
    human_approval_required: bool = True


settings = Settings()
