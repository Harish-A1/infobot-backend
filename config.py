from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import os

# Always find .env relative to this file, not the working directory
ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_key: str = ""

    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8")

@lru_cache()
def get_settings():
    return Settings()