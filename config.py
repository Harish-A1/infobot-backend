from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import os

ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_service_key: str = ""  # service role key — bypasses RLS for backend writes/deletes
    groq_api_key: str = ""
    gemini_api_key: str = ""  # optional — Groq is fallback when not set

    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8")

@lru_cache()
def get_settings() -> Settings:
    s = Settings()
    missing = [k for k, v in {
        "SUPABASE_URL": s.supabase_url,
        "SUPABASE_KEY": s.supabase_key,
        "GROQ_API_KEY": s.groq_api_key,
    }.items() if not v]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    return s
