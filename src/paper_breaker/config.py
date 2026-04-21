import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str
    llm_model_id: str
    llm_cheap_model_id: str
    supabase_url: str
    supabase_service_key: str
    supabase_publishable_key: str
    embedding_provider: str
    embedding_model: str
    embedding_dimensions: int
    host: str
    port: int
    default_user_id: str | None
    daily_trigger_secret: str


def _require(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise RuntimeError(
            f"Missing required env var: {name}. Copy .env.example to .env and fill it in."
        )
    return val


def load_settings() -> Settings:
    return Settings(
        anthropic_api_key=_require("ANTHROPIC_API_KEY"),
        llm_model_id=os.getenv("LLM_MODEL_ID", "anthropic:claude-sonnet-4-6"),
        llm_cheap_model_id=os.getenv(
            "LLM_CHEAP_MODEL_ID", "anthropic:claude-haiku-4-5-20251001"
        ),
        supabase_url=_require("SUPABASE_URL"),
        supabase_service_key=_require("SUPABASE_SERVICE_KEY"),
        supabase_publishable_key=os.getenv("SUPABASE_PUBLISHABLE_KEY", ""),
        embedding_provider=os.getenv("EMBEDDING_PROVIDER", "local"),
        embedding_model=os.getenv(
            "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
        ),
        embedding_dimensions=int(os.getenv("EMBEDDING_DIMENSIONS", "384")),
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8333")),
        default_user_id=os.getenv("DEFAULT_USER_ID") or None,
        daily_trigger_secret=os.getenv("DAILY_TRIGGER_SECRET", "change-me"),
    )
