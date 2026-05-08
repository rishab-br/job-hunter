from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Anthropic
    anthropic_api_key: str
    claude_model: str = "claude-sonnet-4-6"

    # GitHub
    github_token: str
    github_username: str = ""

    # Job platforms
    linkedin_email: str = ""
    linkedin_password: str = ""
    indeed_email: str = ""
    indeed_password: str = ""

    # Target profile
    target_role: str = ""
    target_market: str = ""
    target_niche: str = ""

    # App behaviour
    human_approval_required: bool = True


settings = Settings()
