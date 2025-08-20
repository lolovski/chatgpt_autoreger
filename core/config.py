from typing import Optional

from pydantic import EmailStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    token: str
    telegram_id: str
    bot_token: str
    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()