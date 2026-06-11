from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Gemini
    gemini_api_key: str
    gemini_model: str = "gemini-2.5-flash"

    # Groq (fallback when Gemini is unavailable)
    groq_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("GROQ_API_KEY_1", "GROQ_API_KEY"),
    )

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

    # Notifications (autopilot digests)
    # Email — primary channel. For Gmail: smtp.gmail.com + an App Password
    # (Google Account → Security → 2-Step Verification → App passwords).
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    digest_email_to: str = ""   # defaults to smtp_username when empty

    # Telegram — optional secondary channel
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # App behaviour
    human_approval_required: bool = True


settings = Settings()
