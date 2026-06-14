from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    telegram_bot_token: str
    allowed_user_ids: list[int] = Field(default_factory=list)
    anthropic_api_key: str
    anthropic_model: str = "claude-sonnet-4-6"
    hf_token: str
    log_level: str = "INFO"
    max_order_length: int = 10000


settings = Settings()
